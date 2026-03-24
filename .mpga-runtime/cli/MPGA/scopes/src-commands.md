# Scope: src-commands

## Summary

The **commands** subsystem now registers 15 CLI commands via Commander.js, including the new `develop` workflow entry point [E] `src/cli.ts:20-74` :: createCli().

It also gained a live board subcommand for file-backed HTML board generation plus an optional local Node HTTP server/open flow [E] `src/commands/board.ts:23-32` :: registerBoard().

The new scheduler module handles file-group lane planning, lock checks, and persisted lane transitions [E] `src/commands/develop-scheduler.ts:43-177` :: splitIntoFileGroups()/persistLaneTransition()/runDevelopTask().

The export pipeline now has a shared runtime bundler that vendors `.mpga-runtime/` for all tool exports and points generated skills/agents at the vendored Node entrypoint [E] `src/commands/export/runtime.ts:22-58` :: projectVendoredCliCommand()/globalVendoredCliCommand()/copyVendoredRuntime() [E] `src/commands/export/agents.ts:139-240` :: rewriteCliReferences()/copySkillsTo().

## Where to start in code

- [E] `src/commands/board.ts` — board command registration, now including `board live`
- [E] `src/commands/board-handlers.ts` — file-backed board mutations and live artifact generation
- [E] `src/commands/develop.ts` — `mpga develop <task-id>` command surface
- [E] `src/commands/develop-scheduler.ts` — lane splitting, file-lock checks, and persisted scheduler transitions
- [E] `src/commands/export/runtime.ts` — vendored runtime bundle writer used by all exporters

## Context / stack / skills

- **Languages:** TypeScript
- **Framework:** Commander.js

## Who and what triggers it

Users run `mpga <command>` from terminal. Each command is registered in `cli.ts` during bootstrap.

## What happens

### Knowledge generation commands

| Command | What it does |
|---------|-------------|
| `init [--from-zero\|--from-existing]` | Creates `MPGA/` directory structure + config. `--from-existing` auto-detects languages |
| `sync [--full\|--incremental]` | Scan → graph → scopes → INDEX.md. `--incremental` skips existing scope files |
| `scan` | Standalone file discovery + language detection |
| `graph` | Builds and renders module dependency graph as Mermaid |
| `scope list\|show\|add\|remove\|query` | Scope CRUD + keyword frequency search |

### Evidence commands

| Command | What it does |
|---------|-------------|
| `evidence verify` | Resolves all evidence links, reports health % |
| `evidence heal` | Auto-fixes drifted line ranges |
| `evidence coverage --min N` | Exits 1 if coverage below threshold |
| `evidence add <scope> <link>` | Inserts link before `## Known unknowns` |
| `drift --report\|--quick\|--ci\|--fix` | Drift checking with CI gate support |

### Task management commands

| Command | What it does |
|---------|-------------|
| `board show\|live\|add\|move\|claim\|assign\|update\|block\|unblock\|deps\|stats\|archive` | Full kanban lifecycle plus live HTML board generation |
| `develop <task-id> [--parallel --lanes --dashboard]` | File-group lane scheduling and persisted task/lock transitions |
| `milestone new\|list\|status\|complete` | Milestone lifecycle with `M001-slug/` directories |
| `session handoff\|resume\|log\|budget` | Context handoff between sessions |

### Reporting commands

| Command | What it does |
|---------|-------------|
| `status [--json]` | Knowledge layer + board + config dashboard |
| `health` | Letter grade (A-D) based on evidence + board health |
| `config show\|set` | Read/write `mpga.config.json` via dot-path keys |
| `export --claude\|--cursor\|--codex\|--antigravity` | Generate tool-specific config from MPGA knowledge and vendor `.mpga-runtime/` by default |

## Rules and edge cases

