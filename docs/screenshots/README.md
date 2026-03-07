# 📸 Screenshot Guide

Kanban screenshots are used for README and documentation display. After starting the kanban, take screenshots in the following order and place them in this directory.

## Screenshot List

| Filename | Content | Corresponding Panel |
|--------|------|---------|
| `01-kanban-main.png` | Edict board overview | 📋 Edict Board |
| `02-monitor.png` | Department monitor | 🔭 Department Monitor |
| `03-task-detail.png` | Task flow details (click task card to expand) | 📋 Edict Board → Details |
| `04-model-config.png` | Model configuration panel | ⚙️ Model Config |
| `05-skills-config.png` | Skills configuration panel | 🛠️ Skills Config |
| `06-official-overview.png` | Officials overview (12 Agents) | 👥 Officials Overview |
| `07-sessions.png` | Sessions / tasks | 💬 Sessions |
| `08-memorials.png` | Memorials archive | 📜 Memorials |
| `09-templates.png` | Template library (edict templates) | 📜 Templates |
| `10-morning-briefing.png` | Morning news brief | 📰 Morning Brief |
| `11-ceremony.png` | Court ceremony opening animation | Opening animation |

## Automated Screenshots

```bash
# Make sure the kanban server is running
python3 dashboard/server.py &

# Auto-capture all 11 screenshots
python3 scripts/take_screenshots.py

# Record demo GIF (requires ffmpeg)
python3 scripts/record_demo.py
```

## Recommendations

- Use **1920×1080** or **2560×1440** resolution
- Make sure the kanban has enough data (at least 5+ tasks)
- Dark theme screenshots look best
- Refresh data before taking screenshots to ensure latest state
