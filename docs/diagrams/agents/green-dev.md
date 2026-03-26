# Green Dev — Implementer

## Workflow

```mermaid
flowchart TD
    A[Receive failing tests from red-dev] --> B[Read the failing tests carefully]
    B --> C[Read scope docs for required behavior]
    C --> D[Identify simplest TPP transformation to pass the test]
    D --> E[Write minimal implementation using that transformation]
    E --> F[Run test suite]
    F --> G{Target test passes?}
    G -->|No| H{Stuck for 3+ minutes?}
    H -->|No| I[Fix implementation]
    I --> F
    H -->|Yes| J["RETREAT-TO-GREEN: Comment out failing test"]
    J --> K[Confirm all other tests GREEN]
    K --> L[Signal orchestrator - request blue-dev structural refactor]
    L --> M[Wait for blue-dev to return]
    M --> N[Uncomment test and implement normally]
    N --> F
    G -->|Yes| O[Log TPP transformation used]
    O --> P{More tests from red-dev?}
    P -->|Yes| Q[Hand back to red-dev for next test]
    Q --> A
    P -->|No - all acceptance criteria covered| R["Commit: feat: description"]
    R --> S["Update board: mpga board update task-id --tdd-stage green"]
    S --> T["Hand off to blue-dev: Tests passing, please refactor"]
    T --> U[mpga spoke announcement]
```

## Inputs
- Failing test file(s) from red-dev
- Scope document for the feature area
- Task card with acceptance criteria

## Outputs
- Implementation code committed
- All tests passing
- Task TDD stage updated to green
- TPP transformation log for this cycle
