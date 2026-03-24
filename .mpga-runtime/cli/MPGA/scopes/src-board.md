# Scope: src-board

## Summary

The **board** subsystem manages a kanban task board with 6 columns, WIP limits, TDD stage tracking, and milestone integration.

Tasks are still individual markdown files with YAML frontmatter, and they now also carry execution metadata for lane IDs, run status, current agent, file locks, scope locks, and heartbeat timestamps [E] `src/board/task.ts:27-54` :: Task().

The board state now persists scheduler lanes, active runs, and live UI defaults alongside the existing aggregate stats [E] `src/board/board.ts:25-53` :: BoardState().

The subsystem also gained a live-board projection layer. `live.ts` builds and writes `snapshot.json` from task files plus board state [E] `src/board/live.ts:81-124` :: buildBoardLiveSnapshot()/writeBoardLiveSnapshot().

`live-html.ts` now embeds the latest snapshot directly into the HTML so `file://` opens still render data, then upgrades to polling `snapshot.json` when available [E] `src/board/live-html.ts:23-320` :: renderBoardLiveHtml().

## Where to start in code

- [E] `src/board/task.ts` — task type definitions, lock-aware frontmatter serialization, and backward-compatible parsing
- [E] `src/board/board.ts` — board state normalization, scheduler metadata defaults, and task lifecycle
- [E] `src/board/live.ts` — live snapshot and event projection
- [E] `src/board/live-html.ts` — auto-refresh HTML dashboard renderer

## Context / stack / skills

- **Languages:** TypeScript
- **Dependencies:** gray-matter (YAML frontmatter parsing)

## Who and what triggers it

- `mpga board add|move|claim|assign|update|block|unblock|deps|stats|archive|live` commands [E] `src/commands/board.ts:19-84` :: registerBoard()
- `mpga develop <task-id>` registers the scheduler entry point [E] `src/commands/develop.ts:4-18` :: registerDevelop()
- `mpga develop <task-id>` transitions lanes, locks, and live artifacts through the scheduler [E] `src/commands/develop-scheduler.ts:66-177` :: persistLaneTransition()/runDevelopTask()
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

- **Task files** (`MPGA/board/tasks/T001-slug.md`): YAML frontmatter with id, title, column, priority, assigned, tdd_stage, dependencies, evidence, plus runtime execution fields such as `lane_id`, `run_status`, `current_agent`, `file_locks`, `scope_locks`, `started_at`, `finished_at`, and `heartbeat_at` [E] `src/board/task.ts:27-54` :: Task().
- **Task files** serialize that runtime metadata back into visible markdown frontmatter [E] `src/board/task.ts:66-132` :: renderTaskFile().
- **Board state** (`board.json`): version, milestone, columns, stats, WIP limits, next task id, plus `lanes`, `active_runs`, `scheduler`, and `ui` metadata [E] `src/board/board.ts:25-53` :: BoardState().
- **Live board files** (`MPGA/board/live/`): `snapshot.json` and `index.html`, both derived from task files and board state rather than acting as sources of truth [E] `src/board/live.ts:113-124` :: writeBoardLiveSnapshot().
- **Live board files** include the generated HTML shell for the local dashboard [E] `src/board/live-html.ts:4-279` :: renderBoardLiveHtml()/writeBoardLiveHtml().

### Key invariant

`normalizeBoardState()` backfills scheduler and UI defaults without dropping legacy board files [E] `src/board/board.ts:89-129` :: normalizeBoardState().

`recalcStats()` still rebuilds `board.columns` from task files on every call, so task files remain the source of truth for placement [E] `src/board/board.ts:132-167` :: recalcStats().

### Rendering

- `renderBoardMd()` still generates the human-readable `BOARD.md` with progress bars, column tables, WIP annotations, and evidence ratios [E] `src/board/board-md.ts:29-154` :: renderBoardMd()
- `buildBoardLiveSnapshot()` projects task and lane state into a machine-readable snapshot for polling clients [E] `src/board/live.ts:81-111` :: buildBoardLiveSnapshot()
- `renderBoardLiveHtml()` emits a static HTML shell that renders the embedded snapshot immediately, then polls `snapshot.json` every 2.5 seconds and updates columns, active lanes, file locks, and recent events using escaped DOM text updates [E] `src/board/live-html.ts:180-317` :: renderSnapshot()/loadSnapshot()

## Rules and edge cases

- `status: 'active'` on disk maps to `null` in memory (YAML can't represent null cleanly)
- Legacy task files without runtime fields are backfilled with safe defaults such as `run_status: 'queued'`, `lane_id: null`, and empty lock arrays [E] `src/board/task.ts:134-171` :: parseTaskFile()
- Legacy board files without scheduler metadata are normalized with default `lanes`, `active_runs`, `scheduler.lock_mode = 'file'`, and `ui.refresh_interval_ms = 2500` [E] `src/board/board.ts:89-130` :: normalizeBoardState()
- WIP limits enforced by `moveTask` only; `addTask` and `claim` bypass them
- `findTaskFile` matches by filename prefix (`T001-` or `T001.`) — moving a task does not rename its file
- `taskFilename` generates slugs truncated at 40 chars, lowercase with hyphens
- `time_estimate` defaults to `'5min'` when absent from frontmatter
- Missing or malformed `events.ndjson` files do not break live snapshot generation; the live event list simply renders as empty [E] `src/board/live.ts:43-64` :: readRecentBoardEvents()

## Navigation

**Parent:** [src](./src.md)

**Depends on:** [src-core](./src-core.md) — imports `progressBar` from `core/logger.js` for board-md rendering [E] src/board/board-md.ts:3

**Used by:** [src-commands](./src-commands.md) (board, milestone, session, health, status commands)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `BoardState` (interface) | [E] src/board/board.ts:25-53 :: BoardState()|
| `normalizeBoardState` (function) | [E] src/board/board.ts:89-130 :: normalizeBoardState()|
| `recalcStats` (function) | [E] src/board/board.ts:132-168 :: recalcStats()|
| `Task` (interface) | [E] src/board/task.ts:27-54 :: Task()|
| `renderTaskFile` (function) | [E] src/board/task.ts:66-132 :: renderTaskFile()|
| `parseTaskFile` (function) | [E] src/board/task.ts:134-171 :: parseTaskFile()|
| `BoardLiveSnapshot` (interface) | [E] src/board/live.ts:27-37 :: BoardLiveSnapshot()|
| `buildBoardLiveSnapshot` (function) | [E] src/board/live.ts:81-111 :: buildBoardLiveSnapshot()|
| `writeBoardLiveSnapshot` (function) | [E] src/board/live.ts:113-124 :: writeBoardLiveSnapshot()|
| `renderBoardLiveHtml` (function) | [E] src/board/live-html.ts:23-320 :: renderBoardLiveHtml()|
| `writeBoardLiveHtml` (function) | [E] src/board/live-html.ts:322-324 :: writeBoardLiveHtml()|
| `renderBoardMd` (function) | [E] src/board/board-md.ts:29-154 :: renderBoardMd()|

## Files

- `src/board/board.ts`
- `src/board/task.ts`
- `src/board/board-md.ts`
- `src/board/live.ts`
- `src/board/live-html.ts`
- `src/board/board.test.ts`
- `src/board/task.test.ts`
- `src/board/live.test.ts`
- `src/board/live-html.test.ts`

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-24
- **Drift risk:** low

## Change history

- 2026-03-22: Created as sub-scope split from src
