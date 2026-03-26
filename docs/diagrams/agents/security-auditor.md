# Security Auditor — OWASP, npm audit, Secrets Scan

## Workflow

```mermaid
flowchart TD
    A[Receive source files/directories to audit] --> B[Read scope docs for data flow and external interfaces]
    B --> C["1. OWASP Top 10 Check"]
    C --> D["A01: Broken Access Control - missing auth, IDOR, CORS misconfig"]
    C --> E["A02: Cryptographic Failures - weak hashing, hardcoded keys, missing encryption"]
    C --> F["A03: Injection - SQL, NoSQL, command, LDAP, template injection"]
    C --> G["A04: Insecure Design - missing rate limiting, business logic flaws"]
    C --> H["A05: Security Misconfiguration - debug mode, default creds, verbose errors"]
    C --> I["A06: Vulnerable Components (covered by npm audit)"]
    C --> J["A07: Auth Failures - session mgmt, weak passwords, JWT issues"]
    C --> K["A08: Integrity Failures - insecure deserialization, missing integrity checks"]
    C --> L["A09: Logging Failures - missing auth logging, sensitive data in logs"]
    C --> M["A10: SSRF - user-supplied URLs fetched server-side"]
    D & E & F & G & H & I & J & K & L & M --> N["2. Dependency Vulnerability Check"]
    N --> O{package.json exists?}
    O -->|Yes| P[Run npm audit --json, classify by severity]
    O -->|No| Q[Note as GAP in report]
    P --> R["3. Secrets Scan"]
    Q --> R
    R --> S[Scan for API keys, passwords, tokens, connection strings, private keys]
    S --> T{Matches found?}
    T -->|Yes| U{Env var reference or test fixture?}
    U -->|Yes| V[Exclude - not a real secret]
    U -->|No| W[Flag as finding with severity]
    T -->|No| X["4. Security Headers Check"]
    V --> X
    W --> X
    X --> Y[Check CSP, HSTS, X-Content-Type-Options, X-Frame-Options, CSRF, input validation]
    Y --> Z[Classify all findings: CRITICAL / HIGH / MEDIUM / LOW]
    Z --> AA[Provide remediation steps for every finding]
    AA --> AB[Produce security audit report covering all 10 OWASP categories]
    AB --> AC[mpga spoke announcement]
```

## Inputs
- Source files or directories to audit
- Scope documents for context on data flow and external interfaces
- (Optional) specific focus: owasp, deps, secrets, headers, or all

## Outputs
- OWASP Top 10 coverage table (PASS/FAIL/WARN per category)
- Findings by severity with evidence links and remediation steps
- Dependency audit summary (packages, vulnerabilities, action items)
- Secrets scan results
- Overall security posture assessment
