/**
 * Zustand Store — Three Departments & Six Ministries kanban state management
 * HTTP 5s polling, no WebSocket
 */

import { create } from 'zustand';
import {
  api,
  type Task,
  type LiveStatus,
  type AgentConfig,
  type OfficialsData,
  type AgentsStatusData,
  type MorningBrief,
  type SubConfig,
  type ChangeLogEntry,
} from './api';

// ── Pipeline Definition (PIPE) ──

export const PIPE = [
  { key: 'Inbox',    dept: 'Emperor',   icon: '👑', action: 'Issue Edict' },
  { key: 'Taizi',    dept: 'Taizi',     icon: '🤴', action: 'Triage' },
  { key: 'Zhongshu', dept: 'Zhongshu',  icon: '📜', action: 'Draft' },
  { key: 'Menxia',   dept: 'Menxia',    icon: '🔍', action: 'Review' },
  { key: 'Assigned', dept: 'Shangshu',  icon: '📮', action: 'Dispatch' },
  { key: 'Doing',    dept: 'Six Ministries', icon: '⚙️', action: 'Execute' },
  { key: 'Review',   dept: 'Shangshu',  icon: '🔎', action: 'Summarize' },
  { key: 'Done',     dept: 'Report Back', icon: '✅', action: 'Complete' },
] as const;

export const PIPE_STATE_IDX: Record<string, number> = {
  Inbox: 0, Pending: 0, Taizi: 1, Zhongshu: 2, Menxia: 3,
  AwaitingApproval: 3,
  Assigned: 4, Doing: 5, Review: 6, Done: 7, Blocked: 5, Cancelled: 5, Next: 4,
};

export const DEPT_COLOR: Record<string, string> = {
  'Taizi': '#e8a040', 'Zhongshu': '#a07aff', 'Menxia': '#6a9eff', 'Shangshu': '#6aef9a',
  'Libu': '#f5c842', 'Hubu': '#ff9a6a', 'Bingbu': '#ff5270', 'Xingbu': '#cc4444',
  'Gongbu': '#44aaff', 'Libu_hr': '#9b59b6', 'Emperor': '#ffd700', 'Report Back': '#2ecc8a',
};

export const STATE_LABEL: Record<string, string> = {
  Inbox: 'Inbox', Pending: 'Pending', Taizi: 'Taizi Triage', Zhongshu: 'Zhongshu Drafting',
  Menxia: 'Menxia Review', AwaitingApproval: 'Awaiting Imperial Approval',
  Assigned: 'Dispatched', Doing: 'Executing', Review: 'Awaiting Review',
  Done: 'Completed', Blocked: 'Blocked', Cancelled: 'Cancelled', Next: 'Pending Execution',
};

export function deptColor(d: string): string {
  return DEPT_COLOR[d] || '#6a9eff';
}

export function stateLabel(t: Task): string {
  const r = t.review_round || 0;
  if (t.state === 'Menxia' && r > 1) return `Menxia Review (Round ${r})`;
  if (t.state === 'Zhongshu' && r > 0) return `Zhongshu Revision (Round ${r})`;
  return STATE_LABEL[t.state] || t.state;
}

export function isEdict(t: Task): boolean {
  return /^JJC-/i.test(t.id || '');
}

export function isSession(t: Task): boolean {
  return /^(OC-|MC-)/i.test(t.id || '');
}

export function isArchived(t: Task): boolean {
  return t.archived || ['Done', 'Cancelled'].includes(t.state);
}

export type PipeStatus = { key: string; dept: string; icon: string; action: string; status: 'done' | 'active' | 'pending' };

export function getPipeStatus(t: Task): PipeStatus[] {
  const stateIdx = PIPE_STATE_IDX[t.state] ?? 4;
  return PIPE.map((stage, i) => ({
    ...stage,
    status: (i < stateIdx ? 'done' : i === stateIdx ? 'active' : 'pending') as 'done' | 'active' | 'pending',
  }));
}

