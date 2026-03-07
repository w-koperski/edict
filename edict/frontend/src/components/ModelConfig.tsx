import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api } from '../api';

const FALLBACK_MODELS = [
  { id: 'anthropic/claude-sonnet-4-6', l: 'Claude Sonnet 4.6', p: 'Anthropic' },
  { id: 'anthropic/claude-opus-4-5', l: 'Claude Opus 4.5', p: 'Anthropic' },
  { id: 'anthropic/claude-haiku-3-5', l: 'Claude Haiku 3.5', p: 'Anthropic' },
  { id: 'openai/gpt-4o', l: 'GPT-4o', p: 'OpenAI' },
  { id: 'openai/gpt-4o-mini', l: 'GPT-4o Mini', p: 'OpenAI' },
  { id: 'google/gemini-2.5-pro', l: 'Gemini 2.5 Pro', p: 'Google' },
  { id: 'copilot/claude-sonnet-4', l: 'Claude Sonnet 4', p: 'Copilot' },
  { id: 'copilot/claude-opus-4.5', l: 'Claude Opus 4.5', p: 'Copilot' },
  { id: 'copilot/gpt-4o', l: 'GPT-4o', p: 'Copilot' },
  { id: 'copilot/gemini-2.5-pro', l: 'Gemini 2.5 Pro', p: 'Copilot' },
];

export default function ModelConfig() {
  const agentConfig = useStore((s) => s.agentConfig);
  const changeLog = useStore((s) => s.changeLog);
  const loadAgentConfig = useStore((s) => s.loadAgentConfig);
  const toast = useStore((s) => s.toast);

  const [selMap, setSelMap] = useState<Record<string, string>>({});
  const [statusMap, setStatusMap] = useState<Record<string, { cls: string; text: string }>>({});

  useEffect(() => {
    loadAgentConfig();
  }, [loadAgentConfig]);

  useEffect(() => {
    if (agentConfig?.agents) {
      const m: Record<string, string> = {};
      agentConfig.agents.forEach((ag) => {
        m[ag.id] = ag.model;
      });
      setSelMap(m);
    }
  }, [agentConfig]);

  if (!agentConfig?.agents) {
    return <div className="empty" style={{ gridColumn: '1/-1' }}>⚠️ Please start the local server first</div>;
  }

  const models = agentConfig.knownModels?.length
    ? agentConfig.knownModels.map((m) => ({ id: m.id, l: m.label, p: m.provider }))
    : FALLBACK_MODELS;

  const handleSelect = (agentId: string, val: string) => {
    setSelMap((p) => ({ ...p, [agentId]: val }));
  };

  const resetMC = (agentId: string) => {
    const ag = agentConfig.agents.find((a) => a.id === agentId);
    if (ag) setSelMap((p) => ({ ...p, [agentId]: ag.model }));
  };

  const applyModel = async (agentId: string) => {
    const model = selMap[agentId];
    if (!model) return;
    setStatusMap((p) => ({ ...p, [agentId]: { cls: 'pending', text: '⟳ Submitting…' } }));
    try {
      const r = await api.setModel(agentId, model);
      if (r.ok) {
        setStatusMap((p) => ({ ...p, [agentId]: { cls: 'ok', text: '✅ Submitted, Gateway restarting (~5s)' } }));
        toast(agentId + ' model updated', 'ok');
        setTimeout(() => loadAgentConfig(), 5500);
      } else {
        setStatusMap((p) => ({ ...p, [agentId]: { cls: 'err', text: '❌ ' + (r.error || 'Error') } }));
      }
    } catch {
      setStatusMap((p) => ({ ...p, [agentId]: { cls: 'err', text: '❌ Cannot connect to server' } }));
    }
  };

  return (
    <div>
      <div className="model-grid">
        {agentConfig.agents.map((ag) => {
          const sel = selMap[ag.id] || ag.model;
          const changed = sel !== ag.model;
          const st = statusMap[ag.id];
          return (
            <div className="mc-card" key={ag.id}>
              <div className="mc-top">
                <span className="mc-emoji">{ag.emoji || '🏛️'}</span>
                <div>
                  <div className="mc-name">
                    {ag.label}{' '}
                    <span style={{ fontSize: 11, color: 'var(--muted)' }}>{ag.id}</span>
                  </div>
                  <div className="mc-role">{ag.role}</div>
                </div>
              </div>
              <div className="mc-cur">
                Current: <b>{ag.model}</b>
              </div>
              <select className="msel" value={sel} onChange={(e) => handleSelect(ag.id, e.target.value)}>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.l} ({m.p})
                  </option>
                ))}
              </select>
              <div className="mc-btns">
                <button className="btn btn-p" disabled={!changed} onClick={() => applyModel(ag.id)}>
                  Apply
                </button>
                <button className="btn btn-g" onClick={() => resetMC(ag.id)}>
                  Reset
                </button>
              </div>
              {st && <div className={`mc-st ${st.cls}`}>{st.text}</div>}
            </div>
          );
        })}
      </div>

      {/* Change Log */}
      <div style={{ marginTop: 24 }}>
        <div className="sec-title">Change Log</div>
        <div className="cl-list">
          {!changeLog?.length ? (
            <div style={{ fontSize: 12, color: 'var(--muted)', padding: '8px 0' }}>No changes yet</div>
          ) : (
            [...changeLog]
              .reverse()
              .slice(0, 15)
              .map((e, i) => (
                <div className="cl-row" key={i}>
                  <span className="cl-t">{(e.at || '').substring(0, 16).replace('T', ' ')}</span>
                  <span className="cl-a">{e.agentId}</span>
                  <span className="cl-c">
                    <b>{e.oldModel}</b> → <b>{e.newModel}</b>
                    {e.rolledBack && (
                      <span
                        style={{
                          color: 'var(--danger)',
                          fontSize: 10,
                          border: '1px solid #ff527044',
                          padding: '1px 5px',
                          borderRadius: 3,
                          marginLeft: 4,
                        }}
                      >
                        ⚠ Rolled back
                      </span>
                    )}
                  </span>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}
