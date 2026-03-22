---
description: Orchestrate the TDD cycle for a task (green → red → blue → review)
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

3. **green-dev phase:**
   - Spawn `green-dev` agent with task + scope context
   - Wait for confirmation: tests written and failing
   - Update stage: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage green`

4. **red-dev phase:**
   - Spawn `red-dev` agent with failing tests + scope context
   - Wait for confirmation: tests passing
   - Update stage: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage red`

5. **blue-dev phase:**
   - Spawn `blue-dev` agent with passing tests + implementation
   - Wait for confirmation: tests still passing after refactor
   - Update stage: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --tdd-stage blue`

6. **reviewer phase:**
   - Spawn `reviewer` agent
   - If CRITICAL issues: loop back to appropriate phase
   - If approved: proceed

7. **Record evidence:**
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --evidence-add "<[E] link>"
   ```

8. **Move to done:**
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board move <id> done
   ```

9. **Drift check** (also triggered automatically by hook after each write):
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
