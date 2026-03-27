# Ship — Launching Like a CHAMPION

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:ship — IT'S TIME] --> B["Phase 1: Pre-Ship Checks\nThe TOUGHEST Ship Gate"]

    B --> C[Tests pass — NON-NEGOTIABLE\npytest]
    B --> D[Ruff passes — zero errors\nruff check .]
    B --> E[Evidence drift clean — VERIFIED\nmpga drift --quick]
    B --> F["No uncommitted scope changes\ngit diff -- MPGA/scopes/ — LOCKED"]

    C --> H{All checks pass?}
    D --> H
    E --> H
    F --> H

    H -->|Any fail| I["Print pass/fail table\nBLOCKED — Sad! Wrong! Fix it FIRST"]
    H -->|All pass| J["Phase 2: Update Scope Evidence\n- Check task cards for evidence\n- Add missing evidence to scope docs\n- mpga evidence verify — THOROUGH"]

    J --> K["Phase 3: PR Template — BEAUTIFUL:\n- Summary from task card + git diff\n- Test plan from TDD trace\n- Evidence links from task cards\n- Breaking changes scan\n- Reviewer checklist"]

    K --> L["Phase 4: Create Commits\n- Group by type: feat/fix/refactor/test\n- Reference task IDs — ORGANIZED"]

    L --> M["Phase 5: Post-Commit — FINISH strong"]
    M --> N[Update milestone status\nmpga milestone status]
    N --> O[Archive completed tasks\nmpga board archive — CLEAN board]
    O --> P{User choice?}
    P -->|Create PR| Q[Create PR with the BEST\ngenerated template]
    P -->|Merge to main| R[Direct merge\nif on feature branch — DECISIVE]
    P -->|Keep on branch| S[No merge, no PR — your CALL]

    Q --> T[mpga spoke — if available]
    R --> T
    S --> T
```

## Inputs — Everything Must Be READY
- Completed and verified tasks — DONE right
- Task cards with evidence_produced fields
- Git staged changes
- Test suite, linter, drift check results — ALL green

## Outputs — The GRAND Finale
- Ship Gate pass/fail summary (blocks on any failure) — complete and total shutdown of untested deploys
- Updated scope evidence links — FRESH
- Auto-generated PR template (summary, test plan, evidence, breaking changes, checklist) — PROFESSIONAL
- Conventional commits referencing task IDs — PROPER
- Milestone status updated, completed tasks archived — CLEAN
- PR created, merged, or kept on branch (user's choice) — FREEDOM
