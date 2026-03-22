# /mpga:execute

Execute the TDD cycle for the next task on the board.

## Steps

For each task in `todo` column (or the specified task):

1. Move task to in-progress: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board claim <task-id>`
2. Read the task card: `cat MPGA/board/tasks/<task-file>.md`
3. Read relevant scope docs
4. **TDD Cycle:**
   a. Spawn `green-dev` agent → write failing tests → confirm red
   b. Spawn `red-dev` agent → implement to pass tests → confirm green
   c. Spawn `blue-dev` agent → refactor → confirm tests still green
   d. Spawn `reviewer` agent → two-stage review
   e. If reviewer issues CRITICAL → loop back to appropriate agent
5. After each file write: drift check runs automatically (via hook)
6. If reviewer passes → move to done: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board move <id> done`
7. Record evidence produced: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board update <id> --evidence-add "<link>"`

## Usage
```
/mpga:execute           (picks next todo task)
/mpga:execute T001      (specific task)
/mpga:execute --phase 2 (all tasks in phase 2)
```

## Context management
- Each TDD task runs in a focused context with only relevant scopes loaded
- If context budget is low during execution: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh session budget`
- If context is critical: pause and run `/mpga:handoff`
