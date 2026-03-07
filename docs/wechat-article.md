# I Redesigned AI Multi-Agent Collaboration Architecture Using the Three Departments & Six Ministries System

> A system designed 1300 years ago understands checks and balances better than modern AI frameworks.

![Cover: Grand Council kanban overview](screenshots/01-kanban-main.png)

---

## I. A Strange Idea

Late last year I started heavily using AI Agents for work — writing code, doing analysis, generating documentation. I used several of the most popular multi-agent frameworks on the market.

After a month, I discovered a fundamental problem:

**These frameworks have no concept of "review."**

CrewAI's model: a few Agents each do their work, hand it in when done. AutoGen is slightly better with Human-in-the-loop, but essentially you yourself are acting as QA. MetaGPT has role division, but review is optional.

It's like a company with no QA department, where engineers push code directly to production.

You get the final result without knowing what happened in between — you can't reproduce it, can't audit it, can't intervene. When something goes wrong you can only re-run.

I kept thinking: is there an architecture that naturally embeds review into the process — not as an optional plugin, but as a mandatory checkpoint?

Then one day, while reading the *Zizhi Tongjian*, it suddenly came to me —

**The Three Departments & Six Ministries system.**

Emperor Taizong designed this system 1300 years ago: Zhongshu drafts edicts, Menxia reviews and can veto, Shangshu executes. Three departments check and balance each other; any edict must pass review before being issued.

Isn't this exactly the architecture I was looking for?

![Court ceremony: the easter egg animation on first daily open](screenshots/11-ceremony.png)
*▲ The first time you open the kanban each day, a court ceremony opening animation plays — full ceremony vibes*

---

## II. The Ancients' Architecture Design

The Three Departments & Six Ministries system is not a metaphor — it is a system of checks and balances tested by 1400 years of practice.

Simplified, the information flow is:

```
Emperor (you)
  ↓ issue edict
Zhongshu (Planning)  ← breaks your sentence into executable sub-tasks
  ↓ submit for review
Menxia (Review)      ← reviews plan quality, rejects if unacceptable
  ↓ approved
Shangshu (Dispatch)  ← assigns to the Six Ministries for execution
  ↓
Six Ministries       ← Hubu handles data, Libu handles docs, Bingbu handles dev, Xingbu handles compliance, Gongbu handles infrastructure
  ↓
Shangshu summarizes and reports back  ← results reported to you
```

Note the most critical step here: **Menxia review**.

After Zhongshu plans a solution, it doesn't go directly to the execution layer — it must first pass through Menxia review. Menxia will check:

- Is the sub-task breakdown reasonable? Are there missed requirements?
- Is the department assignment accurate? Was something that should go to Bingbu sent to Libu instead?
- Is the plan executable? Are there any unrealistic parts?

If it's not up to standard, Menxia can **veto** — send it straight back for Zhongshu to re-plan. Not a warning, but a mandatory rework.

This is why the Tang dynasty ran for 289 years. **Unchecked power will inevitably go wrong** — Emperor Taizong understood this clearly.

---

## III. I Made It an Open Source Project

I built a real Three Departments & Six Ministries system using OpenClaw. 9 AI Agents each perform their role, communicating strictly according to the permission matrix.

The project is called **Edict (Three Departments & Six Ministries)**, and it's open source:

**GitHub: https://github.com/cft0808/edict**

The core architecture is simple:

- **Zhongshu**: Receives edicts (your instructions), plans solutions, breaks down sub-tasks
- **Menxia**: Reviews plans, ensures quality, vetoes if unacceptable
- **Shangshu**: Dispatches to the Six Ministries after approval, coordinates execution, summarizes results
- **Six Ministries**: Hubu (data analysis), Libu (documentation writing), Bingbu (code development), Xingbu (security compliance), Gongbu (CI/CD deployment)
- **Morning Officer**: Pushes you a daily news briefing

Each Agent has an independent Workspace, independent Skills, and an independent LLM model. A strict permission matrix — who can message whom, in writing:

| Who ↓ messages whom → | Zhongshu | Menxia | Shangshu | Six Ministries |
|:---:|:---:|:---:|:---:|:---:|
| **Zhongshu** | — | ✅ | ✅ | ❌ |
| **Menxia** | ✅ | — | ✅ | ❌ |
| **Shangshu** | ✅ | ✅ | — | ✅ |
| **Six Ministries** | ❌ | ❌ | ✅ | ❌ |

Zhongshu cannot directly command the Six Ministries; the Six Ministries cannot bypass to report to Zhongshu. All cross-layer communication must go through Shangshu as an intermediary.

