# Verifier — Post-Execution Verifier

## Workflow

```mermaid
flowchart TD
    A[Receive completed task card + milestone plan] --> B[Run full test suite]
    B --> C{ALL tests pass?}
    C -->|No| D[Record failures - automatic FAIL]
    C -->|Yes| E["Check for stubs: TODO, FIXME, throw not implemented"]
    E --> F{New stubs introduced?}
    F -->|Yes| G[Flag stubs - blocks PASS]
    F -->|No| H[Verify evidence links updated for new/modified code]
    H --> I["Run drift check: mpga drift --quick"]
    I --> J{Stale evidence found?}
    J -->|Yes| K[Flag stale evidence]
    J -->|No| L[Confirm milestone progress is accurate]
    G --> L
    K --> L
    L --> M["Check evidence_produced matches evidence_expected"]
    M --> N[Collect quantitative metrics]
    N --> O[Test count and pass rate]
    N --> P[Evidence link count and coverage]
    N --> Q[Scope coverage: scopes verified / scopes touched]
    N --> R["Code complexity delta: decreased / unchanged / increased"]
    N --> S[Lint and type-check status]
    N --> T[Stub and TODO count]
    O & P & Q & R & S & T --> U[Evaluate stop condition]
    U --> V{"pass_rate=100%, evidence>=80%, scopes=100%, 0 type/lint errors, 0 stubs, drift clean?"}
    V -->|All true| W[Verdict: PASS - move task to done]
    V -->|Partial| X{"pass_rate=100%, types=0, evidence>=50%, no critical/high issues?"}
    X -->|Yes| Y[Verdict: CONDITIONAL PASS - list follow-up items]
    X -->|No| Z[Verdict: FAIL - list every failing criterion]
    D --> Z
    W --> AA[Produce human-readable report + structured JSON report]
    Y --> AA
    Z --> AA
    AA --> AB[mpga spoke announcement]
```

## Inputs
- Completed task card(s)
- Milestone plan
- Scope documents for affected areas

## Outputs
- Human-readable verification report with metrics table
- Structured JSON report (verification-report) for programmatic parsing
- Verdict: PASS, CONDITIONAL PASS, or FAIL with explicit threshold evaluation
- Required follow-up items (for CONDITIONAL PASS)
- Specific fixes needed (for FAIL)
