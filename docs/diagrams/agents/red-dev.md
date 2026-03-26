# Red Dev — Test Writer

## Workflow

```mermaid
flowchart TD
    A[Receive task from board] --> B[Read scope docs for the feature area]
    B --> C[Read task acceptance criteria]
    C --> D[Build coverage checklist: map criteria to test cases]
    D --> E[Start with most DEGENERATE test case: null, zero, empty]
    E --> F[Write ONE failing test describing expected behavior]
    F --> G[Run test quality self-check]
    G --> H{Name describes behavior?}
    H --> I{Follows Arrange-Act-Assert?}
    I --> J{One behavior per test?}
    J --> K{Fails for the RIGHT reason?}
    K --> L[Run test suite]
    L --> M{New test FAILS?}
    M -->|No - passes without new code| N[Delete test or make it more specific]
    N --> F
    M -->|Yes - red state| O[Cite scope evidence links in test comment]
    O --> P[Hand off to green-dev to implement]
    P --> Q[Green-dev returns with tests passing]
    Q --> R{All acceptance criteria covered?}
    R -->|No| S[Write next test - slightly more complex, follow TPP ladder]
    S --> F
    R -->|Yes| T["Commit: test: description"]
    T --> U["Update board: mpga board update task-id --tdd-stage red"]
    U --> V[Hand off to green-dev with coverage summary]
    V --> W[mpga spoke announcement]
```

## Inputs
- Scope document for the feature area
- Task description from the board (task card file)

## Outputs
- Test file(s) written and committed
- Task TDD stage updated to red
- Coverage checklist: X of Y acceptance criteria covered, edge cases identified
