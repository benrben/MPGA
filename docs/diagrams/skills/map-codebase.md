# Map-Codebase — The GREATEST Codebase Survey Ever Done

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:map — TREMENDOUS move] --> B{Mode?}

    B -->|Quick mode\ndefault| C{MPGA initialized?}
    C -->|No| D[mpga init --from-existing — START winning]
    C -->|Yes| E[Run full sync — FAST\nmpga sync --full]
    D --> E
    E --> F[Verify evidence health\nmpga evidence verify — TRUST but verify]
    F --> G[Run drift check — ALWAYS\nmpga drift --report]
    G --> H[Show health report — THE NUMBERS\nmpga health]
    H --> I["Quick output — BEAUTIFUL:\n- Files scanned + scopes generated\n- Evidence health percentage\n- Drift detected\n- Recommended next steps"]

    B -->|Deep mode\n--deep flag| J{First map?}
    J -->|Yes| K[mpga sync --full\ngenerate scope scaffolds — BIGLY]
    J -->|No| L[mpga sync --incremental\nonly changed parts — EFFICIENT]
    K --> M[List generated scope docs\nls MPGA/scopes/*.md]
    L --> M
    M --> N["Spawn one scout per scope\nin PARALLEL — maximum SPEED"]
    N --> O["Each scout — BEST investigators:\n- Reads source files\n- Fills TODO sections\n- Adds evidence-backed descriptions"]
    O --> P[Wait for all scouts — TEAMWORK]
    P --> Q["Spawn auditor in background\non changed scopes"]
    P --> R["Spawn architect to review:\n- Fix cross-scope issues\n- Verify references\n- Update GRAPH.md\n- Find circular deps + orphans\n- Fill remaining TODOs"]
    Q --> S[Run verification — FULL sweep\nevidence verify + drift check + health]
    R --> S
    S --> T["Deep output — INCREDIBLE detail:\n- Scopes generated + enriched\n- Sections filled vs remaining\n- Evidence coverage\n- Known unknowns\n- Suggested next steps"]

    I --> U{Spoke available?}
    T --> U
    U -->|Yes| V[mpga spoke — MAP complete]
    U -->|No| W[Done — you now KNOW your codebase]
    V --> W
```

## Inputs — What Goes In
- Mode flag: default (quick) or --deep — your CHOICE
- Existing MPGA/ knowledge layer (if initialized)
- Codebase source files — the RAW material

## Outputs — Total KNOWLEDGE
- Complete MPGA/ knowledge layer with filled scope documents — COMPREHENSIVE
- INDEX.md, GRAPH.md, and scope files regenerated/enriched — FRESH
- Evidence coverage report — we MEASURE everything
- List of unknowns needing human review — TRANSPARENT
- Health report with drift status — the REAL numbers