// ── Tabs ──

export type TabKey =
  | 'edicts' | 'monitor' | 'officials' | 'models'
  | 'skills' | 'sessions' | 'memorials' | 'templates' | 'morning' | 'approval';

export const TAB_DEFS: { key: TabKey; label: string; icon: string }[] = [
  { key: 'edicts',    label: 'Edict Board',              icon: '📜' },
  { key: 'monitor',   label: 'Department Monitor',        icon: '🏛️' },
  { key: 'approval',  label: 'Imperial Approval',         icon: '🏅' },
  { key: 'officials', label: 'Officials Overview',        icon: '👔' },
  { key: 'models',    label: 'Model Config',              icon: '🤖' },
  { key: 'skills',    label: 'Skills Config',             icon: '🎯' },
  { key: 'sessions',  label: 'Sessions',                  icon: '💬' },
  { key: 'memorials', label: 'Memorials',                 icon: '📜' },
  { key: 'templates', label: 'Templates',                 icon: '📋' },
  { key: 'morning',   label: 'Morning Brief',             icon: '🌅' },
];

// ── DEPTS for monitor ──

export const DEPTS = [
  { id: 'taizi',    label: 'Taizi',              emoji: '🤴', role: 'Crown Prince',          rank: 'Crown Prince' },
  { id: 'zhongshu', label: 'Zhongshu',           emoji: '📜', role: 'Chief Secretary',       rank: 'First Rank' },
  { id: 'menxia',   label: 'Menxia',             emoji: '🔍', role: 'Chamberlain',           rank: 'First Rank' },
  { id: 'shangshu', label: 'Shangshu',           emoji: '📮', role: 'Grand Secretary',       rank: 'First Rank' },
  { id: 'libu',     label: 'Libu',               emoji: '📝', role: 'Minister of Rites',     rank: 'Second Rank' },
  { id: 'hubu',     label: 'Hubu',               emoji: '💰', role: 'Minister of Finance',   rank: 'Second Rank' },
  { id: 'bingbu',   label: 'Bingbu',             emoji: '⚔️', role: 'Minister of War',       rank: 'Second Rank' },
  { id: 'xingbu',   label: 'Xingbu',             emoji: '⚖️', role: 'Minister of Justice',   rank: 'Second Rank' },
  { id: 'gongbu',   label: 'Gongbu',             emoji: '🔧', role: 'Minister of Works',     rank: 'Second Rank' },
  { id: 'libu_hr',  label: 'Libu_hr',            emoji: '👔', role: 'Minister of Personnel', rank: 'Second Rank' },
  { id: 'zaochao',  label: 'Imperial Astronomer', emoji: '🌟', role: 'Morning Briefing Officer', rank: 'Third Rank' },
];

// ── Templates ──

export interface TemplateParam {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'select';
  default?: string;
  required?: boolean;
  options?: string[];
}

export interface Template {
  id: string;
  cat: string;
  icon: string;
  name: string;
  desc: string;
  depts: string[];
  est: string;
  cost: string;
  params: TemplateParam[];
  command: string;
}

