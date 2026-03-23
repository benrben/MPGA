# /mpga:execute

Execute the TDD cycle for the next task on the board.

## Steps

For each task in `todo` column (or the specified task):

1. Move task to in-progress: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board claim <task-id>`
2. Read the task card: `cat MPGA/board/tasks/<task-file>.md`
3. Read relevant scope docs
4. **TDD Micro-Cycle:**
   a. Spawn `red-dev` → writes ONE failing test (degenerate case first) — bar turns RED
   b. Spawn `green-dev` → makes that ONE test pass with minimal code — bar turns GREEN
   c. Repeat a–b, building complexity: degenerate → simple → complex → edge cases
   d. If green-dev signals retreat-to-green → spawn `blue-dev` for structural refactoring, then resume a–b
   e. When all acceptance criteria covered → spawn `blue-dev` → refactor production code AND tests (without changing assertions) → confirm green
   f. Spawn `reviewer` agent → two-stage review (including testability + degenerate case checks)
   g. If reviewer issues CRITICAL → loop back to appropriate agent
5. After each file write: drift check runs automatically (via hook)
6. If reviewer passes → move to done: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board move <id> done`
7. Record evidence produced: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board update <id> --evidence-add "<link>"`

## Usage
```
/mpga:execute           (picks next todo task)
/mpga:execute T001      (specific task)
/mpga:execute --phase 2 (all tasks in phase 2)
```

## Context management
- Each TDD task runs in a focused context with only relevant scopes loaded
- If context budget is low during execution: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget`
- If context is critical: pause and run `/mpga:handoff`
