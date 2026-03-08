#!/usr/bin/env python3
"""
Three Departments & Six Ministries · Dashboard Local API Server
Port: 7891 (override with --port)

Endpoints:
  GET  /                       → dashboard.html
  GET  /api/live-status        → data/live_status.json
  GET  /api/agent-config       → data/agent_config.json
  POST /api/set-model          → {agentId, model}
  GET  /api/model-change-log   → data/model_change_log.json
  GET  /api/last-result        → data/last_model_change_result.json
"""
import json, pathlib, subprocess, sys, threading, argparse, datetime, logging, re, os, shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Import file-lock utilities for concurrency safety with other scripts
scripts_dir = str(pathlib.Path(__file__).parent.parent / 'scripts')
sys.path.insert(0, scripts_dir)
from file_lock import atomic_json_read, atomic_json_write, atomic_json_update
from utils import validate_url

log = logging.getLogger('server')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

OCLAW_HOME = pathlib.Path.home() / '.openclaw'
MAX_REQUEST_BODY = 1 * 1024 * 1024  # 1 MB
ALLOWED_ORIGIN = None  # Set via --cors; None means restrict to localhost
_DEFAULT_ORIGINS = {
    'http://127.0.0.1:7891', 'http://localhost:7891',
    'http://127.0.0.1:5173', 'http://localhost:5173',  # Vite dev server
}
_SAFE_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$')

BASE = pathlib.Path(__file__).parent
DIST = BASE / 'dist'          # React build output (npm run build)
DATA = BASE.parent / "data"
SCRIPTS = BASE.parent / 'scripts'

# Static asset MIME types
_MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
    '.svg':  'image/svg+xml',
    '.ico':  'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf':  'font/ttf',
    '.map':  'application/json',
}


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default if default is not None else {}


def cors_headers(h):
    req_origin = h.headers.get('Origin', '')
    if ALLOWED_ORIGIN:
        origin = ALLOWED_ORIGIN
    elif req_origin in _DEFAULT_ORIGINS:
        origin = req_origin
    else:
        origin = 'http://127.0.0.1:7891'
    h.send_header('Access-Control-Allow-Origin', origin)
    h.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    h.send_header('Access-Control-Allow-Headers', 'Content-Type')


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def load_tasks():
    return atomic_json_read(DATA / 'tasks_source.json', [])


def save_tasks(tasks):
    atomic_json_write(DATA / 'tasks_source.json', tasks)
    # Trigger refresh (async, non-blocking, avoid zombie processes)
    def _refresh():
        try:
            subprocess.run(['python3', str(SCRIPTS / 'refresh_live_data.py')], timeout=30)
        except Exception as e:
            log.warning(f'refresh_live_data.py trigger failed: {e}')
    threading.Thread(target=_refresh, daemon=True).start()


def handle_task_action(task_id, action, reason):
    """Stop/cancel/resume a task from the dashboard."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}

    old_state = task.get('state', '')
    _ensure_scheduler(task)
    _scheduler_snapshot(task, f'task-action-before-{action}')

    if action == 'stop':
        task['state'] = 'Blocked'
        task['block'] = reason or 'Stopped by Emperor'
        task['now'] = f'⏸️ Paused: {reason}'
    elif action == 'cancel':
        task['state'] = 'Cancelled'
        task['block'] = reason or 'Cancelled by Emperor'
        task['now'] = f'🚫 Cancelled: {reason}'
    elif action == 'resume':
        # Resume to previous active state or Doing
        task['state'] = task.get('_prev_state', 'Doing')
        task['block'] = 'none'
        task['now'] = '▶️ Resumed'

    if action in ('stop', 'cancel'):
        task['_prev_state'] = old_state  # Save for resume

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': 'Emperor',
        'to': task.get('org', ''),
        'remark': f'{"⏸️ Stopped" if action == "stop" else "🚫 Cancelled" if action == "cancel" else "▶️ Resumed"}: {reason}'
    })

    if action == 'resume':
        _scheduler_mark_progress(task, f'Resumed to {task.get("state", "Doing")}')
    else:
        _scheduler_add_flow(task, f'Emperor {action}: {reason or "none"}')

    task['updatedAt'] = now_iso()

    save_tasks(tasks)
    if action == 'resume' and task.get('state') not in _TERMINAL_STATES:
        dispatch_for_state(task_id, task, task.get('state'), trigger='resume')
    label = {'stop': 'stopped', 'cancel': 'cancelled', 'resume': 'resumed'}[action]
    return {'ok': True, 'message': f'{task_id} {label}'}


def handle_archive_task(task_id, archived, archive_all_done=False):
    """Archive or unarchive a task, or batch-archive all Done/Cancelled tasks."""
    tasks = load_tasks()
    if archive_all_done:
        count = 0
        for t in tasks:
            if t.get('state') in ('Done', 'Cancelled') and not t.get('archived'):
                t['archived'] = True
                t['archivedAt'] = now_iso()
                count += 1
        save_tasks(tasks)
        return {'ok': True, 'message': f'{count} edicts archived', 'count': count}
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    task['archived'] = archived
    if archived:
        task['archivedAt'] = now_iso()
    else:
        task.pop('archivedAt', None)
    task['updatedAt'] = now_iso()
    save_tasks(tasks)
    label = 'archived' if archived else 'unarchived'
    return {'ok': True, 'message': f'{task_id} {label}'}


def update_task_todos(task_id, todos):
    """Update the todos list for a task."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}

    task['todos'] = todos
    task['updatedAt'] = now_iso()
    save_tasks(tasks)
    return {'ok': True, 'message': f'{task_id} todos updated'}


def read_skill_content(agent_id, skill_name):
    """Read SKILL.md content for a specific skill."""
    # Input validation: prevent path traversal
    if not _SAFE_NAME_RE.match(agent_id) or not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': 'Parameters contain invalid characters'}
    cfg = read_json(DATA / 'agent_config.json', {})
    agents = cfg.get('agents', [])
    ag = next((a for a in agents if a.get('id') == agent_id), None)
    if not ag:
        return {'ok': False, 'error': f'Agent {agent_id} not found'}
    sk = next((s for s in ag.get('skills', []) if s.get('name') == skill_name), None)
    if not sk:
        return {'ok': False, 'error': f'Skill {skill_name} not found'}
    skill_path = pathlib.Path(sk.get('path', '')).resolve()
    # Path traversal protection: ensure path is within OCLAW_HOME or project directory
    allowed_roots = (OCLAW_HOME.resolve(), BASE.parent.resolve())
    if not any(str(skill_path).startswith(str(root)) for root in allowed_roots):
        return {'ok': False, 'error': 'Path is outside the allowed directory scope'}
    if not skill_path.exists():
        return {'ok': True, 'name': skill_name, 'agent': agent_id, 'content': '(SKILL.md file not found)', 'path': str(skill_path)}
    try:
        content = skill_path.read_text()
        return {'ok': True, 'name': skill_name, 'agent': agent_id, 'content': content, 'path': str(skill_path)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def add_skill_to_agent(agent_id, skill_name, description, trigger=''):
    """Create a new skill for an agent with a standardised SKILL.md template."""
    if not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': f'skill_name contains invalid characters: {skill_name}'}
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'agentId contains invalid characters: {agent_id}'}
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / skill_name
    workspace.mkdir(parents=True, exist_ok=True)
    skill_md = workspace / 'SKILL.md'
    desc_line = description or skill_name
    trigger_section = f'\n## Trigger Conditions\n{trigger}\n' if trigger else ''
    template = (f'---\n'
                f'name: {skill_name}\n'
                f'description: {desc_line}\n'
                f'---\n\n'
                f'# {skill_name}\n\n'
                f'{desc_line}\n'
                f'{trigger_section}\n'
                f'## Input\n\n'
                f'<!-- Describe what input this skill accepts -->\n\n'
                f'## Process\n\n'
                f'1. Step 1\n'
                f'2. Step 2\n\n'
                f'## Output Specification\n\n'
                f'<!-- Describe the output format and delivery requirements -->\n\n'
                f'## Notes\n\n'
                f'- (Add any constraints, limitations, or special rules here)\n')
    skill_md.write_text(template)
    # Re-sync agent config
    try:
        subprocess.run(['python3', str(SCRIPTS / 'sync_agent_config.py')], timeout=10)
    except Exception:
        pass
    return {'ok': True, 'message': f'Skill {skill_name} added to {agent_id}', 'path': str(skill_md)}


def add_remote_skill(agent_id, skill_name, source_url, description=''):
    """Add a skill SKILL.md file for an Agent from a remote URL or local path.
    
    Supported sources:
    - HTTPS URLs: https://raw.githubusercontent.com/...
    - Local paths: /path/to/SKILL.md or file:///path/to/SKILL.md
    """
    # Input validation
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'agentId contains invalid characters: {agent_id}'}
    if not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': f'skillName contains invalid characters: {skill_name}'}
    if not source_url or not isinstance(source_url, str):
        return {'ok': False, 'error': 'sourceUrl must be a valid string'}
    
    source_url = source_url.strip()
    
    # Check if Agent exists
    cfg = read_json(DATA / 'agent_config.json', {})
    agents = cfg.get('agents', [])
    if not any(a.get('id') == agent_id for a in agents):
        return {'ok': False, 'error': f'Agent {agent_id} not found'}
    
    # Download or read file content
    try:
        if source_url.startswith('http://') or source_url.startswith('https://'):
            # Validate HTTPS URL
            if not validate_url(source_url, allowed_schemes=('https',)):
                return {'ok': False, 'error': 'URL is invalid or insecure (only HTTPS is supported)'}
            
            # Download from URL with timeout protection
            req = Request(source_url, headers={'User-Agent': 'OpenClaw-SkillManager/1.0'})
            try:
                resp = urlopen(req, timeout=10)
                content = resp.read(10 * 1024 * 1024).decode('utf-8')  # max 10MB
                if len(content) > 10 * 1024 * 1024:
                    return {'ok': False, 'error': 'File too large (max 10MB)'}
            except Exception as e:
                return {'ok': False, 'error': f'URL not accessible: {str(e)[:100]}'}
        
        elif source_url.startswith('file://'):
            # file:// URL format
            local_path = pathlib.Path(source_url[7:])
            if not local_path.exists():
                return {'ok': False, 'error': f'Local file not found: {local_path}'}
            content = local_path.read_text()
        
        elif source_url.startswith('/') or source_url.startswith('.'):
            # Local absolute or relative path
            local_path = pathlib.Path(source_url).resolve()
            if not local_path.exists():
                return {'ok': False, 'error': f'Local file not found: {local_path}'}
            # Path traversal protection
            allowed_roots = (OCLAW_HOME.resolve(), BASE.parent.resolve())
            if not any(str(local_path).startswith(str(root)) for root in allowed_roots):
                return {'ok': False, 'error': 'Path is outside the allowed directory scope'}
            content = local_path.read_text()
        
        else:
            return {'ok': False, 'error': 'Unsupported URL format (only https://, file://, or local paths are supported)'}
    except Exception as e:
        return {'ok': False, 'error': f'File read failed: {str(e)[:100]}'}
    
    # Basic validation: check for Markdown with YAML frontmatter
    if not content.startswith('---'):
        return {'ok': False, 'error': 'Invalid file format (missing YAML frontmatter)'}
    
    # Attempt to parse frontmatter
    try:
        import yaml
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {'ok': False, 'error': 'Invalid file format (malformed YAML frontmatter)'}
        frontmatter_str = parts[1]
        yaml.safe_load(frontmatter_str)  # Validate YAML format
    except Exception as e:
        # Full YAML parsing not required, but check basic structure
        if 'name:' not in content[:500]:
            return {'ok': False, 'error': f'Invalid file format: {str(e)[:100]}'}
    
    # Create local directory
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / skill_name
    workspace.mkdir(parents=True, exist_ok=True)
    skill_md = workspace / 'SKILL.md'
    
    # Write SKILL.md
    skill_md.write_text(content)
    
    # Save source info to .source.json
    source_info = {
        'skillName': skill_name,
        'sourceUrl': source_url,
        'description': description,
        'addedAt': now_iso(),
        'lastUpdated': now_iso(),
        'checksum': _compute_checksum(content),
        'status': 'valid',
    }
    source_json = workspace / '.source.json'
    source_json.write_text(json.dumps(source_info, ensure_ascii=False, indent=2))
    
    # Re-sync agent config
    try:
        subprocess.run(['python3', str(SCRIPTS / 'sync_agent_config.py')], timeout=10)
    except Exception:
        pass
    
    return {
        'ok': True,
        'message': f'Skill {skill_name} added to {agent_id} from remote source',
        'skillName': skill_name,
        'agentId': agent_id,
        'source': source_url,
        'localPath': str(skill_md),
        'size': len(content),
        'addedAt': now_iso(),
    }


