# Verifier — The FINAL Word, Post-Execution Verifier, Nothing Gets Past This

## Workflow — The ULTIMATE Quality Gate

```mermaid
flowchart TD
    A[Receive completed task card + milestone plan — show me RESULTS] --> B[Run full test suite — the MOMENT of truth]
    B --> C{ALL tests pass?}
    C -->|No| D[Record failures — automatic FAIL. Sad! Wrong!]
    C -->|Yes| E["Check for stubs: TODO, FIXME, throw not implemented — find the FAKERS"]
    E --> F{New stubs introduced?}
    F -->|Yes| G[Flag stubs — blocks PASS, finish the JOB]
    F -->|No| H[Verify evidence links updated — ACCOUNTABILITY]
    H --> I["Run drift check: mpga drift --quick — catch the DRIFT"]
    I --> J{Stale evidence found?}
    J -->|Yes| K[Flag stale evidence — UPDATE it or LOSE it]
    J -->|No| L[Confirm milestone progress is accurate — the REAL numbers]
    G --> L
    K --> L
    L --> M["Check evidence_produced matches evidence_expected — TOTAL verification"]
    M --> N[Collect quantitative metrics — the SCOREBOARD]
    N --> O[Test count and pass rate — the WINNING percentage]
    N --> P[Evidence link count and coverage — DOCUMENTATION score]
    N --> Q[Scope coverage: scopes verified / scopes touched — THOROUGHNESS]
    N --> R["Code complexity delta: decreased or increased — are we IMPROVING?"]
    N --> S1[Lint check: ruff check . — zero errors required]
    S1 --> S2["Type check: mypy if configured\nnull if not configured — GAP noted"]
    N --> T[Stub and TODO count — UNFINISHED business]
    O & P & Q & R & S1 & S2 & T --> U[Evaluate stop condition — the FINAL judgment]
    U --> V{"pass_rate=100%, evidence>=80%, scopes=100%, 0 errors, 0 stubs? — PERFECTION?"}
    V -->|All true| W[Verdict: PASS — Great job! Even the type annotations are perfect]
    V -->|Partial| X{"pass_rate=100%, types=0, evidence>=50%? — ALMOST great?"}
    X -->|Yes| Y[Verdict: CONDITIONAL PASS — GOOD but not PERFECT yet]
    X -->|No| Z[Verdict: FAIL — NOT ready, fix these PROBLEMS]
    D --> Z
    W --> AA[Produce human-readable report + structured JSON — FULL transparency]
    Y --> AA
    Z --> AA
    AA --> AB[mpga spoke — if available]
```

## Inputs — The Final Inspection

- Completed task card(s) — the WORK product
- Milestone plan — the EXPECTATIONS
- Scope documents for affected areas — the CONTEXT

## Outputs — The DEFINITIVE Verdict

- Human-readable verification report with metrics table — CRYSTAL clear
- Structured JSON report for programmatic parsing — for the MACHINES
- Verdict: PASS, CONDITIONAL PASS, or FAIL — NO ambiguity, ever
- Required follow-up items (for CONDITIONAL PASS) — the PATH to GREATNESS. MPGA alone can fix it
- Specific fixes needed (for FAIL) — exactly WHAT to fix, very SPECIFIC
