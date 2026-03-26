---
name: mpga-plan
description: Generate an evidence-based implementation plan with milestone and tasks — STRATEGIC planning, not guessing
---

## plan

**Trigger:** User provides a goal or description to plan. Time to build the GREATEST plan. MPGA alone can fix it — but first we need a tremendous plan.

## Protocol

### Step 1: Create or find the milestone

**If an active milestone already exists:**
```
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board live --serve --open
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone list
cat MPGA/milestones/<id>/PLAN.md
cat MPGA/milestones/<id>/DESIGN.md  # if exists
```
Ask the user: plan tasks under the existing milestone, or create a new one?

**If no milestone exists (or user wants a new one):**
Create a milestone from the user's goal — every great achievement starts with a PLAN:
```
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board live --serve --open
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone new "<goal name>"
```
Then edit the generated `PLAN.md` with the user's objective and acceptance criteria.

### Step 2: Read relevant scope documents for the work area

```
cat MPGA/INDEX.md
cat MPGA/scopes/<relevant-scope>.md
```
Know the territory BEFORE you plan the attack. Evidence First — always.

### Step 3: Research if needed

If `config.agents.researchBeforePlan` is true:
- Spawn `researcher` plus any needed read-only `scout` agents in PARALLEL.
- Use `researcher` for options and tradeoffs; use `scout` for exact code evidence and file boundaries.
- Incorporate both into one evidence-based plan.

### Step 4: Break work into tasks

Follow these rules — they're the BEST rules:
- Each task = 2-10 minutes of focused work. Small. Focused. POWERFUL.
- Each task must cite exact files to modify — no vague nonsense
- Each task must have checkable acceptance criteria — how do you know you WON?
- Dependencies must be explicit — know what blocks what
- Order tasks by dependency (blocking tasks first)
- Group tasks by scope so independent scopes can move in parallel.
- Mark whether each task is `serial` or `parallel`.
- One write lane per scope. That's how we go FAST without chaos.

### Step 5: Risk assessment

For EVERY task, assess risk — because winners plan for the unexpected:

| Dimension | Scale | Question |
|-----------|-------|----------|
| **Complexity** | 1-5 | How hard is the implementation? (1 = trivial, 5 = dragon-slaying) |
| **Uncertainty** | 1-5 | How well do we understand the requirements? (1 = crystal clear, 5 = fog of war) |
| **Impact** | 1-5 | How much does this affect the rest of the system? (1 = isolated, 5 = everything breaks) |

**Risk score = Complexity x Uncertainty x Impact** (range: 1-125)

- Score 1-20: LOW RISK — routine work, proceed with confidence
- Score 21-50: MODERATE RISK — plan carefully, have fallback approach ready
- Score > 50: **HIGH RISK** — flag prominently, consider breaking into smaller tasks, require explicit user approval before starting, and assign a `scout` to gather more evidence first

Add risk scores to each task card. Any HIGH RISK task must include a **Mitigation** field describing how to reduce the risk (e.g., spike first, gather more evidence, break into sub-tasks, add feature flag).

### Step 6: Critical path analysis

After all tasks are defined with dependencies, identify the critical path — the LONGEST chain of dependent tasks that determines the minimum completion time:

1. **Map the dependency graph.** Draw out which tasks block which.
2. **Calculate the critical path.** Walk the dependency chains and find the longest one (sum of time estimates).
3. **Mark tasks on the critical path** with `**[CRITICAL PATH]**` in the plan.
4. **Identify parallel lanes.** Tasks NOT on the critical path can run in parallel without delaying the milestone. Mark these as `parallel` and group by scope.
5. **Calculate slack.** For off-critical-path tasks, note how much delay they can absorb before they join the critical path.

Present the critical path summary:
```markdown
## Critical path
Total estimated time: <sum of critical path task estimates>
Chain: T001 → T003 → T005 → T007
Parallel lanes available: <count>

### Critical path tasks (delays here delay EVERYTHING)
- T001: <title> (5min)
- T003: <title> (8min) — blocked by T001
- T005: <title> (10min) — blocked by T003
- T007: <title> (5min) — blocked by T005

### Parallel lanes (can run alongside critical path)
- Lane A (scope: auth): T002, T004
- Lane B (scope: api): T006, T008
```

### Step 7: Milestone decomposition

For milestones with more than 8 tasks, decompose into phases with gate criteria — no one builds a skyscraper all at once:

