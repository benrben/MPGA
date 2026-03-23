---
description: Generate an evidence-based implementation plan with milestone and tasks on the board
---

## plan

**Trigger:** User provides a goal or description to plan

## Protocol

### Step 1: Create or find the milestone

**If an active milestone already exists:**
```
/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh milestone list
cat MPGA/milestones/<id>/PLAN.md
cat MPGA/milestones/<id>/DESIGN.md  # if exists
```
Ask the user: plan tasks under the existing milestone, or create a new one?

**If no milestone exists (or user wants a new one):**
Create a milestone from the user's goal:
```
/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh milestone new "<goal name>"
```
Then edit the generated `PLAN.md` with the user's objective and acceptance criteria.

### Step 2: Read relevant scope documents for the work area

```
cat MPGA/INDEX.md
cat MPGA/scopes/<relevant-scope>.md
```

### Step 3: Research if needed

If `config.agents.researchBeforePlan` is true:
- Spawn `researcher` agent first
- Incorporate research findings into plan

### Step 4: Break work into tasks

Follow these rules:
- Each task = 2-10 minutes of focused work
- Each task must cite exact files to modify
- Each task must have checkable acceptance criteria
- Dependencies must be explicit
- Order tasks by dependency (blocking tasks first)

### Step 5: Create task cards on the board

For each task, run:
```
/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board add "<title>" \
  --priority <level> \
  --scope <scope> \
  --column todo \
  --milestone <milestone-id>
```

Every task MUST be linked to the milestone via `--milestone`.

### Step 6: Update the milestone PLAN.md

Write the full task breakdown into `MPGA/milestones/<id>/PLAN.md` with task IDs, files, evidence expected, acceptance criteria, and dependencies.

### Step 7: Show the board

```
/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board show
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
- ALWAYS create a milestone — every plan needs a milestone to track progress
- ALWAYS create tasks on the board — a plan without board tasks is incomplete
- Every task MUST be linked to the milestone
- Every task MUST reference specific files with evidence links
- NO vague tasks like "implement auth" — must be specific
- Tasks must be ordered by dependency
- Each task must have at least one acceptance criterion that can be verified mechanically
