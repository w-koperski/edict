#!/usr/bin/env python3
"""
Kanban task update tool - Edict compatibility layer

Maintains the same CLI interface as the legacy version, internally calls the Edict REST API.
Falls back to writing JSON files if the API is unavailable (transition period safeguard).

Usage (100% compatible with legacy version):
  python3 kanban_update.py create JJC-20260223-012 "Task title" Zhongshu Zhongshu Chancellor
  python3 kanban_update.py state JJC-20260223-012 Menxia "Planning proposal submitted to Menxia"
  python3 kanban_update.py flow JJC-20260223-012 "Zhongshu" "Menxia" "Planning proposal submitted for review"
  python3 kanban_update.py done JJC-20260223-012 "/path/to/output" "Task completion summary"
  python3 kanban_update.py todo JJC-20260223-012 1 "Implement API interface" in-progress
  python3 kanban_update.py progress JJC-20260223-012 "Analyzing requirements" "1.Research✅|2.Docs🔄|3.Prototype"
"""

import json
import logging
import os
import re
import sys
import pathlib

log = logging.getLogger('kanban')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

# Edict API address — environment variable > default localhost:8000
EDICT_API_URL = os.environ.get('EDICT_API_URL', 'http://localhost:8000')

# Whether to enable API mode (EDICT_MODE=api | json | auto)
EDICT_MODE = os.environ.get('EDICT_MODE', 'auto').lower()

# ── Text sanitization logic (identical to legacy version) ──

_MIN_TITLE_LEN = 6
_JUNK_TITLES = {
    '?', '？', '好', '好的', '是', '否', '不', '不是', '对', '了解', '收到',
    '嗯', '哦', '知道了', '开启了么', '可以', '不行', '行', 'ok', 'yes', 'no',
    '你去开启', '测试', '试试', '看看',
}

STATE_ORG_MAP = {
    'Taizi': 'Taizi', 'Zhongshu': 'Zhongshu', 'Menxia': 'Menxia', 'Assigned': 'Shangshu',
    'Doing': 'In Progress', 'Review': 'Shangshu', 'Done': 'Completed', 'Blocked': 'Blocked',
}

# State → Edict TaskState value mapping
_STATE_TO_EDICT = {
    'Taizi': 'taizi', 'Zhongshu': 'zhongshu', 'Menxia': 'menxia',
    'Assigned': 'assigned', 'Next': 'next', 'Doing': 'doing',
    'Review': 'review', 'Done': 'done', 'Blocked': 'blocked',
    'Cancelled': 'cancelled', 'Pending': 'pending',
}


