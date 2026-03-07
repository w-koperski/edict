"""tests for dashboard/server.py route handling"""
import json, pathlib, sys, threading, time
from http.client import HTTPConnection

# Add project paths
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dashboard'))
sys.path.insert(0, str(ROOT / 'scripts'))


def test_healthz(tmp_path):
    """GET /healthz returns 200 with status ok."""
    # Create minimal data dir
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'live_status.json').write_text('{}')
    (data_dir / 'agent_config.json').write_text('{}')

    # Import and patch server
    import server as srv
    srv.DATA = data_dir

    from http.server import HTTPServer
    port = 18971

    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    time.sleep(0.1)
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/healthz')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['status'] in ('ok', 'degraded')

    httpd.server_close()


def test_approval_pending_empty(tmp_path):
    """GET /api/approval-pending returns empty list when no tasks."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text('[]')

    import server as srv
    srv.DATA = data_dir

    from http.server import HTTPServer
    port = 18972
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    time.sleep(0.1)
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/approval-pending')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['pending'] == []
    assert body['count'] == 0

    httpd.server_close()


def test_approval_pending_with_task(tmp_path):
    """GET /api/approval-pending returns tasks in AwaitingApproval state."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    tasks = [
        {'id': 'JJC-TEST-001', 'title': '测试任务', 'state': 'AwaitingApproval',
         'org': '待御批', 'now': '门下省审议通过', 'updatedAt': '2026-01-01T00:00:00Z',
         'flow_log': [{'at': '2026-01-01T00:00:00Z', 'from': '门下省', 'to': '待御批', 'remark': '✅ Approved'}],
         'archived': False},
    ]
    (data_dir / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False))

    import server as srv
    srv.DATA = data_dir

    from http.server import HTTPServer
    port = 18973
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    time.sleep(0.1)
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/approval-pending')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['count'] == 1
    assert body['pending'][0]['id'] == 'JJC-TEST-001'

    httpd.server_close()


def test_imperial_approval_action(tmp_path):
    """POST /api/imperial-approval approves an AwaitingApproval task."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    tasks = [
        {'id': 'JJC-TEST-002', 'title': '测试御批', 'state': 'AwaitingApproval',
         'org': '待御批', 'now': '等待御批', 'updatedAt': '2026-01-01T00:00:00Z',
         'flow_log': [], 'archived': False},
    ]
    (data_dir / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False))

    import server as srv
    orig_data = srv.DATA
    orig_dispatch = srv.dispatch_for_state
    srv.DATA = data_dir
    # Mock dispatch to avoid side effects
    srv.dispatch_for_state = lambda *a, **kw: None

    result = srv.handle_imperial_approval('JJC-TEST-002', 'approve', '御批测试')
    assert result['ok'] is True
    assert 'JJC-TEST-002' in result['message']

    # Verify task state changed
    updated = json.loads((data_dir / 'tasks_source.json').read_text())
    task = next(t for t in updated if t['id'] == 'JJC-TEST-002')
    assert task['state'] == 'Assigned'

    srv.DATA = orig_data
    srv.dispatch_for_state = orig_dispatch


def test_imperial_approval_veto(tmp_path):
    """POST /api/imperial-approval vetoes an AwaitingApproval task."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    tasks = [
        {'id': 'JJC-TEST-003', 'title': '测试御批封驳', 'state': 'AwaitingApproval',
         'org': '待御批', 'now': '等待御批', 'updatedAt': '2026-01-01T00:00:00Z',
         'flow_log': [], 'archived': False},
    ]
    (data_dir / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False))

    import server as srv
    orig_data = srv.DATA
    orig_dispatch = srv.dispatch_for_state
    srv.DATA = data_dir
    srv.dispatch_for_state = lambda *a, **kw: None

    result = srv.handle_imperial_approval('JJC-TEST-003', 'veto', '需修改')
    assert result['ok'] is True

    updated = json.loads((data_dir / 'tasks_source.json').read_text())
    task = next(t for t in updated if t['id'] == 'JJC-TEST-003')
    assert task['state'] == 'Zhongshu'

    srv.DATA = orig_data
    srv.dispatch_for_state = orig_dispatch


def test_imperial_approval_wrong_state(tmp_path):
    """handle_imperial_approval rejects tasks not in AwaitingApproval state."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    tasks = [
        {'id': 'JJC-TEST-004', 'title': '测试错误状态', 'state': 'Menxia',
         'org': '门下省', 'now': '审议中', 'updatedAt': '2026-01-01T00:00:00Z',
         'flow_log': [], 'archived': False},
    ]
    (data_dir / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False))

    import server as srv
    orig_data = srv.DATA
    srv.DATA = data_dir

    result = srv.handle_imperial_approval('JJC-TEST-004', 'approve', '')
    assert result['ok'] is False
    assert '不在御批队列' in result['error']

    srv.DATA = orig_data
