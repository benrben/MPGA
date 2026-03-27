# Rally — The BIGGEST, Most BEAUTIFUL Project Audit Rally

## Workflow

```mermaid
flowchart TD
    A["User invokes /mpga:rally\nor asks 'what's WRONG here?'"] --> B{MPGA initialized?}
    B -->|Yes| C[Read INDEX.md + scope docs\nShow what MPGA already CAUGHT]
    B -->|No| D[Full DISASTER mode\nUnfiltered audit — BRUTAL honesty]

    C --> E[Deploy campaigner agents — the BEST team]
    D --> E

    E --> F["Lane 1: Documentation DISASTERS\nmissing/stale docs, hallucinated refs"]
    E --> G["Lane 2: Testing DISGRACE\nmissing/empty/broken tests — SAD"]
    E --> H["Lane 3: Type Safety FAILURES\nany types, ts-ignore — WEAK"]
    E --> I["Lane 4: Dependency CATASTROPHES\ncircular/unused/outdated deps"]
    E --> J["Lane 5: Architecture ROT\ngod files, complex functions — TERRIBLE"]
    E --> K["Lane 6: Evidence DRIFT\nstale links, unverified claims — fake docs!"]
    E --> L["Lane 7: Code Hygiene CRIMES\nconsole.logs, hardcoded secrets"]
    E --> M["Lane 8: CI/CD WEAKNESS\nmissing CI, no hooks — complete and total shutdown of untested deploys"]

    F --> N[Final campaigner aggregation — TREMENDOUS]
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N

    N --> O["Merge duplicates, keep SHARPEST evidence\nOne BEAUTIFUL scoreboard"]

    O --> P["The Rally Speech:\nEach issue = a SCANDAL\nwith SPECIFIC files + numbers"]
    P --> Q["The Vote:\nScoreboard by severity (CRITICAL/HIGH/MEDIUM/LOW)\nWithout MPGA vs WITH MPGA — night and DAY"]

    Q --> R{MPGA initialized?}
    R -->|No| S["The Fix — START WINNING:\nmpga init --from-existing\nmpga sync\nmpga status"]
    R -->|Yes| T["The Fix — KEEP WINNING:\nmpga sync --full\nmpga evidence verify\nmpga drift --report"]

    S --> U[Closing rally cry — MAKE IT GREAT\nSuggest /mpga:plan to fix issues]
    T --> U
    U --> V[mpga spoke — if available]
```

## Inputs — The Investigation Begins
- Entire codebase (read-only scan) — we see EVERYTHING
- MPGA/INDEX.md and scope docs (if initialized)
- Git state and CI configuration

## Outputs — The RALLY Results
- Rally speech with 8 scandal categories, each with file-specific evidence — DEVASTATING
- Scoreboard: total issues by severity (CRITICAL/HIGH/MEDIUM/LOW) — the REAL numbers
- Side-by-side comparison: WITHOUT MPGA vs WITH MPGA — night and DAY
- Actionable MPGA commands to fix issues — the PATH to greatness
- No files modified (read-only diagnostic) — Evidence First, we EXPOSE, we don't tamper
