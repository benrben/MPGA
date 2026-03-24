# Project: cli

## Identity
- **Type:** TypeScript CLI (Commander.js)
- **Size:** ~6,459 lines across 37 files
- **Languages:** typescript (100%), javascript (0%)
- **Last sync:** 2026-03-24
- **Evidence coverage:** HIGH — all 8 scope documents enriched with evidence links (2026-03-24)

## Key files
| File | Role | Evidence |
|------|------|----------|
| src/commands/export.ts | Multi-tool config generator (Claude, Cursor, Codex, Antigravity) — largest file | [E] src/commands/export.ts:276-525 |
| src/generators/scope-md.ts | Scope document generator with export extraction, framework detection, JSDoc parsing | [E] src/generators/scope-md.ts:264-383 |
| src/commands/board.ts | Kanban board CLI — 11 subcommands for full task lifecycle | [E] src/commands/board.ts:24-398 |
| src/generators/scope-md.test.ts | Test suite for scope generation (extractModuleSummary, detectFrameworks, annotations) | [E] src/generators/scope-md.test.ts:1-242 |
| src/commands/milestone.ts | Milestone lifecycle: new, list, status, complete | [E] src/commands/milestone.ts:50-225 |
| src/commands/scope.ts | Scope CRUD + keyword-frequency query | [E] src/commands/scope.ts:12-223 |
| src/commands/session.ts | Context handoff, resume, log, and token budget estimation | [E] src/commands/session.ts:13-195 |
| src/core/config.ts | Configuration authority: MpgaConfig (9 sections), load/save, dot-path get/set | [E] src/core/config.ts:12-71 |
| src/board/board.ts | Board state management: load/save, task CRUD, WIP limits, stat reconciliation | [E] src/board/board.ts:5-194 |
| src/commands/init.ts | MPGA bootstrap: creates directory structure, config, and initial knowledge layer | [E] src/commands/init.ts:67-194 |

## Conventions
- Every command file exports exactly one `register*(program: Command): void` function [E] src/cli.ts:48-69
- All imports use `.js` extension suffix (ESM-compatible TypeScript) [E] src/cli.ts:4-17
- Every mutating board command follows: load → mutate → `recalcStats()` → save → rewrite BOARD.md [E] src/commands/board.ts:78-82
- TDD enforced: tests before implementation
- Evidence links use format `[E] filepath:lines :: symbol` — all claims about code must cite evidence

## Agent trigger table
| Task pattern | Agent | Scopes to load |
|-------------|-------|-----------------|
| "explore how X works" | scout | (auto-detect from task) |
| "plan feature X" | researcher → architect | (auto-detect from task) |
| "fix bug in X" | scout → red-dev → green-dev | (auto-detect from task) |
| "refactor X" | architect → blue-dev | (auto-detect from task) |
| "add new CLI command" | red-dev → green-dev → blue-dev | commands, core |
| "improve evidence system" | scout → red-dev → green-dev | evidence, commands |

## Scope registry
| Scope | Status | Evidence links | Last verified | Confidence |
|-------|--------|---------------|---------------|------------|
| root | enriched | 13/13 | 2026-03-24 | HIGH |
| bin | enriched | 7/7 | 2026-03-24 | HIGH |
| src | enriched | 12/12 | 2026-03-24 | HIGH |
| board | enriched | 30/30 | 2026-03-24 | HIGH |
| commands | enriched | 30/30 | 2026-03-24 | HIGH |
| core | enriched | 30/30 | 2026-03-24 | HIGH |
| generators | enriched | 26/26 | 2026-03-24 | HIGH |
| evidence | enriched | 38/38 | 2026-03-24 | HIGH |

## Dependency graph summary
```
bin → src → core, commands
commands → core, board, evidence, generators
board → core
generators → core
evidence (standalone — no intra-project imports)
```
See [GRAPH.md](./GRAPH.md) for full Mermaid diagram.

## Active milestone
- (none)

## Known unknowns
- [ ] `board stats --velocity` and `--burndown` options are registered but not implemented [E] src/commands/board.ts:327-328
- [ ] `scope list` always shows `? unknown` for health — `renderScopeMd` never writes a `**Health:**` field [E] src/generators/scope-md.ts:385-593
- [ ] `milestone complete` does not clear `board.milestone`, leaving a stale link [E] src/commands/milestone.ts:200-222
- [ ] `evidenceCoverage` is always passed as `0` during `mpga sync` — never computed [E] src/commands/sync.ts:73
- [ ] `scan(root, ignore, deep)` — the `deep` parameter is a no-op stub [E] src/core/scanner.ts:79-81
- [ ] Orphan detection in `graph-md.ts` uses `path.basename` instead of module names — produces incorrect results [E] src/generators/graph-md.ts:124-127
- [ ] No tests exist for `board.ts` or `board-md.ts` — only `task.test.ts` covers the board module
