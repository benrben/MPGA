# Auditor — Evidence Verifier & Drift Detective

## Workflow

```mermaid
flowchart TD
    A[Receive scope documents to audit] --> B{Which mode?}
    B -->|Full audit| C[For each evidence link in each scope]
    B -->|drift-quick| D[Run mpga drift --quick]
    B -->|drift-ci| E[Run mpga drift --ci --threshold 80]
    C --> F{File:line exists?}
    F -->|No| G["Classify as CRITICAL"]
    F -->|Yes| H{Content matches description?}
    H -->|Symbol moved| I["Classify as HIGH, report new location"]
    H -->|File changed significantly, evidence >30 days old| J["Classify as MEDIUM"]
    H -->|Only whitespace/formatting changed| K["Classify as LOW"]
    H -->|Valid| L["Mark as VALID"]
    G --> M[Calculate evidence coverage ratio per scope]
    I --> M
    J --> M
    K --> M
    L --> M
    M --> N[Produce health report with severity breakdown]
    D --> O[Classify findings by severity tier]
    O --> P{Handle by tier}
    P -->|LOW| Q[Auto-heal with mpga evidence heal --auto]
    P -->|MEDIUM| R[Flag for manual verification]
    P -->|HIGH| S[Flag for healing, recommend heal command]
    P -->|CRITICAL| T[Flag as blocking - must resolve before shipping]
    Q --> U[Report healed vs needs manual review]
    R --> U
    S --> U
    T --> U
    U --> V[Update scope doc status fields]
    E --> W{Below threshold or CRITICAL found?}
    W -->|Yes| X[Exit non-zero - CI gate fails]
    W -->|No| Y[Exit zero - CI gate passes]
    N --> Z[mpga spoke announcement]
    V --> Z
    X --> Z
    Y --> Z
```

## Inputs
- Scope documents to audit
- (Optional) specific scope name
- (Optional) mode: audit (default), drift, drift-quick, drift-ci

## Outputs
- Health report per scope with evidence coverage percentage
- Severity-classified findings (CRITICAL, HIGH, MEDIUM, LOW)
- Auto-healed LOW findings
- CI pass/fail gate status (in drift-ci mode)
