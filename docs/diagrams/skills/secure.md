# Secure — Comprehensive Security Audit

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:secure] --> B[Spawn security-auditor agent]

    B --> C[Dependency audit lane]
    B --> D[Secrets scan lane]
    B --> E[OWASP Top 10 lane]

    C --> F{"requirements.txt or\npyproject.toml exists?"}
    F -->|Yes| G["Run pip audit\nExtract: vuln count by severity,\naffected packages, fix versions, CVEs"]
    F -->|No| H[Skip, note in report]

    D --> I["Search for leaked credentials:\n- API keys (AKIA, sk-, pk_live_, ghp_, xoxb-)\n- Hardcoded passwords/secrets\n- Private keys (BEGIN PRIVATE KEY)\n- Connection strings with credentials\n- .env files committed to git\n- JWT/bearer tokens in source\n- Check .gitignore for exclusions"]

    E --> J["Check patterns against:\nA01 Broken Access Control\nA02 Cryptographic Failures\nA03 Injection\nA04 Insecure Design\nA05 Security Misconfiguration\nA06 Vulnerable Components\nA07 Auth Failures\nA08 Data Integrity Failures\nA09 Logging Failures\nA10 SSRF"]

    G --> K[Collect all findings]
    H --> K
    I --> K
    J --> K

    K --> L["Produce security report:\n- Dependency vulnerabilities table\n- Secrets detected table\n- OWASP findings table\n- Summary by severity"]

    L --> M["Auto-create board tasks:\n- Individual tasks for CRITICAL/HIGH\n- Grouped task for MEDIUM\n- LOW noted in report only"]

    M --> N{Spoke available?}
    N -->|Yes| O[mpga spoke announcement]
    N -->|No| P[Done]
    O --> P
```

## Inputs
- Entire codebase (read-only scan)
- requirements.txt or pyproject.toml (for dependency audit)
- Git tracked files (for secrets scan)
- Source code patterns (for OWASP analysis)

## Outputs
- Security audit report with three sections: Dependencies, Secrets, OWASP Top 10
- Each finding has file:line, severity, evidence
- Secret values never displayed (only type and location)
- Board tasks auto-created for CRITICAL/HIGH findings
- .gitignore recommendations for detected secret files
- No files modified (read-only skill)
