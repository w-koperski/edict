#!/usr/bin/env python3
"""
Three Departments & Six Ministries · Skill Management Tool
Supports adding, updating, viewing, and removing skills from local or remote URLs

Usage:
  python3 scripts/skill_manager.py add-remote --agent zhongshu --name code_review \\
    --source https://raw.githubusercontent.com/org/skills/main/code_review/SKILL.md \\
    --description "code review"
  
  python3 scripts/skill_manager.py list-remote
  
  python3 scripts/skill_manager.py update-remote --agent zhongshu --name code_review
  
  python3 scripts/skill_manager.py remove-remote --agent zhongshu --name code_review
  
  python3 scripts/skill_manager.py import-official-hub --agents zhongshu,menxia,shangshu
"""
import sys
import json
import pathlib
import argparse
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import now_iso, safe_name, read_json

OCLAW_HOME = Path.home() / '.openclaw'


def _download_file(url: str, timeout: int = 30, retries: int = 3) -> str:
    """Download file content from URL (text format), supports retries"""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-SkillManager/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read(10 * 1024 * 1024)  # max 10MB
                return content.decode('utf-8')
        except urllib.error.HTTPError as e:
            last_error = f'HTTP {e.code}: {e.reason}'
            if e.code in (404, 403):
                break  # 不重试 4xx
        except urllib.error.URLError as e:
            last_error = f'Network error: {e.reason}'
        except Exception as e:
            last_error = f'{type(e).__name__}: {e}'
        
        if attempt < retries:
            import time
            wait = attempt * 3  # 3s, 6s
            print(f'   ⚠️ Attempt {attempt} failed ({last_error}), retrying in {wait}s...')
            time.sleep(wait)
    
    # All retries failed
    hint = ''
    if 'timed out' in str(last_error).lower():
        hint = '\n   💡 Hint: If in China, try setting a proxy: export https_proxy=http://proxy:port'
    elif '404' in str(last_error):
        hint = '\n   💡 Hint: The official Skills Hub may not have published this skill yet, check the URL'
    raise Exception(f'{last_error} (retried {retries} times){hint}')


def _compute_checksum(content: str) -> str:
    """Compute a simple checksum of the content"""
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def add_remote(agent_id: str, name: str, source_url: str, description: str = '') -> bool:
    """Add a skill to an Agent from a remote URL"""
    if not safe_name(agent_id) or not safe_name(name):
        print(f'❌ Error: agent_id or skill name contains invalid characters')
        return False
    
    # Set up workspace
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / name
    workspace.mkdir(parents=True, exist_ok=True)
    skill_md = workspace / 'SKILL.md'
    
    # Download file
    print(f'⏳ Downloading from {source_url}...')
    try:
        content = _download_file(source_url)
    except Exception as e:
        print(f'❌ Download failed: {e}')
        print(f'   URL: {source_url}')
        return False
    
    # Basic validation (relaxed: some skills don't start with ---)
    if len(content.strip()) < 10:
        print(f'❌ File content too short or empty')
        return False
    
    # Save SKILL.md
    skill_md.write_text(content)
    
    # Save source info
    source_info = {
        'skillName': name,
        'sourceUrl': source_url,
        'description': description,
        'addedAt': now_iso(),
        'lastUpdated': now_iso(),
        'checksum': _compute_checksum(content),
        'status': 'valid',
    }
    source_json = workspace / '.source.json'
    source_json.write_text(json.dumps(source_info, ensure_ascii=False, indent=2))
    
    print(f'✅ Skill {name} added to {agent_id}')
    print(f'   Path: {skill_md}')
    print(f'   Size: {len(content)} bytes')
    return True


def list_remote() -> bool:
    """List all added remote skills"""
    if not OCLAW_HOME.exists():
        print('❌ OCLAW_HOME does not exist')
        return False
    
    remote_skills = []
    
    for ws_dir in OCLAW_HOME.glob('workspace-*'):
        agent_id = ws_dir.name.replace('workspace-', '')
        skills_dir = ws_dir / 'skills'
        if not skills_dir.exists():
            continue
        
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            source_json = skill_dir / '.source.json'
            
            if not source_json.exists():
                continue
            
            try:
                source_info = json.loads(source_json.read_text())
                remote_skills.append({
                    'agent': agent_id,
                    'skill': skill_name,
                    'source': source_info.get('sourceUrl', 'N/A'),
                    'desc': source_info.get('description', ''),
                    'added': source_info.get('addedAt', 'N/A'),
                })
            except Exception:
                pass
    
    if not remote_skills:
        print('📭 No remote skills found')
        return True
    
    print(f'📋 {len(remote_skills)} remote skill(s):\n')
    print(f'{"Agent":<12} | {"Skill Name":<20} | {"Description":<30} | Added')
    print('-' * 100)
    
    for sk in remote_skills:
        desc = (sk['desc'] or sk['source'])[:30].ljust(30)
        print(f"{sk['agent']:<12} | {sk['skill']:<20} | {desc} | {sk['added'][:10]}")
    
    print()
    return True


def update_remote(agent_id: str, name: str) -> bool:
    """Update a remote skill to the latest version"""
    if not safe_name(agent_id) or not safe_name(name):
        print(f'❌ Error: agent_id or skill name contains invalid characters')
        return False
    
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / name
    source_json = workspace / '.source.json'
    
    if not source_json.exists():
        print(f'❌ Skill not found or not a remote skill: {name}')
        return False
    
    try:
        source_info = json.loads(source_json.read_text())
        source_url = source_info.get('sourceUrl')
        if not source_url:
            print(f'❌ Invalid source URL')
            return False
        
        # Re-download
        return add_remote(agent_id, name, source_url, source_info.get('description', ''))
    except Exception as e:
        print(f'❌ Update failed: {e}')
        return False


