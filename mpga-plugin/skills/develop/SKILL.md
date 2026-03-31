---
name: mpga-develop
description: Orchestrate the TDD cycle for a task (red → green → blue → review) — the WINNING formula
---

## develop

**Trigger:** Plan approved, ready to execute a task. Time to Make Project Great Again.

> This is the canonical TDD execution protocol. The `/mpga:execute` command
> delegates here — use `/mpga:develop` for all TDD cycle work.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

**Agent brief:** Task context from board, scope docs from CLI, acceptance criteria from milestone.
**Expected output:** Structured verdict (PASS/FAIL) with file:line references.

## Protocol

For each task in `todo` column (or a specified task):

1. **Claim the task** — it's OURS now:
   Start the live board in the browser through Node first:
   ```
   mpga board live --serve --open
   ```

   Then claim the task:
   ```
   mpga board claim <task-id>
   ```
   Claim the scope-local write lane too. One writer per scope. ALWAYS.

2. **Load context** — know what we're building:
   - Read task card: `mpga board show <task-id>`
   - Read relevant scope docs: `mpga scope show <scope>`
   - Each TDD task runs in a focused context with only relevant scopes loaded.
   - If another task is already writing to that scope, pick a different ready task.

3. **red-green micro-cycle phase** — the HEART of TDD:
   - Spawn `red-dev` agent with task + scope context
   - red-dev writes ONE failing test (starting with degenerate case) — bar turns RED
   - Spawn `green-dev` agent to make that ONE test pass with minimal code — bar turns GREEN
   - red-dev writes the NEXT test (slightly more complex) — bar turns RED again
   - green-dev makes it pass — bar turns GREEN again
   - Build complexity progressively: degenerate → simple → complex → edge cases
   - Repeat until all acceptance criteria are covered — EVERY SINGLE ONE
   - If handoff cost is dominating and the same scope/fixture is still hot, red-dev MAY queue one additional failing test. Never more than two outstanding red tests.
   - If green-dev signals "retreat-to-green" (architecture blocks): spawn blue-dev for structural refactoring, then resume micro-cycle
   - While red-dev/green-dev own the write lane, `scout` and `auditor` may run in the background as read-only helpers
   - Update stage: `mpga board update <id> --tdd-stage red`
     ```bash
     mpga spoke 'RED phase done. Tests written and failing. Green-dev, your move.'
     ```
   - Then: `mpga board update <id> --tdd-stage green`
     ```bash
     mpga spoke 'GREEN phase done. All tests passing. Minimal code. Blue-dev, clean it up.'
     ```

4. **visual-tester gate** — check the UI before refactoring:
   - Only trigger this step for tasks with UI-related scope tags
   - Spawn `visual-tester` after GREEN and before BLUE
   - Visual regression FAIL blocks the blue phase
   - Human approval may explicitly accept a diff and unblock progress
   - If Playwright is not installed or no baseline exists, skip gracefully and record the reason

5. **blue-dev phase** — make it CLEAN:
   - Spawn `blue-dev` agent with passing tests + implementation
   - blue-dev refactors BOTH production code and test code (without changing assertions)
   - Wait for confirmation: tests still passing after refactor — ALWAYS GREEN
   - Update stage: `mpga board update <id> --tdd-stage blue`
     ```bash
     mpga spoke 'BLUE phase done. Clean code. Tests still green. Reviewer, you are up.'
     ```

6. **reviewer phase** — the FINAL inspection:
   - Spawn `reviewer` agent — two-stage review (including testability + degenerate case checks)
   - If CRITICAL issues: loop back to appropriate phase — no shortcuts
   - If approved: announce then proceed to VICTORY:
     ```bash
     mpga spoke 'Reviewer approved. Moving to done. Mission accomplished.'
     ```
   - Reserve `verifier` for milestone boundaries, risky tasks, or explicit `/mpga:verify` runs. Don't run the full gate on every tiny change.

7. **Record evidence** — Evidence First, document our WIN:
   ```
   mpga board update <id> --evidence-add "<[E] link>"
   ```

8. **Move to done** — MISSION ACCOMPLISHED:
   ```
   mpga board move <id> done
   ```

9. **Drift check** (also triggered automatically by hook after each write):
   ```
   mpga drift --quick
   ```

## Usage
```
/mpga:develop           (picks next todo task)
/mpga:develop T001      (specific task)
/mpga:develop --phase 2 (all tasks in phase 2)
```

## Context budget management
- **Before claiming any task:** run `mpga session budget` — if >70% used, run `/mpga:handoff` FIRST and start a fresh session. Do not begin new work on a nearly-full context.
- Each TDD task runs in a focused context with only relevant scopes loaded
- Independent scopes can move in parallel; never allow two writers in the same scope
- After each task: check budget again before claiming the next one

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict rules
- NEVER skip a TDD phase — red, green, blue. The WINNING formula. All tests pass — very successful!
- NEVER move to next phase if current phase failed — fix it FIRST. Lock her up! (the race condition!)
- ALWAYS record evidence_produced on task completion — document everything. Believe me, this matters big league.
- One WRITE task per scope at a time. No collusion between modules! Independent scopes may move in parallel if WIP limits allow it.