- Every mutating board command follows: load → mutate → `recalcStats` → save → write BOARD.md
- `board live` regenerates `BOARD.md`, `snapshot.json`, and `index.html` from the same file-backed board state and can optionally serve that directory through a local Node HTTP server on `127.0.0.1` [E] `src/commands/board-handlers.ts:39-62` :: handleBoardLive()
- `develop-scheduler` merges overlapping file groups into one lane before scheduling [E] `src/commands/develop-scheduler.ts:19-53` :: mergeFileGroups()/splitIntoFileGroups()
- `develop-scheduler` rejects active same-file lock conflicts before claiming new files [E] `src/commands/develop-scheduler.ts:55-64` :: canAcquireFileLocks()
- Exporters now prefer vendored runtime paths like `node ./.mpga-runtime/cli/dist/index.js` when plugin assets are available, while still falling back to `npx mpga` when they are not [E] `src/commands/export/runtime.ts:22-58` :: projectVendoredCliCommand()/globalVendoredCliCommand()/copyVendoredRuntime()
- `scope list` reads `**Health:**` field from content but sync never writes it → always `? unknown`
- `milestone complete` writes SUMMARY.md but doesn't clear `board.milestone`
- `board stats --velocity` and `--burndown` flags are registered but not implemented
- `scope query` is pure keyword frequency (no semantic search)
- `session budget` estimates tokens at 4 tokens/line of 200K context window

## Navigation

**Parent:** [src](./src.md)

**Depends on:** [src-core](./src-core.md), [src-evidence](./src-evidence.md), [src-board](./src-board.md), [src-generators](./src-generators.md)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `registerBoard` (function) | [E] src/commands/board.ts:23-90 :: registerBoard()|
| `persistBoard` (function) | [E] src/commands/board.ts:9-17 :: persistBoard()|
| `handleBoardLive` (function) | [E] src/commands/board-handlers.ts:39-62 :: handleBoardLive()|
| `registerDevelop` (function) | [E] src/commands/develop.ts:4-18 :: registerDevelop()|
| `splitIntoFileGroups` (function) | [E] src/commands/develop-scheduler.ts:43-53 :: splitIntoFileGroups()|
| `canAcquireFileLocks` (function) | [E] src/commands/develop-scheduler.ts:55-64 :: canAcquireFileLocks()|
| `persistLaneTransition` (function) | [E] src/commands/develop-scheduler.ts:66-141 :: persistLaneTransition()|
| `runDevelopTask` (function) | [E] src/commands/develop-scheduler.ts:143-177 :: runDevelopTask()|
| `registerConfig` (function) | [E] src/commands/config.ts:7-58 :: registerConfig()|
| `registerDrift` (function) | [E] src/commands/drift.ts:8-105 :: registerDrift()|
| `registerEvidence` (function) | [E] src/commands/evidence.ts:11-149 :: registerEvidence()|
| `registerExport` (function) | [E] src/commands/export.ts:14-94 :: registerExport()|
| `copyVendoredRuntime` (function) | [E] src/commands/export/runtime.ts:30-58 :: copyVendoredRuntime()|
| `registerGraph` (function) | [E] src/commands/graph.ts:9-65 :: registerGraph()|
| `registerHealth` (function) | [E] src/commands/health.ts:10-111 :: registerHealth()|
| `registerInit` (function) | [E] src/commands/init.ts:67-183 :: registerInit()|
| `registerMilestone` (function) | [E] src/commands/milestone.ts:91-120 :: registerMilestone()|
| `registerScan` (function) | [E] src/commands/scan.ts:6-74 :: registerScan()|
| `registerScope` (function) | [E] src/commands/scope.ts:208-233 :: registerScope()|
| `registerSession` (function) | [E] src/commands/session.ts:13-45 :: registerSession()|
| `registerStatus` (function) | [E] src/commands/status.ts:128-133 :: registerStatus()|
| `registerSync` (function) | [E] src/commands/sync.ts:11-80 :: registerSync()|

## Files

- `src/commands/board.ts`
- `src/commands/board-handlers.ts`
- `src/commands/develop.ts`
- `src/commands/develop-scheduler.ts`
- `src/commands/export.ts`
- `src/commands/export/runtime.ts`
- `src/commands/export/codex.ts`
- `src/commands/export/cursor.ts`
- `src/commands/export/claude.ts`
- `src/commands/export/antigravity.ts`
- `src/commands/export/runtime.test.ts`
- `src/commands/develop.test.ts`
- `src/commands/develop-scheduler.test.ts`

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-24
- **Drift risk:** low
- `export.ts` at 1080 lines is the largest file — may warrant its own sub-scope if it grows further

## Change history

- 2026-03-22: Created as sub-scope split from src
