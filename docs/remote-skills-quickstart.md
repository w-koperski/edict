# Remote Skills Quick Start

## 5-Minute Experience

### 1. Start the Server

```bash
# Make sure you're in the project root directory
python3 dashboard/server.py
# Output: Three Departments & Six Ministries kanban started → http://127.0.0.1:7891
```

### 2. Add an Official Skill (CLI)

```bash
# Add code review skill to Zhongshu
python3 scripts/skill_manager.py add-remote \
  --agent zhongshu \
  --name code_review \
  --source https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md \
  --description "Code review capability"

# Output:
# ⏳ Downloading from https://raw.githubusercontent.com/...
# ✅ Skill code_review added to zhongshu
#    Path: /Users/xxx/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md
#    Size: 2048 bytes
```

### 3. List All Remote Skills

```bash
python3 scripts/skill_manager.py list-remote

# Output:
# 📋 1 remote skill(s):
# 
# Agent       | Skill Name           | Description                    | Added At
# ------------|----------------------|--------------------------------|----------
# zhongshu    | code_review          | Code review capability         | 2026-03-02
```

### 4. View API Response

```bash
curl http://localhost:7891/api/remote-skills-list | jq .

# Output:
# {
#   "ok": true,
#   "remoteSkills": [
#     {
#       "skillName": "code_review",
#       "agentId": "zhongshu",
#       "sourceUrl": "https://raw.githubusercontent.com/...",
#       "description": "Code review capability",
#       "localPath": "/Users/xxx/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md",
#       "addedAt": "2026-03-02T14:30:00Z",
#       "lastUpdated": "2026-03-02T14:30:00Z",
#       "status": "valid"
#     }
#   ],
#   "count": 1,
#   "listedAt": "2026-03-02T14:35:00Z"
# }
```

---

## Common Operations

### One-click import of all skills from the official library

```bash
python3 scripts/skill_manager.py import-official-hub \
  --agents zhongshu,menxia,shangshu,bingbu,xingbu
```

This automatically adds for each agent:
- **zhongshu**: code_review, api_design, doc_generation
- **menxia**: code_review, api_design, security_audit, data_analysis, doc_generation, test_framework
- **shangshu**: same as menxia (coordinator)
- **bingbu**: code_review, api_design, test_framework
- **xingbu**: code_review, security_audit, test_framework

### Update a Skill to the Latest Version

```bash
python3 scripts/skill_manager.py update-remote \
  --agent zhongshu \
  --name code_review

# Output:
# ⏳ Downloading from https://raw.githubusercontent.com/...
# ✅ Skill code_review added to zhongshu
# ✅ Skill updated
#    Path: /Users/xxx/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md
#    Size: 2156 bytes
```

### Remove a Skill

```bash
python3 scripts/skill_manager.py remove-remote \
  --agent zhongshu \
  --name code_review

# Output:
# ✅ Skill code_review removed from zhongshu
```

---

## Kanban UI Operations

### Adding a Remote Skill in the Kanban

1. Open http://localhost:7891
2. Go to the 🔧 **Skills Config** panel
3. Click the **➕ Add Remote Skill** button
4. Fill in the form:
   - **Agent**: Select from dropdown (e.g. zhongshu)
   - **Skill Name**: Enter internal ID e.g. `code_review`
   - **Remote URL**: Paste GitHub URL e.g. `https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md`
   - **Description**: Optional, e.g. `Code review capability`
5. Click **Import** button
6. Wait 1-2 seconds, see ✅ success message

### Manage Added Skills

In kanban → 🔧 Skills Config → **Remote Skills** tab:

- **View**: Click skill name to view SKILL.md content
- **Update**: Click 🔄 to re-download latest version from source URL
- **Delete**: Click ✕ to remove local copy
- **Copy URL**: Quickly share with others

---

## Create Your Own Skill Library

### Directory Structure

```
my-skills-hub/
├── code_review/
│   └── SKILL.md          # code review capability
├── api_design/
│   └── SKILL.md          # API design review
├── data_analysis/
│   └── SKILL.md          # data analysis
└── README.md
```

### SKILL.md Template

```markdown
---
name: my_custom_skill
description: Short description
version: 1.0.0
tags: [tag1, tag2]
---

# Skill Full Name

Detailed description...

## Input

Explain what parameters are accepted

## Processing Flow

Specific steps...

## Output Specification

Output format description
```

### Upload to GitHub

```bash
git init
git add .
git commit -m "Initial commit: my-skills-hub"
git remote add origin https://github.com/yourname/my-skills-hub
git push -u origin main
```

### Import Your Own Skill

```bash
python3 scripts/skill_manager.py add-remote \
  --agent zhongshu \
  --name my_skill \
  --source https://raw.githubusercontent.com/yourname/my-skills-hub/main/my_skill/SKILL.md \
  --description "My custom skill"
```

---

## Complete API Reference

### POST /api/add-remote-skill

Add a remote skill.

**Request:**
```bash
curl -X POST http://localhost:7891/api/add-remote-skill \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "zhongshu",
    "skillName": "code_review",
    "sourceUrl": "https://raw.githubusercontent.com/...",
    "description": "Code review"
  }'
```

**Response (200):**
```json
{
  "ok": true,
  "message": "Skill code_review added to zhongshu from remote source",
  "skillName": "code_review",
  "agentId": "zhongshu",
  "source": "https://raw.githubusercontent.com/...",
  "localPath": "/Users/xxx/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md",
  "size": 2048,
  "addedAt": "2026-03-02T14:30:00Z"
}
```

### GET /api/remote-skills-list

List all remote skills.

```bash
curl http://localhost:7891/api/remote-skills-list
```

**Response:**
```json
{
  "ok": true,
  "remoteSkills": [
    {
      "skillName": "code_review",
      "agentId": "zhongshu",
      "sourceUrl": "https://raw.githubusercontent.com/...",
      "description": "Code review capability",
      "localPath": "/Users/xxx/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md",
      "addedAt": "2026-03-02T14:30:00Z",
      "lastUpdated": "2026-03-02T14:30:00Z",
      "status": "valid"
    }
  ],
  "count": 1,
  "listedAt": "2026-03-02T14:35:00Z"
}
```

### POST /api/update-remote-skill

Update a remote skill to the latest version.

```bash
curl -X POST http://localhost:7891/api/update-remote-skill \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "zhongshu",
    "skillName": "code_review"
  }'
```

### DELETE /api/remove-remote-skill

Remove a remote skill.

```bash
curl -X POST http://localhost:7891/api/remove-remote-skill \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "zhongshu",
    "skillName": "code_review"
  }'
```

---

## Troubleshooting

### Q: Download failed with "Connection timeout"

**A:** Check network connectivity and URL validity

```bash
curl -I https://raw.githubusercontent.com/...
# Should return HTTP/1.1 200 OK
```

### Q: File format invalid

**A:** Make sure SKILL.md starts with YAML frontmatter

```markdown
---
name: skill_name
description: Description
---

# Body starts here...
```

### Q: Can't see Skill after import

**A:** Refresh the kanban or check if the Agent is configured correctly

```bash
# Check if Agent exists
python3 scripts/skill_manager.py list-remote

# Check local files
ls -la ~/.openclaw/workspace-zhongshu/skills/
```

---

## More Information

- 📚 [Complete Guide](remote-skills-guide.md)
- 🏛️ [Architecture Document](task-dispatch-architecture.md)
- 🤝 [Contributing](../CONTRIBUTING.md)