def remove_remote(agent_id: str, name: str) -> bool:
    """Remove a remote skill"""
    if not safe_name(agent_id) or not safe_name(name):
        print(f'❌ Error: agent_id or skill name contains invalid characters')
        return False
    
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / name
    source_json = workspace / '.source.json'
    
    if not source_json.exists():
        print(f'❌ Skill not found or not a remote skill: {name}')
        return False
    
    try:
        import shutil
        shutil.rmtree(workspace)
        print(f'✅ Skill {name} removed from {agent_id}')
        return True
    except Exception as e:
        print(f'❌ Remove failed: {e}')
        return False


OFFICIAL_SKILLS_HUB = {
    'code_review': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md',
    'api_design': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/api_design/SKILL.md',
    'security_audit': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/security_audit/SKILL.md',
    'data_analysis': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/data_analysis/SKILL.md',
    'doc_generation': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/doc_generation/SKILL.md',
    'test_framework': 'https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/test_framework/SKILL.md',
}

SKILL_AGENT_MAPPING = {
    'code_review': ('bingbu', 'xingbu', 'menxia'),
    'api_design': ('bingbu', 'gongbu', 'menxia'),
    'security_audit': ('xingbu', 'menxia'),
    'data_analysis': ('hubu', 'menxia'),
    'doc_generation': ('libu', 'menxia'),
    'test_framework': ('gongbu', 'xingbu', 'menxia'),
}


def import_official_hub(agent_ids: list) -> bool:
    """Import skills from the official Skills Hub to specified agents.
    If no agents specified, uses recommended agents for each skill.
    """
    if not agent_ids:
        print('❌ No agents specified, using recommended configuration...\n')
        for skill_name, recommended_agents in SKILL_AGENT_MAPPING.items():
            agent_ids.extend(recommended_agents)
        agent_ids = list(set(agent_ids))
    
    total = 0
    success = 0
    failed = []
    
    for skill_name, url in OFFICIAL_SKILLS_HUB.items():
        # 确定目标 agents
        target_agents = agent_ids
        if not agent_ids:
            target_agents = SKILL_AGENT_MAPPING.get(skill_name, ['menxia'])
        
        print(f'\n📥 Importing skill: {skill_name}')
        print(f'   Target agents: {", ".join(target_agents)}')
        
        for agent_id in target_agents:
            total += 1
            if add_remote(agent_id, skill_name, url, f'Official skill: {skill_name}'):
                success += 1
            else:
                failed.append(f'{agent_id}/{skill_name}')
    
    print(f'\n📊 Import complete: {success}/{total} skills succeeded')
    if failed:
        print(f'\n❌ Failed list:')
        for f in failed:
            print(f'   - {f}')
        print(f'\n💡 Troubleshooting:')
        print(f'   1. Check network: curl -I https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md')
        print(f'   2. Set proxy: export https_proxy=http://your-proxy:port')
        print(f'   3. Retry individually: python3 scripts/skill_manager.py add-remote --agent <agent> --name <skill> --source <url>')
    return success == total


def main():
    parser = argparse.ArgumentParser(description='Three Departments & Six Ministries Skill Management Tool', 
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='cmd', help='Command')
    
    # add-remote
    add_parser = subparsers.add_parser('add-remote', help='Add skill from remote URL')
    add_parser.add_argument('--agent', required=True, help='Target Agent ID')
    add_parser.add_argument('--name', required=True, help='Skill internal name')
    add_parser.add_argument('--source', required=True, help='Remote URL or local path')
    add_parser.add_argument('--description', default='', help='Skill description')
    
    # list-remote
    subparsers.add_parser('list-remote', help='List all remote skills')
    
    # update-remote
    update_parser = subparsers.add_parser('update-remote', help='Update remote skill')
    update_parser.add_argument('--agent', required=True, help='Agent ID')
    update_parser.add_argument('--name', required=True, help='Skill name')
    
    # remove-remote
    remove_parser = subparsers.add_parser('remove-remote', help='Remove remote skill')
    remove_parser.add_argument('--agent', required=True, help='Agent ID')
    remove_parser.add_argument('--name', required=True, help='Skill name')
    
    # import-official-hub
    import_parser = subparsers.add_parser('import-official-hub', help='Import skills from official hub')
    import_parser.add_argument('--agents', default='', help='Comma-separated Agent IDs (optional)')
    
    # check-updates
    check_parser = subparsers.add_parser('check-updates', help='Check for updates (future feature)')
    check_parser.add_argument('--interval', default='weekly', 
                             help='Check interval (weekly/daily/monthly)')
    
    args = parser.parse_args()
    
    if not args.cmd:
        parser.print_help()
        return
    
    if args.cmd == 'add-remote':
        success = add_remote(args.agent, args.name, args.source, args.description)
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'list-remote':
        success = list_remote()
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'update-remote':
        success = update_remote(args.agent, args.name)
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'remove-remote':
        success = remove_remote(args.agent, args.name)
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'import-official-hub':
        agent_list = [a.strip() for a in args.agents.split(',') if a.strip()] if args.agents else []
        success = import_official_hub(agent_list)
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'check-updates':
        print(f'⏳ Check updates feature (interval: {args.interval}) not yet implemented')
        print(f'   Coming soon...')


if __name__ == '__main__':
    main()
