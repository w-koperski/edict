# Remote Skills Resource Management Guide

## Overview

Three Departments & Six Ministries now supports connecting and supplementing skills resources from the internet without manually copying files. Supports fetching from the following sources:

- **GitHub repositories** (raw.githubusercontent.com)
- **Any HTTPS URL** (must return a valid skill file)
- **Local file paths**
- **Built-in repository** (official skills library)

---

## Feature Architecture

### 1. API Endpoints

#### `POST /api/add-remote-skill`

Add a skill for a specified Agent from a remote URL or local path.

**Request body:**
```json
{
  "agentId": "zhongshu",
  "skillName": "code_review",
  "sourceUrl": "https://raw.githubusercontent.com/org/skills-repo/main/code_review/SKILL.md",
  "description": "Code review skill"
}
```

**Parameter description:**
- `agentId` (string, required): Target Agent ID (validated)
- `skillName` (string, required): Internal name of the skill (only letters/numbers/underscores/CJK characters allowed)
- `sourceUrl` (string, required): Remote URL or local file path
  - GitHub: `https://raw.githubusercontent.com/user/repo/branch/path/SKILL.md`
  - Any HTTPS: `https://example.com/skills/my_skill.md`
  - Local: `file:///Users/bingsen/skills/code_review.md` or `/Users/bingsen/skills/code_review.md`
- `description` (string, optional): Description of the skill

**Success response (200):**
```json
{
  "ok": true,
  "message": "Skill code_review added to zhongshu",
  "skillName": "code_review",
  "agentId": "zhongshu",
  "source": "https://raw.githubusercontent.com/...",
  "localPath": "/Users/bingsen/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md",
  "size": 2048,
  "addedAt": "2026-03-02T14:30:00Z"
}
```

**Error response (400):**
```json
{
  "ok": false,
  "error": "URL invalid or inaccessible",
  "details": "Connection timeout after 10s"
}
```

#### `GET /api/remote-skills-list`

List all added remote skills and their source information.

**Response:**
```json
{
  "ok": true,
  "remoteSkills": [
    {
      "skillName": "code_review",
      "agentId": "zhongshu",
      "sourceUrl": "https://raw.githubusercontent.com/org/skills-repo/main/code_review/SKILL.md",
      "description": "Code review skill",
      "localPath": "/Users/bingsen/.openclaw/workspace-zhongshu/skills/code_review/SKILL.md",
      "lastUpdated": "2026-03-02T14:30:00Z",
      "status": "valid"  // valid | invalid | not-found
    }
  ],
  "count": 5
}
```

#### `POST /api/update-remote-skill`

Update an already-added remote skill to the latest version.

**Request body:**
```json
{
  "agentId": "zhongshu",
  "skillName": "code_review"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Skill updated",
  "skillName": "code_review",
  "newVersion": "2.1.0",
  "updatedAt": "2026-03-02T15:00:00Z"
}
```

#### `DELETE /api/remove-remote-skill`

Remove an already-added remote skill.

**Request body:**
```json
{
  "agentId": "zhongshu",
  "skillName": "code_review"
}
```

---

## CLI Commands

### Add Remote Skill

```bash
python3 scripts/skill_manager.py add-remote \
  --agent zhongshu \
  --name code_review \
  --source https://raw.githubusercontent.com/org/skills-repo/main/code_review/SKILL.md \
  --description "Code review skill"
```

### List Remote Skills

```bash
python3 scripts/skill_manager.py list-remote
```

### Update Remote Skill

```bash
python3 scripts/skill_manager.py update-remote \
  --agent zhongshu \
  --name code_review
```

### Remove Remote Skill

```bash
python3 scripts/skill_manager.py remove-remote \
  --agent zhongshu \
  --name code_review
```

---

## Official Skills Library

### OpenClaw Skills Hub

> **Official skills library**: https://github.com/openclaw-ai/skills-hub

Available skills:

| Skill Name | Description | Compatible Agents | Source URL |
|-----------|------|----------|--------|
| `code_review` | Code review (supports Python/JS/Go) | Bingbu/Xingbu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/code_review/SKILL.md |
| `api_design` | API design review | Bingbu/Gongbu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/api_design/SKILL.md |
| `security_audit` | Security audit | Xingbu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/security_audit/SKILL.md |
| `data_analysis` | Data analysis | Hubu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/data_analysis/SKILL.md |
| `doc_generation` | Documentation generation | Libu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/doc_generation/SKILL.md |
| `test_framework` | Test framework design | Gongbu/Xingbu | https://raw.githubusercontent.com/openclaw-ai/skills-hub/main/test_framework/SKILL.md |

**One-click import official skills**

```bash
python3 scripts/skill_manager.py import-official-hub \
  --agents zhongshu,menxia,shangshu,bingbu,xingbu,libu
```

---

## Kanban UI Operations

### Quick Add Skill

1. Open kanban → 🔧 **Skills Config** panel
2. Click **➕ Add Remote Skill** button
3. Fill in the form:
   - **Agent**: Select target Agent
   - **Skill Name**: Enter the skill's internal ID
   - **Remote URL**: Paste GitHub/HTTPS URL
   - **Description**: Optional, briefly describe the skill's function
4. Click **Confirm** button

### Manage Added Skills

1. Kanban → 🔧 **Skills Config** → **Remote Skills** tab
2. View all added skills and their source URLs
3. Actions:
   - **View**: Show SKILL.md content
   - **Update**: Re-download latest version from source URL
   - **Delete**: Remove local copy (does not affect source)
   - **Copy Source URL**: Quickly share with others

