---
description: Generate an evidence-based implementation plan with tasks on the board
---

## plan

**Trigger:** Milestone created and ready for task decomposition

## Protocol

1. Read the active milestone's objective:
   ```
   cat MPGA/milestones/<id>/PLAN.md
   cat MPGA/milestones/<id>/DESIGN.md  # if exists
   ```

2. Read relevant scope documents for the work area

3. If `config.agents.researchBeforePlan` is true:
   - Spawn `researcher` agent first
   - Incorporate research findings into plan

4. Break work into tasks following these rules:
   - Each task = 2-10 minutes of focused work
   - Each task must cite exact files to modify
   - Each task must have checkable acceptance criteria
   - Dependencies must be explicit

5. Create task cards on the board:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board add "<title>" \
     --priority <level> \
     --scope <scope> \
     --column todo \
     --milestone <id>
   ```

6. Update PLAN.md with the task breakdown

7. Show the board:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board show
   ```

## Task template
```markdown
### T00N: <title>
**Files:** src/auth/jwt.ts, src/auth/jwt.test.ts
**Evidence expected:**
  - [E] src/auth/jwt.ts :: generateAccessToken()
  - [E] src/auth/jwt.ts :: generateRefreshToken()
**Acceptance criteria:**
  - [ ] generateAccessToken() returns JWT with 15min expiry
  - [ ] generateRefreshToken() returns JWT with 7d expiry
**Depends on:** (none)
**Time estimate:** 5min
```

## Strict rules
- Every task MUST reference specific files with evidence links
- NO vague tasks like "implement auth" — must be specific
- Tasks must be ordered by dependency
- Each task must have at least one acceptance criterion that can be verified mechanically
