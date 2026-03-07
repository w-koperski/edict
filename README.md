<h1 align="center">⚔️ Edict · Three Departments & Six Ministries</h1>

<p align="center">
  <strong>I redesigned AI multi-agent collaboration architecture using an imperial system from 1300 years ago.<br>And found that the ancients understood checks and balances better than modern AI frameworks.</strong>
</p>

<p align="center">
  <sub>12 AI Agents (11 business roles + 1 compatibility role) form the Three Departments & Six Ministries: Taizi triages, Zhongshu plans, Menxia reviews and vetoes, Shangshu dispatches, Six Ministries + Libu_hr execute in parallel.<br>One layer of <b>institutional review</b> more than CrewAI; one <b>real-time kanban</b> more than AutoGen.</sub>
</p>

<p align="center">
  <a href="#-demo">🎬 See Demo</a> ·
  <a href="#-30-second-quick-start">🚀 30-second start</a> ·
  <a href="#-architecture">🏛️ Architecture</a> ·
  <a href="#-feature-overview">📋 Kanban features</a> ·
  <a href="docs/task-dispatch-architecture.md">📚 Architecture docs</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/OpenClaw-Required-blue?style=flat-square" alt="OpenClaw">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Agents-12_Specialized-8B5CF6?style=flat-square" alt="Agents">
  <img src="https://img.shields.io/badge/Dashboard-Real--time-F59E0B?style=flat-square" alt="Dashboard">
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Frontend-React_18-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/Backend-stdlib_only-EC4899?style=flat-square" alt="Zero Backend Dependencies">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/WeChat-cft0808-07C160?style=for-the-badge&logo=wechat&logoColor=white" alt="WeChat">
</p>

---

## 🎬 Demo

<p align="center">
  <video src="docs/Agent_video_Pippit_20260225121727.mp4" width="100%" autoplay muted loop playsinline controls>
    Your browser does not support video playback. See the GIF below or <a href="docs/Agent_video_Pippit_20260225121727.mp4">download the video</a>.
  </video>
  <br>
  <sub>🎥 Three Departments & Six Ministries AI multi-agent collaboration full-flow demo</sub>
</p>

<details>
<summary>📸 GIF preview (loads faster)</summary>
<p align="center">
  <img src="docs/demo.gif" alt="Three Departments & Six Ministries Demo" width="100%">
  <br>
  <sub>Issue edict via Feishu → Taizi triage → Zhongshu planning → Menxia review → Six Ministries parallel execution → Memorial report back (30 seconds)</sub>
</p>
</details>

> 🐳 **No OpenClaw?** Run `docker run -p 7891:7891 cft0808/edict` to experience the full kanban demo (with pre-populated mock data).

---

## 🤔 Why Three Departments & Six Ministries?

Most multi-agent frameworks work like this:

> *"Here, you AIs, talk among yourselves and give me the result."*

Then you get a blob of output with no idea what happened in the middle — can't reproduce, can't audit, can't intervene.

**Three Departments & Six Ministries works completely differently** — we use an institutional architecture that existed in China for 1400 years:

```
You (Emperor) → Taizi (triage) → Zhongshu (plan) → Menxia (review) → Shangshu (dispatch) → Six Ministries (execute) → Report back
```

This is not a fancy metaphor — this is **real checks and balances**:

| | CrewAI | MetaGPT | AutoGen | **Three Dept. & Six Min.** |
|---|:---:|:---:|:---:|:---:|
| **Review mechanism** | ❌ None | ⚠️ Optional | ⚠️ Human-in-loop | **✅ Menxia dedicated review · can veto** |
| **Real-time kanban** | ❌ | ❌ | ❌ | **✅ Grand Council Kanban + timeline** |
| **Task intervention** | ❌ | ❌ | ❌ | **✅ Halt / cancel / resume** |
| **Flow audit** | ⚠️ | ⚠️ | ❌ | **✅ Complete memorial archive** |
| **Agent health monitoring** | ❌ | ❌ | ❌ | **✅ Heartbeat + activity detection** |
| **Hot-swap model** | ❌ | ❌ | ❌ | **✅ One-click LLM switch in kanban** |
| **Skills management** | ❌ | ❌ | ❌ | **✅ View / add Skills** |
| **News aggregation push** | ❌ | ❌ | ❌ | **✅ Morning Brief + Feishu push** |
| **Deployment difficulty** | Medium | High | Medium | **Low · one-click install / Docker** |

