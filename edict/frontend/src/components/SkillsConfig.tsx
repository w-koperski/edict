import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api, RemoteSkillItem } from '../api';

// Community well-known Skills source quick-pick list
const COMMUNITY_SOURCES = [
  {
    label: 'obra/superpowers',
    emoji: '⚡',
    stars: '66.9k',
    desc: 'Complete dev workflow skill set',
    skills: [
      { name: 'brainstorming', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/brainstorming/SKILL.md' },
      { name: 'test-driven-development', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/test-driven-development/SKILL.md' },
      { name: 'systematic-debugging', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/systematic-debugging/SKILL.md' },
      { name: 'subagent-driven-development', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/subagent-driven-development/SKILL.md' },
      { name: 'writing-plans', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/writing-plans/SKILL.md' },
      { name: 'executing-plans', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/executing-plans/SKILL.md' },
      { name: 'requesting-code-review', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/requesting-code-review/SKILL.md' },
      { name: 'root-cause-tracing', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/root-cause-tracing/SKILL.md' },
      { name: 'verification-before-completion', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/verification-before-completion/SKILL.md' },
      { name: 'dispatching-parallel-agents', url: 'https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/dispatching-parallel-agents/SKILL.md' },
    ],
  },
  {
    label: 'anthropics/skills',
    emoji: '🏛️',
    stars: 'Official',
    desc: 'Anthropic Official Skill Library',
    skills: [
      { name: 'docx', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md' },
      { name: 'pdf', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md' },
      { name: 'xlsx', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/xlsx/SKILL.md' },
      { name: 'pptx', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/pptx/SKILL.md' },
      { name: 'mcp-builder', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/mcp-builder/SKILL.md' },
      { name: 'frontend-design', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md' },
      { name: 'web-artifacts-builder', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/web-artifacts-builder/SKILL.md' },
      { name: 'webapp-testing', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md' },
      { name: 'algorithmic-art', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/algorithmic-art/SKILL.md' },
      { name: 'canvas-design', url: 'https://raw.githubusercontent.com/anthropics/skills/main/skills/canvas-design/SKILL.md' },
    ],
  },
  {
    label: 'ComposioHQ/awesome-claude-skills',
    emoji: '🌐',
    stars: '39.2k',
    desc: '100+ community curated skills',
    skills: [
      { name: 'github-integration', url: 'https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/github-integration/SKILL.md' },
      { name: 'data-analysis', url: 'https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/data-analysis/SKILL.md' },
      { name: 'code-review', url: 'https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/code-review/SKILL.md' },
    ],
  },
];

export default function SkillsConfig() {
  const agentConfig = useStore((s) => s.agentConfig);
  const loadAgentConfig = useStore((s) => s.loadAgentConfig);
  const toast = useStore((s) => s.toast);

  // Local skills state
  const [skillModal, setSkillModal] = useState<{ agentId: string; name: string; content: string; path: string } | null>(null);
  const [addForm, setAddForm] = useState<{ agentId: string; agentLabel: string } | null>(null);
  const [formData, setFormData] = useState({ name: '', desc: '', trigger: '' });
  const [submitting, setSubmitting] = useState(false);

  // Main Tab switch
  const [activeTab, setActiveTab] = useState<'local' | 'remote'>('local');

  // Remote skills state
  const [remoteSkills, setRemoteSkills] = useState<RemoteSkillItem[]>([]);
  const [remoteLoading, setRemoteLoading] = useState(false);
  const [addRemoteForm, setAddRemoteForm] = useState(false);
  const [remoteFormData, setRemoteFormData] = useState({ agentId: '', skillName: '', sourceUrl: '', description: '' });
  const [remoteSubmitting, setRemoteSubmitting] = useState(false);
  const [updatingSkill, setUpdatingSkill] = useState<string | null>(null);
  const [removingSkill, setRemovingSkill] = useState<string | null>(null);
  const [quickPickSource, setQuickPickSource] = useState<(typeof COMMUNITY_SOURCES)[0] | null>(null);
  const [quickPickAgent, setQuickPickAgent] = useState('');

  useEffect(() => {
    loadAgentConfig();
  }, [loadAgentConfig]);

  useEffect(() => {
    if (activeTab === 'remote') loadRemoteSkills();
  }, [activeTab]);

  const loadRemoteSkills = async () => {
    setRemoteLoading(true);
    try {
      const r = await api.remoteSkillsList();
      if (r.ok) setRemoteSkills(r.remoteSkills || []);
    } catch {
      toast('Failed to load remote skill list', 'err');
    }
    setRemoteLoading(false);
  };

  const openSkill = async (agentId: string, skillName: string) => {
    setSkillModal({ agentId, name: skillName, content: '⟳ Loading…', path: '' });
    try {
      const r = await api.skillContent(agentId, skillName);
      if (r.ok) {
        setSkillModal({ agentId, name: skillName, content: r.content || '', path: r.path || '' });
      } else {
        setSkillModal({ agentId, name: skillName, content: '❌ ' + (r.error || 'Cannot read'), path: '' });
      }
    } catch {
      setSkillModal({ agentId, name: skillName, content: '❌ Server connection failed', path: '' });
    }
  };

  const openAddForm = (agentId: string, agentLabel: string) => {
    setAddForm({ agentId, agentLabel });
    setFormData({ name: '', desc: '', trigger: '' });
  };

  const submitAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm || !formData.name) return;
    setSubmitting(true);
    try {
      const r = await api.addSkill(addForm.agentId, formData.name, formData.desc, formData.trigger);
      if (r.ok) {
        toast(`✅ Skill ${formData.name} added to ${addForm.agentLabel}`, 'ok');
        setAddForm(null);
        loadAgentConfig();
      } else {
        toast(r.error || 'Add failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
    setSubmitting(false);
  };

  const submitAddRemote = async (e: React.FormEvent) => {
    e.preventDefault();
    const { agentId, skillName, sourceUrl, description } = remoteFormData;
    if (!agentId || !skillName || !sourceUrl) return;
    setRemoteSubmitting(true);
    try {
      const r = await api.addRemoteSkill(agentId, skillName, sourceUrl, description);
      if (r.ok) {
        toast(`✅ Remote skill ${skillName} added to ${agentId}`, 'ok');
        setAddRemoteForm(false);
        setRemoteFormData({ agentId: '', skillName: '', sourceUrl: '', description: '' });
        loadRemoteSkills();
        loadAgentConfig();
      } else {
        toast(r.error || 'Add failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
    setRemoteSubmitting(false);
  };

  const handleUpdate = async (skill: RemoteSkillItem) => {
    const key = `${skill.agentId}/${skill.skillName}`;
    setUpdatingSkill(key);
    try {
      const r = await api.updateRemoteSkill(skill.agentId, skill.skillName);
      if (r.ok) {
        toast(`✅ Skill ${skill.skillName} updated`, 'ok');
        loadRemoteSkills();
      } else {
        toast(r.error || 'Update failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
    setUpdatingSkill(null);
  };

  const handleRemove = async (skill: RemoteSkillItem) => {
    const key = `${skill.agentId}/${skill.skillName}`;
    setRemovingSkill(key);
    try {
      const r = await api.removeRemoteSkill(skill.agentId, skill.skillName);
      if (r.ok) {
        toast(`🗑️ Skill ${skill.skillName} removed`, 'ok');
        loadRemoteSkills();
        loadAgentConfig();
      } else {
        toast(r.error || 'Remove failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
    setRemovingSkill(null);
  };

  const handleQuickImport = async (skillUrl: string, skillName: string) => {
    if (!quickPickAgent) { toast('Please select a target Agent first', 'err'); return; }
    try {
      const r = await api.addRemoteSkill(quickPickAgent, skillName, skillUrl, '');
      if (r.ok) {
        toast(`✅ ${skillName} → ${quickPickAgent}`, 'ok');
        loadRemoteSkills();
        loadAgentConfig();
      } else {
        toast(r.error || 'Import failed', 'err');
      }
    } catch {
      toast('Server connection failed', 'err');
    }
  };

  if (!agentConfig?.agents) {
    return <div className="empty">Failed to load</div>;
  }

  // ── Local Skills Panel ──
  const localPanel = (
    <div>
      <div className="skills-grid">
        {agentConfig.agents.map((ag) => (
          <div className="sk-card" key={ag.id}>
            <div className="sk-hdr">
              <span className="sk-emoji">{ag.emoji || '🏛️'}</span>
              <span className="sk-name">{ag.label}</span>
              <span className="sk-cnt">{(ag.skills || []).length} skills</span>
            </div>
            <div className="sk-list">
              {!(ag.skills || []).length ? (
                <div className="sk-empty">No skills</div>
              ) : (
                (ag.skills || []).map((sk) => (
                  <div className="sk-item" key={sk.name} onClick={() => openSkill(ag.id, sk.name)}>
                    <span className="si-name">📦 {sk.name}</span>
                    <span className="si-desc">{sk.description || 'No description'}</span>
                    <span className="si-arrow">›</span>
                  </div>
                ))
              )}
            </div>
            <div className="sk-add" onClick={() => openAddForm(ag.id, ag.label)}>
              ＋ Add Skill
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // ── Remote Skills Panel ──
  const remotePanel = (
    <div>
      {/* Action bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <button
          style={{ padding: '8px 18px', background: 'var(--acc)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
          onClick={() => { setAddRemoteForm(true); setQuickPickSource(null); }}
        >
          ＋ Add Remote Skill
        </button>
        <button
          style={{ padding: '8px 14px', background: 'transparent', color: 'var(--acc)', border: '1px solid var(--acc)', borderRadius: 8, cursor: 'pointer', fontSize: 12 }}
          onClick={loadRemoteSkills}
        >
          ⟳ Refresh List
        </button>
        <span style={{ fontSize: 11, color: 'var(--muted)', marginLeft: 4 }}>
          {remoteSkills.length} remote skills total
        </span>
      </div>

      {/* Community quick-pick */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', letterSpacing: '.06em', marginBottom: 10 }}>
          🌐 Community Skill Sources — One-click Import
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {COMMUNITY_SOURCES.map((src) => (
            <div
              key={src.label}
              onClick={() => setQuickPickSource(quickPickSource?.label === src.label ? null : src)}
              style={{
                padding: '8px 14px',
                background: quickPickSource?.label === src.label ? '#0d1f45' : 'var(--panel)',
                border: `1px solid ${quickPickSource?.label === src.label ? 'var(--acc)' : 'var(--line)'}`,
                borderRadius: 10,
                cursor: 'pointer',
                fontSize: 12,
                transition: 'all .15s',
              }}
            >
              <span style={{ marginRight: 6 }}>{src.emoji}</span>
              <b style={{ color: 'var(--text)' }}>{src.label}</b>
              <span style={{ marginLeft: 6, color: '#f0b429', fontSize: 11 }}>★ {src.stars}</span>
              <span style={{ marginLeft: 8, color: 'var(--muted)' }}>{src.desc}</span>
            </div>
          ))}
        </div>

        {quickPickSource && (
          <div style={{ marginTop: 14, background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <span style={{ fontSize: 12, fontWeight: 600 }}>Target Agent：</span>
              <select
                value={quickPickAgent}
                onChange={(e) => setQuickPickAgent(e.target.value)}
                style={{ padding: '6px 10px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 6, color: 'var(--text)', fontSize: 12 }}
              >
                <option value="">— Select Agent —</option>
                {agentConfig.agents.map((ag) => (
                  <option key={ag.id} value={ag.id}>{ag.emoji} {ag.label} ({ag.id})</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
              {quickPickSource.skills.map((sk) => {
                const alreadyAdded = remoteSkills.some((r) => r.skillName === sk.name && r.agentId === quickPickAgent);
                return (
                  <div
                    key={sk.name}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '8px 12px', background: 'var(--panel2)', borderRadius: 8,
                      border: '1px solid var(--line)',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>📦 {sk.name}</div>
                      <div style={{ fontSize: 10, color: 'var(--muted)', wordBreak: 'break-all', maxWidth: 180 }}>{sk.url.split('/').slice(-2).join('/')}</div>
                    </div>
                    {alreadyAdded ? (
                      <span style={{ fontSize: 10, color: '#4caf88', fontWeight: 600 }}>✓ Imported</span>
                    ) : (
                      <button
                        onClick={() => handleQuickImport(sk.url, sk.name)}
                        style={{ padding: '4px 10px', background: 'var(--acc)', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 11, whiteSpace: 'nowrap' }}
                      >
                        Import
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Added remote skills list */}
      {remoteLoading ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--muted)', fontSize: 13 }}>⟳ Loading…</div>
      ) : remoteSkills.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', background: 'var(--panel)', borderRadius: 12, border: '1px dashed var(--line)' }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>🌐</div>
          <div style={{ fontSize: 14, color: 'var(--muted)' }}>No remote skills yet</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>Quick-import from community skill sources, or add a URL manually</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {remoteSkills.map((sk) => {
            const key = `${sk.agentId}/${sk.skillName}`;
            const isUpdating = updatingSkill === key;
            const isRemoving = removingSkill === key;
            const agInfo = agentConfig.agents.find((a) => a.id === sk.agentId);
            return (
              <div
                key={key}
                style={{
                  background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, padding: '14px 18px',
                  display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 700 }}>📦 {sk.skillName}</span>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 999,
                      background: sk.status === 'valid' ? '#0d3322' : '#3d1111',
                      color: sk.status === 'valid' ? '#4caf88' : '#ff5270',
                      fontWeight: 600,
                    }}>
                      {sk.status === 'valid' ? '✓ Valid' : '✗ File missing'}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--muted)', background: 'var(--panel2)', padding: '2px 8px', borderRadius: 6 }}>
                      {agInfo?.emoji} {agInfo?.label || sk.agentId}
                    </span>
                  </div>
                  {sk.description && (
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>{sk.description}</div>
                  )}
                  <div style={{ fontSize: 10, color: 'var(--muted)', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                    <span>🔗 <a href={sk.sourceUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--acc)', textDecoration: 'none' }}>{sk.sourceUrl.length > 60 ? sk.sourceUrl.slice(0, 60) + '…' : sk.sourceUrl}</a></span>
                    <span>📅 {sk.lastUpdated ? sk.lastUpdated.slice(0, 10) : sk.addedAt?.slice(0, 10)}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => openSkill(sk.agentId, sk.skillName)}
                    style={{ padding: '6px 12px', background: 'transparent', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleUpdate(sk)}
                    disabled={isUpdating}
                    style={{ padding: '6px 12px', background: 'transparent', color: 'var(--acc)', border: '1px solid var(--acc)', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}
                  >
                    {isUpdating ? '⟳' : 'Update'}
                  </button>
                  <button
                    onClick={() => handleRemove(sk)}
                    disabled={isRemoving}
                    style={{ padding: '6px 12px', background: 'transparent', color: '#ff5270', border: '1px solid #ff5270', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}
                  >
                    {isRemoving ? '⟳' : 'Delete'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  return (
    <div>
      {/* Main Tab switch */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--line)', paddingBottom: 0 }}>
        {[
          { key: 'local', label: '🏛️ Local Skills', count: agentConfig.agents.reduce((n, a) => n + (a.skills?.length || 0), 0) },
          { key: 'remote', label: '🌐 Remote Skills', count: remoteSkills.length },
        ].map((t) => (
          <div
            key={t.key}
            onClick={() => setActiveTab(t.key as 'local' | 'remote')}
            style={{
              padding: '8px 18px', cursor: 'pointer', fontSize: 13, borderRadius: '8px 8px 0 0',
              fontWeight: activeTab === t.key ? 700 : 400,
              background: activeTab === t.key ? 'var(--panel)' : 'transparent',
              color: activeTab === t.key ? 'var(--text)' : 'var(--muted)',
              border: activeTab === t.key ? '1px solid var(--line)' : '1px solid transparent',
              borderBottom: activeTab === t.key ? '1px solid var(--panel)' : '1px solid transparent',
              position: 'relative', bottom: -1,
              transition: 'all .15s',
            }}
          >
            {t.label}
            {t.count > 0 && (
              <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 999, background: '#1a2040', color: 'var(--acc)' }}>
                {t.count}
              </span>
            )}
          </div>
        ))}
      </div>

      {activeTab === 'local' ? localPanel : remotePanel}

      {/* Skill Content Modal */}
      {skillModal && (
        <div className="modal-bg open" onClick={() => setSkillModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSkillModal(null)}>✕</button>
            <div className="modal-body">
              <div style={{ fontSize: 11, color: 'var(--acc)', fontWeight: 700, letterSpacing: '.04em', marginBottom: 4 }}>
                {skillModal.agentId.toUpperCase()}
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 16 }}>📦 {skillModal.name}</div>
              <div className="sk-modal-body">
                <div className="sk-md" style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.7 }}>
                  {skillModal.content}
                </div>
                {skillModal.path && (
                  <div className="sk-path" style={{ fontSize: 10, color: 'var(--muted)', marginTop: 12 }}>
                    📂 {skillModal.path}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Local Add Skill Form Modal */}
      {addForm && (
        <div className="modal-bg open" onClick={() => setAddForm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setAddForm(null)}>✕</button>
            <div className="modal-body">
              <div style={{ fontSize: 11, color: 'var(--acc)', fontWeight: 700, letterSpacing: '.04em', marginBottom: 4 }}>
                Add Skill for {addForm.agentLabel}
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 18 }}>＋ New Skill</div>

              <div
                style={{
                  background: 'var(--panel2)',
                  border: '1px solid var(--line)',
                  borderRadius: 10,
                  padding: 14,
                  marginBottom: 18,
                  fontSize: 12,
                  lineHeight: 1.7,
                  color: 'var(--muted)',
                }}
              >
                <b style={{ color: 'var(--text)' }}>📋 Skill Specification</b>
                <br />
                • Skill name uses <b style={{ color: 'var(--text)' }}>lowercase letters + hyphens</b>
                <br />
                • A template file SKILL.md will be generated on creation
                <br />
                • Skills are <b style={{ color: 'var(--text)' }}>auto-activated</b> when the agent receives a relevant task
              </div>

              <form onSubmit={submitAdd} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Skill Name <span style={{ color: '#ff5270' }}>*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="如 data-analysis, code-review"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData((p) => ({ ...p, name: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') }))
                    }
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Skill Description</label>
                  <input
                    type="text"
                    placeholder="One sentence description"
                    value={formData.desc}
                    onChange={(e) => setFormData((p) => ({ ...p, desc: e.target.value }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Trigger Condition (optional)</label>
                  <input
                    type="text"
                    placeholder="When to activate this skill"
                    value={formData.trigger}
                    onChange={(e) => setFormData((p) => ({ ...p, trigger: e.target.value }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
                  <button type="button" className="btn btn-g" onClick={() => setAddForm(null)} style={{ padding: '8px 20px' }}>
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    style={{ padding: '8px 20px', fontSize: 13, background: 'var(--acc)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}
                  >
                    {submitting ? '⟳ Creating…' : '📦 Create Skill'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Remote Add Remote Skill Modal */}
      {addRemoteForm && (
        <div className="modal-bg open" onClick={() => setAddRemoteForm(false)}>
          <div className="modal" style={{ maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setAddRemoteForm(false)}>✕</button>
            <div className="modal-body">
              <div style={{ fontSize: 11, color: '#a07aff', fontWeight: 700, letterSpacing: '.04em', marginBottom: 4 }}>
                Remote Skill Management
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 18 }}>🌐 Add Remote Skill</div>

              <div style={{ background: 'var(--panel2)', border: '1px solid var(--line)', borderRadius: 10, padding: 12, marginBottom: 18, fontSize: 11, color: 'var(--muted)', lineHeight: 1.7 }}>
                Supports GitHub Raw URLs, e.g.:<br />
                <code style={{ color: 'var(--acc)', fontSize: 10 }}>https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/skills/brainstorming/SKILL.md</code>
              </div>

              <form onSubmit={submitAddRemote} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Target Agent <span style={{ color: '#ff5270' }}>*</span></label>
                  <select
                    required
                    value={remoteFormData.agentId}
                    onChange={(e) => setRemoteFormData((p) => ({ ...p, agentId: e.target.value }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13 }}
                  >
                    <option value="">— Select Agent —</option>
                    {agentConfig.agents.map((ag) => (
                      <option key={ag.id} value={ag.id}>{ag.emoji} {ag.label} ({ag.id})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Skill Name <span style={{ color: '#ff5270' }}>*</span></label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. brainstorming, code-review"
                    value={remoteFormData.skillName}
                    onChange={(e) => setRemoteFormData((p) => ({ ...p, skillName: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Source URL <span style={{ color: '#ff5270' }}>*</span></label>
                  <input
                    type="url"
                    required
                    placeholder="https://raw.githubusercontent.com/..."
                    value={remoteFormData.sourceUrl}
                    onChange={(e) => setRemoteFormData((p) => ({ ...p, sourceUrl: e.target.value }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 12, outline: 'none' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>Description (optional)</label>
                  <input
                    type="text"
                    placeholder="One sentence description"
                    value={remoteFormData.description}
                    onChange={(e) => setRemoteFormData((p) => ({ ...p, description: e.target.value }))}
                    style={{ width: '100%', padding: '10px 12px', background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
                  <button type="button" className="btn btn-g" onClick={() => setAddRemoteForm(false)} style={{ padding: '8px 20px' }}>Cancel</button>
                  <button
                    type="submit"
                    disabled={remoteSubmitting}
                    style={{ padding: '8px 20px', fontSize: 13, background: '#a07aff', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}
                  >
                    {remoteSubmitting ? '⟳ Downloading…' : '🌐 Add Remote Skill'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
