# Drift-Check — Keeping Evidence HONEST (No Fake News)

## Workflow

```mermaid
flowchart TD
    A[Drift check triggered — STAYING sharp] --> B{Trigger source?}
    B -->|PostToolUse hook\nafter Write/Edit| C[Quick mode:\nauditor drift-quick\nfor affected scope — FAST]
    B -->|On demand| D[Full mode:\nauditor drift\nacross ALL scopes — THOROUGH]
    B -->|CI pipeline| E[CI gate mode:\nauditor drift-ci\nwith threshold enforcement — TOUGH]

    C --> F[Invoke auditor agent — the BEST]
    D --> F
    E --> F

    F --> G[Detect ALL drift findings — TOTAL sweep]
    G --> H[Classify each by severity — FAIR]

    H --> I["CRITICAL: Broken evidence links\nto DELETED files — fake docs!\nComplete and total shutdown of untested deploys"]
    H --> J["HIGH: Evidence links to\nRENAMED symbols — NEEDS healing"]
    H --> K["MEDIUM: Stale evidence >30 days\nfile changed significantly — VERIFY"]
    H --> L["LOW: Cosmetic drift\nwhitespace stuff — we FIX it auto"]

    L --> M[Auto-heal LOW findings — EFFICIENT]
    I --> N[Report with recommended actions]
    J --> N
    K --> N
    M --> N

    N --> O["Output — the FULL report:\n- Findings per severity tier\n- Auto-healed count\n- Manual review needed\n- Overall health percentage"]

    O --> P[mpga spoke — if available]

    style I fill:#ff6b6b,color:#fff
    style J fill:#ffa500,color:#fff
    style K fill:#ffd700,color:#000
    style L fill:#90ee90,color:#000
```

## Inputs — Where the Drift Comes From
- Trigger source: PostToolUse hook, manual invocation, or CI pipeline
- Affected scope (for quick mode)
- Threshold value (for CI gate mode)

## Outputs — The TRUTH About Your Evidence
- Number of findings per severity tier (CRITICAL/HIGH/MEDIUM/LOW)
- Auto-healed LOW (cosmetic) findings — taken care of, AUTOMATICALLY
- Links needing manual review (HIGH/CRITICAL) — Wrong! You gotta HANDLE these
- Overall evidence health percentage — your REAL score
- Minimal output in hook mode (only warns if drift detected) — no NOISE