**This is not a decorative setting — this is an architecture-level hard constraint.**

![Demo: complete flow in 30 seconds](demo.gif)
*▲ 30-second demo: a full tour from court ceremony to edict board, memorial archive, and model configuration*

---

## IV. Comparison with Existing Frameworks

You might ask: compared to CrewAI and AutoGen, what's the difference?

| | CrewAI | AutoGen | **Three Departments & Six Ministries** |
|---|:---:|:---:|:---:|
| Review mechanism | ❌ | ⚠️ Optional | ✅ Menxia mandatory review |
| Real-time kanban | ❌ | ❌ | ✅ 10 panels |
| Task intervention | ❌ | ❌ | ✅ Halt / cancel / resume |
| Flow audit | ⚠️ | ❌ | ✅ Complete memorial archive |
| Agent health monitoring | ❌ | ❌ | ✅ Heartbeat detection |
| Hot-swap LLM | ❌ | ❌ | ✅ One-click switch from kanban |

The core difference is the **Menxia review mechanism**.

This is not Human-in-the-loop (that makes you yourself the QA) — this is a dedicated AI Agent responsible for reviewing another AI Agent's output. Institutional, mandatory, at the architecture level.

An AI collaboration system without review is like a team without code review — fast to run, fast to crash.

---

## V. The Grand Council Kanban — Making Everything Observable

Good architecture alone is not enough — you also need visibility.

So I built a **Grand Council Kanban** — a Web panel for real-time monitoring of all task flows. Zero dependencies, single-file HTML, Python standard library backend, opens in browser.

10 feature panels:

**📋 Edict Board**: All tasks displayed as cards, grouped by state, with filter and search. Each card has a heartbeat badge — 🟢 active, 🟡 stalled, 🔴 alert. Click to see the complete flow timeline; halt or cancel at any time.

![Edict board](screenshots/01-kanban-main.png)
*▲ Edict board: task cards grouped by state, heartbeat badges at a glance*

**🔭 Department Monitor**: Visualizes task count per state, department distribution, Agent health cards. See at a glance who is busy, who is idle, who is down.

![Department monitor](screenshots/02-monitor.png)
*▲ Department monitor: state distribution + department load + Agent health cards*

**📜 Memorials**: All completed edicts are automatically archived as "memorials," showing the complete five-phase timeline — Edict→Zhongshu Planning→Menxia Review→Six Ministries Execution→Report Back. One-click copy as Markdown.

![Memorial archive](screenshots/08-memorials.png)
*▲ Memorials: complete five-phase timeline, one-click Markdown export*

**📜 Templates**: 9 preset edict templates. Select one, fill in parameters, preview, issue edict with one click. Covers: weekly reports, code review, API design, competitive analysis, and other common scenarios.

![Edict template library](screenshots/09-templates.png)
*▲ Templates: 9 preset templates, fill parameters and issue edict with one click*

**⚙️ Model Config**: Each Agent can independently switch LLM models. Zhongshu uses Claude for planning, Bingbu uses GPT-4o for coding, Hubu uses DeepSeek for data crunching — each to their strength.

![Model configuration](screenshots/04-model-config.png)
*▲ Model config: each Agent switches LLM independently, each to their strength*

Also: Officials overview (Token consumption leaderboard), skill management, Morning Brief (automated news aggregation), session monitoring, and court ceremony (easter egg animation on first daily open).

**All zero dependencies** — no React, no Vue, pure HTML + CSS + JavaScript, done in 2200 lines.

![Officials overview](screenshots/06-official-overview.png)
*▲ Officials overview: Token consumption leaderboard + activity stats*

![Morning brief](screenshots/10-morning-briefing.png)
*▲ Morning brief: auto-aggregates tech/finance news daily*

---

## VI. A Real Case Walk-Through

Showing beats telling. Here's a real run record — having Three Departments & Six Ministries analyze competitors.

**Edict**: Analyze the differences between the CrewAI, AutoGen, and LangGraph frameworks and output a comparison report.

![Task flow details](screenshots/03-task-detail.png)
*▲ Click any task card to see the complete flow chain and real-time status*

### Zhongshu Planning (45 seconds)

After receiving the edict, Zhongshu broke it into 4 sub-tasks:
1. Bingbu → Architecture & communication mechanism research
2. Hubu → Data collection & quantitative comparison (GitHub Stars, contributors, etc.)
3. Bingbu → Developer experience deep evaluation
4. Libu → Consolidate and write comparison report

### Menxia Review (32 seconds) — Vetoed!

