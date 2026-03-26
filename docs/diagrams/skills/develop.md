# Develop — The GREATEST TDD Cycle (Red-Green-Blue)

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:develop — SMART] --> B[Fire up the live board\nmpga board live --serve --open]
    B --> C[Claim a task — first come first WIN\nmpga board claim task-id]
    C --> D[Load context: task card + scope docs]
    D --> E{Another writer in same scope?}
    E -->|Yes| F[Pick a different task — NO conflicts]
    F --> C
    E -->|No| G["RED: Spawn red-dev agent\nWrite ONE failing test\ndegenerate case FIRST — discipline"]

    G --> H["GREEN: Spawn green-dev agent\nMake that test pass\nMINIMAL code — no bloat"]
    H --> I{All acceptance criteria covered?}
    I -->|No| J[red-dev writes the NEXT test\nslightly tougher — WINNING]
    J --> K[green-dev makes it pass — EASY]
    K --> I

    I -->|Yes| L["BLUE: Spawn blue-dev agent\nRefactor — make it BEAUTIFUL\nassertions UNCHANGED"]
    L --> M{Tests still passing?}
    M -->|No| L
    M -->|Yes| N[Spawn reviewer agent\nTwo-stage review — RIGOROUS]
    N --> O{CRITICAL issues?}
    O -->|Yes| P[Loop back — we FIX things here]
    P --> G
    O -->|No| Q[Record evidence — TOTAL proof\nmpga board update --evidence-add]
    Q --> R[Move task to done — WINNER\nmpga board move id done]
    R --> S[Run drift check — ALWAYS\nmpga drift --quick]
    S --> T{Context budget > 70%?}
    T -->|Yes| U[Consider /mpga:handoff — be SMART]
    T -->|No| V{Spoke available?}
    V -->|Yes| W[mpga spoke — VICTORY lap]
    V -->|No| X[Done — pick next task, KEEP WINNING]
    W --> X

    subgraph "Background helpers — the BEST support"
        Y[scout agent]
        Z[auditor agent]
    end
```

## Inputs — What the CHAMPION Needs
- Task ID (or picks next todo task — we're always MOVING)
- Task card with acceptance criteria
- Relevant scope documents
- Phase number (optional, to run all tasks in a phase)

## Outputs — TREMENDOUS Results
- Failing tests written (red phase) — we PROVE it first
- Minimal implementation passing all tests (green phase) — EFFICIENT
- Refactored clean code (blue phase) — BEAUTIFUL
- Reviewer approval — QUALITY control
- Evidence links recorded on task card — TOTAL accountability
- Task moved to done column — another WIN
- Drift check run after completion — we NEVER let things slide