---

## Skill File Specification

Remote skills must follow standard Markdown format:

### Minimum Required Structure

```markdown
---
name: skill_internal_name
description: Short description
version: 1.0.0
tags: [tag1, tag2]
---

# Skill Name

Detailed description...

## Input

Explain what parameters are accepted

## Processing Flow

Specific steps...

## Output Specification

Output format description
```

### Complete Example

```markdown
---
name: code_review
description: Structural review and optimization suggestions for Python/JavaScript code
version: 2.1.0
author: openclaw-ai
tags: [code-quality, security, performance]
compatibleAgents: [bingbu, xingbu, menxia]
---

# Code Review Skill

This skill is specifically for multi-dimensional review of production code...

## Input

- `code`: Source code to review
- `language`: Programming language (python, javascript, go, rust)
- `focusAreas`: Review focus areas (security, performance, style, structure)

## Processing Flow

1. Language identification and syntax validation
2. Security vulnerability scanning
3. Performance bottleneck identification
4. Code style check
5. Best practice recommendations

## Output Specification

```json
{
  "issues": [
    {
      "type": "security|performance|style|structure",
      "severity": "critical|high|medium|low",
      "location": "line:column",
      "message": "Issue description",
      "suggestion": "Fix suggestion"
    }
  ],
  "summary": {
    "totalIssues": 3,
    "criticalCount": 1,
    "highCount": 2
  }
}
```

## Applicable Scenarios

- Code output review for Bingbu (code implementation)
- Security check for Xingbu (compliance audit)
- Quality assessment for Menxia (review gatekeeping)

## Dependencies & Limitations

- Requires Python 3.9+
- Supported file size: up to 50KB
- Execution timeout: 30 seconds
```

---

## Data Storage

### Local Storage Structure

```
~/.openclaw/
├── workspace-zhongshu/
│   └── skills/
│       ├── code_review/
│       │   ├── SKILL.md
│       │   └── .source.json    # stores source URL and metadata
│       └── api_design/
│           ├── SKILL.md
│           └── .source.json
├── ...
```

### .source.json Format

```json
{
  "skillName": "code_review",
  "sourceUrl": "https://raw.githubusercontent.com/...",
  "description": "Code review skill",
  "version": "2.1.0",
  "addedAt": "2026-03-02T14:30:00Z",
  "lastUpdated": "2026-03-02T14:30:00Z",
  "lastUpdateCheck": "2026-03-02T15:00:00Z",
  "checksum": "sha256:abc123...",
  "status": "valid"
}
```

---

## Security Considerations

### URL Validation

✅ **Allowed URL types:**
- HTTPS URLs: `https://`
- Local files: `file://` or absolute paths
- Relative paths: `./skills/`

❌ **Blocked URL types:**
- HTTP (non-HTTPS): `http://` is rejected
- Local HTTP: `http://localhost/` (prevents loopback attacks)
- FTP/SSH: `ftp://`, `ssh://`

### Content Validation

1. **Format validation**: Ensure valid Markdown with YAML frontmatter
2. **Size limit**: Maximum 10 MB
3. **Timeout protection**: Download auto-aborted after 30 seconds
4. **Path traversal protection**: Check parsed skill name, block `../` patterns
5. **Checksum validation**: Optional GPG signature verification (official library only)

### Sandboxed Execution

- Remote skills execute in a sandbox (provided by OpenClaw runtime)
- Cannot access sensitive files like `~/.openclaw/config.json`
- Can only access assigned workspace directory

---

## Troubleshooting

### Common Issues

**Q: Download failed with "Connection timeout"**

A: Check network connectivity and URL validity:
```bash
curl -I https://raw.githubusercontent.com/...
```

**Q: Skill shows "invalid" status**

A: Check file format:
```bash
python3 -m json.tool ~/.openclaw/workspace-zhongshu/skills/xxx/SKILL.md
```

**Q: Can I import from a private GitHub repository?**

A: Not supported (security consideration). Alternatives:
1. Make the repository public
2. Download locally and add directly
3. Use a public GitHub Gist link

**Q: How do I create my own skills library?**

A: Follow the structure of [OpenClaw Skills Hub](https://github.com/openclaw-ai/skills-hub) to create your own repository, then:

```bash
git clone https://github.com/yourname/my-skills-hub.git
cd my-skills-hub
# create skill file structure
# commit & push to GitHub
```

Then add via URL or the official library import feature.

---

## Best Practices

### 1. Version Management

Always include a version number in the SKILL.md frontmatter:
```yaml
---
version: 2.1.0
---
```

### 2. Backward Compatibility

When updating a skill, maintain input/output format compatibility to avoid breaking existing workflows.

### 3. Complete Documentation

Include detailed:
- Feature description
- Applicable scenarios
- Dependency notes
- Output examples

### 4. Regular Updates

Set up periodic update checks (interval configurable in the kanban):
```bash
python3 scripts/skill_manager.py check-updates --interval weekly
```

### 5. Contribute to the Community

Mature skills can be contributed to [OpenClaw Skills Hub](https://github.com/openclaw-ai/skills-hub).

---

## Complete API Reference

See Part 3 (API & Tools) of the [Task Dispatch Architecture Document](task-dispatch-architecture.md).

---

<p align="center">
  <sub>Empower <strong>institutional</strong> AI collaboration with an <strong>open</strong> ecosystem</sub>
</p>
