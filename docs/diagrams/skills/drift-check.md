# Drift-Check — Evidence Drift Detection and Healing

## Workflow

```mermaid
flowchart TD
    A[Drift check triggered] --> B{Trigger source?}
    B -->|PostToolUse hook\nafter Write/Edit| C[Quick mode:\nauditor drift-quick\nfor affected scope]
    B -->|On demand| D[Full mode:\nauditor drift\nacross all scopes]
    B -->|CI pipeline| E[CI gate mode:\nauditor drift-ci\nwith threshold enforcement]

    C --> F[Invoke auditor agent\nin drift mode]
    D --> F
    E --> F

    F --> G[Detect all drift findings]
    G --> H[Classify each finding by severity]

    H --> I["CRITICAL:\nBroken evidence links\nto deleted files/functions\n(blocks shipping)"]
    H --> J["HIGH:\nEvidence links to\nrenamed/moved symbols\n(needs healing)"]
    H --> K["MEDIUM:\nStale evidence >30 days\nfile significantly changed\n(should verify)"]
    H --> L["LOW:\nCosmetic drift\nwhitespace/formatting\n(auto-healable)"]

    L --> M[Auto-heal LOW findings]
    I --> N[Report with recommended actions]
    J --> N
    K --> N
    M --> N

    N --> O["Output:\n- Findings per severity tier\n- Auto-healed count\n- Manual review needed\n- Overall health percentage"]

    O --> P{Spoke available?}
    P -->|Yes| Q[mpga spoke announcement]
    P -->|No| R[Done]
    Q --> R

    style I fill:#ff6b6b,color:#fff
    style J fill:#ffa500,color:#fff
    style K fill:#ffd700,color:#000
    style L fill:#90ee90,color:#000
```

## Inputs
- Trigger source: PostToolUse hook, manual invocation, or CI pipeline
- Affected scope (for quick mode)
- Threshold value (for CI gate mode)

## Outputs
- Number of findings per severity tier (CRITICAL/HIGH/MEDIUM/LOW)
- Auto-healed LOW (cosmetic) findings
- Links needing manual review (HIGH/CRITICAL)
- Overall evidence health percentage
- Minimal output in hook mode (only warns if drift detected)
