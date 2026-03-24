# Project: MPGA

## Identity
- **Type:** TypeScript
- **Size:** ~6,540 lines across 41 files
- **Languages:** typescript (99%), shell (1%), javascript (0%)
- **Last sync:** 2026-03-24T00:21:46.892Z
- **Evidence coverage:** 0% (target: 80%)

## Key files
| File | Role | Evidence |
|------|------|----------|
| mpga-plugin/cli/src/commands/export.ts | Multi-target export (Claude, Cursor, Codex, Gemini, Antigravity): agents, skills, rules, AGENTS.md. | [E] mpga-plugin/cli/src/commands/export.ts:1-50 |
| mpga-plugin/cli/src/generators/scope-md.ts | Builds per-scope markdown from scan + graph (symbols, files, evidence table). | [E] mpga-plugin/cli/src/generators/scope-md.ts:1-50 |
| mpga-plugin/cli/src/commands/board.ts | Board CLI: columns, tasks, `board show`, moves, Markdown board view. | [E] mpga-plugin/cli/src/commands/board.ts:1-50 |
| mpga-plugin/cli/src/generators/scope-md.test.ts | (describe role) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:1-50 |
| mpga-plugin/cli/src/commands/milestone.ts | Milestone lifecycle under `MPGA/milestones` and board linkage. | [E] mpga-plugin/cli/src/commands/milestone.ts:1-50 |
| mpga-plugin/cli/src/commands/scope.ts | Scope subcommands: list, show, split suggestions, evidence stats. | [E] mpga-plugin/cli/src/commands/scope.ts:1-50 |
| mpga-plugin/cli/src/commands/session.ts | Session handoff and context export under `MPGA/sessions`. | [E] mpga-plugin/cli/src/commands/session.ts:1-50 |
| mpga-plugin/cli/src/core/config.ts | Loads `mpga.config.json`, defaults, deep merge, project root discovery. | [E] mpga-plugin/cli/src/core/config.ts:1-50 |
| mpga-plugin/cli/src/board/board.ts | Board JSON state: load/save, columns, stats, task IDs. | [E] mpga-plugin/cli/src/board/board.ts:1-50 |
| mpga-plugin/cli/src/commands/init.ts | Bootstraps `MPGA/` tree, templates for INDEX and GRAPH. | [E] mpga-plugin/cli/src/commands/init.ts:1-50 |

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
| board | ✓ fresh | 0/20 | 2026-03-24 |
| commands | ✓ fresh | 0/15 | 2026-03-24 |
| core | ✓ fresh | 0/22 | 2026-03-24 |
| evidence | ✓ fresh | 0/20 | 2026-03-24 |
| generators | ✓ fresh | 0/22 | 2026-03-24 |

## Active milestone
- (none)

## Known unknowns
- [ ] (run `mpga evidence verify` to detect unknowns)
