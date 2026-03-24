# /mpga:next

Auto-detect the next logical action based on current project state.

## Decision tree

1. Read `MPGA/INDEX.md` for active milestone
2. Read board state: `node ./.mpga-runtime/cli/dist/index.js board show --json`
3. Check context budget: `node ./.mpga-runtime/cli/dist/index.js session budget`

### If context budget is critical (>80% used)
→ Run `/mpga:handoff` — create handoff and clear context

### If blocked tasks exist
→ Show blocked tasks, ask user how to unblock

### If in-progress tasks
→ Continue: `/mpga:execute <task-id>`

### If todo tasks ready
→ Pick up the next task whose scope is not already locked by another in-progress write lane: `/mpga:execute`

### If all tasks done
→ Run `/mpga:verify`, then suggest `/mpga:ship`

### If board is empty and milestone exists
→ Suggest `/mpga:plan` to generate tasks

### If no milestone
→ Suggest `node ./.mpga-runtime/cli/dist/index.js milestone new "<name>"`

### If MPGA not initialized
→ Run `/mpga:init`

## Usage
```
/mpga:next
```
