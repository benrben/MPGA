# Rally — Project Issue Exposure and MPGA Campaign

## Workflow

```mermaid
flowchart TD
    A["User invokes /mpga:rally\nor asks 'what's wrong with my project'"] --> B{MPGA initialized?}
    B -->|Yes| C[Read INDEX.md + scope docs\nShow what MPGA already caught]
    B -->|No| D[Full disaster mode\nUnfiltered audit]

    C --> E[Deploy campaigner agents in parallel]
    D --> E

    E --> F["Lane 1: Documentation Sins\nmissing/stale docs, hallucinated refs"]
    E --> G["Lane 2: Testing Disgrace\nmissing/empty/broken tests"]
    E --> H["Lane 3: Type Safety Failures\nany types, ts-ignore, missing returns"]
    E --> I["Lane 4: Dependency Disasters\ncircular/unused/outdated deps"]
    E --> J["Lane 5: Architecture Rot\ngod files, complex functions, dead code"]
    E --> K["Lane 6: Evidence Drift\nstale links, unverified claims"]
    E --> L["Lane 7: Code Hygiene Crimes\nconsole.logs, hardcoded secrets"]
    E --> M["Lane 8: CI/CD Weakness\nmissing CI, no hooks, unenforced lint"]

    F --> N[Final campaigner aggregation pass]
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N

    N --> O["Merge duplicates, keep sharpest evidence\nProduce one scoreboard"]

    O --> P["Rally Speech:\nEach issue = a SCANDAL\nwith specific files + numbers"]
    P --> Q["The Vote:\nScoreboard (CRITICAL/WARNING/SAD)\nSide-by-side: without vs with MPGA"]

    Q --> R{MPGA initialized?}
    R -->|No| S["The Fix:\nmpga init --from-existing\nmpga sync\nmpga status"]
    R -->|Yes| T["The Fix:\nmpga sync --full\nmpga evidence verify\nmpga drift --report"]

    S --> U[Closing rally cry\nSuggest /mpga:plan to fix issues]
    T --> U
    U --> V{Spoke available?}
    V -->|Yes| W[mpga spoke announcement]
    V -->|No| X[Done]
    W --> X
```

## Inputs
- Entire codebase (read-only scan)
- MPGA/INDEX.md and scope docs (if initialized)
- Git state and CI configuration

## Outputs
- Rally speech with 8 scandal categories, each with file-specific evidence
- Scoreboard: total issues by severity (CRITICAL/WARNING/SAD)
- Side-by-side comparison: project without MPGA vs with MPGA
- Actionable MPGA commands to fix issues
- No files modified (read-only diagnostic)