**Menxia's first round sent it straight back:**

> *"The plan has three problems: 1) The edict explicitly requires evaluating 'observability,' but there's no corresponding sub-task in the plan; 2) Sub-tasks 1 and 3 are both Bingbu research with overlap, suggest merging; 3) Missing a conclusory sub-task for recommended use cases — analysis without conclusions is no analysis. Rejected."*

After Zhongshu revised the plan, Menxia approved on the second round.

**This is the value of Menxia.** Without this step, Bingbu would have done two research tasks, and the final report would have no recommended use cases — because the original plan didn't require it.

### Execution by Departments (17 minutes)

- **Bingbu**: In-depth technical comparison covering architecture, communication, and observability dimensions
- **Hubu**: Quantitative data table — Stars, contributors, issue response time, Hello World setup time
- **Libu**: Integrates Bingbu + Hubu data, writes the final report

### Report Back

22 minutes, 15,800 tokens, a structured comparison report. Interesting conclusions:

| Scenario | Recommendation | Reason |
|------|------|------|
| Rapid prototyping | CrewAI | Fastest to learn |
| Conversational collaboration | AutoGen | Naturally suited for multi-round discussion |
| Complex workflows | LangGraph | Most flexible state machine |
| **Reliability first** | **Three Departments & Six Ministries** | Only one with built-in mandatory review |

---

## VII. Some Technical Choices

When building this project, I made several deliberate technical decisions:

**1. Zero dependencies**

The kanban frontend is one HTML file, 2200 lines, no frameworks used. The backend is Python's standard library `http.server`, no Flask or FastAPI.

Why? Because I didn't want people to `pip install` a pile of things before running it. The target users for this project might just want to quickly experience the Three Departments & Six Ministries flow, without setting up an environment.

**2. One SOUL.md per Agent**

Each Agent's personality, responsibilities, and workflow rules are written in a single Markdown file. Want to change Menxia's review standards? Edit `agents/menxia/SOUL.md` and it takes effect on the next start.

This means you can customize your own Three Departments & Six Ministries — maybe your "Bingbu" handles market analysis instead of engineering. Just change the SOUL.md.

**3. The permission matrix is mandatory**

It's not "suggesting" that Agents avoid cross-level communication — it's enforced at the architecture level. The Six Ministries cannot message Zhongshu; Zhongshu cannot bypass Menxia to have Shangshu execute directly. The OpenClaw config file has in writing exactly who can talk to whom.

---

## VIII. Try It Now

The project is open source under MIT license.

**GitHub: https://github.com/cft0808/edict**

Fastest way to experience it:

```bash
# Start with Docker in one line
docker run -p 7891:7891 cft0808/edict

# Open browser
open http://localhost:7891
```

If you have OpenClaw installed, you can do a full install:

```bash
git clone https://github.com/cft0808/edict.git
cd edict
chmod +x install.sh && ./install.sh
```

The install script automatically creates 9 Agent Workspaces, writes personality files, registers the permission matrix, and restarts Gateway.

![Skills configuration](screenshots/05-skills-config.png)
*▲ Skill management: an overview of installed Skills per department, with option to view details and add new skills*

---

## IX. What's Next

Phase 1 (core architecture) is complete. Next things to build:

- **Imperial Approval Mode**: Push Menxia's review results to your Feishu/Telegram so you personally decide whether to approve or veto
- **Merit Record**: Performance scoring for each Agent — completion rate, rework rate, time statistics
- **Express Courier**: Add a real-time Agent communication flow diagram to the kanban — a connection lights up when Zhongshu messages Menxia
- **National History Archive**: Accumulate historical edicts and memorials into a knowledge base; new edicts can reference historical experience

The complete Roadmap is on GitHub; each sub-item in Phase 2 and Phase 3 has a difficulty label — contributions welcome.

---

## Finally

The core problem of AI Agent collaboration is not "making Agents smarter" — it's "giving Agent collaboration rules."

CrewAI solved the problem of "multiple Agents working together." AutoGen solved the problem of "Agents being able to talk to each other."

But who solves the problem of "ensuring the quality of Agent output"?

Emperor Taizong gave the answer 1300 years ago: **checks and balances**. Planners don't review, reviewers don't execute, executors don't plan. Every step is watched by someone; every decision must go through deliberation.

This may be the most elegant "AI governance" solution I've ever seen — because it wasn't designed for AI at all.

It was designed for **governance** itself.

---

**GitHub: https://github.com/cft0808/edict**

Open source · MIT · Stars welcome ⚔️
