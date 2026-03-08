#!/usr/bin/env python3
"""End-to-end tests for kanban_update.py: sanitization + create + flow full workflow

Can be run with pytest or directly with python3.
"""
import sys, os, json, pathlib, pytest

# Switch to scripts directory (file_lock dependency)
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
os.chdir(_SCRIPTS_DIR)
sys.path.insert(0, '.')

from kanban_update import (
    _sanitize_title, _sanitize_remark, _is_valid_task_title,
    cmd_create, cmd_flow, cmd_state, cmd_done, load, TASKS_FILE
)

# ── Ensure data directory and tasks_source.json exist (may be missing in CI)
data_dir = TASKS_FILE.parent
if data_dir.exists() and not data_dir.is_dir():
    data_dir.unlink()
data_dir.mkdir(parents=True, exist_ok=True)
if not TASKS_FILE.exists():
    TASKS_FILE.write_text('[]')


def _get_task(tid):
    return next((x for x in load() if x['id'] == tid), None)


@pytest.fixture(autouse=True)
def _backup_and_restore():
    """Back up data before each test, restore and clean up test tasks after."""
    backup = TASKS_FILE.read_text()
    yield
    TASKS_FILE.write_text(backup)
    tasks = json.loads(TASKS_FILE.read_text())
    tasks = [t for t in tasks if not t.get('id', '').startswith('JJC-TEST-')]
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))


# ── TEST 1: Dirty title (with file path + Conversation) should be sanitized then created
def test_dirty_title_cleaned():
    cmd_create('JJC-TEST-E2E-01',
        'Review project /Users/bingsen/clawd/openclaw-edict/this-project\nConversation info (xxx)',
        'Zhongshu', 'Zhongshu', 'Grand Chancellor',
        'Edict issued (auto-pre-create): Review /Users/bingsen/clawd/project')
    t = _get_task('JJC-TEST-E2E-01')
    assert t is not None, "Task should be created"
    assert '/Users' not in t['title'], f"Title should not contain path: {t['title']}"
    assert 'Conversation' not in t['title'], f"Title should not contain Conversation: {t['title']}"
    assert '/Users' not in t['flow_log'][0]['remark'], f"remark should not contain path: {t['flow_log'][0]['remark']}"


# ── TEST 2: Pure file path title should be rejected
def test_pure_path_rejected():
    cmd_create('JJC-TEST-E2E-02', '/Users/bingsen/clawd/openclaw-edict/', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    assert _get_task('JJC-TEST-E2E-02') is None, "Pure path title should be rejected"


# ── TEST 3: Normal title should create normally
def test_normal_title():
    cmd_create('JJC-TEST-E2E-03', 'Research industrial data analysis LLM application plan', 'Zhongshu', 'Zhongshu', 'Grand Chancellor', 'Taizi compiled edict')
    t = _get_task('JJC-TEST-E2E-03')
    assert t is not None, "Normal task should be created"
    assert t['title'] == 'Research industrial data analysis LLM application plan', f"Title should be fully preserved: {t['title']}"


# ── TEST 4: flow remark sanitization
def test_flow_remark_cleaned():
    cmd_create('JJC-TEST-E2E-04', 'Research industrial data analysis LLM application plan', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    cmd_flow('JJC-TEST-E2E-04', 'Taizi', 'Zhongshu', 'Edict transmitted: Review /Users/bingsen/clawd/xxx project Conversation blah')
    t = _get_task('JJC-TEST-E2E-04')
    assert t is not None
    last_flow = t['flow_log'][-1]
    assert '/Users' not in last_flow['remark'], f"remark should not contain path: {last_flow['remark']}"
    assert 'Conversation' not in last_flow['remark'], f"remark should not contain Conversation: {last_flow['remark']}"


# ── TEST 5: Too-short title rejected
def test_short_title_rejected():
    cmd_create('JJC-TEST-E2E-05', 'ok', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    assert _get_task('JJC-TEST-E2E-05') is None, "Short title should be rejected"


# ── TEST 6: state update + org auto-sync
def test_state_update():
    cmd_create('JJC-TEST-E2E-07', 'Test state update and org sync functionality', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    cmd_state('JJC-TEST-E2E-07', 'Menxia', 'Proposal submitted to Menxia for review')
    t = _get_task('JJC-TEST-E2E-07')
    assert t is not None
    assert t['state'] == 'Menxia', f"state should be Menxia: {t['state']}"
    assert t['org'] == 'Menxia', f"org should be Menxia: {t['org']}"


# ── TEST 7: done completion
def test_done():
    cmd_create('JJC-TEST-E2E-08', 'Test task completion state marking functionality', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    cmd_done('JJC-TEST-E2E-08', '/tmp/output.md', 'Task completed')
    t = _get_task('JJC-TEST-E2E-08')
    assert t is not None
    assert t['state'] == 'Done', f"state should be Done: {t['state']}"


# ── TEST 8: Completed task cannot be overwritten
def test_done_not_overwritable():
    cmd_create('JJC-TEST-E2E-09', 'Test completed task cannot be overwritten protection', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    cmd_done('JJC-TEST-E2E-09', '/tmp/output.md', 'Task completed')
    cmd_create('JJC-TEST-E2E-09', 'Attempting to overwrite a completed task title', 'Zhongshu', 'Zhongshu', 'Grand Chancellor')
    t = _get_task('JJC-TEST-E2E-09')
    assert t is not None
    assert t['state'] == 'Done', f"Should still be Done: {t['state']}"


# ── 支持直接运行 python3 tests/test_e2e_kanban.py
if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
