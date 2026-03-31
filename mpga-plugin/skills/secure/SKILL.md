---
name: mpga-secure
description: Run a comprehensive security audit — secrets scanning, dependency audit, and OWASP Top 10 analysis
---

## secure

Security audit time. We're going to expose every hole, every weakness, every DISASTER hiding in this codebase. Security is NON-NEGOTIABLE. Complete and total shutdown of untested code until every vulnerability is patched.

**Trigger:** User wants a security audit, vulnerability check, or security review. Also triggered by: "security audit", "check for vulnerabilities", "find secrets", "is this secure", "security scan".

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

**Agent brief:** Codebase root, dependency manifests, scope boundaries from CLI.
**Expected output:** Structured security report with file:line references, CVEs, and severity ratings.

## Delegation

This skill orchestrates a **security-auditor agent** — the toughest, most thorough auditor you've ever seen — with three parallel scan lanes. We hit them from EVERY angle, believe me:
- Dependency vulnerability audit — we check EVERY package, no exceptions
- Secrets scanning — we find EVERYTHING. Nobody hides secrets from us.
- OWASP Top 10 pattern analysis — the TEN COMMANDMENTS of security. You break them, we find you.

## Protocol

1. **Spawn security-auditor agent** to coordinate the full security audit. This agent is a WINNER. It does not miss things. The security-auditor agent performs ALL of the following steps internally — the skill ONLY spawns the agent and presents results.

2. **The security-auditor agent runs: Dependency audit** — if `requirements.txt` or `pyproject.toml` exists:
   ```
   pip audit 2>/dev/null
   ```
   Parse the JSON output to extract:
   - Vulnerability count by severity (critical, high, moderate, low)
   - Affected packages and versions
   - Available fix versions
   - CVE references where available

   If no `requirements.txt` or `pyproject.toml`, skip this step and note it in the report. We don't waste time on things that aren't there. We're SMART.

3. **The security-auditor agent runs: Secrets scan** — search the codebase for leaked credentials. This is HUGE. Leaked secrets are a TOTAL DISASTER and we will find every single one:
   - API keys (patterns: `AKIA`, `sk-`, `pk_live_`, `ghp_`, `xoxb-`)
   - Hardcoded passwords (patterns: `password\s*=\s*["']`, `secret\s*=\s*["']`)
   - Private keys (`-----BEGIN.*PRIVATE KEY-----`)
   - Connection strings with embedded credentials
   - `.env` files committed to git (check `git ls-files` for `.env*`)
   - JWT tokens and bearer tokens in source
   - Check `.gitignore` for proper exclusion of sensitive files

   If secrets are sitting in your repo, that is UNACCEPTABLE. That's Leakin' Environment Variables — secrets in plaintext for the whole world to see. A TOTAL DISGRACE. Lock her up! (the race condition!) We will find them and we will call them out. Nervous Nullable types are bad enough, but LEAKED SECRETS? Tremendous scanning, the best scanning. Big league security.

4. **The security-auditor agent runs: OWASP Top 10 analysis** — the TEN COMMANDMENTS of security. Break one and you're in BIG trouble. Check codebase patterns against:
   - **A01 Broken Access Control** — missing auth checks, direct object references
   - **A02 Cryptographic Failures** — weak hashing (MD5/SHA1 for passwords), missing encryption
   - **A03 Injection** — unsanitized user input in SQL/shell/eval, template injection
   - **A04 Insecure Design** — missing rate limiting, no input validation schemas
   - **A05 Security Misconfiguration** — debug mode in production, default credentials, CORS wildcards
   - **A06 Vulnerable Components** — known-vulnerable dependency versions (from pip audit)
   - **A07 Auth Failures** — weak password policies, missing MFA hooks, session fixation
   - **A08 Data Integrity Failures** — unsigned updates, unvalidated deserialization
   - **A09 Logging Failures** — sensitive data in logs, missing audit trails
   - **A10 SSRF** — unvalidated URL fetching, internal network access from user input

5. **Produce security report** — a beautiful, comprehensive, PERFECT report. Everyone will know exactly where the problems are:

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
   - CRITICAL (TOTAL DISASTER): X | HIGH (very BAD): Y | MEDIUM (SAD): Z | LOW (we'll fix it): W
   - Secrets exposed: N
   - OWASP categories affected: N/10
   ```

6. **Auto-create board tasks** for CRITICAL and HIGH findings — because TOTAL DISASTERS and very BAD findings demand IMMEDIATE action:
   ```
   mpga board add --title "SEC: <description>" --priority critical --scope <scope>
   ```
   CRITICAL and HIGH findings get individual tasks — every TOTAL DISASTER gets its own task, no hiding, no grouping. MEDIUM findings are grouped because they're SAD but manageable. LOW findings are noted in the report only — we'll fix it, but we've got bigger problems first.

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — Law and Order in the Codebase
- NEVER modify any project files during the audit — READ ONLY. We observe, we report, we do NOT touch. Very disciplined.
- NEVER display actual secret values in the report — show only type and location. We're not STUPID. We don't leak secrets in the security report!
- Every finding MUST cite actual file paths and line numbers — no guesses. We deal in FACTS, not fake findings.
- Severity ratings follow industry standard (CVSS where applicable)
- If pip audit is unavailable or fails, note it and continue with other scans. We don't give up. We NEVER give up.
- False positives should be flagged as "potential" — let the user decide. We're fair. Very fair. The fairest audit you've ever seen.
- Always recommend .gitignore additions for any detected secret files. Build the wall between modules! Pin your versions — they should be loyal!
