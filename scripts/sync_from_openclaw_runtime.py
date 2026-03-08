#!/usr/bin/env python3
import json
import pathlib
import time
import datetime
import traceback
import logging
from file_lock import atomic_json_write, atomic_json_read

log = logging.getLogger('sync_runtime')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
SYNC_STATUS = DATA / 'sync_status.json'
SESSIONS_ROOT = pathlib.Path.home() / '.openclaw' / 'agents'


def write_status(**kwargs):
    atomic_json_write(SYNC_STATUS, kwargs)


def ms_to_str(ts_ms):
    if not ts_ms:
        return '-'
    try:
        return datetime.datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '-'


def state_from_session(age_ms, aborted):
    if aborted:
        return 'Blocked'
    if age_ms <= 2 * 60 * 1000:
        return 'Doing'
    if age_ms <= 60 * 60 * 1000:
        return 'Review'
    return 'Next'


def detect_official(agent_id):
    mapping = {
        'main':     ('Crown Prince', 'Taizi'),      # legacy id for taizi
        'taizi':    ('Crown Prince', 'Taizi'),
        'zhongshu': ('Grand Chancellor', 'Zhongshu'),
        'menxia':   ('Chief Censor', 'Menxia'),
        'shangshu': ('Grand Secretary', 'Shangshu'),
        'hubu':     ('Minister of Revenue', 'Hubu'),
        'libu':     ('Minister of Rites', 'Libu'),
        'bingbu':   ('Minister of War', 'Bingbu'),
        'xingbu':   ('Minister of Justice', 'Xingbu'),
        'gongbu':   ('Minister of Works', 'Gongbu'),
        'libu_hr':  ('Minister of Personnel', 'Libu_hr'),
        'zaochao':  ('Morning Official', 'Zaochao'),
    }
    return mapping.get(agent_id, ('Grand Secretary', 'Shangshu'))


def load_activity(session_file, limit=12):
    p = pathlib.Path(session_file or '')
    if not p.exists():
        return []
    rows = []
    try:
        lines = p.read_text(errors='ignore').splitlines()
    except Exception:
        return []

    # Read all valid JSON lines first
    events = []
    for ln in lines:
        try:
            item = json.loads(ln)
            events.append(item)
        except:
            continue

    # Process events to extract meaningful activity
    # We want to show what the agent is *thinking* or *doing*
    for item in reversed(events):
        msg = item.get('message') or {}
        role = msg.get('role')
        ts = item.get('timestamp') or ''

        if role == 'toolResult':
            tool = msg.get('toolName', '-')
            details = msg.get('details') or {}
            # If tool output is short, show it
            content = msg.get('content', [{'text': ''}])[0].get('text', '')
            if len(content) < 50:
                text = f"Tool '{tool}' returned: {content}"
            else:
                text = f"Tool '{tool}' finished"
            rows.append({'at': ts, 'kind': 'tool', 'text': text})

        elif role == 'assistant':
            text = ''
            for c in msg.get('content', []):
                if c.get('type') == 'text' and c.get('text'):
                    raw_text = c.get('text').strip()
                    # Clean up common prefixes
                    clean_text = raw_text.replace('[[reply_to_current]]', '').strip()
                    if clean_text:
                        text = clean_text
                    break
            if text:
                # Prioritize showing the "thought" - usually the first few sentences
                summary = text.split('\n')[0]
                if len(summary) > 200:
                    summary = summary[:200] + '...'
                rows.append({'at': ts, 'kind': 'assistant', 'text': summary})
                
        elif role == 'user':
             # Also show what user asked, can be context relevant
             text = ''
             for c in msg.get('content', []):
                if c.get('type') == 'text':
                     text = c.get('text', '')[:100]
             if text:
                 rows.append({'at': ts, 'kind': 'user', 'text': f"User: {text}..."})

        if len(rows) >= limit:
            break

    # Re-order to chronological for display if needed, but the caller usually takes the first (latest)
    return rows


