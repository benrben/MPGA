# Project: MPGA

## Identity
- **Type:** TypeScript
- **Size:** ~11,017 lines across 61 files
- **Languages:** typescript (96%), javascript (3%), shell (1%)
- **Last sync:** 2026-03-24T12:59:43.941Z
- **Evidence coverage:** 100% (target: 80%)

## Key files
| File | Role | Evidence |
|------|------|----------|
| mpga-plugin/cli/src/commands/init.test.ts | Tests init, config, status, and health CLI commands. | [E] mpga-plugin/cli/src/commands/init.test.ts:1-50 |
| mpga-plugin/cli/src/commands/board-evidence-drift.test.ts | Tests board CRUD, evidence verify/add, and drift detection commands. | [E] mpga-plugin/cli/src/commands/board-evidence-drift.test.ts:1-50 |
| mpga-plugin/cli/src/generators/scope-md.ts | Builds per-scope markdown from scan + graph (symbols, files, evidence table). | [E] mpga-plugin/cli/src/generators/scope-md.ts:1-50 |
| mpga-plugin/cli/src/evidence/ast.test.ts | Tests language detection, symbol extraction, lookup, and range verification. | [E] mpga-plugin/cli/src/evidence/ast.test.ts:1-50 |
| mpga-plugin/cli/src/evidence/drift.test.ts | Tests drift checking and scope file healing against stale evidence links. | [E] mpga-plugin/cli/src/evidence/drift.test.ts:1-50 |
| mpga-plugin/cli/src/commands/session-export.test.ts | Tests session handoff/log/resume/budget and export --claude commands. | [E] mpga-plugin/cli/src/commands/session-export.test.ts:1-50 |
| mpga-plugin/cli/src/commands/board.ts | Board CLI: columns, tasks, `board show`, moves, Markdown board view. | [E] mpga-plugin/cli/src/commands/board.ts:1-50 |
| mpga-plugin/cli/src/core/scanner.test.ts | Tests language detection, line counting, scan, and project type detection. | [E] mpga-plugin/cli/src/core/scanner.test.ts:1-50 |
| mpga-plugin/cli/src/commands/scan-sync-graph-scope.test.ts | Tests scan, sync, graph show, and scope add/remove/list commands. | [E] mpga-plugin/cli/src/commands/scan-sync-graph-scope.test.ts:1-50 |
| mpga-plugin/cli/src/commands/export/antigravity.ts | Exports MPGA context to Gemini/Antigravity rules, skills, and GEMINI.md. | [E] mpga-plugin/cli/src/commands/export/antigravity.ts:1-50 |

## Conventions
- Read `MPGA/INDEX.md` before substantive work; cite `[E] path:lines` when stating how code behaves.
- The MPGA CLI package lives in `mpga-plugin/cli` (ESM TypeScript, `.js` import specifiers); build with `npm run build` there so `dist/` matches source.
- Generated knowledge output is under repo-root `MPGA/`; `project.ignore` includes `MPGA/` so scans do not recurse into the layer.
- Prefer extending existing Commander commands and generators (`sync`, `export`, `evidence`, `drift`) over parallel scripts.
- Vitest tests live under `mpga-plugin/cli/src/**`; run `npm run check` in `mpga-plugin/cli` before shipping CLI changes.

## Agent trigger table
| Task pattern | Agent | Scopes to load |
|-------------|-------|-----------------|
| "add/modify authentication" | red-dev → green-dev → blue-dev | auth, database |
| "explore how X works" | scout | (auto-detect) |
| "plan feature X" | researcher → architect | (auto-detect) |
| "fix bug in X" | scout → red-dev → green-dev | (auto-detect) |
| "refactor X" | architect → blue-dev | (auto-detect) |

## Scope registry
| Scope | Status | Evidence links | Last verified |
|-------|--------|---------------|---------------|
| mpga-plugin | ✓ fresh | 0/1 | 2026-03-24 |
| commands | ✓ fresh | 0/31 | 2026-03-24 |
| board | ✓ fresh | 0/20 | 2026-03-24 |
| core | ✓ fresh | 0/24 | 2026-03-24 |
| evidence | ✓ fresh | 0/49 | 2026-03-24 |
| generators | ✓ fresh | 0/25 | 2026-03-24 |

## Active milestone
- (none)

## Known unknowns
- [ ] (run `mpga evidence verify` to detect unknowns)