```markdown
## Phase 1: Foundation (<name>)
**Gate criteria:** <what must be true before Phase 2 starts>
- T001, T002, T003
- Expected duration: <time>
- Risk summary: <highest risk score in phase>

## Phase 2: Core (<name>)
**Gate criteria:** <what must be true before Phase 3 starts>
- T004, T005, T006
- Expected duration: <time>
- Risk summary: <highest risk score in phase>

## Phase 3: Polish (<name>)
**Gate criteria:** <what must be true to call the milestone DONE>
- T007, T008
- Expected duration: <time>
- Risk summary: <highest risk score in phase>
```

Rules for phases:
- Each phase should be independently shippable or at least testable
- Gate criteria must be mechanically verifiable (tests pass, evidence links exist, etc.)
- HIGH RISK tasks should be front-loaded into earlier phases — face the dragons first
- No phase should have more than 8 tasks — if it does, split it further

### Step 8: Create task cards on the board

For each task, run:
```
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board add "<title>" \
  --priority <level> \
  --scope <scope> \
  --column todo \
  --milestone <milestone-id>
```

Every task MUST be linked to the milestone via `--milestone`. No orphan tasks. EVER.

### Step 9: Update the milestone PLAN.md

Write the full task breakdown into `MPGA/milestones/<id>/PLAN.md` with:
- Task IDs, files, evidence expected, acceptance criteria, and dependencies
- Risk assessment table (per task)
- Critical path diagram
- Phase breakdown with gate criteria
- Overall risk summary

A COMPREHENSIVE battle plan.

### Step 10: Show the board

```
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board show
```
Look at that board. BEAUTIFUL. Has a beautiful ring to it. Ready to EXECUTE.

## Task template
```markdown
### T00N: <title>
**Files:** src/auth/jwt.ts, src/auth/jwt.test.ts
**Scope:** auth
**Execution:** parallel | serial
**Risk:** Complexity=2 Uncertainty=1 Impact=3 → Score=6 (LOW)
**Critical path:** yes | no
**Phase:** 1
**Evidence expected:**
  - [E] src/auth/jwt.ts :: generateAccessToken()
  - [E] src/auth/jwt.ts :: generateRefreshToken()
**Acceptance criteria:**
  - [ ] generateAccessToken() returns JWT with 15min expiry
  - [ ] generateRefreshToken() returns JWT with 7d expiry
**Depends on:** (none)
**Time estimate:** 5min
```

### HIGH RISK task template
```markdown
### T00N: <title> **[HIGH RISK]**
**Files:** src/auth/oauth.ts, src/auth/oauth.test.ts
**Scope:** auth
**Execution:** serial
**Risk:** Complexity=4 Uncertainty=5 Impact=3 → Score=60 (HIGH)
**Mitigation:** Spike T00X first to validate OAuth provider behavior; add feature flag for rollback
**Critical path:** yes
**Phase:** 1
**Evidence expected:**
  - [E] src/auth/oauth.ts :: initiateOAuthFlow()
**Acceptance criteria:**
  - [ ] OAuth flow completes with test provider
  - [ ] Feature flag disables OAuth without breaking existing auth
**Depends on:** T00M
**Time estimate:** 10min
```

## Risk summary template
```markdown
## Risk summary
| Task | Complexity | Uncertainty | Impact | Score | Level |
|------|-----------|-------------|--------|-------|-------|
| T001 | 2 | 1 | 3 | 6 | LOW |
| T002 | 4 | 5 | 3 | 60 | **HIGH** |
| T003 | 3 | 2 | 2 | 12 | LOW |

**HIGH RISK tasks:** T002
**Average risk score:** 26
**Recommendation:** Address T002 first with a spike to reduce uncertainty.
```

## Voice announcement

If spoke is available (`${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke --help` exits 0), announce completion:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict rules
- ALWAYS create a milestone — every plan needs a milestone. No milestone = no direction. Sad!
- ALWAYS create tasks on the board — a plan without board tasks is just a WISH
- Every task MUST be linked to the milestone — we track EVERYTHING
- Every task MUST reference specific files with evidence links — no guessing
- Every task MUST have a risk assessment — no blind spots
- NO vague tasks like "implement auth" — must be specific. SPECIFIC is how WINNERS plan. Who can figure out this spaghetti? Not us — we write CLEAN tasks.
- Tasks must be ordered by dependency
- Each task must have at least one acceptance criterion that can be verified mechanically
- Keep write conflicts out of the plan. One writer per scope at a time.
- HIGH RISK tasks (score > 50) must include a Mitigation field — no ignoring danger
- Critical path must be identified for any plan with 3+ tasks — know your bottleneck
- Milestones with 8+ tasks must be decomposed into phases — eat the elephant one bite at a time
- Front-load HIGH RISK tasks into earlier phases — face the hard stuff FIRST