def build_task(agent_id, session_key, row, now_ms):
    session_id = row.get('sessionId') or session_key
    updated_at = row.get('updatedAt') or 0
    age_ms = max(0, now_ms - updated_at) if updated_at else 99 * 24 * 3600 * 1000
    aborted = bool(row.get('abortedLastRun'))
    state = state_from_session(age_ms, aborted)

    official, org = detect_official(agent_id)
    channel = row.get('lastChannel') or (row.get('origin') or {}).get('channel') or '-'
    session_file = row.get('sessionFile', '')
    
    # Try to get a more meaningful current status description from activity
    latest_act = 'Awaiting instructions'
    acts = load_activity(session_file, limit=5)
    
    # If the absolute latest is a tool result, look for the preceding assistant thought
    # because that explains *why* the tool was called.
    if acts:
        first_act = acts[0]
        if first_act['kind'] == 'tool' and len(acts) > 1:
            # Look for next assistant message (which is actually previous in time)
            for next_act in acts[1:]:
                if next_act['kind'] == 'assistant':
                    latest_act = f"Executing: {next_act['text'][:80]}"
                    break
            else:
                latest_act = first_act['text'][:60]
        elif first_act['kind'] == 'assistant':
             latest_act = f"Thinking: {first_act['text'][:80]}"
        else:
             latest_act = acts[0]['text'][:60]
    
    title_label = (row.get('origin') or {}).get('label') or session_key
    # Clean session title: agent:xxx:cron:uuid → scheduled task, agent:xxx:subagent:uuid → subtask
    import re
    if re.match(r'agent:\w+:cron:', title_label):
        title = f"{org} Scheduled Task"
    elif re.match(r'agent:\w+:subagent:', title_label):
        title = f"{org} Subtask"
    elif title_label == session_key or len(title_label) > 40:
        title = f"{org} Session"
    else:
        title = f"{title_label}"
    
    return {
        'id': f"OC-{agent_id}-{str(session_id)[:8]}",
        'title': title,
        'official': official,
        'org': org,
        'state': state,
        'now': latest_act,
        'eta': ms_to_str(updated_at),
        'block': 'Last run was interrupted' if aborted else 'none',
        'output': session_file,
        'flow': {
            'draft': f"agent={agent_id}",
            'review': f"updatedAt={ms_to_str(updated_at)}",
            'dispatch': f"sessionKey={session_key}",
        },
        'ac': 'Real-time mapping from OpenClaw runtime sessions',
        'activity': load_activity(session_file, limit=10),
        'sourceMeta': {
            'agentId': agent_id,
            'sessionKey': session_key,
            'sessionId': session_id,
            'updatedAt': updated_at,
            'ageMs': age_ms,
            'systemSent': bool(row.get('systemSent')),
            'abortedLastRun': aborted,
            'inputTokens': row.get('inputTokens'),
            'outputTokens': row.get('outputTokens'),
            'totalTokens': row.get('totalTokens'),
        }
    }


