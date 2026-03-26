# Secure — The STRONGEST Security Audit, Believe Me

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:secure — VERY smart] --> B[Spawn security-auditor — ELITE agent]

    B --> C[Dependency audit lane — CHECK everything]
    B --> D[Secrets scan lane — FIND the leaks]
    B --> E[OWASP Top 10 lane — the BIG threats]

    C --> F{"requirements.txt or\npyproject.toml exists?"}
    F -->|Yes| G["Run pip audit — FULL sweep:\nVuln count by severity,\naffected packages, fix versions, CVEs"]
    F -->|No| H[Skip, note in report — TRANSPARENT]

    D --> I["Hunt for leaked credentials — RELENTLESS:\n- API keys (AKIA, sk-, pk_live_, ghp_, xoxb-)\n- Hardcoded passwords — TERRIBLE\n- Private keys (BEGIN PRIVATE KEY)\n- Connection strings with creds\n- .env files in git — DISASTER\n- JWT/bearer tokens in source\n- Check .gitignore for exclusions"]

    E --> J["Check OWASP Top 10 — COMPREHENSIVE:\nA01 Broken Access Control\nA02 Cryptographic Failures\nA03 Injection\nA04 Insecure Design\nA05 Security Misconfiguration\nA06 Vulnerable Components\nA07 Auth Failures\nA08 Data Integrity Failures\nA09 Logging Failures\nA10 SSRF"]

    G --> K[Collect ALL findings — TOTAL sweep]
    H --> K
    I --> K
    J --> K

    K --> L["Produce TREMENDOUS security report:\n- Dependency vulnerabilities table\n- Secrets detected table\n- OWASP findings table\n- Summary by severity"]

    L --> M["Auto-create board tasks:\n- Individual tasks for CRITICAL/HIGH\n- Grouped task for MEDIUM\n- LOW noted in report only — EFFICIENT"]

    M --> N{Spoke available?}
    N -->|Yes| O[mpga spoke — SECURITY report delivered]
    N -->|No| P[Done — your project is NOW safer]
    O --> P
```

## Inputs — What We Scan
- Entire codebase (read-only scan) — EVERY file
- requirements.txt or pyproject.toml (for dependency audit)
- Git tracked files (for secrets scan) — NOWHERE to hide
- Source code patterns (for OWASP analysis)

## Outputs — FORT KNOX Level Report
- Security audit report with three sections: Dependencies, Secrets, OWASP Top 10 — COMPLETE
- Each finding has file:line, severity, evidence — HARD proof
- Secret values NEVER displayed (only type and location) — we're RESPONSIBLE
- Board tasks auto-created for CRITICAL/HIGH findings — IMMEDIATE action
- .gitignore recommendations for detected secret files — LOCK it down
- No files modified (read-only skill) — we PROTECT, we don't break
