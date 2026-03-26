# Ship — Pre-Ship Checks, PR Generation, and Deployment

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:ship] --> B["Phase 1: Parallel Pre-Ship Checks\n(Ship Gate)"]

    B --> C[Tests pass\npytest]
    B --> D[Ruff check passes\nruff check src/]
    B --> E[Lint clean\nruff check .]
    B --> F[Evidence drift check\nmpga drift --quick]
    B --> G["No uncommitted scope changes\ngit diff -- MPGA/scopes/"]

    C --> H{All checks pass?}
    D --> H
    E --> H
    F --> H
    G --> H

    H -->|Any fail| I["Print pass/fail summary table\nBLOCKED: fix issues first"]
    H -->|All pass| J["Phase 2: Update Scope Evidence\n- Check task cards for evidence_produced\n- Add missing evidence to scope docs\n- mpga evidence verify"]

    J --> K["Phase 3: PR Template Generation\n- Summary from task card + git diff --stat\n- Test plan from TDD trace\n- Evidence links from task cards\n- Breaking changes scan\n- Reviewer checklist from gate results"]

    K --> L["Phase 4: Create Commits\n- Group by type: feat/fix/refactor/test\n- Reference task IDs in commit body"]

    L --> M["Phase 5: Post-Commit Actions"]
    M --> N[Update milestone status\nmpga milestone status]
    N --> O[Archive completed tasks\nmpga board archive]
    O --> P{User choice?}
    P -->|Create PR| Q[Create PR with\ngenerated template]
    P -->|Merge to main| R[Direct merge\nif on feature branch]
    P -->|Keep on branch| S[No merge, no PR]

    Q --> T{Spoke available?}
    R --> T
    S --> T
    T -->|Yes| U[mpga spoke announcement]
    T -->|No| V[Done]
    U --> V
```

## Inputs
- Completed and verified tasks
- Task cards with evidence_produced fields
- Git staged changes
- Test suite, linter, drift check results

## Outputs
- Ship Gate pass/fail summary (blocks on any failure)
- Updated scope evidence links
- Auto-generated PR template (summary, test plan, evidence, breaking changes, checklist)
- Conventional commits referencing task IDs
- Milestone status updated, completed tasks archived
- PR created, merged, or kept on branch (user's choice)