def get_remote_skills_list():
    """List all added remote skills and their source information."""
    remote_skills = []
    
    # Iterate over all workspaces
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
            skill_md = skill_dir / 'SKILL.md'
            
            if not source_json.exists():
                # Locally created skill, skip
                continue
            
            try:
                source_info = json.loads(source_json.read_text())
                # Check if SKILL.md exists
                status = 'valid' if skill_md.exists() else 'not-found'
                remote_skills.append({
                    'skillName': skill_name,
                    'agentId': agent_id,
                    'sourceUrl': source_info.get('sourceUrl', ''),
                    'description': source_info.get('description', ''),
                    'localPath': str(skill_md),
                    'addedAt': source_info.get('addedAt', ''),
                    'lastUpdated': source_info.get('lastUpdated', ''),
                    'status': status,
                })
            except Exception:
                pass
    
    return {
        'ok': True,
        'remoteSkills': remote_skills,
        'count': len(remote_skills),
        'listedAt': now_iso(),
    }


def update_remote_skill(agent_id, skill_name):
    """Update an already-added remote skill to the latest version (re-download from source URL)."""
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'agentId contains invalid characters: {agent_id}'}
    if not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': f'skillName contains invalid characters: {skill_name}'}
    
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / skill_name
    source_json = workspace / '.source.json'
    skill_md = workspace / 'SKILL.md'
    
    if not source_json.exists():
        return {'ok': False, 'error': f'Skill {skill_name} is not a remote skill (no .source.json)'}
    
    try:
        source_info = json.loads(source_json.read_text())
        source_url = source_info.get('sourceUrl', '')
        if not source_url:
            return {'ok': False, 'error': 'Source URL not found'}
        
        # Re-download
        result = add_remote_skill(agent_id, skill_name, source_url, 
                                  source_info.get('description', ''))
        if result['ok']:
            result['message'] = 'Skill updated'
            source_info_updated = json.loads(source_json.read_text())
            result['newVersion'] = source_info_updated.get('checksum', 'unknown')
        return result
    except Exception as e:
        return {'ok': False, 'error': f'Update failed: {str(e)[:100]}'}


def remove_remote_skill(agent_id, skill_name):
    """Remove an already-added remote skill."""
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'agentId contains invalid characters: {agent_id}'}
    if not _SAFE_NAME_RE.match(skill_name):
        return {'ok': False, 'error': f'skillName contains invalid characters: {skill_name}'}
    
    workspace = OCLAW_HOME / f'workspace-{agent_id}' / 'skills' / skill_name
    if not workspace.exists():
        return {'ok': False, 'error': f'Skill not found: {skill_name}'}
    
    # Check if it is a remote skill
    source_json = workspace / '.source.json'
    if not source_json.exists():
        return {'ok': False, 'error': f'Skill {skill_name} is not a remote skill and cannot be removed via this API'}
    
    try:
        # Delete the entire skill directory
        import shutil
        shutil.rmtree(workspace)
        
        # Re-sync agent config
        try:
            subprocess.run(['python3', str(SCRIPTS / 'sync_agent_config.py')], timeout=10)
        except Exception:
            pass
        
        return {'ok': True, 'message': f'Skill {skill_name} removed from {agent_id}'}
    except Exception as e:
        return {'ok': False, 'error': f'Remove failed: {str(e)[:100]}'}


def _compute_checksum(content: str) -> str:
    """Compute a simple checksum of content (first 16 chars of SHA256)."""
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def push_to_feishu():
    """Push morning brief link to Feishu via webhook."""
    cfg = read_json(DATA / 'morning_brief_config.json', {})
    webhook = cfg.get('feishu_webhook', '').strip()
    if not webhook:
        return
    if not validate_url(webhook, allowed_schemes=('https',), allowed_domains=('open.feishu.cn', 'open.larksuite.com')):
        log.warning(f'Feishu Webhook URL is invalid: {webhook}')
        return
    brief = read_json(DATA / 'morning_brief.json', {})
    date_str = brief.get('date', '')
    total = sum(len(v) for v in (brief.get('categories') or {}).values())
    if not total:
        return
    cat_lines = []
    for cat, items in (brief.get('categories') or {}).items():
        if items:
            cat_lines.append(f'  {cat}: {len(items)} items')
    summary = '\n'.join(cat_lines)
    date_fmt = date_str[:4] + '-' + date_str[4:6] + '-' + date_str[6:] if len(date_str) == 8 else date_str
    payload = json.dumps({
        'msg_type': 'interactive',
        'card': {
            'header': {'title': {'tag': 'plain_text', 'content': f'📰 Daily Brief · {date_fmt}'}, 'template': 'blue'},
            'elements': [
                {'tag': 'div', 'text': {'tag': 'lark_md', 'content': f'**{total}** news items updated\n{summary}'}},
                {'tag': 'action', 'actions': [{'tag': 'button', 'text': {'tag': 'plain_text', 'content': '🔗 View Full Brief'}, 'url': 'http://127.0.0.1:7891', 'type': 'primary'}]},
                {'tag': 'note', 'elements': [{'tag': 'plain_text', 'content': f"Collected at {brief.get('generated_at', '')}"}]}
            ]
        }
    }).encode()
    try:
        req = Request(webhook, data=payload, headers={'Content-Type': 'application/json'})
        resp = urlopen(req, timeout=10)
        print(f'[Feishu] Push succeeded ({resp.status})')
    except Exception as e:
        print(f'[Feishu] Push failed: {e}', file=sys.stderr)


# Minimum requirements for edict titles
_MIN_TITLE_LEN = 10
_JUNK_TITLES = {
    '?', '？', 'ok', 'yes', 'no',
}


def handle_create_task(title, org='Zhongshu', official='Zhongshu Chancellor', priority='normal', template_id='', params=None, target_dept=''):
    """Create a new task from the dashboard (imperial edict template)."""
    if not title or not title.strip():
        return {'ok': False, 'error': 'Task title cannot be empty'}
    title = title.strip()
    # Strip Conversation info metadata
    title = re.split(r'\n*Conversation info\s*\(', title, maxsplit=1)[0].strip()
    title = re.split(r'\n*```', title, maxsplit=1)[0].strip()
    # Strip common edict prefixes like "edict:" "decree:"
    title = re.sub(r'^(edict|decree)[：:\uff1a]\s*', '', title, flags=re.IGNORECASE)
    if len(title) > 100:
        title = title[:100] + '...'
    # Title quality check: prevent casual chat from being mistaken as an edict
    if len(title) < _MIN_TITLE_LEN:
        return {'ok': False, 'error': f'Title too short ({len(title)}<{_MIN_TITLE_LEN} chars), does not look like an edict'}
    if title.lower() in _JUNK_TITLES:
        return {'ok': False, 'error': f'"{title}" is not a valid edict, please enter a specific work instruction'}
    # Generate task id: JJC-YYYYMMDD-NNN
    today = datetime.datetime.now().strftime('%Y%m%d')
    tasks = load_tasks()
    today_ids = [t['id'] for t in tasks if t.get('id', '').startswith(f'JJC-{today}-')]
    seq = 1
    if today_ids:
        nums = [int(tid.split('-')[-1]) for tid in today_ids if tid.split('-')[-1].isdigit()]
        seq = max(nums) + 1 if nums else 1
    task_id = f'JJC-{today}-{seq:03d}'
    # Correct workflow start: Emperor -> Taizi triage
    # target_dept records the template-suggested final execution department (for Shangshu dispatch reference only)
    initial_org = 'Taizi'
    new_task = {
        'id': task_id,
        'title': title,
        'official': official,
        'org': initial_org,
        'state': 'Taizi',
        'now': 'Waiting for Taizi to receive and triage edict',
        'eta': '-',
        'block': 'none',
        'output': '',
        'ac': '',
        'priority': priority,
        'templateId': template_id,
        'templateParams': params or {},
        'flow_log': [{
            'at': now_iso(),
            'from': 'Emperor',
            'to': initial_org,
            'remark': f'Edict issued: {title}'
        }],
        'updatedAt': now_iso(),
    }
    if target_dept:
        new_task['targetDept'] = target_dept

    _ensure_scheduler(new_task)
    _scheduler_snapshot(new_task, 'create-task-initial')
    _scheduler_mark_progress(new_task, 'Task created')

    tasks.insert(0, new_task)
    save_tasks(tasks)
    log.info(f'Task created: {task_id} | {title[:40]}')

    dispatch_for_state(task_id, new_task, 'Taizi', trigger='imperial-edict')

    return {'ok': True, 'taskId': task_id, 'message': f'Edict {task_id} issued, dispatching to Taizi'}


