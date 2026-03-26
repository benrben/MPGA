# Reviewer — Code Reviewer

## Workflow

```mermaid
flowchart TD
    A[Receive code changes + scope docs + task criteria] --> B[Review the DIFF first, not whole repo]
    B --> C["Stage 1: Spec Compliance"]
    C --> D{Implementation matches acceptance criteria?}
    D --> E{Tests written BEFORE implementation? Check commit history}
    E --> F{Tests start with degenerate cases?}
    F --> G{Evidence links still valid after changes?}
    G --> H{Scope docs updated if evidence locations changed?}
    H --> I{"Task card has evidence_produced populated?"}
    I --> J["Stage 2: Code Quality"]
    J --> K["2a: Clean Code - naming, function size, error handling, typing, testability"]
    J --> L["2b: Performance - re-renders, memoization, O(n^2), unbounded queries, sync blocking"]
    J --> M["2c: Security - XSS, SQL injection, command injection, path traversal, SSRF, hardcoded creds, CSRF"]
    J --> N["2d: Test Smells - duplicated setup, brittle assertions, missing edge cases, over-mocking"]
    J --> O["2e: Code Smells - long methods, large classes, feature envy, data clumps, dead code"]
    J --> P["2f: Architecture - circular deps, layer violations, missing abstractions, god objects"]
    K & L & M & N & O & P --> Q[Tag every finding with severity: CRITICAL / HIGH / MEDIUM / LOW]
    Q --> R{Any CRITICAL findings?}
    R -->|Yes| S[Verdict: FAIL]
    R -->|No| T{Any HIGH findings?}
    T -->|Yes| U[Verdict: CONDITIONAL PASS]
    T -->|No| V[Verdict: PASS]
    S --> W[List required fixes before done]
    U --> W
    V --> X[List recommended and consider items]
    W --> Y[mpga spoke announcement]
    X --> Y
```

## Inputs
- Code changes (diff or files modified)
- Relevant scope documents
- Milestone plan with task acceptance criteria
- TDD trace from task card

## Outputs
- Two-stage review report: spec compliance + code quality
- Findings grouped by category with severity ratings
- Verdict: PASS, CONDITIONAL PASS, or FAIL
- Required fixes (CRITICAL + HIGH), recommended (MEDIUM), consider (LOW)
