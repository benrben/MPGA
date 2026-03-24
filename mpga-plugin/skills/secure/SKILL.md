---
name: mpga-secure
description: Run a comprehensive security audit — secrets scanning, dependency audit, and OWASP Top 10 analysis
---

## secure

**Trigger:** User wants a security audit, vulnerability check, or security review. Also triggered by: "security audit", "check for vulnerabilities", "find secrets", "is this secure", "security scan".

## Delegation

This skill orchestrates a **security-auditor agent** with three parallel scan lanes:
- Dependency vulnerability audit
- Secrets/credential scanning
- OWASP Top 10 pattern analysis

## Protocol

1. **Spawn security-auditor agent** to coordinate the full security audit:

2. **Dependency audit** — if `package.json` exists:
   ```
   npm audit --json 2>/dev/null
   ```
   Parse the JSON output to extract:
   - Vulnerability count by severity (critical, high, moderate, low)
   - Affected packages and versions
   - Available fix versions
   - CVE references where available

   If no `package.json`, skip this step and note it in the report.

3. **Secrets scan** — search the codebase for leaked credentials:
   - API keys (patterns: `AKIA`, `sk-`, `pk_live_`, `ghp_`, `xoxb-`)
   - Hardcoded passwords (patterns: `password\s*=\s*["']`, `secret\s*=\s*["']`)
   - Private keys (`-----BEGIN.*PRIVATE KEY-----`)
   - Connection strings with embedded credentials
   - `.env` files committed to git (check `git ls-files` for `.env*`)
   - JWT tokens and bearer tokens in source
   - Check `.gitignore` for proper exclusion of sensitive files

4. **OWASP Top 10 analysis** — check codebase patterns against:
   - **A01 Broken Access Control** — missing auth checks, direct object references
   - **A02 Cryptographic Failures** — weak hashing (MD5/SHA1 for passwords), missing encryption
   - **A03 Injection** — unsanitized user input in SQL/shell/eval, template injection
   - **A04 Insecure Design** — missing rate limiting, no input validation schemas
   - **A05 Security Misconfiguration** — debug mode in production, default credentials, CORS wildcards
   - **A06 Vulnerable Components** — known-vulnerable dependency versions (from npm audit)
   - **A07 Auth Failures** — weak password policies, missing MFA hooks, session fixation
   - **A08 Data Integrity Failures** — unsigned updates, unvalidated deserialization
   - **A09 Logging Failures** — sensitive data in logs, missing audit trails
   - **A10 SSRF** — unvalidated URL fetching, internal network access from user input

5. **Produce security report**:

   ```
   # SECURITY AUDIT REPORT

   ## Dependency Vulnerabilities
   | Package | Severity | CVE | Fix Available |
   |---------|----------|-----|---------------|
   | ...     | CRITICAL | ... | Yes (v X.Y.Z) |

   ## Secrets Detected
   | # | File:Line | Type | Status |
   |---|-----------|------|--------|
   | 1 | ...       | API Key | EXPOSED |

   ## OWASP Top 10 Findings
   | # | Category | File:Line | Risk | Description |
   |---|----------|-----------|------|-------------|
   | 1 | A03      | ...       | HIGH | ...         |

   ## Summary
   - CRITICAL: X | HIGH: Y | MEDIUM: Z | LOW: W
   - Secrets exposed: N
   - OWASP categories affected: N/10
   ```

6. **Auto-create board tasks** for CRITICAL and HIGH findings:
   ```
   node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js board add --title "SEC: <description>" --priority critical --scope <scope>
   ```
   CRITICAL and HIGH findings get individual tasks. MEDIUM findings are grouped. LOW findings are noted in the report only.

## Strict Rules
- NEVER modify any project files during the audit — READ ONLY
- NEVER display actual secret values in the report — show only type and location
- Every finding MUST cite actual file paths and line numbers — no guesses
- Severity ratings follow industry standard (CVSS where applicable)
- If npm audit is unavailable or fails, note it and continue with other scans
- False positives should be flagged as "potential" — let the user decide
- Always recommend .gitignore additions for any detected secret files