def handle_review_action(task_id, action, comment=''):
    """Menxia imperial review: approve/reject."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    if task.get('state') not in ('Review', 'Menxia'):
        return {'ok': False, 'error': f'Task {task_id} current state is {task.get("state")}, cannot perform review'}

    _ensure_scheduler(task)
    _scheduler_snapshot(task, f'review-before-{action}')

    if action == 'approve':
        if task['state'] == 'Menxia':
            task['state'] = 'Assigned'
            task['now'] = 'Menxia approved, transferring to Shangshu for dispatch'
            remark = f'✅ Approved: {comment or "Menxia review passed"}'
            to_dept = 'Shangshu'
        else:  # Review
            task['state'] = 'Done'
            task['now'] = 'Imperial review approved, task complete'
            remark = f'✅ Imperial approval: {comment or "Review passed"}'
            to_dept = 'Emperor'
    elif action == 'reject':
        round_num = (task.get('review_round') or 0) + 1
        task['review_round'] = round_num
        task['state'] = 'Zhongshu'
        task['now'] = f'Rejected, returned to Zhongshu for revision (round {round_num})'
        remark = f'🚫 Rejected: {comment or "Revision required"}'
        to_dept = 'Zhongshu'
    else:
        return {'ok': False, 'error': f'Unknown action: {action}'}

    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': 'Menxia' if task.get('state') != 'Done' else 'Emperor',
        'to': to_dept,
        'remark': remark
    })
    _scheduler_mark_progress(task, f'Review action {action} -> {task.get("state")}')
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    # 🚀 Auto-dispatch corresponding Agent after approval
    new_state = task['state']
    if new_state not in ('Done',):
        dispatch_for_state(task_id, task, new_state)

    label = 'approved' if action == 'approve' else 'rejected'
    dispatched = ' (Agent auto-dispatched)' if new_state != 'Done' else ''
    return {'ok': True, 'message': f'{task_id} {label}{dispatched}'}


# ══ Agent Online Status Detection ══

_AGENT_DEPTS = [
    {'id':'taizi',   'label':'Taizi (Crown Prince)', 'emoji':'🤴', 'role':'Taizi',                    'rank':'Crown Prince'},
    {'id':'zhongshu','label':'Zhongshu (Planning)',   'emoji':'📜', 'role':'Zhongshu Chancellor',      'rank':'First Rank'},
    {'id':'menxia',  'label':'Menxia (Review)',        'emoji':'🔍', 'role':'Menxia Director',          'rank':'First Rank'},
    {'id':'shangshu','label':'Shangshu (Dispatch)',    'emoji':'📮', 'role':'Shangshu Director',        'rank':'First Rank'},
    {'id':'hubu',    'label':'Hubu (Finance)',         'emoji':'💰', 'role':'Hubu Minister',            'rank':'Second Rank'},
    {'id':'libu',    'label':'Libu (Rites)',           'emoji':'📝', 'role':'Libu Minister',            'rank':'Second Rank'},
    {'id':'bingbu',  'label':'Bingbu (War)',           'emoji':'⚔️', 'role':'Bingbu Minister',          'rank':'Second Rank'},
    {'id':'xingbu',  'label':'Xingbu (Justice)',       'emoji':'⚖️', 'role':'Xingbu Minister',          'rank':'Second Rank'},
    {'id':'gongbu',  'label':'Gongbu (Works)',         'emoji':'🔧', 'role':'Gongbu Minister',          'rank':'Second Rank'},
    {'id':'libu_hr', 'label':'Libu_hr (Personnel)',    'emoji':'👔', 'role':'Libu_hr Minister',         'rank':'Second Rank'},
    {'id':'zaochao', 'label':'Zaochao (Observatory)',  'emoji':'📰', 'role':'Court Reporter',           'rank':'Third Rank'},
]


def _check_gateway_alive():
    """Detect whether the Gateway process is running."""
    try:
        result = subprocess.run(['pgrep', '-f', 'openclaw-gateway'],
                                capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_gateway_probe():
    """Probe Gateway via HTTP to check responsiveness."""
    try:
        from urllib.request import urlopen
        resp = urlopen('http://127.0.0.1:18789/', timeout=3)
        return resp.status == 200
    except Exception:
        return False


def _get_agent_session_status(agent_id):
    """Read Agent's sessions.json to get active status.
    Returns: (last_active_ts_ms, session_count, is_busy)
    """
    sessions_file = OCLAW_HOME / 'agents' / agent_id / 'sessions' / 'sessions.json'
    if not sessions_file.exists():
        return 0, 0, False
    try:
        data = json.loads(sessions_file.read_text())
        if not isinstance(data, dict):
            return 0, 0, False
        session_count = len(data)
        last_ts = 0
        for v in data.values():
            ts = v.get('updatedAt', 0)
            if isinstance(ts, (int, float)) and ts > last_ts:
                last_ts = ts
        now_ms = int(datetime.datetime.now().timestamp() * 1000)
        age_ms = now_ms - last_ts if last_ts else 9999999999
        is_busy = age_ms <= 2 * 60 * 1000  # considered working within 2 minutes
        return last_ts, session_count, is_busy
    except Exception:
        return 0, 0, False


def _check_agent_process(agent_id):
    """Detect whether an openclaw-agent process is running for this Agent."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', f'openclaw.*--agent.*{agent_id}'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_agent_workspace(agent_id):
    """Check whether the Agent workspace exists."""
    ws = OCLAW_HOME / f'workspace-{agent_id}'
    return ws.is_dir()


def _get_openclaw_bin():
    """Return the openclaw binary path, respecting OPENCLAW_BIN env var override.

    Returns the resolved path string if found, or None if the binary cannot be located.
    """
    bin_name = os.environ.get('OPENCLAW_BIN', 'openclaw')
    resolved = shutil.which(bin_name)
    if resolved:
        return resolved
    # If an absolute path was given, check it exists directly
    if os.path.isabs(bin_name) and os.path.isfile(bin_name):
        return bin_name
    return None


def get_agents_status():
    """Get online status for all Agents.
    Returns for each Agent:
    - status: 'running' | 'idle' | 'offline' | 'unconfigured'
    - lastActive: last active time
    - sessions: session count
    - hasWorkspace: whether workspace exists
    - processAlive: whether a process is running
    """
    gateway_alive = _check_gateway_alive()
    gateway_probe = _check_gateway_probe() if gateway_alive else False

    agents = []
    seen_ids = set()
    for dept in _AGENT_DEPTS:
        aid = dept['id']
        if aid in seen_ids:
            continue
        seen_ids.add(aid)

        has_workspace = _check_agent_workspace(aid)
        last_ts, sess_count, is_busy = _get_agent_session_status(aid)
        process_alive = _check_agent_process(aid)

        # Status determination
        if not has_workspace:
            status = 'unconfigured'
            status_label = '❌ Unconfigured'
        elif not gateway_alive:
            status = 'offline'
            status_label = '🔴 Gateway Offline'
        elif process_alive or is_busy:
            status = 'running'
            status_label = '🟢 Running'
        elif last_ts > 0:
            now_ms = int(datetime.datetime.now().timestamp() * 1000)
            age_ms = now_ms - last_ts
            if age_ms <= 10 * 60 * 1000:  # within 10 minutes
                status = 'idle'
                status_label = '🟡 Standby'
            elif age_ms <= 3600 * 1000:  # within 1 hour
                status = 'idle'
                status_label = '⚪ Idle'
            else:
                status = 'idle'
                status_label = '⚪ Dormant'
        else:
            status = 'idle'
            status_label = '⚪ No Records'

        # Format last active time
        last_active_str = None
        if last_ts > 0:
            try:
                last_active_str = datetime.datetime.fromtimestamp(
                    last_ts / 1000
                ).strftime('%m-%d %H:%M')
            except Exception:
                pass

        agents.append({
            'id': aid,
            'label': dept['label'],
            'emoji': dept['emoji'],
            'role': dept['role'],
            'status': status,
            'statusLabel': status_label,
            'lastActive': last_active_str,
            'lastActiveTs': last_ts,
            'sessions': sess_count,
            'hasWorkspace': has_workspace,
            'processAlive': process_alive,
        })

    return {
        'ok': True,
        'gateway': {
            'alive': gateway_alive,
            'probe': gateway_probe,
            'status': '🟢 Running' if gateway_probe else ('🟡 Process alive but not responding' if gateway_alive else '🔴 Not started'),
        },
        'agents': agents,
        'checkedAt': now_iso(),
    }


def wake_agent(agent_id, message=''):
    """Wake the specified Agent by sending a heartbeat/wake message."""
    if not _SAFE_NAME_RE.match(agent_id):
        return {'ok': False, 'error': f'agent_id is invalid: {agent_id}'}
    if not _check_agent_workspace(agent_id):
        return {'ok': False, 'error': f'{agent_id} workspace does not exist, please configure first'}
    if not _check_gateway_alive():
        return {'ok': False, 'error': 'Gateway is not running, please run: openclaw gateway start'}

    # agent_id used directly as runtime_id (registered name in openclaw agents list)
    runtime_id = agent_id
    msg = message or f'🔔 System heartbeat check — please reply OK to confirm online. Current time: {now_iso()}'

    def do_wake():
        try:
            oclaw_bin = _get_openclaw_bin()
            if not oclaw_bin:
                log.error(f'❌ {agent_id} wake failed: openclaw binary not found — set OPENCLAW_BIN or add it to PATH')
                return
            cmd = [oclaw_bin, 'agent', '--agent', runtime_id, '-m', msg, '--timeout', '120']
            log.info(f'🔔 Waking {agent_id}...')
            # with retry (up to 2 attempts)
            for attempt in range(1, 3):
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=130)
                if result.returncode == 0:
                    log.info(f'✅ {agent_id} woken')
                    return
                err_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
                log.warning(f'⚠️ {agent_id} wake failed (attempt {attempt}): {err_msg}')
                if attempt < 2:
                    import time
                    time.sleep(5)
            log.error(f'❌ {agent_id} wake ultimately failed')
        except subprocess.TimeoutExpired:
            log.error(f'❌ {agent_id} wake timed out (130s)')
        except Exception as e:
            log.warning(f'⚠️ {agent_id} wake exception: {e}')
    threading.Thread(target=do_wake, daemon=True).start()

    return {'ok': True, 'message': f'{agent_id} wake command sent, takes effect in ~10-30 seconds'}


# ══ Agent Real-time Activity Reading ══

# State → agent_id mapping
_STATE_AGENT_MAP = {
    'Taizi': 'taizi',
    'Zhongshu': 'zhongshu',
    'Menxia': 'menxia',
    'Assigned': 'shangshu',
    'Doing': None,         # Six Ministries, infer from org
    'Review': 'shangshu',
    'Next': None,          # Pending execution, infer from org
    'Pending': 'zhongshu', # Pending, default to Zhongshu
}
_ORG_AGENT_MAP = {
    'Libu': 'libu', 'Hubu': 'hubu', 'Bingbu': 'bingbu',
    'Xingbu': 'xingbu', 'Gongbu': 'gongbu', 'Libu_hr': 'libu_hr',
    'Zhongshu': 'zhongshu', 'Menxia': 'menxia', 'Shangshu': 'shangshu',
}

_TERMINAL_STATES = {'Done', 'Cancelled'}


def _parse_iso(ts):
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


def _ensure_scheduler(task):
    sched = task.setdefault('_scheduler', {})
    if not isinstance(sched, dict):
        sched = {}
        task['_scheduler'] = sched
    sched.setdefault('enabled', True)
    sched.setdefault('stallThresholdSec', 180)
    sched.setdefault('maxRetry', 1)
    sched.setdefault('retryCount', 0)
    sched.setdefault('escalationLevel', 0)
    sched.setdefault('autoRollback', True)
    if not sched.get('lastProgressAt'):
        sched['lastProgressAt'] = task.get('updatedAt') or now_iso()
    if 'stallSince' not in sched:
        sched['stallSince'] = None
    if 'lastDispatchStatus' not in sched:
        sched['lastDispatchStatus'] = 'idle'
    if 'snapshot' not in sched:
        sched['snapshot'] = {
            'state': task.get('state', ''),
            'org': task.get('org', ''),
            'now': task.get('now', ''),
            'savedAt': now_iso(),
            'note': 'init',
        }
    return sched


