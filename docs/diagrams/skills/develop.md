# Develop — TDD Cycle Orchestration (Red-Green-Blue)

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:develop] --> B[Start live board server\nmpga board live --serve --open]
    B --> C[Claim task from todo column\nmpga board claim task-id]
    C --> D[Load context: task card + scope docs]
    D --> E{Another writer in same scope?}
    E -->|Yes| F[Pick a different ready task]
    F --> C
    E -->|No| G["RED: Spawn red-dev agent\nWrite ONE failing test\n(degenerate case first)"]

    G --> H["GREEN: Spawn green-dev agent\nMake that ONE test pass\nwith minimal code"]
    H --> I{All acceptance criteria covered?}
    I -->|No| J[red-dev writes NEXT test\nslightly more complex]
    J --> K[green-dev makes it pass]
    K --> I

    I -->|Yes| L["BLUE: Spawn blue-dev agent\nRefactor production + test code\n(assertions unchanged)"]
    L --> M{Tests still passing?}
    M -->|No| L
    M -->|Yes| N[Spawn reviewer agent\nTwo-stage review]
    N --> O{CRITICAL issues?}
    O -->|Yes| P[Loop back to appropriate phase]
    P --> G
    O -->|No| Q[Record evidence\nmpga board update --evidence-add]
    Q --> R[Move task to done\nmpga board move id done]
    R --> S[Run drift check\nmpga drift --quick]
    S --> T{Context budget > 70%?}
    T -->|Yes| U[Consider /mpga:handoff]
    T -->|No| V{Spoke available?}
    V -->|Yes| W[mpga spoke announcement]
    V -->|No| X[Done - pick next task]
    W --> X

    subgraph "Background helpers (read-only)"
        Y[scout agent]
        Z[auditor agent]
    end
```

## Inputs
- Task ID (or picks next todo task)
- Task card with acceptance criteria
- Relevant scope documents
- Phase number (optional, to run all tasks in a phase)

## Outputs
- Failing tests written (red phase)
- Minimal implementation passing all tests (green phase)
- Refactored clean code (blue phase)
- Reviewer approval
- Evidence links recorded on task card
- Task moved to done column
- Drift check run after completion
