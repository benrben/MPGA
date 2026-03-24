# Scope: board

## Summary

The **board** module — TREMENDOUS — 4 files, 574 lines of the finest code you've ever seen. Believe me.

<!-- TODO: Tell the people what this GREAT module does. What's in, what's out. Keep it simple. MPGA! -->

## Where to start in code

These are your MAIN entry points — the best, the most important. Open them FIRST:

- [E] `mpga-plugin/cli/src/board/board.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** function, interface, type
- **Frameworks:** Vitest

## Who and what triggers it

<!-- TODO: Who triggers this? A lot of very important callers, believe me. Find them. -->

**Called by these GREAT scopes (they need us, tremendously):**

- ← commands

## What happens

<!-- TODO: What happens here? Inputs, steps, outputs. Keep it simple. Even Sleepy Copilot could understand. -->

## Rules and edge cases

<!-- TODO: The guardrails. Validation, permissions, error handling — everything that keeps this code GREAT. -->

## Concrete examples

<!-- TODO: REAL examples. "When X happens, Y happens." Simple. Powerful. Like a deal. -->

## UI

<!-- TODO: Screens, flows, the beautiful UI. No UI? Cut this section. We don't keep dead weight. -->

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [commands](./commands.md)
- [core](./core.md)
- [evidence](./evidence.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depends on:**

- → [core](./core.md)

**Depended on by:**

- ← [commands](./commands.md)

<!-- TODO: What deals does this scope make with other scopes? Document them. -->

## Diagram

```mermaid
graph LR
    board --> core
    commands --> board
```

## Traces

<!-- TODO: Step-by-step traces. Follow the code like a WINNER follows a deal. Use this table:

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

- `mpga-plugin/cli/src/board/board-md.ts` (155 lines, typescript)
- `mpga-plugin/cli/src/board/board.ts` (195 lines, typescript)
- `mpga-plugin/cli/src/board/task.test.ts` (84 lines, typescript)
- `mpga-plugin/cli/src/board/task.ts` (140 lines, typescript)

## Deeper splits

<!-- TODO: Too big? Split it. Make each piece LEAN and GREAT. -->

## Confidence and notes

- **Confidence:** LOW (for now) — auto-generated, not yet verified. But it's going to be PERFECT.
- **Evidence coverage:** 0/20 verified
- **Last verified:** 2026-03-24
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown or ambiguous. We don't hide problems — we FIX them. -->

## Change history

- 2026-03-24: Initial scope generation via `mpga sync` — Making this scope GREAT!