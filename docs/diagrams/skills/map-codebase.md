# Map-Codebase — Unified Codebase Mapping and Sync

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:map] --> B{Mode?}

    B -->|Quick mode\ndefault| C{MPGA initialized?}
    C -->|No| D[mpga init --from-existing]
    C -->|Yes| E[Run full sync\nmpga sync --full]
    D --> E
    E --> F[Verify evidence health\nmpga evidence verify]
    F --> G[Run drift check\nmpga drift --report]
    G --> H[Show health report\nmpga health]
    H --> I["Quick output:\n- Files scanned + scopes generated\n- Evidence health percentage\n- Drift detected\n- Recommended next steps"]

    B -->|Deep mode\n--deep flag| J{First map?}
    J -->|Yes| K[mpga sync --full\ngenerate scope scaffolds]
    J -->|No| L[mpga sync --incremental\nonly changed parts]
    K --> M[List generated scope docs\nls MPGA/scopes/*.md]
    L --> M
    M --> N["Spawn one scout agent per\nnew/changed scope in PARALLEL\n(each scout owns one scope doc)"]
    N --> O["Each scout:\n- Reads source files\n- Fills TODO sections\n- Adds evidence-backed descriptions"]
    O --> P[Wait for all scouts to complete]
    P --> Q["Spawn auditor (background)\non changed scopes"]
    P --> R["Spawn architect to review:\n- Fix cross-scope inconsistencies\n- Verify cross-scope references\n- Update GRAPH.md\n- Identify circular deps + orphans\n- Fill remaining TODOs"]
    Q --> S[Run verification steps\nevidence verify + drift check + health]
    R --> S
    S --> T["Deep output:\n- Scopes generated + enriched\n- Sections filled vs remaining TODOs\n- Evidence coverage\n- Known unknowns\n- Suggested next steps"]

    I --> U{Spoke available?}
    T --> U
    U -->|Yes| V[mpga spoke announcement]
    U -->|No| W[Done]
    V --> W
```

## Inputs
- Mode flag: default (quick) or --deep
- Existing MPGA/ knowledge layer (if initialized)
- Codebase source files

## Outputs
- Complete MPGA/ knowledge layer with filled scope documents
- INDEX.md, GRAPH.md, and scope files regenerated/enriched
- Evidence coverage report
- List of unknowns needing human review
- Health report with drift status