def _sanitize_text(raw, max_len=80):
    t = (raw or '').strip()
    t = re.split(r'\n*Conversation\b', t, maxsplit=1)[0].strip()
    t = re.split(r'\n*```', t, maxsplit=1)[0].strip()
    t = re.sub(r'[/\\.~][A-Za-z0-9_\-./]+(?:\.(?:py|js|ts|json|md|sh|yaml|yml|txt|csv|html|css|log))?', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'^(传旨|下旨)([（(][^)）]*[)）])?[：:\uff1a]\s*', '', t)
    t = re.sub(r'(message_id|session_id|chat_id|open_id|user_id|tenant_key)\s*[:=]\s*\S+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > max_len:
        t = t[:max_len] + '…'
    return t


def _sanitize_title(raw):
    return _sanitize_text(raw, 80)


def _sanitize_remark(raw):
    return _sanitize_text(raw, 120)


def _is_valid_task_title(title):
    t = (title or '').strip()
    if len(t) < _MIN_TITLE_LEN:
        return False, f'Title too short ({len(t)}<{_MIN_TITLE_LEN} chars), likely not an edict'
    if t.lower() in _JUNK_TITLES:
        return False, f'Title "{t}" is not a valid edict'
    if re.fullmatch(r'[\s?？!！.。,，…·\-—~]+', t):
        return False, 'Title contains only punctuation'
    if re.match(r'^[/\\~.]', t) or re.search(r'/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+', t):
        return False, f'Title looks like a file path, please summarize the task in plain text'
    if re.fullmatch(r'[\s\W]*', t):
        return False, 'Title is empty after sanitization'
    return True, ''


def _infer_agent_id():
    for k in ('OPENCLAW_AGENT_ID', 'OPENCLAW_AGENT', 'AGENT_ID'):
        v = (os.environ.get(k) or '').strip()
        if v:
            return v
    cwd = str(pathlib.Path.cwd())
    m = re.search(r'workspace-([a-zA-Z0-9_\-]+)', cwd)
    if m:
        return m.group(1)
    return 'system'


# ── API 客户端 ──

def _api_available() -> bool:
    """Check if the Edict API is available."""
    if EDICT_MODE == 'json':
        return False
    if EDICT_MODE == 'api':
        return True
    # auto mode: probe
    try:
        import urllib.request
        req = urllib.request.Request(f"{EDICT_API_URL}/health", method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _api_post(path: str, data: dict) -> dict | None:
    """Send a POST request to the Edict API."""
    try:
        import urllib.request
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f"{EDICT_API_URL}{path}",
            data=body,
            method='POST',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f'API call failed ({path}): {e}')
        return None


def _api_put(path: str, data: dict) -> dict | None:
    """Send a PUT request to the Edict API."""
    try:
        import urllib.request
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f"{EDICT_API_URL}{path}",
            data=body,
            method='PUT',
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.warning(f'API call failed ({path}): {e}')
        return None


# ── Command → API call ──

# Cache API availability
_api_ok = None


def _check_api():
    global _api_ok
    if _api_ok is None:
        _api_ok = _api_available()
        if _api_ok:
            log.debug('Edict API available, using API mode')
        else:
            log.debug('Edict API unavailable, falling back to JSON mode')
    return _api_ok


def _fallback_json():
    """Fallback: import legacy kanban_update logic."""
    # Fall back to the legacy implementation in the same directory
    old_path = pathlib.Path(__file__).parent / 'kanban_update_legacy.py'
    if old_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('kanban_legacy', old_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def cmd_create(task_id, title, state, org, official, remark=None):
    title = _sanitize_title(title)
    valid, reason = _is_valid_task_title(title)
    if not valid:
        log.warning(f'⚠️ Rejected creation of {task_id}: {reason}')
        print(f'[kanban] Creation rejected: {reason}', flush=True)
        return

    if _check_api():
        edict_state = _STATE_TO_EDICT.get(state, state.lower())
        result = _api_post('/api/tasks', {
            'title': title,
            'description': remark or f'Edict issued: {title}',
            'priority': 'normal',
            'assignee_org': org,
            'creator': official,
            'tags': [task_id],
            'meta': {'legacy_id': task_id, 'legacy_state': state},
        })
        if result:
            log.info(f'✅ 创建 {task_id} → Edict {result.get("task_id", "?")} | {title[:30]}')
            return

    # 降级
    legacy = _fallback_json()
    if legacy:
        legacy.cmd_create(task_id, title, state, org, official, remark)
    else:
        log.error(f'Cannot create task: API unavailable and no fallback module')


def cmd_state(task_id, new_state, now_text=None):
    if _check_api():
        edict_state = _STATE_TO_EDICT.get(new_state, new_state.lower())
        agent = _infer_agent_id()
        # Need to find edict task_id via legacy_id first
        # Using legacy_id tag search for now
        result = _api_post(f'/api/tasks/by-legacy/{task_id}/transition', {
            'new_state': edict_state,
            'agent': agent,
            'reason': now_text or f'State updated to {new_state}',
        })
        if result:
            log.info(f'✅ {task_id} 状态更新 → {new_state}')
            return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_state(task_id, new_state, now_text)
    else:
        log.error(f'Cannot update state: API unavailable and no fallback module')


def cmd_flow(task_id, from_dept, to_dept, remark):
    clean_remark = _sanitize_remark(remark)
    if _check_api():
        agent = _infer_agent_id()
        result = _api_post(f'/api/tasks/by-legacy/{task_id}/progress', {
            'agent': agent,
            'content': f'流转: {from_dept} → {to_dept} | {clean_remark}',
        })
        if result:
            log.info(f'✅ {task_id} 流转记录: {from_dept} → {to_dept}')
            return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_flow(task_id, from_dept, to_dept, remark)


def cmd_done(task_id, output_path='', summary=''):
    if _check_api():
        agent = _infer_agent_id()
        result = _api_post(f'/api/tasks/by-legacy/{task_id}/transition', {
            'new_state': 'done',
            'agent': agent,
            'reason': summary or 'Task completed',
        })
        if result:
            log.info(f'✅ {task_id} 已完成')
            return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_done(task_id, output_path, summary)


def cmd_block(task_id, reason):
    if _check_api():
        agent = _infer_agent_id()
        result = _api_post(f'/api/tasks/by-legacy/{task_id}/transition', {
            'new_state': 'blocked',
            'agent': agent,
            'reason': reason,
        })
        if result:
            log.warning(f'⚠️ {task_id} 已阻塞: {reason}')
            return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_block(task_id, reason)


def cmd_progress(task_id, now_text, todos_pipe='', tokens=0, cost=0.0, elapsed=0):
    clean = _sanitize_remark(now_text)

    # Parse todos
    parsed_todos = None
    if todos_pipe:
        new_todos = []
        for i, item in enumerate(todos_pipe.split('|'), 1):
            item = item.strip()
            if not item:
                continue
            if item.endswith('✅'):
                status = 'completed'
                title = item[:-1].strip()
            elif item.endswith('🔄'):
                status = 'in-progress'
                title = item[:-1].strip()
            else:
                status = 'not-started'
                title = item
            new_todos.append({'id': str(i), 'title': title, 'status': status})
        if new_todos:
            parsed_todos = new_todos

    if _check_api():
        agent = _infer_agent_id()
        # Update progress
        _api_post(f'/api/tasks/by-legacy/{task_id}/progress', {
            'agent': agent,
            'content': clean,
        })
        # Update todos
        if parsed_todos:
            _api_put(f'/api/tasks/by-legacy/{task_id}/todos', {
                'todos': parsed_todos,
            })
        log.info(f'📡 {task_id} progress: {clean[:40]}...')
        return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_progress(task_id, now_text, todos_pipe, tokens, cost, elapsed)


def cmd_todo(task_id, todo_id, title, status='not-started', detail=''):
    if status not in ('not-started', 'in-progress', 'completed'):
        status = 'not-started'

    if _check_api():
        # Read existing todos and update — simplified to direct progress update here
        agent = _infer_agent_id()
        _api_post(f'/api/tasks/by-legacy/{task_id}/progress', {
            'agent': agent,
            'content': f'Todo #{todo_id}: {title} → {status}',
        })
        log.info(f'✅ {task_id} todo: {todo_id} → {status}')
        return

    legacy = _fallback_json()
    if legacy:
        legacy.cmd_todo(task_id, todo_id, title, status, detail)


# ── CLI 分发 ──

_CMD_MIN_ARGS = {
    'create': 6, 'state': 3, 'flow': 5, 'done': 2, 'block': 3, 'todo': 4, 'progress': 3,
}

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    if cmd in _CMD_MIN_ARGS and len(args) < _CMD_MIN_ARGS[cmd]:
        print(f'Error: "{cmd}" command requires at least {_CMD_MIN_ARGS[cmd]} arguments, got {len(args)}')
        print(__doc__)
        sys.exit(1)

    if cmd == 'create':
        cmd_create(args[1], args[2], args[3], args[4], args[5], args[6] if len(args) > 6 else None)
    elif cmd == 'state':
        cmd_state(args[1], args[2], args[3] if len(args) > 3 else None)
    elif cmd == 'flow':
        cmd_flow(args[1], args[2], args[3], args[4])
    elif cmd == 'done':
        cmd_done(args[1], args[2] if len(args) > 2 else '', args[3] if len(args) > 3 else '')
    elif cmd == 'block':
        cmd_block(args[1], args[2])
    elif cmd == 'todo':
        todo_pos = []
        todo_detail = ''
        ti = 1
        while ti < len(args):
            if args[ti] == '--detail' and ti + 1 < len(args):
                todo_detail = args[ti + 1]; ti += 2
            else:
                todo_pos.append(args[ti]); ti += 1
        cmd_todo(
            todo_pos[0] if len(todo_pos) > 0 else '',
            todo_pos[1] if len(todo_pos) > 1 else '',
            todo_pos[2] if len(todo_pos) > 2 else '',
            todo_pos[3] if len(todo_pos) > 3 else 'not-started',
            detail=todo_detail,
        )
    elif cmd == 'progress':
        pos_args = []
        kw = {}
        i = 1
        while i < len(args):
            if args[i] == '--tokens' and i + 1 < len(args):
                kw['tokens'] = args[i + 1]; i += 2
            elif args[i] == '--cost' and i + 1 < len(args):
                kw['cost'] = args[i + 1]; i += 2
            elif args[i] == '--elapsed' and i + 1 < len(args):
                kw['elapsed'] = args[i + 1]; i += 2
            else:
                pos_args.append(args[i]); i += 1
        cmd_progress(
            pos_args[0] if len(pos_args) > 0 else '',
            pos_args[1] if len(pos_args) > 1 else '',
            pos_args[2] if len(pos_args) > 2 else '',
            tokens=kw.get('tokens', 0),
            cost=kw.get('cost', 0.0),
            elapsed=kw.get('elapsed', 0),
        )
    else:
        print(__doc__)
        sys.exit(1)