export const TEMPLATES: Template[] = [
  {
    id: 'tpl-weekly-report', cat: 'Daily Office', icon: '📝', name: 'Weekly Report',
    desc: 'Automatically generates a structured weekly report based on kanban data and department output',
    depts: ['Hubu', 'Libu'], est: '~10 min', cost: '¥0.5',
    params: [
      { key: 'date_range', label: 'Report Period', type: 'text', default: 'This Week', required: true },
      { key: 'focus', label: 'Key Focus (comma-separated)', type: 'text', default: 'Project Progress,Next Week Plan' },
      { key: 'format', label: 'Output Format', type: 'select', options: ['Markdown', 'Feishu Doc'], default: 'Markdown' },
    ],
    command: 'Generate the weekly report for {date_range}, covering {focus}, output as {format} format',
  },
  {
    id: 'tpl-code-review', cat: 'Engineering', icon: '🔍', name: 'Code Review',
    desc: 'Performs quality review of specified code repositories/files, outputs issue list and improvement suggestions',
    depts: ['Bingbu', 'Xingbu'], est: '~20 min', cost: '¥2',
    params: [
      { key: 'repo', label: 'Repository/File Path', type: 'text', required: true },
      { key: 'scope', label: 'Review Scope', type: 'select', options: ['Full', 'Incremental (recent commit)', 'Specified files'], default: 'Incremental (recent commit)' },
      { key: 'focus', label: 'Key Focus (optional)', type: 'text', default: 'Security vulnerabilities,Error handling,Performance' },
    ],
    command: 'Perform code review on {repo}, scope: {scope}, focus: {focus}',
  },
  {
    id: 'tpl-api-design', cat: 'Engineering', icon: '⚡', name: 'API Design & Implementation',
    desc: 'End-to-end from requirements to RESTful API design, implementation, and testing',
    depts: ['Zhongshu', 'Bingbu'], est: '~45 min', cost: '¥3',
    params: [
      { key: 'requirement', label: 'Requirements Description', type: 'textarea', required: true },
      { key: 'tech', label: 'Tech Stack', type: 'select', options: ['Python/FastAPI', 'Node/Express', 'Go/Gin'], default: 'Python/FastAPI' },
      { key: 'auth', label: 'Auth Method', type: 'select', options: ['JWT', 'API Key', 'None'], default: 'JWT' },
    ],
    command: 'Design and implement a {tech} RESTful API: {requirement}. Auth method: {auth}',
  },
  {
    id: 'tpl-competitor', cat: 'Data Analysis', icon: '📊', name: 'Competitor Analysis',
    desc: 'Scrapes competitor website data, analyzes and compares, generates structured report',
    depts: ['Bingbu', 'Hubu', 'Libu'], est: '~60 min', cost: '¥5',
    params: [
      { key: 'targets', label: 'Competitor Names/URLs (one per line)', type: 'textarea', required: true },
      { key: 'dimensions', label: 'Analysis Dimensions', type: 'text', default: 'Product features,Pricing strategy,User reviews' },
      { key: 'format', label: 'Output Format', type: 'select', options: ['Markdown report', 'Comparison table'], default: 'Markdown report' },
    ],
    command: 'Analyze the following competitors:\n{targets}\n\nDimensions: {dimensions}, Output format: {format}',
  },
  {
    id: 'tpl-data-report', cat: 'Data Analysis', icon: '📈', name: 'Data Report',
    desc: 'Cleans, analyzes, and visualizes a given dataset, outputs analysis report',
    depts: ['Hubu', 'Libu'], est: '~30 min', cost: '¥2',
    params: [
      { key: 'data_source', label: 'Data Source Description/Path', type: 'text', required: true },
      { key: 'questions', label: 'Analysis Questions (one per line)', type: 'textarea' },
      { key: 'viz', label: 'Visualization Charts Needed', type: 'select', options: ['Yes', 'No'], default: 'Yes' },
    ],
    command: 'Analyze data {data_source}. {questions}\nVisualization needed: {viz}',
  },
  {
    id: 'tpl-blog', cat: 'Content Creation', icon: '✍️', name: 'Blog Article',
    desc: 'Generates high-quality blog articles given a topic and requirements',
    depts: ['Libu'], est: '~15 min', cost: '¥1',
    params: [
      { key: 'topic', label: 'Article Topic', type: 'text', required: true },
      { key: 'audience', label: 'Target Audience', type: 'text', default: 'Technical professionals' },
      { key: 'length', label: 'Target Length', type: 'select', options: ['~500 words', '~1000 words', '~1500 words'], default: '~1000 words' },
      { key: 'style', label: 'Style', type: 'select', options: ['Technical tutorial', 'Opinion piece', 'Case study'], default: 'Technical tutorial' },
    ],
    command: 'Write a blog article about "{topic}", aimed at {audience}, {length}, style: {style}',
  },
  {
    id: 'tpl-deploy', cat: 'Engineering', icon: '🚀', name: 'Deployment Plan',
    desc: 'Generates complete deployment checklist, Docker config, and CI/CD pipeline',
    depts: ['Bingbu', 'Gongbu'], est: '~25 min', cost: '¥2',
    params: [
      { key: 'project', label: 'Project Name/Description', type: 'text', required: true },
      { key: 'env', label: 'Deployment Environment', type: 'select', options: ['Docker', 'K8s', 'VPS', 'Serverless'], default: 'Docker' },
      { key: 'ci', label: 'CI/CD Tool', type: 'select', options: ['GitHub Actions', 'GitLab CI', 'None'], default: 'GitHub Actions' },
    ],
    command: 'Generate a {env} deployment plan for project "{project}", using {ci} for CI/CD',
  },
  {
    id: 'tpl-email', cat: 'Content Creation', icon: '📧', name: 'Email / Notification Copy',
    desc: 'Generates professional email or notification copy based on scenario and purpose',
    depts: ['Libu'], est: '~5 min', cost: '¥0.3',
    params: [
      { key: 'scenario', label: 'Use Case', type: 'select', options: ['Business email', 'Product launch', 'Customer notice', 'Internal announcement'], default: 'Business email' },
      { key: 'purpose', label: 'Purpose/Content', type: 'textarea', required: true },
      { key: 'tone', label: 'Tone', type: 'select', options: ['Formal', 'Friendly', 'Concise'], default: 'Formal' },
    ],
    command: 'Write a {scenario} with a {tone} tone. Content: {purpose}',
  },
  {
    id: 'tpl-standup', cat: 'Daily Office', icon: '🗓️', name: 'Daily Standup Summary',
    desc: 'Summarizes today\'s progress and tomorrow\'s plans across departments, generates standup summary',
    depts: ['Shangshu'], est: '~5 min', cost: '¥0.3',
    params: [
      { key: 'range', label: 'Summary Range', type: 'select', options: ['Today', 'Last 24 hours', 'Yesterday + Today'], default: 'Today' },
    ],
    command: 'Summarize {range} work progress and todos across departments, generate standup summary',
  },
];

