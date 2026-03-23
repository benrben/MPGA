---
description: Orchestrate the TDD cycle for a task (red → green → blue → review)
---

## develop

**Trigger:** Plan approved, ready to execute a task

## Protocol

For each task in `todo` column:

1. **Claim the task:**
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board claim <task-id>
   ```

2. **Load context:**
   - Read task card: `cat MPGA/board/tasks/<task-file>.md`
   - Read relevant scope docs: `cat MPGA/scopes/<scope>.md`

3. **red↔green micro-cycle phase:**
   - Spawn `red-dev` agent with task + scope context
   - red-dev writes ONE failing test (starting with degenerate case) — bar turns RED
   - Spawn `green-dev` agent to make that ONE test pass with minimal code — bar turns GREEN
   - red-dev writes the NEXT test (slightly more complex) — bar turns RED again
   - green-dev makes it pass — bar turns GREEN again
   - Repeat until all acceptance criteria are covered
   - If green-dev signals "retreat-to-green" (architecture blocks): spawn blue-dev for structural refactoring, then resume micro-cycle
   - Update stage: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage red`
   - Then: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage green`

4. **blue-dev phase:**
   - Spawn `blue-dev` agent with passing tests + implementation
   - blue-dev refactors BOTH production code and test code (without changing assertions)
   - Wait for confirmation: tests still passing after refactor
   - Update stage: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage blue`

5. **reviewer phase:**
   - Spawn `reviewer` agent
   - If CRITICAL issues: loop back to appropriate phase
   - If approved: proceed

6. **Record evidence:**
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --evidence-add "<[E] link>"
   ```

7. **Move to done:**
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board move <id> done
   ```

8. **Drift check** (also triggered automatically by hook after each write):
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --quick
   ```

## Context budget management
After each task: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh session budget`
If >70% used: consider `/mpga:handoff` before next task

## Strict rules
- NEVER skip a TDD phase
- NEVER move to next phase if current phase failed
- ALWAYS record evidence_produced on task completion
- ONE task in-progress at a time (unless WIP limit allows more)
