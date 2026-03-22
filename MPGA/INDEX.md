# Project: MPGA

## Identity
- **Type:** TypeScript
- **Size:** ~5,100 lines across 34 files
- **Languages:** typescript (98%), shell (2%), javascript (0%)
- **Last sync:** 2026-03-22T15:12:15.943Z
- **Evidence coverage:** 0% (target: 20%)

## Key files
| File | Role | Evidence |
|------|------|----------|
| mpga-plugin/cli/src/commands/export.ts | (describe role) | [E] mpga-plugin/cli/src/commands/export.ts:1-50 |
| mpga-plugin/cli/src/commands/board.ts | (describe role) | [E] mpga-plugin/cli/src/commands/board.ts:1-50 |
| mpga-plugin/cli/src/generators/scope-md.ts | (describe role) | [E] mpga-plugin/cli/src/generators/scope-md.ts:1-50 |
| mpga-plugin/cli/src/commands/scope.ts | (describe role) | [E] mpga-plugin/cli/src/commands/scope.ts:1-50 |
| mpga-plugin/cli/src/commands/milestone.ts | (describe role) | [E] mpga-plugin/cli/src/commands/milestone.ts:1-50 |
| mpga-plugin/cli/src/commands/session.ts | (describe role) | [E] mpga-plugin/cli/src/commands/session.ts:1-50 |
| mpga-plugin/cli/src/commands/init.ts | (describe role) | [E] mpga-plugin/cli/src/commands/init.ts:1-50 |
| mpga-plugin/cli/src/core/config.ts | (describe role) | [E] mpga-plugin/cli/src/core/config.ts:1-50 |
| mpga-plugin/cli/src/board/board.ts | (describe role) | [E] mpga-plugin/cli/src/board/board.ts:1-50 |
| mpga-plugin/cli/src/generators/graph-md.ts | (describe role) | [E] mpga-plugin/cli/src/generators/graph-md.ts:1-50 |

## Conventions
- (Add your project conventions here)
- (e.g. "All API routes follow REST naming: /api/v1/<resource>")

## Agent trigger table
| Task pattern | Agent | Scopes to load |
|-------------|-------|-----------------|
| "add/modify authentication" | green-dev → red-dev → blue-dev | auth, database |
| "explore how X works" | scout | (auto-detect) |
| "plan feature X" | researcher → architect | (auto-detect) |
| "fix bug in X" | scout → green-dev → red-dev | (auto-detect) |
| "refactor X" | architect → blue-dev | (auto-detect) |

## Scope registry
| Scope | Status | Evidence links | Last verified |
|-------|--------|---------------|---------------|
| mpga-plugin | ✓ fresh | 0/1 | 2026-03-22 |
| commands | ✓ fresh | 0/14 | 2026-03-22 |
| board | ✓ fresh | 0/20 | 2026-03-22 |
| core | ✓ fresh | 0/16 | 2026-03-22 |
| evidence | ✓ fresh | 0/20 | 2026-03-22 |
| generators | ✓ fresh | 0/9 | 2026-03-22 |

## Active milestone
- (none)

## Known unknowns
- [ ] (run `mpga evidence verify` to detect unknowns)