export const TPL_CATS = [
  { name: 'All', icon: '📋' },
  { name: 'Daily Office', icon: '💼' },
  { name: 'Data Analysis', icon: '📊' },
  { name: 'Engineering', icon: '⚙️' },
  { name: 'Content Creation', icon: '✍️' },
];

// ── Main Store ──

interface AppStore {
  // Data
  liveStatus: LiveStatus | null;
  agentConfig: AgentConfig | null;
  changeLog: ChangeLogEntry[];
  officialsData: OfficialsData | null;
  agentsStatusData: AgentsStatusData | null;
  morningBrief: MorningBrief | null;
  subConfig: SubConfig | null;

  // UI State
  activeTab: TabKey;
  edictFilter: 'active' | 'archived' | 'all';
  sessFilter: string;
  tplCatFilter: string;
  selectedOfficial: string | null;
  modalTaskId: string | null;
  countdown: number;

  // Toast
  toasts: { id: number; msg: string; type: 'ok' | 'err' }[];

  // Actions
  setActiveTab: (tab: TabKey) => void;
  setEdictFilter: (f: 'active' | 'archived' | 'all') => void;
  setSessFilter: (f: string) => void;
  setTplCatFilter: (f: string) => void;
  setSelectedOfficial: (id: string | null) => void;
  setModalTaskId: (id: string | null) => void;
  setCountdown: (n: number) => void;
  toast: (msg: string, type?: 'ok' | 'err') => void;

  // Data fetching
  loadLive: () => Promise<void>;
  loadAgentConfig: () => Promise<void>;
  loadOfficials: () => Promise<void>;
  loadAgentsStatus: () => Promise<void>;
  loadMorning: () => Promise<void>;
  loadSubConfig: () => Promise<void>;
  loadAll: () => Promise<void>;
}

