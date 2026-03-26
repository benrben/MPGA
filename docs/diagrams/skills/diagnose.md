# Diagnose — Finding Bugs Like NOBODY Else Can

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:diagnose — WISE move] --> B{Target specified?}
    B -->|User specifies files| C[Use specified files — PRECISION]
    B -->|Git diff has changes| D[Use changed files — SMART]
    B -->|No target| E[Use current scope or\nmost recent changes]

    C --> F[Lock onto target files]
    D --> F
    E --> F

    F --> G[Spawn bug-hunter agent\nthe BEST detective — read-only]
    F --> H[Spawn optimizer agent\nread-only — PARALLEL for speed]

    G --> I["Bug-hunter EXPOSES:\n- Spec vs implementation gaps\n- Edge cases NOBODY else catches\n- Error handling disasters\n- Logic errors / off-by-one\n- Type safety violations\n- Async/race conditions"]

    H --> J["Optimizer REVEALS:\n- Cyclomatic complexity — SAD\n- Duplicated code — WASTEFUL\n- Dead code — pathetic\n- Performance anti-patterns\n- Memory leak patterns\n- Dependency coupling"]

    I --> K[Collect results — COMPREHENSIVE]
    J --> K

    K --> L["Produce TREMENDOUS diagnosis report:\n- Bugs table with severity + evidence\n- Quality issues table\n- Priority-ranked fix list\n- Summary with counts + effort"]

    L --> M{User wants board tasks?}
    M -->|Yes| N[Create tasks for CRITICAL/HIGH\nfindings — FIX THEM]
    N --> O[Group LOW/MEDIUM into\none cleanup task — EFFICIENT]
    M -->|No| P{Spoke available?}
    O --> P
    P -->|Yes| Q[mpga spoke — DIAGNOSIS delivered]
    P -->|No| R[Done — NOW you know]
    Q --> R
```

## Inputs — Point Us at the Problem
- Target files/directories (optional)
- Git diff changes (fallback)
- Current scope (fallback)

## Outputs — The FULL Picture
- Unified diagnosis report — bugs AND quality issues, NOTHING hidden
- Each finding has severity, file:line, evidence citation — REAL proof
- Priority-ranked fix list with effort estimates — we're PRACTICAL
- Optional board tasks for CRITICAL/HIGH findings — take ACTION
- No files modified (read-only skill) — we diagnose, we don't break things
