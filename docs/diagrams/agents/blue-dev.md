# Blue Dev — Refactorer

## Workflow

```mermaid
flowchart TD
    A[Receive passing tests from green-dev] --> B[Run all tests - confirm GREEN]
    B --> C{All tests green?}
    C -->|No| STOP[STOP - do not proceed]
    C -->|Yes| D[Measure baseline metrics: function length, complexity, nesting, params, file length, duplicates]
    D --> E[Identify refactoring opportunities using Decision Matrix]
    E --> F[Select Fowler refactoring pattern: Extract Function, Inline Function, Move Function, etc.]
    F --> G[Apply ONE refactoring]
    G --> H[Run tests]
    H --> I{Tests still green?}
    I -->|No| J[Immediately revert change]
    J --> E
    I -->|Yes| K[Re-measure metrics]
    K --> L{At least one metric improved, none regressed?}
    L -->|No| M[Consider reverting - refactoring not worth it]
    L -->|Yes| N{More refactoring opportunities?}
    M --> N
    N -->|Yes| F
    N -->|No| O[Update scope evidence links if function locations changed]
    O --> P["Commit: refactor: description"]
    P --> Q["Update board: mpga board update task-id --tdd-stage blue"]
    Q --> R[Hand off to reviewer]
    R --> S[mpga spoke announcement]
```

## Inputs
- Passing tests from the TDD cycle
- Implementation from green-dev
- Scope document (to update evidence links if code moves)

## Outputs
- Metrics snapshot: before and after values for every function touched
- Refactored code committed (tests still green)
- Scope evidence links updated for any moved code
- Task TDD stage updated to blue
