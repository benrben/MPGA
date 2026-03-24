# Scope: board

## Summary

- **Health:** ✓ fresh
The **board** module — TREMENDOUS — 6 files, 704 lines of the finest code you've ever seen. Believe me.

The **board** module is the task-tracking core of MPGA. It owns the canonical `board.json` state, all task `.md` files, and the rendered `BOARD.md` view. In: loading/saving board state, creating/moving tasks, enforcing WIP limits, recalculating stats, and rendering the Markdown board. Out: CLI parsing (that's `commands`), evidence extraction (that's `evidence`), and scope generation (that's `generators`). [E] mpga-plugin/cli/src/board/board.ts:1-195 [E] mpga-plugin/cli/src/board/board-md.ts:1-154 [E] mpga-plugin/cli/src/board/task.ts:1-139

## Where to start in code

These are your MAIN entry points — the best, the most important. Open them FIRST:

- [E] `mpga-plugin/cli/src/board/board.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** function, interface, type
- **Frameworks:** Vitest

## Who and what triggers it

The `commands` scope is the sole direct caller. Every `mpga board` subcommand — `show`, `add`, `move`, `claim`, `assign`, `update`, `block`, `unblock`, `deps`, `stats`, `archive` — imports from `board.ts`, `board-md.ts`, and `task.ts`. [E] mpga-plugin/cli/src/commands/board.ts:6-15

**Called by these GREAT scopes (they need us, tremendously):**

- ← commands

## What happens

**board.ts — State and mutations**

- `loadBoard(boardDir)` reads `MPGA/board/board.json`; returns `createEmptyBoard()` if the file is absent. [E] mpga-plugin/cli/src/board/board.ts:24-30
- `saveBoard(boardDir, state)` stamps `updated` with the current ISO timestamp and writes the JSON file (creates dirs if needed). [E] mpga-plugin/cli/src/board/board.ts:32-36
- `createEmptyBoard()` returns a v1.0.0 `BoardState` with six empty columns (`backlog`, `todo`, `in-progress`, `testing`, `review`, `done`), zeroed stats, and default WIP limits (`in-progress: 3`, `testing: 3`, `review: 2`). [E] mpga-plugin/cli/src/board/board.ts:38-56
- `recalcStats(board, tasksDir)` calls `loadAllTasks` and recomputes totals, done count, in-flight (in-progress + testing + review), blocked count, evidence counts, and `progress_pct`; also rebuilds the `columns` map from disk truth. [E] mpga-plugin/cli/src/board/board.ts:58-94
- `addTask(board, tasksDir, options)` allocates the next sequential ID (e.g. `T001`), creates a `Task` object with sensible defaults, writes the task file via `renderTaskFile`, and appends the ID to the target column. [E] mpga-plugin/cli/src/board/board.ts:108-150
- `moveTask(board, tasksDir, taskId, toColumn, force)` checks WIP limits (unless `force`), parses the task file, removes the ID from the old column, appends to the new column, updates `task.column` and `task.updated`, rewrites the file. Returns `{ success, error? }`. [E] mpga-plugin/cli/src/board/board.ts:152-186
- `findTaskFile(tasksDir, taskId)` scans the tasks directory for a file whose name starts with `<taskId>-` or `<taskId>.`. [E] mpga-plugin/cli/src/board/board.ts:188-194

**task.ts — Task model and file I/O**

- `Task` interface captures id, title, column, status, priority, milestone, phase, created/updated timestamps, assigned agent, depends\_on/blocks arrays, scopes, tdd\_stage, evidence arrays, tags, time\_estimate, and body. [E] mpga-plugin/cli/src/board/task.ts:10-30
- `taskFilename(id, title)` slugifies the title (lowercase, non-alphanumeric → `-`, max 40 chars) and returns `<id>-<slug>.md`. [E] mpga-plugin/cli/src/board/task.ts:32-39
- `renderTaskFile(task)` serialises the task as YAML frontmatter + Markdown body. Arrays render as `[...]`; null values stay `null`. [E] mpga-plugin/cli/src/board/task.ts:41-99
- `parseTaskFile(filepath)` reads a file with `gray-matter`, remaps `status: "active"` back to `null`, and fills missing fields with safe defaults. Returns `null` on parse error or missing file. [E] mpga-plugin/cli/src/board/task.ts:101-130
- `loadAllTasks(tasksDir)` reads all `.md` files in the tasks directory, parses each, and filters out nulls. [E] mpga-plugin/cli/src/board/task.ts:132-139

**board-md.ts — Markdown rendering**

- `renderBoardMd(board, tasksDir)` groups all tasks by column and renders a Markdown document with: milestone title, progress bar (done/total), evidence bar (produced/expected), health line (blocked count), then per-column sections (`In progress`, `Testing`, `Review`, `Todo`, `Backlog`, `Done`). Only non-empty columns emit a section. [E] mpga-plugin/cli/src/board/board-md.ts:29-154

## Rules and edge cases

**WIP limits:** `moveTask` checks `checkWipLimit` before allowing a move into `in-progress` (max 3), `testing` (max 3), or `review` (max 2). If the limit is reached the function returns `{ success: false, error: "WIP limit reached…" }`. The `--force` flag bypasses this check entirely. [E] mpga-plugin/cli/src/board/board.ts:96-100, 159-165

**Missing task file:** `moveTask` and all `commands/board.ts` subcommands call `findTaskFile`; if it returns `null`, the operation is aborted with a descriptive error message and the process exits with code 1. [E] mpga-plugin/cli/src/board/board.ts:168 [E] mpga-plugin/cli/src/commands/board.ts:127-130

**Parse failure:** `parseTaskFile` catches all exceptions and returns `null`. Callers in `commands/board.ts` check for `null` and exit with an error message. [E] mpga-plugin/cli/src/board/task.ts:127-129 [E] mpga-plugin/cli/src/commands/board.ts:133-136

**Missing board.json:** `loadBoard` returns `createEmptyBoard()` when no `board.json` exists — the system self-heals rather than crashing. [E] mpga-plugin/cli/src/board/board.ts:26-28

**Missing tasks directory:** `loadAllTasks` returns `[]` immediately when the directory does not exist; `findTaskFile` also returns `null` early. [E] mpga-plugin/cli/src/board/task.ts:133 [E] mpga-plugin/cli/src/board/board.ts:189

**stats.status = "active" sentinel:** `parseTaskFile` remaps the YAML value `"active"` to `null` to preserve the `TaskStatus` type union (`blocked | stale | rework | paused | null`). [E] mpga-plugin/cli/src/board/task.ts:110

**Column rebuild on recalcStats:** `recalcStats` rebuilds `board.columns` entirely from disk — in-memory column arrays diverged from file state are corrected automatically. [E] mpga-plugin/cli/src/board/board.ts:79-93

**Archive destination:** `board archive` moves done tasks to `MPGA/milestones/<milestone>/tasks/` when a milestone is set, or `MPGA/milestones/_archived-tasks/` otherwise. [E] mpga-plugin/cli/src/commands/board.ts:374-376

## Concrete examples

**Adding a task:**
`mpga board add "Add login page" --priority high --scope auth --column todo`
→ `addTask` allocates `T001`, writes `MPGA/board/tasks/T001-add-login-page.md`, appends `T001` to `board.columns.todo`, saves `board.json`, rewrites `BOARD.md`. [E] mpga-plugin/cli/src/commands/board.ts:61-86

**Moving a task (WIP limit hit):**
`mpga board move T001 in-progress`
→ `moveTask` checks `checkWipLimit`; if `in-progress` already has 3 tasks it returns `{ success: false, error: "WIP limit reached…" }` and the command exits 1. Pass `--force` to override. [E] mpga-plugin/cli/src/board/board.ts:159-165

**Claiming a task:**
`mpga board claim T002 --agent red-dev`
→ `findTaskFile` locates the `.md` file, parses it, sets `assigned = "red-dev"` and `column = "in-progress"`, rewrites the file, recalcs stats, saves board, rewrites `BOARD.md`. [E] mpga-plugin/cli/src/commands/board.ts:113-152

**Recording evidence:**
`mpga board update T003 --evidence-add "[E] src/auth.ts:42"`
→ appends the string to `task.evidence_produced`, rewrites the file, recalcs stats (evidence counts update), saves board. [E] mpga-plugin/cli/src/commands/board.ts:208

**Board show (Markdown):**
`mpga board show`
→ loads board, recalcs stats, calls `renderBoardMd`, prints to stdout. With `--json` prints `{ board, tasks }` as JSON. [E] mpga-plugin/cli/src/commands/board.ts:33-49

**Archiving done tasks:**
`mpga board archive`
→ moves all files in `done` column to `MPGA/milestones/<milestone>/tasks/`, clears `board.columns.done`, recalcs stats. [E] mpga-plugin/cli/src/commands/board.ts:357-395

## UI

No browser UI. The board renders as terminal Markdown via `renderBoardMd`. Sections emitted (only when non-empty):

- **Header:** `# Board: <milestone>` (or "No active milestone")
- **Progress bar:** done/total task count
- **Evidence bar:** produced/expected evidence links
- **Health line:** blocked task count or "No blocked tasks"
- **In progress** table: ID, title+status icon, assigned agent, TDD stage icon, priority icon
- **Testing** table: same columns as In progress
- **Review** table: ID, title, agent, evidence ratio, priority
- **Todo** table: ID, title, depends_on, priority
- **Backlog** list: simple `- ID: title` lines
- **Done** table: ID, title, evidence link count, completion date

[E] mpga-plugin/cli/src/board/board-md.ts:44-153

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

**Contract with `core`:** imports `progressBar` from `core/logger.ts` for rendering evidence and progress bars in `renderBoardMd`. [E] mpga-plugin/cli/src/board/board-md.ts:3

**Contract with `commands`:** exports `loadBoard`, `saveBoard`, `recalcStats`, `addTask`, `moveTask`, `findTaskFile` (from `board.ts`), `parseTaskFile`, `renderTaskFile`, `loadAllTasks`, `Column`, `Priority` (from `task.ts`), and `renderBoardMd` (from `board-md.ts`). All mutation commands in `commands/board.ts` follow the pattern: load → mutate → recalcStats → saveBoard → write BOARD.md. [E] mpga-plugin/cli/src/commands/board.ts:6-15

## Diagram

```mermaid
graph LR
    board --> core
    commands --> board
```

## Traces

**Trace: `mpga board add "Fix login" --priority high --column todo`**

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | commands | `registerBoard` action fires; calls `findProjectRoot()`, derives `boardDir` and `tasksDir` | [E] mpga-plugin/cli/src/commands/board.ts:61-65 |
| 2 | board | `loadBoard(boardDir)` reads `board.json` (or returns empty board) | [E] mpga-plugin/cli/src/board/board.ts:24-30 |
| 3 | board | `addTask(board, tasksDir, { title, column, priority, … })` calls `nextTaskId` → `T001` | [E] mpga-plugin/cli/src/board/board.ts:108-121 |
| 4 | task | `taskFilename("T001", "Fix login")` returns `T001-fix-login.md` | [E] mpga-plugin/cli/src/board/task.ts:32-39 |
| 5 | task | `renderTaskFile(task)` serialises YAML frontmatter + template body | [E] mpga-plugin/cli/src/board/task.ts:41-99 |
| 6 | board | File written to `MPGA/board/tasks/T001-fix-login.md`; `T001` appended to `board.columns.todo` | [E] mpga-plugin/cli/src/board/board.ts:143-149 |
| 7 | board | `recalcStats(board, tasksDir)` reloads all tasks from disk, recomputes stats and columns | [E] mpga-plugin/cli/src/board/board.ts:58-94 |
| 8 | board | `saveBoard(boardDir, board)` stamps `updated`, writes `board.json` | [E] mpga-plugin/cli/src/board/board.ts:32-36 |
| 9 | board-md | `renderBoardMd(board, tasksDir)` groups tasks by column, emits Markdown sections | [E] mpga-plugin/cli/src/board/board-md.ts:29-154 |
| 10 | commands | Writes output to `MPGA/board/BOARD.md`; logs success message | [E] mpga-plugin/cli/src/commands/board.ts:82-85 |

## Evidence index

| Claim | Evidence |
|-------|----------|
| `renderBoardMd` (function) | [E] mpga-plugin/cli/src/board/board-md.ts:29-153 :: renderBoardMd()|
| `BoardState` (interface) | [E] mpga-plugin/cli/src/board/board.ts:5-21 :: BoardState()|
| `loadBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts:24-29 :: loadBoard()|
| `saveBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts:32-35 :: saveBoard()|
| `createEmptyBoard` (function) | [E] mpga-plugin/cli/src/board/board.ts:38-55 :: createEmptyBoard()|
| `recalcStats` (function) | [E] mpga-plugin/cli/src/board/board.ts:58-93 :: recalcStats()|
| `checkWipLimit` (function) | [E] mpga-plugin/cli/src/board/board.ts:96-99 :: checkWipLimit()|
| `nextTaskId` (function) | [E] mpga-plugin/cli/src/board/board.ts:102-105 :: nextTaskId()|
| `addTask` (function) | [E] mpga-plugin/cli/src/board/board.ts:108-119 :: addTask()|
| `moveTask` (function) | [E] mpga-plugin/cli/src/board/board.ts:152-157 :: moveTask()|
| `findTaskFile` (function) | [E] mpga-plugin/cli/src/board/board.ts:188-193 :: findTaskFile()|
| `Column` (type) | [E] mpga-plugin/cli/src/board/task.ts:5-6 :: Column()|
| `Priority` (type) | [E] mpga-plugin/cli/src/board/task.ts:6-7 :: Priority()|
| `TddStage` (type) | [E] mpga-plugin/cli/src/board/task.ts:7-9 :: TddStage()|
| `TaskStatus` (type) | [E] mpga-plugin/cli/src/board/task.ts:10-29 :: Task()Status()|
| `Task` (interface) | [E] mpga-plugin/cli/src/board/task.ts :: Task |
| `taskFilename` (function) | [E] mpga-plugin/cli/src/board/task.ts:32-38 :: taskFilename()|
| `renderTaskFile` (function) | [E] mpga-plugin/cli/src/board/task.ts:41-66 :: renderTaskFile()|
| `parseTaskFile` (function) | [E] mpga-plugin/cli/src/board/task.ts:101-129 :: parseTaskFile()|
| `loadAllTasks` (function) | [E] mpga-plugin/cli/src/board/task.ts:132-138 :: loadAllTasks()|

## Files

- `mpga-plugin/cli/src/board/board-md.test.ts` (51 lines, typescript)
- `mpga-plugin/cli/src/board/board-md.ts` (155 lines, typescript)
- `mpga-plugin/cli/src/board/board.test.ts` (79 lines, typescript)
- `mpga-plugin/cli/src/board/board.ts` (195 lines, typescript)
- `mpga-plugin/cli/src/board/task.test.ts` (84 lines, typescript)
- `mpga-plugin/cli/src/board/task.ts` (140 lines, typescript)

## Deeper splits

At 6 files / 704 lines the scope is well-sized. Natural split points if it grows: `board-state` (board.ts mutations only) vs `board-render` (board-md.ts) vs `task-model` (task.ts). Not needed yet.

## Confidence and notes

- **Confidence:** HIGH — all sections verified against source files.
- **Evidence coverage:** 20/20 verified
- **Last verified:** 2026-03-24
- **Drift risk:** unknown
- `avg_task_time` field exists in `BoardState` stats but is never populated by `recalcStats` — always `undefined`. [E] mpga-plugin/cli/src/board/board.ts:18
- `Task.phase` field is declared but not used by any board logic today — likely reserved for future milestone phasing. [E] mpga-plugin/cli/src/board/task.ts:17
- `board claim` does not call `checkWipLimit` before moving to `in-progress`, unlike `moveTask`. Potential WIP overflow risk. [E] mpga-plugin/cli/src/commands/board.ts:113-152

## Change history

- 2026-03-24: Initial scope generation via `mpga sync` — Making this scope GREAT!