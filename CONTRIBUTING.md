# 🤝 Contributing

<p align="center">
  <strong>Three Departments & Six Ministries welcomes all heroes ⚔️</strong><br>
  <sub>Whether you fix a typo or design a new Agent role, we are deeply grateful</sub>
</p>

---

## 📋 How to Contribute

### 🐛 Report a Bug

Please use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template to submit an Issue, including:
- OpenClaw version (`openclaw --version`)
- Python version (`python3 --version`)
- Operating system
- Steps to reproduce (the more detail the better)
- Expected behavior vs actual behavior
- Screenshot (if involving the kanban UI)

### 💡 Feature Suggestions

Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template.

We recommend describing your needs in the format of an "edict" — like writing a memorial to the Emperor 😄

### 🔧 Submit a Pull Request

```bash
# 1. Fork this repository
# 2. Clone your fork
git clone https://github.com/<your-username>/edict.git
cd edict

# 3. Create a feature branch
git checkout -b feat/my-awesome-feature

# 4. Develop & test
python3 dashboard/server.py  # start kanban to verify

# 5. Commit
git add .
git commit -m "feat: add a really cool feature"

# 6. Push & create PR
git push origin feat/my-awesome-feature
```

---

## ��️ Development Environment

### Prerequisites
- [OpenClaw](https://openclaw.ai) installed
- Python 3.9+
- macOS / Linux

### Local Start

```bash
# Install
./install.sh

# Start data refresh (run in background)
bash scripts/run_loop.sh &

# Start kanban server
python3 dashboard/server.py

# Open browser
open http://127.0.0.1:7891
```

> 💡 **Kanban ready out of the box**: `server.py` embeds `dashboard/dashboard.html`; Docker image includes pre-built React frontend

### Project Structure Overview

| Directory/File | Description | Change Frequency |
|----------|------|--------|
| `dashboard/dashboard.html` | Kanban frontend (single file, zero dependencies, ready to use) | 🔥 High |
| `dashboard/server.py` | API server (stdlib, ~2200 lines) | 🔥 High |
| `agents/*/SOUL.md` | 12 Agent personality templates | 🔶 Medium |
| `scripts/kanban_update.py` | Kanban CLI + data sanitization (~300 lines) | 🔶 Medium |
| `scripts/*.py` | Data sync / automation scripts | 🔶 Medium |
| `tests/test_e2e_kanban.py` | E2E kanban tests (17 assertions) | 🔶 Medium |
| `install.sh` | Installation script | 🟢 Low |

---

## 📝 Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     ✨ New feature
fix:      🐛 Bug fix
docs:     📝 Documentation update
style:    🎨 Code formatting (no logic changes)
refactor: ♻️ Code refactor
perf:     ⚡ Performance optimization
test:     ✅ Tests
chore:    🔧 Miscellaneous maintenance
ci:       👷 CI/CD configuration
```

Examples:
```
feat: add memorial export to PDF
fix: fix Gateway not restarting after model switch
docs: update README screenshots
```

---

## 🎯 Especially Welcome Contributions

### 🎨 Kanban UI
- Dark/light theme toggle
- Responsive layout optimization
- Animation enhancements
- Accessibility (a11y) improvements

### 🤖 New Agent Roles
- Specialized Agents for specific industries/scenarios
- New SOUL.md personality templates
- Innovations in Agent collaboration patterns

### 📦 Skills Ecosystem
- Department-specific skill packs
- MCP integration skills
- Data processing / code analysis / documentation generation skills

### 🔗 Third-party Integrations
- Notion / Jira / Linear sync
- GitHub Issues / PR integration
- Slack / Discord messaging channels
- Webhook extensions

### 🌐 Internationalization
- Japanese / Korean / Spanish translations
- Kanban UI multi-language support

### 📱 Mobile
- Responsive adaptation
- PWA support
- Mobile operation optimization

---

## 🧪 Testing

```bash
# Compilation check
python3 -m py_compile dashboard/server.py
python3 -m py_compile scripts/kanban_update.py

# E2E kanban tests (9 scenarios, 17 assertions)
python3 tests/test_e2e_kanban.py

# Verify data sync
python3 scripts/refresh_live_data.py
python3 scripts/sync_agent_config.py

# Start server to verify API
python3 dashboard/server.py &
curl -s http://localhost:7891/api/live-status | python3 -m json.tool | head -20
```

---

## 📏 Code Style

- **Python**: PEP 8, use pathlib for paths
- **TypeScript/React**: Function components + Hooks, CSS variable names start with `--`
- **CSS**: Use CSS variables (`--bg`, `--text`, `--acc`, etc.), BEM-style class names
- **Markdown**: Use `#` for headings, `-` for lists, annotate language in code blocks

---

## 🙏 Code of Conduct

- Be friendly and constructive
- Respect different viewpoints and experiences
- Accept constructive criticism
- Focus on what is best for the community
- Show empathy toward other community members

**We have zero tolerance for harassment.**

---

## 📬 Contact

- GitHub Issues: [Submit an issue](https://github.com/cft0808/edict/issues)
- GitHub Discussions: [Community discussion](https://github.com/cft0808/edict/discussions)

---

<p align="center">
  <sub>Thank you to every contributor — you are the cornerstone of Three Departments & Six Ministries ⚔️</sub>
</p>
