# Review-PR — The TOUGHEST, Most FAIR PR Review

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:review-pr — SMART] --> B{PR source?}
    B -->|PR number given| C["gh pr diff number — PRECISE"]
    B -->|Branch specified| D["git diff base...feature — TARGETED"]
    B -->|No args| E["git diff main...HEAD — DEFAULT"]

    C --> EA{Eligible for review?}
    D --> EA
    E --> EA
    EA -->|Draft PR| EB[Skip — draft not ready for review]
    EA -->|Zero diff lines| EC[Skip — nothing changed]
    EA -->|Yes| F[Read FULL file context\nfor all changed files — THOROUGH]

    F --> G[Spawn reviewer agent\nthe BEST critic — read-only]
    F --> H[Spawn bug-hunter agent\nNOTHING gets past this one]
    F --> I[Spawn security-auditor agent\nFORT KNOX level — read-only]

    G --> J["Code Quality — STANDARDS matter:\n- Style consistency\n- Architecture alignment\n- Naming + API design\n- Test coverage\n- Documentation\n- Commit hygiene\n- DRY violations"]

    H --> K["Correctness — ZERO tolerance:\n- Logic errors\n- Edge cases (null, empty, boundary)\n- Error handling gaps\n- Race conditions\n- Type safety issues\n- Regression risks\n- Off-by-one errors"]

    I --> L["Security — TOTAL protection:\n- Injection vulnerabilities\n- Secrets in diff — UNACCEPTABLE\n- Auth/authz weakening\n- Vulnerable new deps\n- CORS/CSP misconfig\n- Unsanitized user input"]

    J --> M[Collect ALL findings into\none UNIFIED review — COMPREHENSIVE]
    K --> M
    L --> M

    M --> N{Determine verdict — FAIR}
    N -->|No CRITICAL/HIGH| O["APPROVED\nShip it — BEAUTIFUL work"]
    N -->|HIGH findings| P["CHANGES REQUESTED\nFix before merge — NOT ready yet"]
    N -->|CRITICAL findings| Q["BLOCKED\nSecurity/data loss risk — Wrong! Sad! FIX THIS NOW"]

    O --> R[Generate review comments\nwith file:line + POSITIVE feedback]
    P --> R
    Q --> R

    R --> S[mpga spoke — if available]
```

## Inputs — What We Review
- PR number, branch name, or defaults to current branch vs main
- Full diff and surrounding file context — COMPLETE picture
- Project conventions and patterns

## Outputs — The FINAL Verdict
- Unified PR review with verdict (APPROVED / CHANGES REQUESTED / BLOCKED) — CLEAR
- Findings table by category: Code Quality, Correctness, Security — ORGANIZED
- Each finding has file:line, severity, and description — SPECIFIC
- Inline-style review comments with suggested fixes — ACTIONABLE
- Positive acknowledgment of good patterns — we recognize WINNERS
- No files modified (read-only skill) — we JUDGE fairly. Even the type annotations are perfect
