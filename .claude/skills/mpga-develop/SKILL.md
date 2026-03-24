---
name: mpga-develop
description: Orchestrate the TDD cycle for a task (red → green → blue → review) — the WINNING formula
---

## develop

**Trigger:** Plan approved, ready to execute a task. Time to MAKE IT HAPPEN.

> This is the canonical TDD execution protocol. The `/mpga:execute` command
> delegates here — use `/mpga:develop` for all TDD cycle work.

## Protocol

For each task in `todo` column (or a specified task):

1. **Claim the task** — it's OURS now:
   Start the live board in the browser through Node first:
   ```
   node ./.mpga-runtime/cli/dist/index.js board live --serve --open
   ```

   Then claim the task:
   ```
   node ./.mpga-runtime/cli/dist/index.js board claim <task-id>
   ```
   Claim the scope-local write lane too. One writer per scope. ALWAYS.

2. **Load context** — know what we're building:
   - Read task card: `cat MPGA/board/tasks/<task-file>.md`
   - Read relevant scope docs: `cat MPGA/scopes/<scope>.md`
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
   - Update stage: `node ./.mpga-runtime/cli/dist/index.js board update <id> --tdd-stage red`
   - Then: `node ./.mpga-runtime/cli/dist/index.js board update <id> --tdd-stage green`

4. **blue-dev phase** — make it CLEAN:
   - Spawn `blue-dev` agent with passing tests + implementation
   - blue-dev refactors BOTH production code and test code (without changing assertions)
   - Wait for confirmation: tests still passing after refactor — ALWAYS GREEN
   - Update stage: `node ./.mpga-runtime/cli/dist/index.js board update <id> --tdd-stage blue`

5. **reviewer phase** — the FINAL inspection:
   - Spawn `reviewer` agent — two-stage review (including testability + degenerate case checks)
   - If CRITICAL issues: loop back to appropriate phase — no shortcuts
   - If approved: proceed to VICTORY
   - Reserve `verifier` for milestone boundaries, risky tasks, or explicit `/mpga:verify` runs. Don't run the full gate on every tiny change.

6. **Record evidence** — document our WIN:
   ```
   node ./.mpga-runtime/cli/dist/index.js board update <id> --evidence-add "<[E] link>"
   ```

7. **Move to done** — MISSION ACCOMPLISHED:
   ```
   node ./.mpga-runtime/cli/dist/index.js board move <id> done
   ```

8. **Drift check** (also triggered automatically by hook after each write):
   ```
   node ./.mpga-runtime/cli/dist/index.js drift --quick
   ```

## Usage
```
/mpga:develop           (picks next todo task)
/mpga:develop T001      (specific task)
/mpga:develop --phase 2 (all tasks in phase 2)
```

## Context budget management
- Each TDD task runs in a focused context with only relevant scopes loaded
- Independent scopes can move in parallel; never allow two writers in the same scope
- After each task: `node ./.mpga-runtime/cli/dist/index.js session budget`
- If >70% used: consider `/mpga:handoff` before next task. We manage resources WISELY.
- If context is critical: pause and run `/mpga:handoff`

## Strict rules
- NEVER skip a TDD phase — red, green, blue. The WINNING formula.
- NEVER move to next phase if current phase failed — fix it FIRST
- ALWAYS record evidence_produced on task completion — document everything
- One WRITE task per scope at a time. Independent scopes may move in parallel if WIP limits allow it.
