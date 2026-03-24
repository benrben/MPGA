# Scope: src-board

## Summary

The **board** subsystem manages a kanban task board with 6 columns, WIP limits, TDD stage tracking, and milestone integration. Tasks are individual markdown files with YAML frontmatter; the board state is derived from these files.

## Where to start in code

- [E] `src/board/board.ts` — board state management and task lifecycle
- [E] `src/board/task.ts` — task type definitions and file serialization

## Context / stack / skills

- **Languages:** TypeScript
- **Dependencies:** gray-matter (YAML frontmatter parsing)

## Who and what triggers it

- `mpga board add|move|claim|assign|update|block|unblock|deps|stats|archive` commands
- `mpga milestone new|complete` creates/archives board context
- `mpga session handoff` reads board state for in-flight summary

## What happens

### Task lifecycle

```
backlog → todo → in-progress → testing → review → done → (archive)
```

Each task has an orthogonal TDD stage: `green → red → blue → review → done`
And a status overlay: `blocked | stale | rework | paused | null`

### Data model

- **Task files** (`MPGA/board/tasks/T001-slug.md`): YAML frontmatter with id, title, column, priority, assigned, tdd_stage, depends_on, evidence_produced, time_estimate, status + markdown body
- **Board state** (`board.json`): version, milestone, columns (maps to task ID arrays), stats, wip_limits, next_task_id

### Key invariant

`recalcStats()` rebuilds `board.columns` from task files on every call. Task files are the source of truth — `board.json` columns are derived state that self-corrects.

### Rendering (`board-md.ts`)

`renderBoardMd()` generates a human-readable `BOARD.md` with progress bars, column tables with TDD stage emoji icons, WIP limit indicators, and evidence ratio columns.

## Rules and edge cases

- `status: 'active'` on disk maps to `null` in memory (YAML can't represent null cleanly)
- WIP limits enforced by `moveTask` only; `addTask` and `claim` bypass them
- `findTaskFile` matches by filename prefix (`T001-` or `T001.`) — moving a task does not rename its file
- `taskFilename` generates slugs truncated at 40 chars, lowercase with hyphens
- `time_estimate` defaults to `'5min'` when absent from frontmatter

## Navigation

**Parent:** [src](./src.md)

**Depends on:** [src-core](./src-core.md) — imports `progressBar` from `core/logger.js` for board-md rendering [E] src/board/board-md.ts:3

**Used by:** [src-commands](./src-commands.md) (board, milestone, session, health, status commands)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `BoardState` (interface) | [E] src/board/board.ts:5-21 :: BoardState()|
| `loadBoard` (function) | [E] src/board/board.ts:24-29 :: loadBoard()|
| `saveBoard` (function) | [E] src/board/board.ts:32-35 :: saveBoard()|
| `createEmptyBoard` (function) | [E] src/board/board.ts:38-50 :: createEmptyBoard()|
| `recalcStats` (function) | [E] src/board/board.ts:53-81 :: recalcStats()|
| `checkWipLimit` (function) | [E] src/board/board.ts:96-99 :: checkWipLimit()|
| `nextTaskId` (function) | [E] src/board/board.ts:102-105 :: nextTaskId()|
| `addTask` (function) | [E] src/board/board.ts:108-119 :: addTask()|
| `moveTask` (function) | [E] src/board/board.ts:152-157 :: moveTask()|
| `findTaskFile` (function) | [E] src/board/board.ts:188-193 :: findTaskFile()|
| `Column` (type) | [E] src/board/task.ts:5-6 :: Column()|
| `Priority` (type) | [E] src/board/task.ts:6-7 :: Priority()|
| `TddStage` (type) | [E] src/board/task.ts:7-9 :: TddStage()|
| `TaskStatus` (type) | [E] src/board/task.ts:8-9 :: TaskStatus()|
| `Task` (interface) | [E] src/board/task.ts:10-29 :: Task()|
| `taskFilename` (function) | [E] src/board/task.ts:32-34 :: taskFilename()|
| `renderTaskFile` (function) | [E] src/board/task.ts:37-60 :: renderTaskFile()|
| `parseTaskFile` (function) | [E] src/board/task.ts:95-123 :: parseTaskFile()|
| `loadAllTasks` (function) | [E] src/board/task.ts:132-138 :: loadAllTasks()|
| `renderBoardMd` (function) | [E] src/board/board-md.ts:19-123 :: renderBoardMd()|

## Files

- `src/board/board.ts` (181 lines)
- `src/board/task.ts` (133 lines)
- `src/board/board-md.ts` (125 lines)

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-22
- **Drift risk:** low

## Change history

- 2026-03-22: Created as sub-scope split from src