let _toastId = 0;

export const useStore = create<AppStore>((set, get) => ({
  liveStatus: null,
  agentConfig: null,
  changeLog: [],
  officialsData: null,
  agentsStatusData: null,
  morningBrief: null,
  subConfig: null,

  activeTab: 'edicts',
  edictFilter: 'active',
  sessFilter: 'all',
  tplCatFilter: 'All',
  selectedOfficial: null,
  modalTaskId: null,
  countdown: 5,

  toasts: [],

  setActiveTab: (tab) => {
    set({ activeTab: tab });
    const s = get();
    if (['models', 'skills', 'sessions'].includes(tab) && !s.agentConfig) s.loadAgentConfig();
    if (tab === 'officials' && !s.officialsData) s.loadOfficials();
    if (tab === 'monitor') s.loadAgentsStatus();
    if (tab === 'morning' && !s.morningBrief) s.loadMorning();
  },
  setEdictFilter: (f) => set({ edictFilter: f }),
  setSessFilter: (f) => set({ sessFilter: f }),
  setTplCatFilter: (f) => set({ tplCatFilter: f }),
  setSelectedOfficial: (id) => set({ selectedOfficial: id }),
  setModalTaskId: (id) => set({ modalTaskId: id }),
  setCountdown: (n) => set({ countdown: n }),

  toast: (msg, type = 'ok') => {
    const id = ++_toastId;
    set((s) => ({ toasts: [...s.toasts, { id, msg, type }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 3000);
  },

  loadLive: async () => {
    try {
      const data = await api.liveStatus();
      set({ liveStatus: data });
      // Also preload officials for monitor tab
      const s = get();
      if (!s.officialsData) {
        api.officialsStats().then((d) => set({ officialsData: d })).catch(() => {});
      }
    } catch {
      // silently fail
    }
  },

  loadAgentConfig: async () => {
    try {
      const cfg = await api.agentConfig();
      const log = await api.modelChangeLog();
      set({ agentConfig: cfg, changeLog: log });
    } catch {
      // silently fail
    }
  },

  loadOfficials: async () => {
    try {
      const data = await api.officialsStats();
      set({ officialsData: data });
    } catch {
      // silently fail
    }
  },

  loadAgentsStatus: async () => {
    try {
      const data = await api.agentsStatus();
      set({ agentsStatusData: data });
    } catch {
      set({ agentsStatusData: null });
    }
  },

  loadMorning: async () => {
    try {
      const [brief, config] = await Promise.all([api.morningBrief(), api.morningConfig()]);
      set({ morningBrief: brief, subConfig: config });
    } catch {
      // silently fail
    }
  },

  loadSubConfig: async () => {
    try {
      const config = await api.morningConfig();
      set({ subConfig: config });
    } catch {
      // silently fail
    }
  },

  loadAll: async () => {
    const s = get();
    await s.loadLive();
    const tab = s.activeTab;
    if (['models', 'skills'].includes(tab)) await s.loadAgentConfig();
  },
}));

// ── Countdown & Polling ──

let _cdTimer: ReturnType<typeof setInterval> | null = null;

export function startPolling() {
  if (_cdTimer) return;
  useStore.getState().loadAll();
  _cdTimer = setInterval(() => {
    const s = useStore.getState();
    const cd = s.countdown - 1;
    if (cd <= 0) {
      s.setCountdown(5);
      s.loadAll();
    } else {
      s.setCountdown(cd);
    }
  }, 1000);
}

export function stopPolling() {
  if (_cdTimer) {
    clearInterval(_cdTimer);
    _cdTimer = null;
  }
}

// ── Utility ──

export function esc(s: string | undefined | null): string {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function timeAgo(iso: string | undefined): string {
  if (!iso) return '';
  try {
    const d = new Date(iso.includes('T') ? iso : iso.replace(' ', 'T') + 'Z');
    if (isNaN(d.getTime())) return '';
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  } catch {
    return '';
  }
}
