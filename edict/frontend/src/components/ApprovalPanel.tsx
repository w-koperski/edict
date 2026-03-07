import { useEffect, useState, useCallback } from 'react';
import { useStore } from '../store';
import { api, type ApprovalPendingItem, type ApprovalHistoryItem } from '../api';

function fmtTime(ts: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts.substring(0, 16).replace('T', ' ');
  }
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    urgent: '#ff5270', high: '#ff9a6a', normal: '#6a9eff', low: '#aaa',
  };
  return (
    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: `${colors[priority] || '#6a9eff'}22`, color: colors[priority] || '#6a9eff', fontWeight: 600, textTransform: 'uppercase' }}>
      {priority || 'normal'}
    </span>
  );
}

function PendingCard({ item, onAction }: { item: ApprovalPendingItem; onAction: (id: string, action: string) => void }) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--bdr)', borderLeft: '3px solid #ffd700', borderRadius: 8, padding: '14px 16px', marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <div>
          <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'monospace', marginRight: 8 }}>{item.id}</span>
          <PriorityBadge priority={item.priority} />
          {(item.reviewRound || 0) > 1 && (
            <span style={{ fontSize: 10, color: '#a07aff', marginLeft: 6 }}>Round {item.reviewRound}</span>
          )}
        </div>
        <span style={{ fontSize: 10, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{fmtTime(item.updatedAt)}</span>
      </div>
      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6, lineHeight: 1.4 }}>{item.title}</div>
      {item.menxiaOpinion && (
        <div style={{ fontSize: 11, color: '#6a9eff', background: '#6a9eff11', padding: '6px 10px', borderRadius: 6, marginBottom: 8, lineHeight: 1.5 }}>
          🔍 Menxia: {item.menxiaOpinion}
        </div>
      )}
      {item.now && (
        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 10, lineHeight: 1.4 }}>{item.now}</div>
      )}
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={() => onAction(item.id, 'approve')}
          style={{ flex: 1, padding: '7px 0', borderRadius: 6, border: '1px solid #2ecc8a44', background: '#2ecc8a18', color: '#2ecc8a', fontWeight: 600, cursor: 'pointer', fontSize: 13 }}
        >
          ✅ Imperial Approve
        </button>
        <button
          onClick={() => onAction(item.id, 'veto')}
          style={{ flex: 1, padding: '7px 0', borderRadius: 6, border: '1px solid #ff527044', background: '#ff527018', color: '#ff5270', fontWeight: 600, cursor: 'pointer', fontSize: 13 }}
        >
          🚫 Imperial Veto
        </button>
      </div>
    </div>
  );
}

function HistoryRow({ item }: { item: ApprovalHistoryItem }) {
  const isApprove = item.action === 'approve';
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--bdr)' }}>
      <span style={{ fontSize: 16, marginTop: 2 }}>{isApprove ? '✅' : '🚫'}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--muted)' }}>{item.taskId}</span>
          <span style={{ fontWeight: 600, fontSize: 12, color: isApprove ? '#2ecc8a' : '#ff5270' }}>
            {isApprove ? 'Approved' : 'Vetoed'}
          </span>
          <span style={{ fontSize: 10, color: 'var(--muted)' }}>{fmtTime(item.at)}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--fg)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.title}</div>
        {item.comment && (
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>"{item.comment}"</div>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2, fontSize: 10, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
        <span>→ {item.newState}</span>
      </div>
    </div>
  );
}

export default function ApprovalPanel() {
  const toast = useStore((s) => s.toast);
  const loadAll = useStore((s) => s.loadAll);

  const [pending, setPending] = useState<ApprovalPendingItem[]>([]);
  const [history, setHistory] = useState<ApprovalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'pending' | 'history'>('pending');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pRes, hRes] = await Promise.all([api.approvalPending(), api.approvalHistory()]);
      if (pRes.ok) setPending(pRes.pending || []);
      if (hRes.ok) setHistory(hRes.history || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 8000);
    return () => clearInterval(timer);
  }, [loadData]);

  const handleAction = async (taskId: string, action: string) => {
    const label = action === 'approve' ? 'Imperial Approve' : 'Imperial Veto';
    const comment = prompt(`${label} ${taskId}\n\nEnter comment (optional):`);
    if (comment === null) return;
    try {
      const r = await api.imperialApproval(taskId, action, comment || '');
      if (r.ok) {
        toast(`🏅 ${taskId} ${action === 'approve' ? 'Approved' : 'Vetoed'}`, 'ok');
        loadAll();
        loadData();
      } else {
        toast(r.error || 'Action failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
  };

  return (
    <div style={{ padding: '20px 24px', maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <span style={{ fontSize: 28 }}>🏅</span>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Imperial Approval</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>One-click approve or veto Menxia review results</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {pending.length > 0 && (
            <span style={{ background: '#ffd70033', color: '#ffd700', border: '1px solid #ffd70066', padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 700 }}>
              {pending.length} pending
            </span>
          )}
          <button onClick={loadData} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid var(--bdr)', background: 'var(--card)', cursor: 'pointer', fontSize: 12, color: 'var(--fg)' }}>
            ⟳ Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '1px solid var(--bdr)' }}>
        {(['pending', 'history'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 20px', border: 'none', background: 'none', cursor: 'pointer', fontSize: 13,
              fontWeight: tab === t ? 700 : 400,
              color: tab === t ? 'var(--acc)' : 'var(--muted)',
              borderBottom: tab === t ? '2px solid var(--acc)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {t === 'pending' ? `⏳ Pending Approval${pending.length > 0 ? ` (${pending.length})` : ''}` : '📋 Approval History'}
          </button>
        ))}
      </div>

      {loading && <div style={{ textAlign: 'center', color: 'var(--muted)', padding: 40 }}>Loading…</div>}

      {!loading && tab === 'pending' && (
        <>
          {pending.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>👑</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>No edicts awaiting imperial approval</div>
              <div style={{ fontSize: 12 }}>When Menxia completes a review, it will appear here for your approval</div>
            </div>
          ) : (
            <>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
                {pending.length} edict{pending.length !== 1 ? 's' : ''} pending your imperial review
              </div>
              {pending.map((item) => (
                <PendingCard key={item.id} item={item} onAction={handleAction} />
              ))}
            </>
          )}
        </>
      )}

      {!loading && tab === 'history' && (
        <>
          {history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>No approval history yet</div>
              <div style={{ fontSize: 12 }}>Imperial decrees will be recorded here</div>
            </div>
          ) : (
            <div style={{ background: 'var(--card)', border: '1px solid var(--bdr)', borderRadius: 8, padding: '0 16px' }}>
              {history.map((item, i) => (
                <HistoryRow key={i} item={item} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
