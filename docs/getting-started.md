# 🚀 Quick Start Guide

> From zero to a running Three Departments & Six Ministries AI collaboration system in 5 minutes

---

## Step 1: Install OpenClaw

Three Departments & Six Ministries runs on [OpenClaw](https://openclaw.ai) — install it first:

```bash
# macOS
brew install openclaw

# or download the installer
# https://openclaw.ai/download
```

After installation, initialize:

```bash
openclaw init
```

## Step 2: Clone and Install Three Departments & Six Ministries

```bash
git clone https://github.com/cft0808/edict.git
cd edict
chmod +x install.sh && ./install.sh
```

The installation script automatically:
- ✅ Creates 12 Agent Workspaces (`~/.openclaw/workspace-*`)
- ✅ Writes each department's SOUL.md personality file
- ✅ Registers Agents and permission matrix to `openclaw.json`
- ✅ Configures edict data sanitization rules
- ✅ Builds React frontend to `dashboard/dist/` (requires Node.js 18+)
- ✅ Initializes data directory
- ✅ Runs first data sync
- ✅ Restarts Gateway for configuration to take effect

## Step 3: Configure Message Channel

Configure a message channel in OpenClaw (Feishu / Telegram / Signal), setting the `taizi` (Taizi) Agent as the edict entry point. Taizi will automatically triage casual chat vs. commands; commands are summarized and forwarded to Zhongshu.

```bash
# View current channels
openclaw channels list

# Add Feishu channel (entry point set to Taizi)
openclaw channels add --type feishu --agent taizi
```

Reference OpenClaw documentation: https://docs.openclaw.ai/channels

## Step 4: Start Services

```bash
# Terminal 1: Data refresh loop (syncs every 15 seconds)
bash scripts/run_loop.sh

# Terminal 2: Kanban server
python3 dashboard/server.py

# Open browser
open http://127.0.0.1:7891
```

> 💡 **Tip**: `run_loop.sh` auto-syncs every 15 seconds. Can run with `&` in the background.

> 💡 **Kanban ready out of the box**: `server.py` embeds `dashboard/dashboard.html`, no extra build needed. Docker image includes pre-built React frontend.

## Step 5: Send Your First Edict

Send a task through the message channel (Taizi will automatically recognize and forward to Zhongshu):

```
Please help me write a text classifier in Python:
1. Use scikit-learn
2. Support multi-class classification
3. Output a confusion matrix
4. Write complete documentation
```

## Step 6: Observe the Execution Process

Open the kanban at http://127.0.0.1:7891

1. **📋 Edict Board** — watch tasks flow between states
2. **🔭 Department Monitor** — view work distribution across departments
3. **📜 Memorials** — tasks auto-archived as memorials after completion

Task flow path:
```
Inbox → Taizi Triage → Zhongshu Planning → Menxia Review → Dispatched → Executing → Completed
```

---

## 🎯 Advanced Usage

### Using Edict Templates

> Kanban → 📜 Templates → Select template → Fill in parameters → Issue edict

9 preset templates: Weekly report · Code review · API design · Competitive analysis · Data report · Blog post · Deployment plan · Email copy · Standup summary

### Switch Agent Model

> Kanban → ⚙️ Model Config → Select new model → Apply changes

Gateway automatically restarts and takes effect in ~5 seconds.

### Manage Skills

> Kanban → 🛠️ Skills Config → View installed skills → Click to add new skill

### Halt / Cancel Task

> In the Edict Board or task details, click the **⏸ Halt** or **🚫 Cancel** button

### Subscribe to Morning Brief

> Kanban → 📰 Morning Brief → ⚙️ Subscription Management → Select categories / add sources / configure Feishu push

---

## ❓ Troubleshooting

### Kanban shows "Server not started"
```bash
# Confirm the server is running
python3 dashboard/server.py
```

### Agent not responding
```bash
# Check Gateway status
openclaw gateway status

# Restart if necessary
openclaw gateway restart
```

### Data not updating
```bash
# Check if refresh loop is running
ps aux | grep run_loop

# Manually run one sync
python3 scripts/refresh_live_data.py
```

### Heartbeat shows red / alert
```bash
# Check the process for the corresponding Agent
openclaw agent status <agent-id>

# Restart the specified Agent
openclaw agent restart <agent-id>
```

### Model switch not taking effect
Wait ~5 seconds for Gateway to finish restarting. If still not working:
```bash
python3 scripts/apply_model_changes.py
openclaw gateway restart
```

---

## 📚 More Resources

- [🏠 Project homepage](https://github.com/cft0808/edict)
- [📖 README](../README.md)
- [🤝 Contributing guide](../CONTRIBUTING.md)
- [💬 OpenClaw documentation](https://docs.openclaw.ai)
- [📮 WeChat account · cft0808](wechat.md) — architecture breakdowns / lessons learned / token cost-saving tips
