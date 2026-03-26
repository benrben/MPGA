# Review-PR — Multi-Agent PR Review

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:review-pr] --> B{PR source?}
    B -->|PR number given| C["gh pr diff number"]
    B -->|Branch specified| D["git diff base...feature"]
    B -->|No args| E["git diff main...HEAD"]

    C --> F[Read full file context\nfor all changed files]
    D --> F
    E --> F

    F --> G[Spawn reviewer agent\nread-only / parallel]
    F --> H[Spawn bug-hunter agent\nread-only / parallel]
    F --> I[Spawn security-auditor agent\nread-only / parallel]

    G --> J["Code Quality:\n- Style consistency\n- Architecture alignment\n- Naming + API design\n- Test coverage\n- Documentation\n- Commit hygiene\n- DRY violations"]

    H --> K["Correctness:\n- Logic errors\n- Edge cases (null, empty, boundary)\n- Error handling gaps\n- Race conditions\n- Type safety issues\n- Regression risks\n- Off-by-one errors"]

    I --> L["Security:\n- Injection vulnerabilities\n- Secrets in diff\n- Auth/authz weakening\n- Vulnerable new deps\n- CORS/CSP misconfig\n- Unsanitized user input"]

    J --> M[Collect all findings into\nunified PR review]
    K --> M
    L --> M

    M --> N{Determine verdict}
    N -->|No CRITICAL/HIGH| O["APPROVED\nShip it!"]
    N -->|HIGH findings| P["CHANGES REQUESTED\nFix before merge"]
    N -->|CRITICAL findings| Q["BLOCKED\nSecurity/data loss risk"]

    O --> R[Generate review comments\nwith file:line references\n+ positive feedback]
    P --> R
    Q --> R

    R --> S{Spoke available?}
    S -->|Yes| T[mpga spoke announcement]
    S -->|No| U[Done]
    T --> U
```

## Inputs
- PR number, branch name, or defaults to current branch vs main
- Full diff and surrounding file context
- Project conventions and patterns

## Outputs
- Unified PR review report with verdict (APPROVED / CHANGES REQUESTED / BLOCKED)
- Findings table by category: Code Quality, Correctness, Security
- Each finding has file:line, severity, and description
- Inline-style review comments with suggested fixes
- Positive acknowledgment of good patterns
- No files modified (read-only skill)