def _scheduler_add_flow(task, remark, to=''):
    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': 'Taizi Scheduler',
        'to': to or task.get('org', ''),
        'remark': f'🧭 {remark}'
    })


def _scheduler_snapshot(task, note=''):
    sched = _ensure_scheduler(task)
    sched['snapshot'] = {
        'state': task.get('state', ''),
        'org': task.get('org', ''),
        'now': task.get('now', ''),
        'savedAt': now_iso(),
        'note': note or 'snapshot',
    }


def _scheduler_mark_progress(task, note=''):
    sched = _ensure_scheduler(task)
    sched['lastProgressAt'] = now_iso()
    sched['stallSince'] = None
    sched['retryCount'] = 0
    sched['escalationLevel'] = 0
    sched['lastEscalatedAt'] = None
    if note:
        _scheduler_add_flow(task, f'Progress confirmed: {note}')


def _update_task_scheduler(task_id, updater):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return False
    sched = _ensure_scheduler(task)
    updater(task, sched)
    task['updatedAt'] = now_iso()
    save_tasks(tasks)
    return True


def get_scheduler_state(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    sched = _ensure_scheduler(task)
    last_progress = _parse_iso(sched.get('lastProgressAt') or task.get('updatedAt'))
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    stalled_sec = 0
    if last_progress:
        stalled_sec = max(0, int((now_dt - last_progress).total_seconds()))
    return {
        'ok': True,
        'taskId': task_id,
        'state': task.get('state', ''),
        'org': task.get('org', ''),
        'scheduler': sched,
        'stalledSec': stalled_sec,
        'checkedAt': now_iso(),
    }


def handle_scheduler_retry(task_id, reason=''):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    state = task.get('state', '')
    if state in _TERMINAL_STATES or state == 'Blocked':
        return {'ok': False, 'error': f'Task {task_id} current state {state} does not support retry'}

    sched = _ensure_scheduler(task)
    sched['retryCount'] = int(sched.get('retryCount') or 0) + 1
    sched['lastRetryAt'] = now_iso()
    sched['lastDispatchTrigger'] = 'taizi-retry'
    _scheduler_add_flow(task, f'Retry triggered (attempt {sched["retryCount"]}): {reason or "timed out without progress"}')
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    dispatch_for_state(task_id, task, state, trigger='taizi-retry')
    return {'ok': True, 'message': f'{task_id} retry dispatch triggered', 'retryCount': sched['retryCount']}


def handle_scheduler_escalate(task_id, reason=''):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    state = task.get('state', '')
    if state in _TERMINAL_STATES:
        return {'ok': False, 'error': f'Task {task_id} has ended, no escalation needed'}

    sched = _ensure_scheduler(task)
    current_level = int(sched.get('escalationLevel') or 0)
    next_level = min(current_level + 1, 2)
    target = 'menxia' if next_level == 1 else 'shangshu'
    target_label = 'Menxia' if next_level == 1 else 'Shangshu'

    sched['escalationLevel'] = next_level
    sched['lastEscalatedAt'] = now_iso()
    _scheduler_add_flow(task, f'Escalated to {target_label} for coordination: {reason or "task stalled"}', to=target_label)
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    msg = (
        f'🧭 Taizi Scheduler Escalation Notice\n'
        f'Task ID: {task_id}\n'
        f'Current State: {state}\n'
        f'Stall Handling: Please intervene to coordinate and advance\n'
        f'Reason: {reason or "task exceeded threshold without progress"}\n'
        f'⚠️ Task already exists in dashboard, do not create a duplicate.'
    )
    wake_agent(target, msg)

    return {'ok': True, 'message': f'{task_id} escalated to {target_label}', 'escalationLevel': next_level}


def handle_scheduler_rollback(task_id, reason=''):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    sched = _ensure_scheduler(task)
    snapshot = sched.get('snapshot') or {}
    snap_state = snapshot.get('state')
    if not snap_state:
        return {'ok': False, 'error': f'Task {task_id} has no available rollback snapshot'}

    old_state = task.get('state', '')
    task['state'] = snap_state
    task['org'] = snapshot.get('org', task.get('org', ''))
    task['now'] = f'↩️ Taizi Scheduler auto-rollback: {reason or "restore to last stable checkpoint"}'
    task['block'] = 'none'
    sched['retryCount'] = 0
    sched['escalationLevel'] = 0
    sched['stallSince'] = None
    sched['lastProgressAt'] = now_iso()
    _scheduler_add_flow(task, f'Rollback executed: {old_state} → {snap_state}, reason: {reason or "stall recovery"}')
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    if snap_state not in _TERMINAL_STATES:
        dispatch_for_state(task_id, task, snap_state, trigger='taizi-rollback')

    return {'ok': True, 'message': f'{task_id} rolled back to {snap_state}'}


def handle_scheduler_scan(threshold_sec=180):
    threshold_sec = max(30, int(threshold_sec or 180))
    tasks = load_tasks()
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    pending_retries = []
    pending_escalates = []
    pending_rollbacks = []
    actions = []
    changed = False

    for task in tasks:
        task_id = task.get('id', '')
        state = task.get('state', '')
        if not task_id or state in _TERMINAL_STATES or task.get('archived'):
            continue
        if state == 'Blocked':
            continue

        sched = _ensure_scheduler(task)
        task_threshold = int(sched.get('stallThresholdSec') or threshold_sec)
        last_progress = _parse_iso(sched.get('lastProgressAt') or task.get('updatedAt'))
        if not last_progress:
            continue
        stalled_sec = max(0, int((now_dt - last_progress).total_seconds()))
        if stalled_sec < task_threshold:
            continue

        if not sched.get('stallSince'):
            sched['stallSince'] = now_iso()
            changed = True

        retry_count = int(sched.get('retryCount') or 0)
        max_retry = max(0, int(sched.get('maxRetry') or 1))
        level = int(sched.get('escalationLevel') or 0)

        if retry_count < max_retry:
            sched['retryCount'] = retry_count + 1
            sched['lastRetryAt'] = now_iso()
            sched['lastDispatchTrigger'] = 'taizi-scan-retry'
            _scheduler_add_flow(task, f'Stalled {stalled_sec}s, triggering auto-retry (attempt {sched["retryCount"]})')
            pending_retries.append((task_id, state))
            actions.append({'taskId': task_id, 'action': 'retry', 'stalledSec': stalled_sec})
            changed = True
            continue

        if level < 2:
            next_level = level + 1
            target = 'menxia' if next_level == 1 else 'shangshu'
            target_label = 'Menxia' if next_level == 1 else 'Shangshu'
            sched['escalationLevel'] = next_level
            sched['lastEscalatedAt'] = now_iso()
            _scheduler_add_flow(task, f'Stalled {stalled_sec}s, escalating to {target_label} for coordination', to=target_label)
            pending_escalates.append((task_id, state, target, target_label, stalled_sec))
            actions.append({'taskId': task_id, 'action': 'escalate', 'to': target_label, 'stalledSec': stalled_sec})
            changed = True
            continue

        if sched.get('autoRollback', True):
            snapshot = sched.get('snapshot') or {}
            snap_state = snapshot.get('state')
            if snap_state and snap_state != state:
                old_state = state
                task['state'] = snap_state
                task['org'] = snapshot.get('org', task.get('org', ''))
                task['now'] = '↩️ Taizi Scheduler auto-rollback to stable checkpoint'
                task['block'] = 'none'
                sched['retryCount'] = 0
                sched['escalationLevel'] = 0
                sched['stallSince'] = None
                sched['lastProgressAt'] = now_iso()
                _scheduler_add_flow(task, f'Consecutive stall, auto-rollback: {old_state} → {snap_state}')
                pending_rollbacks.append((task_id, snap_state))
                actions.append({'taskId': task_id, 'action': 'rollback', 'toState': snap_state})
                changed = True

    if changed:
        save_tasks(tasks)

    for task_id, state in pending_retries:
        retry_task = next((t for t in tasks if t.get('id') == task_id), None)
        if retry_task:
            dispatch_for_state(task_id, retry_task, state, trigger='taizi-scan-retry')

    for task_id, state, target, target_label, stalled_sec in pending_escalates:
        msg = (
            f'🧭 Taizi Scheduler Escalation Notice\n'
            f'Task ID: {task_id}\n'
            f'Current State: {state}\n'
            f'Stalled: {stalled_sec} seconds\n'
            f'Please intervene immediately to coordinate and advance\n'
            f'⚠️ Task already exists in dashboard, do not create a duplicate.'
        )
        wake_agent(target, msg)

    for task_id, state in pending_rollbacks:
        rollback_task = next((t for t in tasks if t.get('id') == task_id), None)
        if rollback_task and state not in _TERMINAL_STATES:
            dispatch_for_state(task_id, rollback_task, state, trigger='taizi-auto-rollback')

    return {
        'ok': True,
        'thresholdSec': threshold_sec,
        'actions': actions,
        'count': len(actions),
        'checkedAt': now_iso(),
    }


def _startup_recover_queued_dispatches():
    """Scan tasks with lastDispatchStatus=queued after server startup and re-dispatch.
    Fixes: dispatch thread interrupted by kill -9 restart leaving tasks permanently stuck."""
    tasks = load_tasks()
    recovered = 0
    for task in tasks:
        task_id = task.get('id', '')
        state = task.get('state', '')
        if not task_id or state in _TERMINAL_STATES or task.get('archived'):
            continue
        sched = task.get('_scheduler') or {}
        if sched.get('lastDispatchStatus') == 'queued':
            log.info(f'🔄 Startup recovery: {task_id} state={state} last dispatch incomplete, re-dispatching')
            sched['lastDispatchTrigger'] = 'startup-recovery'
            dispatch_for_state(task_id, task, state, trigger='startup-recovery')
            recovered += 1
    if recovered:
        log.info(f'✅ Startup recovery complete: re-dispatched {recovered} task(s)')
    else:
        log.info(f'✅ Startup recovery: nothing to recover')


def handle_repair_flow_order():
    """Fix historical tasks where the first flow entry was incorrectly ordered as Emperor->Zhongshu."""
    tasks = load_tasks()
    fixed = 0
    fixed_ids = []

    for task in tasks:
        task_id = task.get('id', '')
        if not task_id.startswith('JJC-'):
            continue
        flow_log = task.get('flow_log') or []
        if not flow_log:
            continue

        first = flow_log[0]
        if first.get('from') != 'Emperor' or first.get('to') != 'Zhongshu':
            continue

        first['to'] = 'Taizi'
        remark = first.get('remark', '')
        if isinstance(remark, str) and remark.startswith('Edict issued:'):
            first['remark'] = remark

        if task.get('state') == 'Zhongshu' and task.get('org') == 'Zhongshu' and len(flow_log) == 1:
            task['state'] = 'Taizi'
            task['org'] = 'Taizi'
            task['now'] = 'Waiting for Taizi to receive and triage edict'

        task['updatedAt'] = now_iso()
        fixed += 1
        fixed_ids.append(task_id)

    if fixed:
        save_tasks(tasks)

    return {
        'ok': True,
        'count': fixed,
        'taskIds': fixed_ids[:80],
        'more': max(0, fixed - 80),
        'checkedAt': now_iso(),
    }


def _collect_message_text(msg):
    """Collect searchable text from a message for task_id/keyword filtering."""
    parts = []
    for c in msg.get('content', []) or []:
        ctype = c.get('type')
        if ctype == 'text' and c.get('text'):
            parts.append(str(c.get('text', '')))
        elif ctype == 'thinking' and c.get('thinking'):
            parts.append(str(c.get('thinking', '')))
        elif ctype == 'tool_use':
            parts.append(json.dumps(c.get('input', {}), ensure_ascii=False))
    details = msg.get('details') or {}
    for key in ('output', 'stdout', 'stderr', 'message'):
        val = details.get(key)
        if isinstance(val, str) and val:
            parts.append(val)
    return ''.join(parts)


def _parse_activity_entry(item):
    """Parse a session JSONL message into a unified dashboard activity entry."""
    msg = item.get('message') or {}
    role = str(msg.get('role', '')).strip().lower()
    ts = item.get('timestamp', '')

    if role == 'assistant':
        text = ''
        thinking = ''
        tool_calls = []
        for c in msg.get('content', []) or []:
            if c.get('type') == 'text' and c.get('text') and not text:
                text = str(c.get('text', '')).strip()
            elif c.get('type') == 'thinking' and c.get('thinking') and not thinking:
                thinking = str(c.get('thinking', '')).strip()[:200]
            elif c.get('type') == 'tool_use':
                tool_calls.append({
                    'name': c.get('name', ''),
                    'input_preview': json.dumps(c.get('input', {}), ensure_ascii=False)[:100]
                })
        if not (text or thinking or tool_calls):
            return None
        entry = {'at': ts, 'kind': 'assistant'}
        if text:
            entry['text'] = text[:300]
        if thinking:
            entry['thinking'] = thinking
        if tool_calls:
            entry['tools'] = tool_calls
        return entry

    if role in ('toolresult', 'tool_result'):
        details = msg.get('details') or {}
        code = details.get('exitCode')
        if code is None:
            code = details.get('code', details.get('status'))
        output = ''
        for c in msg.get('content', []) or []:
            if c.get('type') == 'text' and c.get('text'):
                output = str(c.get('text', '')).strip()[:200]
                break
        if not output:
            for key in ('output', 'stdout', 'stderr', 'message'):
                val = details.get(key)
                if isinstance(val, str) and val.strip():
                    output = val.strip()[:200]
                    break

        entry = {
            'at': ts,
            'kind': 'tool_result',
            'tool': msg.get('toolName', msg.get('name', '')),
            'exitCode': code,
            'output': output,
        }
        duration_ms = details.get('durationMs')
        if isinstance(duration_ms, (int, float)):
            entry['durationMs'] = int(duration_ms)
        return entry

    if role == 'user':
        text = ''
        for c in msg.get('content', []) or []:
            if c.get('type') == 'text' and c.get('text'):
                text = str(c.get('text', '')).strip()
                break
        if not text:
            return None
        return {'at': ts, 'kind': 'user', 'text': text[:200]}

    return None


def get_agent_activity(agent_id, limit=30, task_id=None):
    """Read recent activity from an Agent's session JSONL.
    If task_id is provided, only return entries mentioning that task_id.
    """
    sessions_dir = OCLAW_HOME / 'agents' / agent_id / 'sessions'
    if not sessions_dir.exists():
        return []

    # Scan all JSONL files (reverse mtime order), newest first
    jsonl_files = sorted(sessions_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return []

    entries = []
    # If filtering by task_id, may need to scan multiple files
    files_to_scan = jsonl_files[:3] if task_id else jsonl_files[:1]

    for session_file in files_to_scan:
        try:
            lines = session_file.read_text(errors='ignore').splitlines()
        except Exception:
            continue

        # Forward scan to maintain time order; if task_id present, collect entries mentioning it
        for ln in lines:
            try:
                item = json.loads(ln)
            except Exception:
                continue
            msg = item.get('message') or {}
            all_text = _collect_message_text(msg)

            # task_id filter: only keep entries mentioning task_id
            if task_id and task_id not in all_text:
                continue
            entry = _parse_activity_entry(item)
            if entry:
                entries.append(entry)

            if len(entries) >= limit:
                break
        if len(entries) >= limit:
            break

    # Keep only the last limit entries
    return entries[-limit:]


def _extract_keywords(title):
    """Extract meaningful keywords from a task title (for session content matching)."""
    stop = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
            'is', 'are', 'was', 'be', 'do', 'make', 'use', 'with', 'from', 'by'}
    # Extract English words
    en_words = re.findall(r'[a-zA-Z][\w.-]{1,}', title)
    all_words = en_words
    kws = [w for w in all_words if w.lower() not in stop and len(w) >= 2]
    # Deduplicate, preserve order
    seen = set()
    unique = []
    for w in kws:
        if w.lower() not in seen:
            seen.add(w.lower())
            unique.append(w)
    return unique[:8]  # max 8 keywords


def get_agent_activity_by_keywords(agent_id, keywords, limit=20):
    """Get activity entries from agent session matching keywords.
    Find the session file containing keywords, read only that file's activity.
    """
    sessions_dir = OCLAW_HOME / 'agents' / agent_id / 'sessions'
    if not sessions_dir.exists():
        return []

    jsonl_files = sorted(sessions_dir.glob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return []

    # Find session file containing keywords
    target_file = None
    for sf in jsonl_files[:5]:
        try:
            content = sf.read_text(errors='ignore')
        except Exception:
            continue
        hits = sum(1 for kw in keywords if kw.lower() in content.lower())
        if hits >= min(2, len(keywords)):
            target_file = sf
            break

    if not target_file:
        return []

    # Parse session file, split by user messages into conversation segments
    # Find the conversation segment containing keywords, return only that segment's activity
    try:
        lines = target_file.read_text(errors='ignore').splitlines()
    except Exception:
        return []

    # First pass: find user message positions matching keywords
    user_msg_indices = []  # (line_index, user_text)
    for i, ln in enumerate(lines):
        try:
            item = json.loads(ln)
        except Exception:
            continue
        msg = item.get('message') or {}
        if msg.get('role') == 'user':
            text = ''
            for c in msg.get('content', []):
                if c.get('type') == 'text' and c.get('text'):
                    text += c['text']
            user_msg_indices.append((i, text))

    # Find the user message with the highest keyword match score
    best_idx = -1
    best_hits = 0
    for line_idx, utext in user_msg_indices:
        hits = sum(1 for kw in keywords if kw.lower() in utext.lower())
        if hits > best_hits:
            best_hits = hits
            best_idx = line_idx

    # Determine line range for the conversation segment: from matching user msg to next user msg
    if best_idx >= 0 and best_hits >= min(2, len(keywords)):
        # Find the position of the next user message
        next_user_idx = len(lines)
        for line_idx, _ in user_msg_indices:
            if line_idx > best_idx:
                next_user_idx = line_idx
                break
        start_line = best_idx
        end_line = next_user_idx
    else:
        # No matching conversation segment found, return empty
        return []

    # Second pass: parse only lines within the conversation segment
    entries = []
    for ln in lines[start_line:end_line]:
        try:
            item = json.loads(ln)
        except Exception:
            continue
        entry = _parse_activity_entry(item)
        if entry:
            entries.append(entry)

    return entries[-limit:]


def get_agent_latest_segment(agent_id, limit=20):
    """Get Agent's latest conversation segment (all content from last user message).
    Used when no exact match exists for an active task, to show Agent's real-time work status.
    """
    sessions_dir = OCLAW_HOME / 'agents' / agent_id / 'sessions'
    if not sessions_dir.exists():
        return []

    jsonl_files = sorted(sessions_dir.glob('*.jsonl'),
                         key=lambda f: f.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return []

    # Read the latest session file
    target_file = jsonl_files[0]
    try:
        lines = target_file.read_text(errors='ignore').splitlines()
    except Exception:
        return []

    # Find the line number of the last user message
    last_user_idx = -1
    for i, ln in enumerate(lines):
        try:
            item = json.loads(ln)
        except Exception:
            continue
        msg = item.get('message') or {}
        if msg.get('role') == 'user':
            last_user_idx = i

    if last_user_idx < 0:
        return []

    # Parse from the last user message to end of file
    entries = []
    for ln in lines[last_user_idx:]:
        try:
            item = json.loads(ln)
        except Exception:
            continue
        entry = _parse_activity_entry(item)
        if entry:
            entries.append(entry)

    return entries[-limit:]


def _compute_phase_durations(flow_log):
    """Calculate the time spent in each phase from flow_log."""
    if not flow_log or len(flow_log) < 1:
        return []
    phases = []
    for i, fl in enumerate(flow_log):
        start_at = fl.get('at', '')
        to_dept = fl.get('to', '')
        remark = fl.get('remark', '')
        # The start time of the next phase is the end time of the current phase
        if i + 1 < len(flow_log):
            end_at = flow_log[i + 1].get('at', '')
            ongoing = False
        else:
            end_at = now_iso()
            ongoing = True
        # Calculate duration
        dur_sec = 0
        try:
            from_dt = datetime.datetime.fromisoformat(start_at.replace('Z', '+00:00'))
            to_dt = datetime.datetime.fromisoformat(end_at.replace('Z', '+00:00'))
            dur_sec = max(0, int((to_dt - from_dt).total_seconds()))
        except Exception:
            pass
        # Human-readable duration
        if dur_sec < 60:
            dur_text = f'{dur_sec}s'
        elif dur_sec < 3600:
            dur_text = f'{dur_sec // 60}m {dur_sec % 60}s'
        elif dur_sec < 86400:
            h, rem = divmod(dur_sec, 3600)
            dur_text = f'{h}h {rem // 60}m'
        else:
            d, rem = divmod(dur_sec, 86400)
            dur_text = f'{d}d {rem // 3600}h'
        phases.append({
            'phase': to_dept,
            'from': start_at,
            'to': end_at,
            'durationSec': dur_sec,
            'durationText': dur_text,
            'ongoing': ongoing,
            'remark': remark,
        })
    return phases


def _compute_todos_summary(todos):
    """Calculate todos completion rate summary."""
    if not todos:
        return None
    total = len(todos)
    completed = sum(1 for t in todos if t.get('status') == 'completed')
    in_progress = sum(1 for t in todos if t.get('status') == 'in-progress')
    not_started = total - completed - in_progress
    percent = round(completed / total * 100) if total else 0
    return {
        'total': total,
        'completed': completed,
        'inProgress': in_progress,
        'notStarted': not_started,
        'percent': percent,
    }


def _compute_todos_diff(prev_todos, curr_todos):
    """Calculate the difference between two todos snapshots."""
    prev_map = {str(t.get('id', '')): t for t in (prev_todos or [])}
    curr_map = {str(t.get('id', '')): t for t in (curr_todos or [])}
    changed, added, removed = [], [], []
    for tid, ct in curr_map.items():
        if tid in prev_map:
            pt = prev_map[tid]
            if pt.get('status') != ct.get('status'):
                changed.append({
                    'id': tid, 'title': ct.get('title', ''),
                    'from': pt.get('status', ''), 'to': ct.get('status', ''),
                })
        else:
            added.append({'id': tid, 'title': ct.get('title', '')})
    for tid, pt in prev_map.items():
        if tid not in curr_map:
            removed.append({'id': tid, 'title': pt.get('title', '')})
    if not changed and not added and not removed:
        return None
    return {'changed': changed, 'added': added, 'removed': removed}


def get_task_activity(task_id):
    """Get real-time progress data for a task.
    Data sources:
    1. Task's own now / todos / flow_log fields (reported by Agent via progress command)
    2. Agent session JSONL conversation logs (thinking / tool_result / user, for showing thought process)

    Enhanced fields:
    - taskMeta: task metadata (title/state/org/output/block/priority/reviewRound/archived)
    - phaseDurations: time spent in each phase
    - todosSummary: todos completion rate summary
    - resourceSummary: Agent resource consumption summary (tokens/cost/elapsed)
    - activity entries in progress/todos retain state/org snapshots
    - activity todos entries contain diff field
    """
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}

    state = task.get('state', '')
    org = task.get('org', '')
    now_text = task.get('now', '')
    todos = task.get('todos', [])
    updated_at = task.get('updatedAt', '')

    # ── Task Metadata ──
    task_meta = {
        'title': task.get('title', ''),
        'state': state,
        'org': org,
        'output': task.get('output', ''),
        'block': task.get('block', ''),
        'priority': task.get('priority', 'normal'),
        'reviewRound': task.get('review_round', 0),
        'archived': task.get('archived', False),
    }

    # Current responsible Agent (backward compatible)
    agent_id = _STATE_AGENT_MAP.get(state)
    if agent_id is None and state in ('Doing', 'Next'):
        agent_id = _ORG_AGENT_MAP.get(org)

    # ── Build activity entry list (flow_log + progress_log) ──
    activity = []
    flow_log = task.get('flow_log', [])

    # 1. Convert flow_log to activity entries
    for fl in flow_log:
        activity.append({
            'at': fl.get('at', ''),
            'kind': 'flow',
            'from': fl.get('from', ''),
            'to': fl.get('to', ''),
            'remark': fl.get('remark', ''),
        })

    progress_log = task.get('progress_log', [])
    related_agents = set()

    # Accumulate resource consumption
    total_tokens = 0
    total_cost = 0.0
    total_elapsed = 0
    has_resource_data = False

    # For todos diff calculation
    prev_todos_snapshot = None

    if progress_log:
        # 2. Multi-Agent real-time progress log (each progress entry keeps its own todo snapshot)
        for pl in progress_log:
            p_at = pl.get('at', '')
            p_agent = pl.get('agent', '')
            p_text = pl.get('text', '')
            p_todos = pl.get('todos', [])
            p_state = pl.get('state', '')
            p_org = pl.get('org', '')
            if p_agent:
                related_agents.add(p_agent)
            # Accumulate resource consumption
            if pl.get('tokens'):
                total_tokens += pl['tokens']
                has_resource_data = True
            if pl.get('cost'):
                total_cost += pl['cost']
                has_resource_data = True
            if pl.get('elapsed'):
                total_elapsed += pl['elapsed']
                has_resource_data = True
            if p_text:
                entry = {
                    'at': p_at,
                    'kind': 'progress',
                    'text': p_text,
                    'agent': p_agent,
                    'agentLabel': pl.get('agentLabel', ''),
                    'state': p_state,
                    'org': p_org,
                }
                # Per-entry resource data
                if pl.get('tokens'):
                    entry['tokens'] = pl['tokens']
                if pl.get('cost'):
                    entry['cost'] = pl['cost']
                if pl.get('elapsed'):
                    entry['elapsed'] = pl['elapsed']
                activity.append(entry)
            if p_todos:
                todos_entry = {
                    'at': p_at,
                    'kind': 'todos',
                    'items': p_todos,
                    'agent': p_agent,
                    'agentLabel': pl.get('agentLabel', ''),
                    'state': p_state,
                    'org': p_org,
                }
                # Calculate diff
                diff = _compute_todos_diff(prev_todos_snapshot, p_todos)
                if diff:
                    todos_entry['diff'] = diff
                activity.append(todos_entry)
                prev_todos_snapshot = p_todos

        # Only fall back to last reported Agent when state-based lookup fails
        if not agent_id:
            last_pl = progress_log[-1]
            if last_pl.get('agent'):
                agent_id = last_pl.get('agent')
    else:
        # Backward compat: use only now/todos
        if now_text:
            activity.append({
                'at': updated_at,
                'kind': 'progress',
                'text': now_text,
                'agent': agent_id or '',
                'state': state,
                'org': org,
            })
        if todos:
            activity.append({
                'at': updated_at,
                'kind': 'todos',
                'items': todos,
                'agent': agent_id or '',
                'state': state,
                'org': org,
            })

    # Sort by time to ensure correct interleaving of flow/progress entries
    activity.sort(key=lambda x: x.get('at', ''))

    if agent_id:
        related_agents.add(agent_id)

    # ── Merge Agent Session Activity (thinking / tool_result / user) ──
    # Extract Agent thinking and tool call records from session JSONL
    try:
        session_entries = []
        # Active task: try exact match by task_id
        if state not in ('Done', 'Cancelled'):
            if agent_id:
                entries = get_agent_activity(agent_id, limit=30, task_id=task_id)
                session_entries.extend(entries)
            # Also fetch from other related Agents
            for ra in related_agents:
                if ra != agent_id:
                    entries = get_agent_activity(ra, limit=20, task_id=task_id)
                    session_entries.extend(entries)
        else:
            # Completed task: match by keywords
            title = task.get('title', '')
            keywords = _extract_keywords(title)
            if keywords:
                agents_to_scan = list(related_agents) if related_agents else ([agent_id] if agent_id else [])
                for ra in agents_to_scan[:5]:
                    entries = get_agent_activity_by_keywords(ra, keywords, limit=15)
                    session_entries.extend(entries)
        # Deduplicate (by at+kind to avoid duplicates)
        existing_keys = {(a.get('at', ''), a.get('kind', '')) for a in activity}
        for se in session_entries:
            key = (se.get('at', ''), se.get('kind', ''))
            if key not in existing_keys:
                activity.append(se)
                existing_keys.add(key)
        # Re-sort
        activity.sort(key=lambda x: x.get('at', ''))
    except Exception as e:
        log.warning(f'Session JSONL merge failed (task={task_id}): {e}')

    # ── Phase Duration Statistics ──
    phase_durations = _compute_phase_durations(flow_log)

    # ── Todos Summary ──
    todos_summary = _compute_todos_summary(todos)

    # ── Total Duration (first flow_log entry to last/current) ──
    total_duration = None
    if flow_log:
        try:
            first_at = datetime.datetime.fromisoformat(flow_log[0].get('at', '').replace('Z', '+00:00'))
            if state in ('Done', 'Cancelled') and len(flow_log) >= 2:
                last_at = datetime.datetime.fromisoformat(flow_log[-1].get('at', '').replace('Z', '+00:00'))
            else:
                last_at = datetime.datetime.now(datetime.timezone.utc)
            dur = max(0, int((last_at - first_at).total_seconds()))
            if dur < 60:
                total_duration = f'{dur}s'
            elif dur < 3600:
                total_duration = f'{dur // 60}m {dur % 60}s'
            elif dur < 86400:
                h, rem = divmod(dur, 3600)
                total_duration = f'{h}h {rem // 60}m'
            else:
                d, rem = divmod(dur, 86400)
                total_duration = f'{d}d {rem // 3600}h'
        except Exception:
            pass

    result = {
        'ok': True,
        'taskId': task_id,
        'taskMeta': task_meta,
        'agentId': agent_id,
        'agentLabel': _STATE_LABELS.get(state, state),
        'lastActive': updated_at[:19].replace('T', ' ') if updated_at else None,
        'activity': activity,
        'activitySource': 'progress+session',
        'relatedAgents': sorted(list(related_agents)),
        'phaseDurations': phase_durations,
        'totalDuration': total_duration,
    }
    if todos_summary:
        result['todosSummary'] = todos_summary
    if has_resource_data:
        result['resourceSummary'] = {
            'totalTokens': total_tokens,
            'totalCost': round(total_cost, 4),
            'totalElapsedSec': total_elapsed,
        }
    return result


# State advancement order (for manual advancement)
_STATE_FLOW = {
    'Pending':  ('Taizi', 'Emperor', 'Taizi', 'Pending edict transferred to Taizi for triage'),
    'Taizi':    ('Zhongshu', 'Taizi', 'Zhongshu', 'Taizi triage complete, transfer to Zhongshu for drafting'),
    'Zhongshu': ('Menxia', 'Zhongshu', 'Menxia', 'Zhongshu proposal submitted to Menxia for review'),
    'Menxia':   ('Assigned', 'Menxia', 'Shangshu', 'Menxia approved, transfer to Shangshu for dispatch'),
    'Assigned': ('Doing', 'Shangshu', 'Six Ministries', 'Shangshu dispatching for execution'),
    'Next':     ('Doing', 'Shangshu', 'Six Ministries', 'Pending task starting execution'),
    'Doing':    ('Review', 'Six Ministries', 'Shangshu', 'Ministries complete, entering summary review'),
    'Review':   ('Done', 'Shangshu', 'Taizi', 'Full workflow complete, reporting back to Taizi for Emperor'),
}
_STATE_LABELS = {
    'Pending': 'Pending', 'Taizi': 'Taizi', 'Zhongshu': 'Zhongshu', 'Menxia': 'Menxia',
    'Assigned': 'Shangshu', 'Next': 'Pending Execution', 'Doing': 'In Progress', 'Review': 'Review', 'Done': 'Done',
}


def dispatch_for_state(task_id, task, new_state, trigger='state-transition'):
    """Auto-dispatch the corresponding Agent after state advance/approval (async background, non-blocking)."""
    agent_id = _STATE_AGENT_MAP.get(new_state)
    if agent_id is None and new_state in ('Doing', 'Next'):
        org = task.get('org', '')
        agent_id = _ORG_AGENT_MAP.get(org)
    if not agent_id:
        log.info(f'ℹ️ {task_id} new state {new_state} has no corresponding Agent, skipping auto-dispatch')
        return

    _update_task_scheduler(task_id, lambda t, s: (
        s.update({
            'lastDispatchAt': now_iso(),
            'lastDispatchStatus': 'queued',
            'lastDispatchAgent': agent_id,
            'lastDispatchTrigger': trigger,
        }),
        _scheduler_add_flow(t, f'Dispatch queued: {new_state} → {agent_id} ({trigger})', to=_STATE_LABELS.get(new_state, new_state))
    ))

    title = task.get('title', '(no title)')
    target_dept = task.get('targetDept', '')

    # Build targeted message based on agent_id
    _msgs = {
        'taizi': (
            f'📜 Imperial edict requires your attention\n'
            f'Task ID: {task_id}\n'
            f'Edict: {title}\n'
            f'⚠️ Task already exists in dashboard, do not create a duplicate. Use kanban_update.py to update status.\n'
            f'Please immediately transfer to Zhongshu for drafting an execution plan.'
        ),
        'zhongshu': (
            f'📜 Edict received at Zhongshu, please draft a plan\n'
            f'Task ID: {task_id}\n'
            f'Edict: {title}\n'
            f'⚠️ Task already recorded in dashboard, do not create a duplicate. Use kanban_update.py state to update status.\n'
            f'Please immediately draft an execution plan, completing the full Three Departments flow (Zhongshu draft → Menxia review → Shangshu dispatch → Ministries execute).'
        ),
        'menxia': (
            f'📋 Zhongshu proposal submitted for review\n'
            f'Task ID: {task_id}\n'
            f'Edict: {title}\n'
            f'⚠️ Task already exists in dashboard, do not create a duplicate.\n'
            f'Please review the Zhongshu proposal and provide approval or rejection.'
        ),
        'shangshu': (
            f'📮 Menxia approved, please dispatch for execution\n'
            f'Task ID: {task_id}\n'
            f'Edict: {title}\n'
            f'{"Suggested dispatch department: " + target_dept if target_dept else ""}\n'
            f'⚠️ Task already exists in dashboard, do not create a duplicate.\n'
            f'Please analyze the plan and dispatch to the Ministries for execution.'
        ),
    }
    msg = _msgs.get(agent_id, (
        f'📌 Please handle task\n'
        f'Task ID: {task_id}\n'
        f'Edict: {title}\n'
        f'⚠️ Task already exists in dashboard, do not create a duplicate. Use kanban_update.py to update status.'
    ))

    def _do_dispatch():
        try:
            if not _check_gateway_alive():
                log.warning(f'⚠️ {task_id} auto-dispatch skipped: Gateway not running')
                _update_task_scheduler(task_id, lambda t, s: s.update({
                    'lastDispatchAt': now_iso(),
                    'lastDispatchStatus': 'gateway-offline',
                    'lastDispatchAgent': agent_id,
                    'lastDispatchTrigger': trigger,
                }))
                return
            oclaw_bin = _get_openclaw_bin()
            if not oclaw_bin:
                log.error(f'❌ {task_id} auto-dispatch failed: openclaw binary not found — set OPENCLAW_BIN or add it to PATH')
                _update_task_scheduler(task_id, lambda t, s: s.update({
                    'lastDispatchAt': now_iso(),
                    'lastDispatchStatus': 'error',
                    'lastDispatchAgent': agent_id,
                    'lastDispatchTrigger': trigger,
                    'lastDispatchError': 'openclaw binary not found',
                }))
                return
            cmd = [oclaw_bin, 'agent', '--agent', agent_id, '-m', msg,
                   '--deliver', '--channel', 'feishu', '--timeout', '300']
            max_retries = 2
            err = ''
            for attempt in range(1, max_retries + 1):
                log.info(f'🔄 Auto-dispatching {task_id} → {agent_id} (attempt {attempt})...')
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=310)
                if result.returncode == 0:
                    log.info(f'✅ {task_id} auto-dispatch succeeded → {agent_id}')
                    _update_task_scheduler(task_id, lambda t, s: (
                        s.update({
                            'lastDispatchAt': now_iso(),
                            'lastDispatchStatus': 'success',
                            'lastDispatchAgent': agent_id,
                            'lastDispatchTrigger': trigger,
                            'lastDispatchError': '',
                        }),
                        _scheduler_add_flow(t, f'Dispatch succeeded: {agent_id} ({trigger})', to=t.get('org', ''))
                    ))
                    return
                err = result.stderr[:200] if result.stderr else result.stdout[:200]
                log.warning(f'⚠️ {task_id} auto-dispatch failed (attempt {attempt}): {err}')
                if attempt < max_retries:
                    import time
                    time.sleep(5)
            log.error(f'❌ {task_id} auto-dispatch ultimately failed → {agent_id}')
            _update_task_scheduler(task_id, lambda t, s: (
                s.update({
                    'lastDispatchAt': now_iso(),
                    'lastDispatchStatus': 'failed',
                    'lastDispatchAgent': agent_id,
                    'lastDispatchTrigger': trigger,
                    'lastDispatchError': err,
                }),
                _scheduler_add_flow(t, f'Dispatch failed: {agent_id} ({trigger})', to=t.get('org', ''))
            ))
        except subprocess.TimeoutExpired:
            log.error(f'❌ {task_id} auto-dispatch timed out → {agent_id}')
            _update_task_scheduler(task_id, lambda t, s: (
                s.update({
                    'lastDispatchAt': now_iso(),
                    'lastDispatchStatus': 'timeout',
                    'lastDispatchAgent': agent_id,
                    'lastDispatchTrigger': trigger,
                    'lastDispatchError': 'timeout',
                }),
                _scheduler_add_flow(t, f'Dispatch timed out: {agent_id} ({trigger})', to=t.get('org', ''))
            ))
        except Exception as e:
            log.warning(f'⚠️ {task_id} auto-dispatch exception: {e}')
            _update_task_scheduler(task_id, lambda t, s: (
                s.update({
                    'lastDispatchAt': now_iso(),
                    'lastDispatchStatus': 'error',
                    'lastDispatchAgent': agent_id,
                    'lastDispatchTrigger': trigger,
                    'lastDispatchError': str(e)[:200],
                }),
                _scheduler_add_flow(t, f'Dispatch error: {agent_id} ({trigger})', to=t.get('org', ''))
            ))

    threading.Thread(target=_do_dispatch, daemon=True).start()
    log.info(f'🚀 {task_id} post-advance auto-dispatch → {agent_id}')


def handle_advance_state(task_id, comment=''):
    """Manually advance a task to the next stage (for unblocking), then auto-dispatch the corresponding Agent."""
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        return {'ok': False, 'error': f'Task {task_id} not found'}
    cur = task.get('state', '')
    if cur not in _STATE_FLOW:
        return {'ok': False, 'error': f'Task {task_id} state is {cur}, cannot advance'}
    _ensure_scheduler(task)
    _scheduler_snapshot(task, f'advance-before-{cur}')
    next_state, from_dept, to_dept, default_remark = _STATE_FLOW[cur]
    remark = comment or default_remark

    task['state'] = next_state
    task['now'] = f'⬇️ Manual advance: {remark}'
    task.setdefault('flow_log', []).append({
        'at': now_iso(),
        'from': from_dept,
        'to': to_dept,
        'remark': f'⬇️ Manual advance: {remark}'
    })
    _scheduler_mark_progress(task, f'Manual advance {cur} -> {next_state}')
    task['updatedAt'] = now_iso()
    save_tasks(tasks)

    # 🚀 Auto-dispatch corresponding Agent after advance (no dispatch for Done state)
    if next_state != 'Done':
        dispatch_for_state(task_id, task, next_state)

    from_label = _STATE_LABELS.get(cur, cur)
    to_label = _STATE_LABELS.get(next_state, next_state)
    dispatched = ' (Agent auto-dispatched)' if next_state != 'Done' else ''
    return {'ok': True, 'message': f'{task_id} {from_label} → {to_label}{dispatched}'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Only log 4xx/5xx error requests
        if args and len(args) >= 1:
            status = str(args[0]) if args else ''
            if status.startswith('4') or status.startswith('5'):
                log.warning(f'{self.client_address[0]} {fmt % args}')

    def handle_error(self):
        pass  # Silently handle connection errors to avoid BrokenPipe crashes

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected, ignore

    def do_OPTIONS(self):
        self.send_response(200)
        cors_headers(self)
        self.end_headers()

    def send_json(self, data, code=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            cors_headers(self)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_file(self, path: pathlib.Path, mime='text/html; charset=utf-8'):
        if not path.exists():
            self.send_error(404)
            return
        try:
            body = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            cors_headers(self)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_static(self, rel_path):
        """Serve static files from the dist/ directory."""
        safe = rel_path.replace('\\', '/').lstrip('/')
        if '..' in safe:
            self.send_error(403)
            return True
        fp = DIST / safe
        if fp.is_file():
            mime = _MIME_TYPES.get(fp.suffix.lower(), 'application/octet-stream')
            self.send_file(fp, mime)
            return True
        return False

    def do_GET(self):
        p = urlparse(self.path).path.rstrip('/')
        if p in ('', '/dashboard', '/dashboard.html'):
            self.send_file(DIST / 'index.html')
        elif p == '/healthz':
            checks = {'dataDir': DATA.is_dir(), 'tasksReadable': (DATA / 'tasks_source.json').exists()}
            checks['dataWritable'] = os.access(str(DATA), os.W_OK)
            all_ok = all(checks.values())
            self.send_json({'status': 'ok' if all_ok else 'degraded', 'ts': now_iso(), 'checks': checks})
        elif p == '/api/live-status':
            self.send_json(read_json(DATA / 'live_status.json'))
        elif p == '/api/agent-config':
            self.send_json(read_json(DATA / 'agent_config.json'))
        elif p == '/api/model-change-log':
            self.send_json(read_json(DATA / 'model_change_log.json', []))
        elif p == '/api/last-result':
            self.send_json(read_json(DATA / 'last_model_change_result.json', {}))
        elif p == '/api/officials-stats':
            self.send_json(read_json(DATA / 'officials_stats.json', {}))
        elif p == '/api/morning-brief':
            self.send_json(read_json(DATA / 'morning_brief.json', {}))
        elif p == '/api/morning-config':
            self.send_json(read_json(DATA / 'morning_brief_config.json', {
                'categories': [
                    {'name': 'Politics', 'enabled': True},
                    {'name': 'Military', 'enabled': True},
                    {'name': 'Economy', 'enabled': True},
                    {'name': 'AI/LLM', 'enabled': True},
                ],
                'keywords': [], 'custom_feeds': [], 'feishu_webhook': '',
            }))
        elif p.startswith('/api/morning-brief/'):
            date = p.split('/')[-1]
            # Normalize date format to YYYYMMDD (accepts YYYY-MM-DD input)
            date_clean = date.replace('-', '')
            if not date_clean.isdigit() or len(date_clean) != 8:
                self.send_json({'ok': False, 'error': f'Invalid date format: {date}, please use YYYYMMDD'}, 400)
                return
            self.send_json(read_json(DATA / f'morning_brief_{date_clean}.json', {}))
        elif p == '/api/remote-skills-list':
            self.send_json(get_remote_skills_list())
        elif p.startswith('/api/skill-content/'):
            # /api/skill-content/{agentId}/{skillName}
            parts = p.replace('/api/skill-content/', '').split('/', 1)
            if len(parts) == 2:
                self.send_json(read_skill_content(parts[0], parts[1]))
            else:
                self.send_json({'ok': False, 'error': 'Usage: /api/skill-content/{agentId}/{skillName}'}, 400)
        elif p.startswith('/api/task-activity/'):
            task_id = p.replace('/api/task-activity/', '')
            if not task_id:
                self.send_json({'ok': False, 'error': 'task_id required'}, 400)
            else:
                self.send_json(get_task_activity(task_id))
        elif p.startswith('/api/scheduler-state/'):
            task_id = p.replace('/api/scheduler-state/', '')
            if not task_id:
                self.send_json({'ok': False, 'error': 'task_id required'}, 400)
            else:
                self.send_json(get_scheduler_state(task_id))
        elif p == '/api/agents-status':
            self.send_json(get_agents_status())
        elif p.startswith('/api/agent-activity/'):
            agent_id = p.replace('/api/agent-activity/', '')
            if not agent_id or not _SAFE_NAME_RE.match(agent_id):
                self.send_json({'ok': False, 'error': 'invalid agent_id'}, 400)
            else:
                self.send_json({'ok': True, 'agentId': agent_id, 'activity': get_agent_activity(agent_id)})
        elif self._serve_static(p):
            pass  # Already handled by _serve_static (JS/CSS/images etc.)
        else:
            # SPA fallback: non-/api/ paths return index.html
            if not p.startswith('/api/'):
                idx = DIST / 'index.html'
                if idx.exists():
                    self.send_file(idx)
                    return
            self.send_error(404)

    def do_POST(self):
        p = urlparse(self.path).path.rstrip('/')
        length = int(self.headers.get('Content-Length', 0))
        if length > MAX_REQUEST_BODY:
            self.send_json({'ok': False, 'error': f'Request body too large (max {MAX_REQUEST_BODY} bytes)'}, 413)
            return
        raw = self.rfile.read(length) if length else b''
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            self.send_json({'ok': False, 'error': 'invalid JSON'}, 400)
            return

        if p == '/api/morning-config':
            # Field validation
            if not isinstance(body, dict):
                self.send_json({'ok': False, 'error': 'Request body must be a JSON object'}, 400)
                return
            allowed_keys = {'categories', 'keywords', 'custom_feeds', 'feishu_webhook'}
            unknown = set(body.keys()) - allowed_keys
            if unknown:
                self.send_json({'ok': False, 'error': f'Unknown fields: {", ".join(unknown)}'}, 400)
                return
            if 'categories' in body and not isinstance(body['categories'], list):
                self.send_json({'ok': False, 'error': 'categories must be an array'}, 400)
                return
            if 'keywords' in body and not isinstance(body['keywords'], list):
                self.send_json({'ok': False, 'error': 'keywords must be an array'}, 400)
                return
            # Feishu Webhook validation
            webhook = body.get('feishu_webhook', '').strip()
            if webhook and not validate_url(webhook, allowed_schemes=('https',), allowed_domains=('open.feishu.cn', 'open.larksuite.com')):
                self.send_json({'ok': False, 'error': 'Feishu Webhook URL is invalid, only https://open.feishu.cn or open.larksuite.com domains are supported'}, 400)
                return
            cfg_path = DATA / 'morning_brief_config.json'
            cfg_path.write_text(json.dumps(body, ensure_ascii=False, indent=2))
            self.send_json({'ok': True, 'message': 'Subscription config saved'})
            return

        if p == '/api/scheduler-scan':
            threshold_sec = body.get('thresholdSec', 180)
            try:
                result = handle_scheduler_scan(threshold_sec)
                self.send_json(result)
            except Exception as e:
                self.send_json({'ok': False, 'error': f'scheduler scan failed: {e}'}, 500)
            return

        if p == '/api/repair-flow-order':
            try:
                self.send_json(handle_repair_flow_order())
            except Exception as e:
                self.send_json({'ok': False, 'error': f'repair flow order failed: {e}'}, 500)
            return

        if p == '/api/scheduler-retry':
            task_id = body.get('taskId', '').strip()
            reason = body.get('reason', '').strip()
            if not task_id:
                self.send_json({'ok': False, 'error': 'taskId required'}, 400)
                return
            self.send_json(handle_scheduler_retry(task_id, reason))
            return

        if p == '/api/scheduler-escalate':
            task_id = body.get('taskId', '').strip()
            reason = body.get('reason', '').strip()
            if not task_id:
                self.send_json({'ok': False, 'error': 'taskId required'}, 400)
                return
            self.send_json(handle_scheduler_escalate(task_id, reason))
            return

        if p == '/api/scheduler-rollback':
            task_id = body.get('taskId', '').strip()
            reason = body.get('reason', '').strip()
            if not task_id:
                self.send_json({'ok': False, 'error': 'taskId required'}, 400)
                return
            self.send_json(handle_scheduler_rollback(task_id, reason))
            return

        if p == '/api/morning-brief/refresh':
            force = body.get('force', True)  # manually triggered from dashboard defaults to force
            def do_refresh():
                try:
                    cmd = ['python3', str(SCRIPTS / 'fetch_morning_news.py')]
                    if force:
                        cmd.append('--force')
                    subprocess.run(cmd, timeout=120)
                    push_to_feishu()
                except Exception as e:
                    print(f'[refresh error] {e}', file=sys.stderr)
            threading.Thread(target=do_refresh, daemon=True).start()
            self.send_json({'ok': True, 'message': 'Collection triggered, refresh in ~30-60 seconds'})
            return

        if p == '/api/add-skill':
            agent_id = body.get('agentId', '').strip()
            skill_name = body.get('skillName', body.get('name', '')).strip()
            desc = body.get('description', '').strip() or skill_name
            trigger = body.get('trigger', '').strip()
            if not agent_id or not skill_name:
                self.send_json({'ok': False, 'error': 'agentId and skillName required'}, 400)
                return
            result = add_skill_to_agent(agent_id, skill_name, desc, trigger)
            self.send_json(result)
            return

        if p == '/api/add-remote-skill':
            agent_id = body.get('agentId', '').strip()
            skill_name = body.get('skillName', '').strip()
            source_url = body.get('sourceUrl', '').strip()
            description = body.get('description', '').strip()
            if not agent_id or not skill_name or not source_url:
                self.send_json({'ok': False, 'error': 'agentId, skillName, and sourceUrl required'}, 400)
                return
            result = add_remote_skill(agent_id, skill_name, source_url, description)
            self.send_json(result)
            return

        if p == '/api/remote-skills-list':
            result = get_remote_skills_list()
            self.send_json(result)
            return

        if p == '/api/update-remote-skill':
            agent_id = body.get('agentId', '').strip()
            skill_name = body.get('skillName', '').strip()
            if not agent_id or not skill_name:
                self.send_json({'ok': False, 'error': 'agentId and skillName required'}, 400)
                return
            result = update_remote_skill(agent_id, skill_name)
            self.send_json(result)
            return

        if p == '/api/remove-remote-skill':
            agent_id = body.get('agentId', '').strip()
            skill_name = body.get('skillName', '').strip()
            if not agent_id or not skill_name:
                self.send_json({'ok': False, 'error': 'agentId and skillName required'}, 400)
                return
            result = remove_remote_skill(agent_id, skill_name)
            self.send_json(result)
            return

        if p == '/api/task-action':
            task_id = body.get('taskId', '').strip()
            action = body.get('action', '').strip()  # stop, cancel, resume
            reason = body.get('reason', '').strip() or f'Emperor dashboard {action}'
            if not task_id or action not in ('stop', 'cancel', 'resume'):
                self.send_json({'ok': False, 'error': 'taskId and action(stop/cancel/resume) required'}, 400)
                return
            result = handle_task_action(task_id, action, reason)
            self.send_json(result)
            return

        if p == '/api/archive-task':
            task_id = body.get('taskId', '').strip() if body.get('taskId') else ''
            archived = body.get('archived', True)
            archive_all = body.get('archiveAllDone', False)
            if not task_id and not archive_all:
                self.send_json({'ok': False, 'error': 'taskId or archiveAllDone required'}, 400)
                return
            result = handle_archive_task(task_id, archived, archive_all)
            self.send_json(result)
            return

        if p == '/api/task-todos':
            task_id = body.get('taskId', '').strip()
            todos = body.get('todos', [])  # [{id, title, status}]
            if not task_id:
                self.send_json({'ok': False, 'error': 'taskId required'}, 400)
                return
            # todos input validation
            if not isinstance(todos, list) or len(todos) > 200:
                self.send_json({'ok': False, 'error': 'todos must be a list (max 200 items)'}, 400)
                return
            valid_statuses = {'not-started', 'in-progress', 'completed'}
            for td in todos:
                if not isinstance(td, dict) or 'id' not in td or 'title' not in td:
                    self.send_json({'ok': False, 'error': 'each todo must have id and title'}, 400)
                    return
                if td.get('status', 'not-started') not in valid_statuses:
                    td['status'] = 'not-started'
            result = update_task_todos(task_id, todos)
            self.send_json(result)
            return

        if p == '/api/create-task':
            title = body.get('title', '').strip()
            org = body.get('org', 'Zhongshu').strip()
            official = body.get('official', 'Zhongshu Chancellor').strip()
            priority = body.get('priority', 'normal').strip()
            template_id = body.get('templateId', '')
            params = body.get('params', {})
            if not title:
                self.send_json({'ok': False, 'error': 'title required'}, 400)
                return
            target_dept = body.get('targetDept', '').strip()
            result = handle_create_task(title, org, official, priority, template_id, params, target_dept)
            self.send_json(result)
            return

        if p == '/api/review-action':
            task_id = body.get('taskId', '').strip()
            action = body.get('action', '').strip()  # approve, reject
            comment = body.get('comment', '').strip()
            if not task_id or action not in ('approve', 'reject'):
                self.send_json({'ok': False, 'error': 'taskId and action(approve/reject) required'}, 400)
                return
            result = handle_review_action(task_id, action, comment)
            self.send_json(result)
            return

        if p == '/api/advance-state':
            task_id = body.get('taskId', '').strip()
            comment = body.get('comment', '').strip()
            if not task_id:
                self.send_json({'ok': False, 'error': 'taskId required'}, 400)
                return
            result = handle_advance_state(task_id, comment)
            self.send_json(result)
            return

        if p == '/api/agent-wake':
            agent_id = body.get('agentId', '').strip()
            message = body.get('message', '').strip()
            if not agent_id:
                self.send_json({'ok': False, 'error': 'agentId required'}, 400)
                return
            result = wake_agent(agent_id, message)
            self.send_json(result)
            return

        if p == '/api/set-model':
            agent_id = body.get('agentId', '').strip()
            model = body.get('model', '').strip()
            if not agent_id or not model:
                self.send_json({'ok': False, 'error': 'agentId and model required'}, 400)
                return

            # Write to pending (atomic)
            pending_path = DATA / 'pending_model_changes.json'
            def update_pending(current):
                current = [x for x in current if x.get('agentId') != agent_id]
                current.append({'agentId': agent_id, 'model': model})
                return current
            atomic_json_update(pending_path, update_pending, [])

            # Async apply
            def apply_async():
                try:
                    subprocess.run(['python3', str(SCRIPTS / 'apply_model_changes.py')], timeout=30)
                    subprocess.run(['python3', str(SCRIPTS / 'sync_agent_config.py')], timeout=10)
                except Exception as e:
                    print(f'[apply error] {e}', file=sys.stderr)

            threading.Thread(target=apply_async, daemon=True).start()
            self.send_json({'ok': True, 'message': f'Queued: {agent_id} → {model}'})
        else:
            self.send_error(404)


def main():
    parser = argparse.ArgumentParser(description='Three Departments & Six Ministries Dashboard Server')
    parser.add_argument('--port', type=int, default=7891)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--cors', default=None, help='Allowed CORS origin (default: reflect request Origin header)')
    args = parser.parse_args()

    global ALLOWED_ORIGIN
    ALLOWED_ORIGIN = args.cors

    server = HTTPServer((args.host, args.port), Handler)
    log.info(f'Three Departments & Six Ministries Dashboard started → http://{args.host}:{args.port}')
    print(f'   Press Ctrl+C to stop')

    # Startup recovery: re-dispatch queued tasks interrupted by previous kill
    threading.Timer(3.0, _startup_recover_queued_dispatches).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped')


if __name__ == '__main__':
    main()