def main():
    start = time.time()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    now_ms = int(time.time() * 1000)

    try:
        tasks = []
        scan_files = 0

        if SESSIONS_ROOT.exists():
            for agent_dir in sorted(SESSIONS_ROOT.iterdir()):
                if not agent_dir.is_dir():
                    continue
                agent_id = agent_dir.name
                sessions_file = agent_dir / 'sessions' / 'sessions.json'
                if not sessions_file.exists():
                    continue
                scan_files += 1

                try:
                    raw = json.loads(sessions_file.read_text())
                except Exception:
                    continue

                if not isinstance(raw, dict):
                    continue

                for session_key, row in raw.items():
                    if not isinstance(row, dict):
                        continue
                    tasks.append(build_task(agent_id, session_key, row, now_ms))

        # merge mission control tasks
        mc_tasks_file = DATA / 'mission_control_tasks.json'
        if mc_tasks_file.exists():
            try:
                mc_tasks = json.loads(mc_tasks_file.read_text())
                if isinstance(mc_tasks, list):
                    tasks.extend(mc_tasks)
            except Exception:
                pass

        # merge manual parallel tasks (for dashboard parallel kanban display)
        manual_tasks_file = DATA / 'manual_parallel_tasks.json'
        if manual_tasks_file.exists():
            try:
                manual_tasks = json.loads(manual_tasks_file.read_text())
                if isinstance(manual_tasks, list):
                    tasks.extend(manual_tasks)
            except Exception:
                pass

        tasks.sort(key=lambda x: x.get('sourceMeta', {}).get('updatedAt', 0), reverse=True)

        # Deduplicate (keep only first = newest per id)
        seen_ids = set()
        deduped = []
        for t in tasks:
            if t['id'] not in seen_ids:
                seen_ids.add(t['id'])
                deduped.append(t)
        tasks = deduped

        # ── Filter out inactive system sessions to reduce dashboard noise ──
        # Rule: only keep sessions updated within 24 hours, exclude cron/subagent background tasks
        filtered_tasks = []
        one_day_ago = now_ms - 24 * 3600 * 1000
        for t in tasks:
            # Always keep JJC tasks (edict tasks from the Emperor)
            if str(t['id']).startswith('JJC'):
                filtered_tasks.append(t)
                continue
            
            # OC 任务过滤
            updated = t.get('sourceMeta', {}).get('updatedAt', 0)
            title = t.get('title', '')
            
            # 1. Exclude stale sessions (older than 24 hours)
            if updated < one_day_ago:
                continue
            
            # 2. Exclude pure background cron / subagent tasks, unless erroring
            if 'Scheduled Task' in title or 'Subtask' in title:
                # 只有当它 block 或者 error 时才显示，否则视为噪音
                if t.get('state') != 'Blocked':
                    continue

            # 3. Hide inactive OC sessions (no response for > 5 min) to avoid polluting kanban
            # Exception: Blocked (erroring) sessions or sessions created today
            state = t.get('state')
            # state_from_session: < 2min = Doing, < 60min = Review, else = Next
            if state not in ('Doing', 'Blocked'):
                # 如果不是正在进行或报错，就隐藏掉
                # 特例: 如果是 mission control (mc-) 的心跳，可能也没必要显示，除非 Doing
                continue

            filtered_tasks.append(t)
        
        tasks = filtered_tasks
        
        # ── Preserve existing JJC-* edict tasks (don't overwrite Emperor's edicts) ──
        # JJC task 'now' field is actively reported by Agents via kanban_update.py progress,
        # not passively scraped from session logs. Just merge here, no activity mapping.
        existing_tasks_file = DATA / 'tasks_source.json'
        if existing_tasks_file.exists():
            try:
                existing = json.loads(existing_tasks_file.read_text())
                jjc_existing = [t for t in existing if str(t.get('id', '')).startswith('JJC')]
                
                # 去掉 tasks 里已有的 JJC（以防重复），再把旨意放到最前面
                tasks = [t for t in tasks if not str(t.get('id', '')).startswith('JJC')]
                tasks = jjc_existing + tasks
            except Exception as e:
                log.error(f'merge existing JJC tasks failed: {e}')
                pass

        atomic_json_write(DATA / 'tasks_source.json', tasks)

        duration_ms = int((time.time() - start) * 1000)
        write_status(
            ok=True,
            lastSyncAt=now,
            durationMs=duration_ms,
            source='openclaw_runtime_sessions',
            recordCount=len(tasks),
            scannedSessionFiles=scan_files,
            missingFields={},
            error=None,
        )
        log.info(f'synced {len(tasks)} tasks from openclaw runtime in {duration_ms}ms')

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        write_status(
            ok=False,
            lastSyncAt=now,
            durationMs=duration_ms,
            source='openclaw_runtime_sessions',
            recordCount=0,
            missingFields={},
            error=f'{type(e).__name__}: {e}',
            traceback=traceback.format_exc(limit=3),
        )
        raise


if __name__ == '__main__':
    main()
