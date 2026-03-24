# Scope: src-commands

## Summary

The **commands** subsystem registers all 14 CLI commands via Commander.js. Each file exports a `register*` function that adds a command (with subcommands, options, and action handlers) to the program.

## Where to start in code

- [E] `src/commands/sync.ts` — the primary knowledge generation command
- [E] `src/commands/evidence.ts` — evidence verify/heal/coverage/add
- [E] `src/commands/board.ts` — the largest command with 11 subcommands

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
| `board show\|add\|move\|claim\|assign\|update\|block\|unblock\|deps\|stats\|archive` | Full kanban lifecycle |
| `milestone new\|list\|status\|complete` | Milestone lifecycle with `M001-slug/` directories |
| `session handoff\|resume\|log\|budget` | Context handoff between sessions |

### Reporting commands

| Command | What it does |
|---------|-------------|
| `status [--json]` | Knowledge layer + board + config dashboard |
| `health` | Letter grade (A-D) based on evidence + board health |
| `config show\|set` | Read/write `mpga.config.json` via dot-path keys |
| `export --claude\|--cursor\|--codex\|--antigravity` | Generate tool-specific config from MPGA knowledge |

## Rules and edge cases

- Every mutating board command follows: load → mutate → `recalcStats` → save → write BOARD.md
- `export` rewrites `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh` to `npx mpga` for non-Claude targets
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
| `registerBoard` (function) | [E] src/commands/board.ts:15-53 :: registerBoard()|
| `registerConfig` (function) | [E] src/commands/config.ts:7-58 :: registerConfig()|
| `registerDrift` (function) | [E] src/commands/drift.ts:8-105 :: registerDrift()|
| `registerEvidence` (function) | [E] src/commands/evidence.ts:11-149 :: registerEvidence()|
| `registerExport` (function) | [E] src/commands/export.ts:14-94 :: registerExport()|
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

- `src/commands/board.ts` (368 lines)
- `src/commands/export.ts` (1080 lines)
- `src/commands/scope.ts` (229 lines)
- `src/commands/milestone.ts` (215 lines)
- `src/commands/session.ts` (189 lines)
- `src/commands/init.ts` (185 lines)
- `src/commands/evidence.ts` (151 lines)
- `src/commands/health.ts` (129 lines)
- `src/commands/status.ts` (115 lines)
- `src/commands/drift.ts` (99 lines)
- `src/commands/sync.ts` (82 lines)
- `src/commands/scan.ts` (77 lines)
- `src/commands/config.ts` (74 lines)
- `src/commands/graph.ts` (67 lines)

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-22
- **Drift risk:** low
- `export.ts` at 1080 lines is the largest file — may warrant its own sub-scope if it grows further

## Change history

- 2026-03-22: Created as sub-scope split from src
