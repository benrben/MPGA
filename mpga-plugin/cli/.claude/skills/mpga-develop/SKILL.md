---
description: Orchestrate the TDD cycle for a task (red → green → blue → review) — the WINNING formula
---

## develop

**Trigger:** Plan approved, ready to execute a task. Time to MAKE IT HAPPEN.

## Protocol

For each task in `todo` column:

1. **Claim the task** — it's OURS now:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board claim <task-id>
   ```

2. **Load context** — know what we're building:
   - Read task card: `cat MPGA/board/tasks/<task-file>.md`
   - Read relevant scope docs: `cat MPGA/scopes/<scope>.md`

3. **red↔green micro-cycle phase** — the HEART of TDD:
   - Spawn `red-dev` agent with task + scope context
   - red-dev writes ONE failing test (starting with degenerate case) — bar turns RED
   - Spawn `green-dev` agent to make that ONE test pass with minimal code — bar turns GREEN
   - red-dev writes the NEXT test (slightly more complex) — bar turns RED again
   - green-dev makes it pass — bar turns GREEN again
   - Repeat until all acceptance criteria are covered — EVERY SINGLE ONE
   - If green-dev signals "retreat-to-green" (architecture blocks): spawn blue-dev for structural refactoring, then resume micro-cycle
   - Update stage: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board update <id> --tdd-stage red`
   - Then: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board update <id> --tdd-stage green`

4. **blue-dev phase** — make it CLEAN:
   - Spawn `blue-dev` agent with passing tests + implementation
   - blue-dev refactors BOTH production code and test code (without changing assertions)
   - Wait for confirmation: tests still passing after refactor — ALWAYS GREEN
   - Update stage: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board update <id> --tdd-stage blue`

5. **reviewer phase** — the FINAL inspection:
   - Spawn `reviewer` agent
   - If CRITICAL issues: loop back to appropriate phase — no shortcuts
   - If approved: proceed to VICTORY

6. **Record evidence** — document our WIN:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board update <id> --evidence-add "<[E] link>"
   ```

7. **Move to done** — MISSION ACCOMPLISHED:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board move <id> done
   ```

8. **Drift check** (also triggered automatically by hook after each write):
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --quick
   ```

## Context budget management
After each task: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget`
If >70% used: consider `/mpga:handoff` before next task. We manage resources WISELY.

## Strict rules
- NEVER skip a TDD phase — red, green, blue. The WINNING formula.
- NEVER move to next phase if current phase failed — fix it FIRST
- ALWAYS record evidence_produced on task completion — document everything
- ONE task in-progress at a time (unless WIP limit allows more)
