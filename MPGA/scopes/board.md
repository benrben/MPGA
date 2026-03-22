# Scope: board

## Summary

The **board** module contains 4 files (518 lines).

<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code

Main entry points — open these first to understand this behavior:

- [E] `mpga-plugin/cli/src/board/board.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** function, interface, type
- <!-- TODO: Add relevant frameworks, integrations, and expertise areas -->

## Who and what triggers it

<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

**Called by scopes:**

- ← commands

## What happens

<!-- TODO: Describe the flow in plain language: inputs, main steps, outputs or side effects -->

## Rules and edge cases

<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples

<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI

<!-- TODO: Screens or flows if relevant — intent, layout, interactions, data shown/submitted. Remove this section if not applicable. -->

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [core](./core.md)
- [evidence](./evidence.md)
- [commands](./commands.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depends on:**

- → [core](./core.md)

**Depended on by:**

- ← [commands](./commands.md)

<!-- TODO: Shared concepts or data with other scopes -->

## Diagram

```mermaid
graph LR
    board --> core
    commands --> board
```

## Traces

<!-- TODO: Step-by-step paths through the system. Use the table format below:

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | (layer) | (description) | [E] file:line |
-->

## Evidence index

| Claim | Evidence |
|-------|----------|
| `renderBoardMd` (function) | [E] mpga-plugin/cli/src/board/board-md.ts :: renderBoardMd |
| `BoardState` (interface) | [E] mpga-plugin/cli/src/board/board.ts :: BoardState |
| `loadBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts :: loadBoard |
| `saveBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts :: saveBoard |
| `createEmptyBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts :: createEmptyBoard |
| `recalcStats` (function) | [E] mpga-plugin/cli/src/board/board.ts :: recalcStats |
| `checkWipLimit` (function) | [E] mpga-plugin/cli/src/board/board.ts :: checkWipLimit |
| `nextTaskId` (function) | [E] mpga-plugin/cli/src/board/board.ts :: nextTaskId |
| `addTask` (function) | [E] mpga-plugin/cli/src/board/board.ts :: addTask |
| `moveTask` (function) | [E] mpga-plugin/cli/src/board/board.ts :: moveTask |
| `findTaskFile` (function) | [E] mpga-plugin/cli/src/board/board.ts :: findTaskFile |
| `Column` (type) | [E] mpga-plugin/cli/src/board/task.ts :: Column |
| `Priority` (type) | [E] mpga-plugin/cli/src/board/task.ts :: Priority |
| `TddStage` (type) | [E] mpga-plugin/cli/src/board/task.ts :: TddStage |
| `TaskStatus` (type) | [E] mpga-plugin/cli/src/board/task.ts :: TaskStatus |
| `Task` (interface) | [E] mpga-plugin/cli/src/board/task.ts :: Task |
| `taskFilename` (function) | [E] mpga-plugin/cli/src/board/task.ts :: taskFilename |
| `renderTaskFile` (function) | [E] mpga-plugin/cli/src/board/task.ts :: renderTaskFile |
| `parseTaskFile` (function) | [E] mpga-plugin/cli/src/board/task.ts :: parseTaskFile |
| `loadAllTasks` (function) | [E] mpga-plugin/cli/src/board/task.ts :: loadAllTasks |

## Files

- `mpga-plugin/cli/src/board/board-md.ts` (125 lines, typescript)
- `mpga-plugin/cli/src/board/board.ts` (181 lines, typescript)
- `mpga-plugin/cli/src/board/task.test.ts` (79 lines, typescript)
- `mpga-plugin/cli/src/board/task.ts` (133 lines, typescript)

## Deeper splits

<!-- TODO: Pointers to smaller sub-topic scopes if this capability is large enough to split -->

## Confidence and notes

- **Confidence:** low — auto-generated, not yet verified
- **Evidence coverage:** 0/20 verified
- **Last verified:** 2026-03-22
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history

- 2026-03-22: Initial scope generation via `mpga sync`