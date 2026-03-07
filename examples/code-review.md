# Case 2: Code Security Review

> **Edict**: Review a piece of FastAPI code for security issues and output a problem list with fix suggestions

---

## 📜 Edict (Original Instruction)

```
Review the security of the following FastAPI code, focusing on:
1. Authentication and authorization vulnerabilities
2. SQL injection risks
3. Input validation
4. Sensitive information leakage
Provide a prioritized issue list (sorted by severity) and fix code.

[Attachment: app/main.py, app/models.py, app/auth.py — 320 lines total]
```

**Edict ID**: `JJC-20260221-007`
**Issued At**: 2026-02-21 14:30:00

---

## 📋 Zhongshu Planning

> Planning completed within 30 seconds of receiving edict

**Plan:**

| # | Sub-task | Assigned Department | Notes |
|---|--------|----------|------|
| 1 | Code security scan | ⚔️ Bingbu | Review each file, flag security issues |
| 2 | Compliance & best practices check | ⚖️ Xingbu | Check compliance against OWASP Top 10 |
| 3 | Fix output | ⚔️ Bingbu | Provide fix code for each issue |

**Estimated time**: 12 minutes
**Estimated tokens**: ~9,000

---

## 🔍 Menxia Review

> ⏱️ Review took 18 seconds

### Approved ✅ (Passed on first round)

**Menxia comments:** *"Plan is reasonable. Bingbu handles the engineering-side review, Xingbu handles compliance-side review, with clear division of responsibilities. Note that Xingbu must provide an OWASP line-by-line comparison table — not just 'generally compliant'. Approved."*

---

## ⚔️ Execution Results per Department

### Bingbu · Code Security Scan (took 5 minutes)

**Scan found 6 issues:**

| # | Severity | File | Issue |
|---|--------|------|------|
| 1 | 🔴 Critical | auth.py:23 | JWT secret hardcoded in source code |
| 2 | 🔴 Critical | main.py:45 | SQL query uses f-string concatenation, injection risk |
| 3 | 🟠 High | main.py:67 | User input has no length limit, could cause DoS |
| 4 | 🟠 High | auth.py:41 | Token expiry set to 30 days, too long |
| 5 | 🟡 Medium | main.py:12 | CORS set to `allow_origins=["*"]` |
| 6 | �� Medium | models.py:8 | Password field not excluded from response_model |

### Xingbu · OWASP Compliance Check (took 4 minutes)

**OWASP Top 10 line-by-line comparison:**

| OWASP ID | Category | Status | Notes |
|-----------|------|------|------|
| A01 | Broken Access Control | 🟠 Partial | Has JWT but lacks role-level validation |
| A02 | Cryptographic Failures | 🔴 Non-compliant | Secret hardcoded |
| A03 | Injection | 🔴 Non-compliant | SQL concatenation |
| A04 | Insecure Design | ✅ Compliant | Overall architecture reasonable |
| A05 | Security Misconfiguration | 🟡 Needs improvement | CORS too permissive |
| A06 | Vulnerable Components | ✅ Compliant | Dependencies up to date |
| A07 | Auth Failures | 🟠 Partial | Token expiry too long |
| A08 | Data Integrity | ✅ Compliant | — |
| A09 | Logging Failures | 🟡 Needs improvement | Missing security event logging |
| A10 | SSRF | ✅ Compliant | No external requests |

**Xingbu conclusion:** 6/10 items need attention; 2 are non-compliant (A02, A03) and must be fixed immediately.

### Bingbu · Fix Code (took 3 minutes)

```python
# Fix #1: auth.py — read JWT secret from environment variable
import os
JWT_SECRET = os.environ["JWT_SECRET"]  # no longer hardcoded

# Fix #2: main.py — use parameterized query
from sqlalchemy import text
result = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})

# Fix #3: main.py — add input length limits
from pydantic import Field
class UserInput(BaseModel):
    name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)

# Fix #4: auth.py — shorten token expiry
ACCESS_TOKEN_EXPIRE = timedelta(hours=1)  # changed from 30 days to 1 hour

# Fix #5: main.py — tighten CORS
app.add_middleware(CORSMiddleware, allow_origins=["https://yourdomain.com"])

# Fix #6: models.py — exclude password field
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    # password field not in this model
```

---

## 📮 Final Memorial (Shangshu Summary)

**Memorial ID**: `JJC-20260221-007`
**Total time**: 14 minutes (planning 1 + review 0.5 + execution 12.5)
**Total tokens**: 8,200

### Executive Summary

Completed security review of 320 lines of FastAPI code. Found 6 security issues (2 critical / 2 high / 2 medium); 2 items non-compliant in OWASP Top 10. Fix code provided for all 6 issues.

Menxia approved on first round; Bingbu and Xingbu had clear division of responsibilities: Bingbu handled code-level scanning and fixes, Xingbu handled compliance framework comparison.

### Recommended Priority

1. **Fix immediately**: JWT secret hardcoding + SQL injection (must resolve before going live)
2. **Within this week**: Input length limits + token expiry time
3. **Next iteration**: Tighten CORS + password field exposure

---

*This case is compiled from real run records; code content has been anonymized.*