> **Core difference: institutional review + fully observable + real-time intervable**

<details>
<summary><b>🔍 Why is "Menxia Review" the killer feature? (click to expand)</b></summary>

<br>

CrewAI and AutoGen's agent collaboration model is **"hand in when done"** — no one checks output quality. Like a company with no QA department, where engineers push code directly to production.

Three Departments & Six Ministries' **Menxia** specifically does this:

- 📋 **Reviews plan quality** — is Zhongshu's plan complete? Is the sub-task breakdown reasonable?
- 🚫 **Vetoes unqualified output** — not a warning, but a mandatory rework
- 🔄 **Enforces rework loop** — only passes when the plan is up to standard

This is not an optional plugin — **it is part of the architecture**. Every edict must pass through Menxia, no exceptions.

This is why Three Departments & Six Ministries can handle complex tasks with reliable results: because before reaching the execution layer, there is a mandatory quality checkpoint. Emperor Taizong figured this out 1300 years ago — **unchecked power will inevitably go wrong**.

</details>

---

## ✨ Feature Overview

### 🏛️ Twelve-Department Agent Architecture
- **Taizi** message triage — casual chat auto-replied, only commands create tasks
- **Three Departments** (Zhongshu · Menxia · Shangshu) handle planning, review, dispatch
- **Seven Ministries** (Hubu · Libu · Bingbu · Xingbu · Gongbu · Libu_hr + Morning Officer) handle specialized execution
- Strict permission matrix — who can message whom, in writing
- Each Agent: independent Workspace · independent Skills · independent model
- **Edict data sanitization** — titles/notes auto-strip file paths, metadata, invalid prefixes

### 📋 Grand Council Kanban (10 Feature Panels)

<table>
<tr><td width="50%">

**📋 Edict Board · Kanban**
- Display all tasks in state columns
- Department filter + full-text search
- Heartbeat badges (🟢active 🟡stalled 🔴alert)
- Task details + complete flow chain
- Halt / cancel / resume operations

</td><td width="50%">

**🔭 Department Monitor · Monitor**
- Visualize task counts per state
- Department distribution horizontal bar chart
- Agent health status real-time cards

</td></tr>
<tr><td>

**📜 Memorials · Memorials**
- Completed edicts auto-archived as memorials
- Five-phase timeline: Edict→Zhongshu→Menxia→Six Ministries→Report Back
- One-click copy as Markdown
- Filter by status

</td><td>

**📜 Templates · Template Library**
- 9 preset edict templates
- Category filter · parameter form · estimated time and cost
- Preview edict → issue with one click

</td></tr>
<tr><td>

**👥 Officials Overview · Officials**
- Token consumption leaderboard
- Activity · completion count · session stats

</td><td>

**📰 Morning Brief · News**
- Daily auto-collects tech/finance news
- Category subscription management + Feishu push

</td></tr>
<tr><td>

**⚙️ Model Config · Models**
- Each Agent independently switches LLM
- Gateway auto-restarts after apply (~5 seconds)

</td><td>

**🛠️ Skills Config · Skills**
- Overview of installed Skills per department
- View details + add new skills

</td></tr>
<tr><td>

**💬 Sessions · Sessions**
- OC-* session real-time monitoring
- Source channel · heartbeat · message preview

</td><td>

**🎬 Court Ceremony · Ceremony**
- Opening animation on first daily open
- Today's stats · auto-disappears in 3.5 seconds

</td></tr>
</table>

---

## 🖼️ Screenshots

### Edict Board
![Edict Board](docs/screenshots/01-kanban-main.png)

<details>
<summary>📸 Expand to see more screenshots</summary>

### Department Monitor
![Department Monitor](docs/screenshots/02-monitor.png)

### Task Flow Details
![Task Flow Details](docs/screenshots/03-task-detail.png)

### Model Configuration
![Model Configuration](docs/screenshots/04-model-config.png)

### Skills Configuration
![Skills Configuration](docs/screenshots/05-skills-config.png)

