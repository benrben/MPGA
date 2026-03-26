# Bug Hunter — Specification-Based Bug Detection

## Workflow

```mermaid
flowchart TD
    A[Receive task with acceptance criteria] --> B[Read the spec FIRST: task acceptance criteria + scope docs]
    B --> C[Read the implementation code]
    C --> D[Trace logic for each acceptance criterion]
    D --> E{Criterion fully implemented?}
    E -->|Yes| F[Mark as implemented]
    E -->|Partial| G[Flag as partial implementation]
    E -->|No code path found| H[Flag as GAP - missing implementation]
    F --> I[Hunt edge cases]
    G --> I
    H --> I
    I --> J[Check null/undefined inputs]
    J --> K[Check empty collections]
    K --> L[Check boundary values / off-by-one]
    L --> M[Check concurrent access / race conditions]
    M --> N[Check error paths: network, file not found, timeout]
    N --> O[Check type coercion traps]
    O --> P[Identify specification gaps: undocumented behavior, silent fallbacks, swallowed errors]
    P --> Q[Classify each finding]
    Q --> R{"BUG: spec AND contradicting code cited?"}
    R -->|Yes| S["Label as BUG - confirmed spec deviation"]
    R -->|No| T{"Code looks wrong but can't confirm against spec?"}
    T -->|Yes| U["Label as RISK - needs investigation"]
    T -->|No| V["Label as GAP - missing specification"]
    S --> W[Build spec coverage matrix]
    U --> W
    V --> W
    W --> X[Produce structured bug hunt report with file:line evidence]
    X --> Y[mpga spoke announcement]
```

## Inputs
- Task acceptance criteria (from board task card or milestone plan)
- Scope documents for the relevant modules
- Implementation code under investigation
- Test files (to check what is and is not covered)

## Outputs
- Spec coverage matrix (each criterion: implemented? tested? evidence?)
- Classified findings: BUGs, RISKs, GAPs with file:line evidence
- Verdict: PASS or FAIL based on whether BUGs exist
