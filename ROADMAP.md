# 🗺️ Three Departments & Six Ministries · Roadmap

> This roadmap is public. Feel free to claim unfinished items and submit a PR to contribute.
>
> To claim: reply "I'll take this" on the corresponding Issue, or submit a PR directly mentioning it in the description.

---

## Phase 1 — Core Architecture ✅

> The skeleton of Three Departments & Six Ministries: twelve-department system + Taizi triage + real-time kanban + complete workflow.

- [x] Twelve-department Agent architecture (Taizi + Zhongshu/Menxia/Shangshu + Hubu/Libu/Bingbu/Xingbu/Gongbu + Libu_hr + Morning Officer)
- [x] Taizi triage layer — automatically identifies casual chat vs. commands; casual chat replied directly, commands summarized and forwarded to Zhongshu
- [x] Strict permission matrix — who can message whom, in writing
- [x] Grand Council real-time kanban (10 feature panels)
- [x] Full task lifecycle management (create → triage → plan → review → dispatch → execute → report back)
- [x] Task halt / cancel / resume
- [x] Memorial system (completed edicts auto-archived + five-phase timeline)
- [x] Edict template library (9 preset templates + parameter forms + estimated time/cost)
- [x] Court ceremony (opening animation on first daily visit + today's stats)
- [x] Daily News Brief (auto-collects tech/finance news + Feishu push + subscription management)
- [x] Hot model switching (one-click switch of each Agent's LLM from the kanban)
- [x] Skills management (view installed Skills per department + add new skills)
- [x] Officials overview (Token consumption ranking + activity + completion stats)
- [x] Sessions / session monitoring (OC-* session real-time tracking)
- [x] Edict data sanitization — title/notes auto-cleaned, dirty data rejected
- [x] Duplicate task protection — completed/cancelled edicts cannot be overwritten
- [x] E2E kanban tests (9 scenarios, 17 assertions all passing)
- [x] React 18 frontend refactor — TypeScript + Vite + Zustand, 13 feature components
- [x] Agent thinking process visualization — real-time display of thinking / tool_result / user messages
- [x] Integrated frontend+backend deployment — server.py serves both API + static files

---

## Phase 2 — System Deepening 🚧

> Upgrade from "useful" to "indispensable": make checks and balances not just a concept, but a complete system with performance evaluation, human approval, and knowledge accumulation.

### 🏅 Imperial Approval Mode (Human Approval Node)
- [x] Menxia review results submitted for "imperial review" — one-click approve / veto
- [x] Kanban approval panel (pending approval list + approval history)
- [ ] Feishu / Telegram push approval notifications
- **Difficulty**: ⭐⭐ | **Good first contribution**

### 📊 Merit Record (Agent Performance Scoring)
- [ ] Completion rate, rework rate, time stats per Agent
- [ ] Kanban panel showing leaderboard + trend charts
- [ ] Auto-tag "top performers" and "Agents needing training"
- **Difficulty**: ⭐⭐

### 🚀 Express Courier (Real-time Agent Message Flow Visualization)
- [ ] Real-time connection animations in kanban: Zhongshu→Menxia→Shangshu→Six Ministries
- [ ] Message type coloring (dispatch / review / report back / veto)
- [ ] Timeline replay mode
- **Difficulty**: ⭐⭐⭐

### 📚 National History Archive (Knowledge Base + Citation Tracing)
- [ ] Historical edict experience auto-accumulated
- [ ] Similar edict search + recommendations
- [ ] Memorial citation tracing chain
- **Difficulty**: ⭐⭐⭐

---

## Phase 3 — Ecosystem Expansion

> From standalone tool to ecosystem: more integrations, more users, more scenarios.

### 🐳 Docker Compose + Demo Image
- [ ] `docker run` one-liner to experience full kanban (pre-populated mock data)
- [ ] Docker Compose orchestration (kanban + data sync + OpenClaw Gateway)
- [ ] CI/CD auto-build and push image
- **Difficulty**: ⭐⭐ | **Good first contribution**

### 🔗 Kanban Adapters
- [ ] Notion adapter — turn Notion database into Grand Council kanban
- [ ] Linear adapter — sync Linear projects to Three Departments & Six Ministries
- [ ] GitHub Issues bidirectional sync
- **Difficulty**: ⭐⭐⭐

### 📱 Mobile + PWA
- [ ] Responsive layout for phones/tablets
- [ ] PWA offline support + push notifications
- **Difficulty**: ⭐⭐

### 🏪 ClawHub Listing
- [ ] Submit core Skills to the OpenClaw official Skill marketplace
- [ ] One-click install Three Departments & Six Ministries Skill Pack
- **Difficulty**: ⭐

### 📈 Annual Review
- [ ] Agent annual performance report (total token consumption, completion rate, most complex edict)
- [ ] Visual annual review dashboard
- **Difficulty**: ⭐⭐

---

## How to Contribute

1. **Check Phase 2** — these are the areas most in need of help right now
2. **Find items marked ⭐⭐ or "Good first contribution"** to get started
3. **Open an Issue** to say what you want to do, to avoid duplication
4. **Submit a PR** — see [CONTRIBUTING.md](CONTRIBUTING.md) for details

> 💡 Don't see what you want to work on? Open an Issue to suggest new features — good ideas will be added to the Roadmap.