### Officials Overview
![Officials Overview](docs/screenshots/06-official-overview.png)

### Sessions
![Sessions](docs/screenshots/07-sessions.png)

### Memorial Archive
![Memorial Archive](docs/screenshots/08-memorials.png)

### Edict Templates
![Edict Templates](docs/screenshots/09-templates.png)

### Morning Brief
![Morning Brief](docs/screenshots/10-morning-briefing.png)

### Court Ceremony
![Court Ceremony](docs/screenshots/11-ceremony.png)

</details>

---

## 🚀 30-Second Quick Start

### One-click Docker Start

```bash
docker run -p 7891:7891 cft0808/sansheng-demo
```
Open http://localhost:7891 to experience the Grand Council kanban.

<details>
<summary><b>⚠️ Getting <code>exec format error</code>? (click to expand)</b></summary>

If on an **x86/amd64** machine (e.g. Ubuntu, WSL2) you see:
```
exec /usr/local/bin/python3: exec format error
```

This is because of image architecture mismatch. Use the `--platform` flag:
```bash
docker run --platform linux/amd64 -p 7891:7891 cft0808/sansheng-demo
```

Or use docker-compose (has `platform: linux/amd64` built in):
```bash
docker compose up
```

</details>

### Full Installation

#### Prerequisites
- [OpenClaw](https://openclaw.ai) installed
- Python 3.9+
- macOS / Linux

#### Install

```bash
git clone https://github.com/cft0808/edict.git
cd edict
chmod +x install.sh && ./install.sh
```

The installation script automatically:
- ✅ Creates full Agent Workspaces (including Taizi/Libu_hr/Morning Officer, compatible with legacy main)
- ✅ Writes each department's SOUL.md (role personality + workflow rules + data sanitization specs)
- ✅ Registers Agents and permission matrix to `openclaw.json`
- ✅ Builds React frontend (requires Node.js 18+, skipped if not installed)
- ✅ Initializes data directory + first data sync
- ✅ Restarts Gateway for configuration to take effect

#### Start

```bash
# Terminal 1: Data refresh loop
bash scripts/run_loop.sh

# Terminal 2: Kanban server
python3 dashboard/server.py

# Open browser
open http://127.0.0.1:7891
```

> 💡 **Kanban ready out of the box**: `server.py` embeds `dashboard/dashboard.html`; Docker image includes pre-built React frontend

> 💡 For detailed tutorial see the [Getting Started guide](docs/getting-started.md)

---

## 🏛️ Architecture

```
                           ┌───────────────────────────────────┐
                           │          👑 Emperor (you)          │
                           │     Feishu · Telegram · Signal     │
                           └─────────────────┬─────────────────┘
                                             │ issue edict
                           ┌─────────────────▼─────────────────┐
                           │          🤴 Taizi (taizi)           │
                           │    Triage: chat replied / edict → task  │
                           └─────────────────┬─────────────────┘
                                             │ relay edict
                           ┌─────────────────▼─────────────────┐
                           │          📜 Zhongshu (zhongshu)    │
                           │    Receive → Plan → Break into sub-tasks  │
                           └─────────────────┬─────────────────┘
                                             │ submit for review
                           ┌─────────────────▼─────────────────┐
                           │          🔍 Menxia (menxia)        │
                           │    Review plan → Approve / Veto 🚫  │
                           └─────────────────┬─────────────────┘
                                             │ approved ✅
                           ┌─────────────────▼─────────────────┐
                           │          📮 Shangshu (shangshu)    │
                           │  Dispatch → Coordinate → Summarize │
                           └───┬──────┬──────┬──────┬──────┬───┘
                               │      │      │      │      │
                         ┌─────▼┐ ┌───▼───┐ ┌▼─────┐ ┌───▼─┐ ┌▼─────┐
                         │💰Hubu│ │📝 Libu│ │⚔️Bingbu│ │⚖️Xingbu│ │🔧Gongbu│
                         │ Data │ │ Docs  │ │ Eng.  │ │Compliance│ │Infra │
                         └──────┘ └──────┘ └──────┘ └─────┘ └──────┘
                                                               ┌──────┐
                                                               │📋Libu_hr│
                                                               │  HR  │
                                                               └──────┘
```

### Department Responsibilities

| Department | Agent ID | Responsibility | Specialty |
|------|----------|------|---------|
| 🤴 **Taizi** | `taizi` | Message triage, requirement sorting | Chat recognition, edict extraction, title summarization |
| 📜 **Zhongshu** | `zhongshu` | Receive edict, plan, break down | Requirement understanding, task decomposition, solution design |
| 🔍 **Menxia** | `menxia` | Review, gatekeeping, veto | Quality review, risk identification, standard control |
| 📮 **Shangshu** | `shangshu` | Dispatch, coordinate, summarize | Task scheduling, progress tracking, result integration |
| 💰 **Hubu** | `hubu` | Data, resources, accounting | Data processing, report generation, cost analysis |
| 📝 **Libu** | `libu` | Documentation, standards, reports | Technical docs, API docs, standards drafting |
| ⚔️ **Bingbu** | `bingbu` | Code, algorithms, inspection | Feature dev, bug fixing, code review |
| ⚖️ **Xingbu** | `xingbu` | Security, compliance, audit | Security scanning, compliance checking, red-line control |
| 🔧 **Gongbu** | `gongbu` | CI/CD, deployment, tooling | Docker config, pipelines, automation |
| 📋 **Libu_hr** | `libu_hr` | Personnel, Agent management | Agent registration, permission maintenance, training |
| 🌅 **Morning Officer** | `zaochao` | Daily morning court, news aggregation | Scheduled broadcasts, data summaries |

### Permission Matrix

> Not anyone can message anyone — real checks and balances

| From ↓ \ To → | Taizi | Zhongshu | Menxia | Shangshu | Hubu | Libu | Bingbu | Xingbu | Gongbu | Libu_hr |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Taizi** | — | ✅ | | | | | | | | |
| **Zhongshu** | ✅ | — | ✅ | ✅ | | | | | | |
| **Menxia** | | ✅ | — | ✅ | | | | | | |
| **Shangshu** | | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Six Ministries+Libu_hr** | | | | ✅ | | | | | | |

### Task State Flow

```
Emperor → Taizi Triage → Zhongshu Planning → Menxia Review → Dispatched → Executing → Awaiting Review → ✅ Completed
                              ↑          │                                          │
                              └── Veto ──┘                              Blocked
```

---

## 📁 Project Structure

```
edict/
├── agents/                     # 12 Agent personality templates
│   ├── taizi/SOUL.md           # Taizi · message triage (including edict title specs)
│   ├── zhongshu/SOUL.md        # Zhongshu · planning hub
│   ├── menxia/SOUL.md          # Menxia · review gatekeeping
│   ├── shangshu/SOUL.md        # Shangshu · dispatch brain
│   ├── hubu/SOUL.md            # Hubu · data resources
│   ├── libu/SOUL.md            # Libu · documentation standards
│   ├── bingbu/SOUL.md          # Bingbu · engineering implementation
│   ├── xingbu/SOUL.md          # Xingbu · compliance audit
│   ├── gongbu/SOUL.md          # Gongbu · infrastructure
│   ├── libu_hr/                # Libu_hr · personnel management
│   └── zaochao/SOUL.md         # Morning Officer · intelligence hub
├── dashboard/
│   ├── dashboard.html          # Grand Council kanban (single file · zero dependencies · ~2500 lines)
│   ├── dist/                   # React frontend build output (included in Docker image, optional locally)
│   └── server.py               # API server (Python stdlib · zero dependencies · ~1200 lines)
├── scripts/
│   ├── run_loop.sh             # Data refresh loop (every 15 seconds)
│   ├── kanban_update.py        # Kanban CLI (including edict data sanitization + title validation)
│   ├── skill_manager.py        # Skill management tool (remote/local Skills add, update, remove)
│   ├── sync_from_openclaw_runtime.py
│   ├── sync_agent_config.py
│   ├── sync_officials_stats.py
│   ├── fetch_morning_news.py
│   ├── refresh_live_data.py
│   ├── apply_model_changes.py
│   └── file_lock.py            # File lock (prevents concurrent multi-agent writes)
├── tests/
│   └── test_e2e_kanban.py      # End-to-end tests (17 assertions)
├── data/                       # Runtime data (gitignored)
├── docs/
│   ├── task-dispatch-architecture.md  # 📚 Detailed architecture doc: complete design of task dispatch, flow, and scheduling (business+technical)
│   ├── getting-started.md             # Quick start guide
│   ├── wechat-article.md              # WeChat article
│   └── screenshots/                   # Feature screenshots (11 images)
├── install.sh                  # One-click install script
├── CONTRIBUTING.md             # Contributing guide
└── LICENSE                     # MIT License
```

---

## 🎯 Usage

### Issue an Edict to AI

Send a message to Zhongshu via Feishu / Telegram / Signal:

```
Design a user registration system for me, requirements:
1. RESTful API (FastAPI)
2. PostgreSQL database
3. JWT authentication
4. Complete test cases
5. Deployment documentation
```

**Then sit back and watch:**

1. 📜 Zhongshu receives edict, plans sub-task allocation
2. 🔍 Menxia reviews, passes / vetoes and sends back for re-planning
3. 📮 Shangshu approves, dispatches to Bingbu + Gongbu + Libu
4. ⚔️ Departments execute in parallel, progress visible in real time
5. 📮 Shangshu summarizes results, reports back to you

The whole process can be monitored in real time on the **Grand Council Kanban**; you can **halt, cancel, or resume** at any time.

### Use Edict Templates

> Kanban → 📜 Templates → select template → fill parameters → issue edict

9 preset templates: Weekly report · Code review · API design · Competitive analysis · Data report · Blog post · Deployment plan · Email copy · Standup summary

### Customize Agents

Edit `agents/<id>/SOUL.md` to modify an Agent's personality, responsibilities, and output specifications.

### Add Skills (from the internet)

**Three ways to add Skills:**

#### 1️⃣ Kanban UI (simplest)

```
Kanban → 🔧 Skills Config → ➕ Add Remote Skill
→ enter Agent + Skill name + GitHub URL
→ Confirm → ✅ Done
```

#### 2️⃣ CLI command (most flexible)

```bash
# Add code_review skill to Zhongshu from GitHub
python3 scripts/skill_manager.py add-remote \
  --agent zhongshu \
  --name code_review \
  --source https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md \
  --description "Code review skill"

# One-click import official skills library to specified agents
python3 scripts/skill_manager.py import-official-hub \
  --agents zhongshu,menxia,shangshu,bingbu,xingbu

# List all added remote skills
python3 scripts/skill_manager.py list-remote

# Update a skill to latest version
python3 scripts/skill_manager.py update-remote \
  --agent zhongshu \
  --name code_review
```

#### 3️⃣ API request (automation integration)

```bash
# Add remote skill
curl -X POST http://localhost:7891/api/add-remote-skill \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "zhongshu",
    "skillName": "code_review",
    "sourceUrl": "https://raw.githubusercontent.com/...",
    "description": "Code review"
  }'

# View all remote skills
curl http://localhost:7891/api/remote-skills-list
```

**Official Skills Hub:** https://github.com/openclaw-ai/skills-hub

Available Skills:
- `code_review` — Code review (Python/JS/Go)
- `api_design` — API design review
- `security_audit` — Security audit
- `data_analysis` — Data analysis
- `doc_generation` — Documentation generation
- `test_framework` — Test framework design

See [🎓 Remote Skills Resource Management Guide](docs/remote-skills-guide.md)

---

## 🔧 Technical Highlights

| Feature | Description |
|------|------|
| **React 18 Frontend** | TypeScript + Vite + Zustand state management, 13 feature components |
| **Pure stdlib backend** | `server.py` based on `http.server`, zero dependencies, serves both API + static files |
| **Agent thinking visible** | Real-time display of Agent thinking process, tool calls, return results |
| **One-click install** | `install.sh` completes all configuration automatically |
| **15-second sync** | Data auto-refreshes, kanban shows countdown |
| **Daily ceremony** | Opening animation plays on first daily open |
| **Remote Skills ecosystem** | One-click import capabilities from GitHub/URL, with version management + CLI + API + UI |

---

## 📚 Deep Dive

### Core Documentation

- **[📖 Complete Task Dispatch Architecture](docs/task-dispatch-architecture.md)** — **Must-read**
  - Detailed explanation of the business design and technical implementation of how Three Departments & Six Ministries handles complex tasks
  - Covers: 9-state task state machine / permission matrix / 4-phase scheduling (retry→escalation→rollback) / Session JSONL data fusion
  - Includes complete use cases, API endpoint documentation, CLI tool docs
  - Comparison with CrewAI/AutoGen: why institutional > free collaboration
  - Failure scenarios and recovery mechanisms
  - **Reading this document will help you understand why Three Departments & Six Ministries is so powerful** (9500+ words, 30 minutes for full understanding)

- **[🎓 Remote Skills Resource Management Guide](docs/remote-skills-guide.md)** — Skills ecosystem
  - Connect and supplement skills from the internet, supporting GitHub/any HTTPS URL
  - Official Skills Hub preset capability library
  - CLI tools + kanban UI + RESTful API
  - Skill file specification and security protection
  - Supports version management and one-click update

- **[⚡ Remote Skills Quick Start](docs/remote-skills-quickstart.md)** — 5-minute start
  - Quick experience, CLI commands, kanban operation examples
  - Create your own Skills library
  - Complete API reference + FAQ

- **[🚀 Getting Started Guide](docs/getting-started.md)** — New user guide
- **[🤝 Contributing Guide](CONTRIBUTING.md)** — Want to contribute? Start here

---

## 🔧 Common Troubleshooting

<details>
<summary><b>❌ Tasks always timeout / subordinates completed but cannot report back to Taizi</b></summary>

**Symptom**: Six Ministries or Shangshu completed the task, but Taizi doesn't receive the report and it times out.

**Troubleshooting steps**:

1. **Check Agent registration status**:
```bash
curl -s http://127.0.0.1:7891/api/agents-status | python3 -m json.tool
```
Confirm that `taizi` agent's `statusLabel` is `alive`.

2. **Check Gateway logs**:
```bash
ls /tmp/openclaw/ | tail -5          # find latest log
grep -i "error\|fail\|unknown" /tmp/openclaw/openclaw-*.log | tail -20
```

3. **Common causes**:
   - Agent ID mismatch (fixed in v1.2: `main` → `taizi`)
   - LLM provider timeout (automatic retry added)
   - Zombie Agent process (run `ps aux | grep openclaw` to check)

4. **Force retry**:
```bash
# Manually trigger scheduler scan (auto-retries stuck tasks)
curl -X POST http://127.0.0.1:7891/api/scheduler-scan \
  -H 'Content-Type: application/json' -d '{"thresholdSec":60}'
```

</details>

<details>
<summary><b>❌ Docker: exec format error</b></summary>

**Symptom**: `exec /usr/local/bin/python3: exec format error`

**Cause**: Image architecture (arm64) doesn't match host architecture (amd64).

**Fix**:
```bash
# Option 1: specify platform
docker run --platform linux/amd64 -p 7891:7891 cft0808/sansheng-demo

# Option 2: use docker-compose (has platform built in)
docker compose up
```

</details>

<details>
<summary><b>❌ Skill download failed</b></summary>

**Symptom**: `python3 scripts/skill_manager.py import-official-hub` errors.

**Diagnose**:
```bash
# Test network connectivity
curl -I https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md

# If timeout, use a proxy
export https_proxy=http://your-proxy:port
python3 scripts/skill_manager.py import-official-hub --agents zhongshu
```

**Common causes**:
- Accessing GitHub raw resources from mainland China may require a proxy
- Network timeout (increased to 30 seconds + automatic retry 3 times)
- Official Skills Hub repository under maintenance

</details>

---

## 🗺️ Roadmap

> Full roadmap and how to participate: [ROADMAP.md](ROADMAP.md)

### Phase 1 — Core Architecture ✅
- [x] Twelve-department Agent architecture (Taizi + Three Departments + Seven Ministries + Morning Officer) + permission matrix
- [x] Grand Council real-time kanban (10 feature panels + real-time activity panel)
- [x] Task halt / cancel / resume
- [x] Memorial system (auto-archive + five-phase timeline)
- [x] Edict template library (9 presets + parameter forms)
- [x] Court ceremony animation
- [x] Morning Brief + Feishu push + subscription management
- [x] Hot-swap models + skill management + skill addition
- [x] Officials overview + Token consumption stats
- [x] Sessions / session monitoring
- [x] Taizi message triage (casual chat auto-reply / commands create tasks)
- [x] Edict data sanitization (auto-strip paths/metadata/prefixes)
- [x] Duplicate task protection + completed task protection
- [x] End-to-end test coverage (17 assertions)
- [x] React 18 frontend refactor (TypeScript + Vite + Zustand · 13 components)
- [x] Agent thinking process visualization (real-time thinking / tool calls / return results)
- [x] Integrated frontend+backend deployment (server.py serves both API + static files)

### Phase 2 — System Deepening 🚧
- [ ] Imperial approval mode (human approval + one-click approve/veto)
- [ ] Merit record (Agent performance scoring system)
- [ ] Express courier (real-time Agent message flow visualization)
- [ ] National History Archive (knowledge base retrieval + citation tracing)

### Phase 3 — Ecosystem Expansion
- [ ] Docker Compose + Demo image
- [ ] Notion / Linear adapters
- [ ] Annual review (Agent annual performance report)
- [ ] Mobile adaptation + PWA
- [ ] ClawHub listing

---

## 🤝 Contributing

All forms of contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

Especially welcome directions:
- 🎨 **UI enhancements**: dark/light theme, responsive, animation optimization
- 🤖 **New Agents**: specialized Agent roles for specific scenarios
- 📦 **Skills ecosystem**: department-specific skill packs
- 🔗 **Integration extensions**: Notion · Jira · Linear · GitHub Issues
- 🌐 **Internationalization**: Japanese · Korean · Spanish
- 📱 **Mobile**: responsive adaptation, PWA

---

## 📂 Examples

The `examples/` directory contains real end-to-end use cases:

| Case | Edict | Departments Involved |
|------|------|----------|
| [Competitive Analysis](examples/competitive-analysis.md) | "Analyze CrewAI vs AutoGen vs LangGraph" | Zhongshu→Menxia→Hubu+Bingbu+Libu |
| [Code Review](examples/code-review.md) | "Review this FastAPI code for security" | Zhongshu→Menxia→Bingbu+Xingbu |
| [Weekly Report](examples/weekly-report.md) | "Generate this week's engineering team report" | Zhongshu→Menxia→Hubu+Libu |

Each case includes: complete edict → Zhongshu planning → Menxia review comments → department execution results → final memorial.

---

## ⭐ Star History

If this project made you smile, please give it a Star ⚔️

[![Star History Chart](https://api.star-history.com/svg?repos=cft0808/edict&type=Date)](https://star-history.com/#cft0808/edict&Date)

---

## 📮 The Imperial Gazette — WeChat Account

> In ancient times, the imperial gazette spread edicts across the realm. Today, the WeChat account talks about AI architecture.

<p align="center">
  <img src="docs/assets/wechat-qrcode.jpg" width="220" alt="WeChat QR Code · cft0808">
  <br><br>
  <b>👆 Scan to follow "cft0808" — the Emperor's tech gazette</b>
</p>

You'll see:

- 🏛️ **Architecture breakdowns** — How exactly does Three Departments & Six Ministries divide power? What does each of the 12 Agents do?
- 🔥 **Lessons learned** — What to do when Agents argue? How to save tokens? Why does Menxia always veto?
- 🛠️ **Bug fix records** — Every bug is a memorial, watch how the Emperor handles it
- 💡 **Token cost-saving tips** — The secret to running Menxia review with 1/10 the tokens
- 🎭 **Agent persona easter eggs** — How were the Six Ministries' SOUL.md files written?

> *"I made AI attend court, and AI turned out to be more diligent than me."* — You'll understand after following.

---

## 📄 License

[MIT](LICENSE) · Built by the [OpenClaw](https://openclaw.ai) community

---

<p align="center">
  <strong>⚔️ Govern new technology with ancient wisdom, command AI with institutional design</strong><br>
  <sub>Governing AI with the wisdom of ancient empires</sub><br><br>
  <a href="#-the-imperial-gazette--wechat-account"><img src="https://img.shields.io/badge/WeChat_cft0808-Follow_for_updates-07C160?style=for-the-badge&logo=wechat&logoColor=white" alt="WeChat"></a>
</p>
