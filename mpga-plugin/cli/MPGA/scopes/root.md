# Scope: root

## Summary

The **root** scope contains the Vitest configuration file (`vitest.config.ts`) that governs how the project's test suite is discovered, executed, and measured for coverage. It defines the test environment, file inclusion patterns, coverage provider, thresholds, and reporters [E] `vitest.config.ts:1-18`.

## Where to start in code

- [E] `vitest.config.ts` — the sole file in this scope; a single `defineConfig` call

## Context / stack / skills

- **Languages:** TypeScript
- **Frameworks:** Vitest (test runner), V8 (coverage provider)

## Who and what triggers it

- **Developers** running `npm run test`, `npm run test:watch`, or `npm run test:coverage` [E] `package.json:42-44`.
- **CI pipelines** that execute the test suite.
- **Vitest** automatically loads `vitest.config.ts` from the project root when invoked.

## What happens

Vitest reads `vitest.config.ts` and applies the following configuration:

1. **Globals enabled** — test utilities (`describe`, `it`, `expect`) are available without explicit imports [E] `vitest.config.ts:5`.
2. **Node environment** — tests run in a Node.js context (not jsdom or edge) [E] `vitest.config.ts:6`.
3. **Test discovery** — only files matching `src/**/*.test.ts` are included [E] `vitest.config.ts:7`.
4. **Coverage provider** — uses V8 for native code-coverage instrumentation [E] `vitest.config.ts:9`.
5. **Coverage inclusion** — all `src/**/*.ts` files are measured [E] `vitest.config.ts:10`.
6. **Coverage exclusions** — test files (`src/**/*.test.ts`) and the barrel export (`src/index.ts`) are excluded from coverage metrics [E] `vitest.config.ts:11`.
7. **Coverage reporters** — `text` (terminal table) and `lcov` (for CI/HTML reports) [E] `vitest.config.ts:12`.
8. **Coverage threshold** — a minimum of 50% line coverage is enforced; the build fails if coverage drops below this [E] `vitest.config.ts:13-15`.

## Rules and edge cases

- **Threshold enforcement:** The 50% line-coverage threshold means any new code that significantly reduces coverage will cause `vitest run --coverage` to fail [E] `vitest.config.ts:14`.
- **Index exclusion:** `src/index.ts` is explicitly excluded from coverage because it is a thin bootstrap file (4 lines) that simply wires up the CLI [E] `vitest.config.ts:11`, `src/index.ts:1-4`.
- **No branch/function thresholds:** Only `lines` is configured under `thresholds`; branch and function coverage are not gated [E] `vitest.config.ts:13-15`.
- **Test file pattern:** Only `*.test.ts` files inside `src/` are picked up. Tests placed elsewhere (e.g., a top-level `__tests__/` directory) would be ignored.

## Concrete examples

- Running `npm run test` executes `vitest run`, which loads this config, discovers all `src/**/*.test.ts` files, and runs them in a Node environment with global test APIs.
- Running `npm run test:coverage` additionally collects V8-based coverage, prints a text summary, writes an `lcov` report, and asserts >= 50% line coverage.

## UI

N/A — this is a configuration file with no user-facing interface.

## Navigation

**Sibling scopes:**

- [bin](./bin.md)
- [src](./src.md)
- [board](./board.md)
- [commands](./commands.md)
- [core](./core.md)
- [generators](./generators.md)
- [evidence](./evidence.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

- **Configures testing for [src](./src.md):** The `include` pattern `src/**/*.test.ts` means every test file in the src scope is governed by this config [E] `vitest.config.ts:7`.
- **Coverage measures [src](./src.md):** The coverage `include` pattern `src/**/*.ts` instruments all source files in the src scope [E] `vitest.config.ts:10`.
- **Depends on Vitest** (`devDependencies`): `vitest` ^2.0.0 and `@vitest/coverage-v8` ^2.0.0 [E] `package.json:65-66`, `package.json:69`.

## Diagram

```
┌────────────────────┐
│  npm run test      │
│  npm run test:cov  │
└────────┬───────────┘
         │ invokes
         ▼
┌────────────────────┐      reads       ┌──────────────────────┐
│  vitest            │ ───────────────► │  vitest.config.ts    │
│  (test runner)     │                  │  (this scope)        │
└────────┬───────────┘                  └──────────────────────┘
         │ discovers & runs
         ▼
┌────────────────────┐
│  src/**/*.test.ts  │
│  (test files)      │
└────────────────────┘
```

## Traces

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | npm | User runs `npm run test` or `npm run test:coverage` | [E] `package.json:42-44` |
| 2 | Vitest | Vitest loads `vitest.config.ts` from the project root | [E] `vitest.config.ts:1` |
| 3 | Vitest | `defineConfig` applies test settings: globals, node env, include pattern | [E] `vitest.config.ts:4-7` |
| 4 | Vitest | Test files matching `src/**/*.test.ts` are discovered and executed | [E] `vitest.config.ts:7` |
| 5 | V8 | If coverage is requested, V8 provider instruments `src/**/*.ts` (excluding tests and index) | [E] `vitest.config.ts:9-11` |
| 6 | Vitest | Coverage reporters (`text`, `lcov`) generate output | [E] `vitest.config.ts:12` |
| 7 | Vitest | Line coverage threshold (50%) is asserted; run fails if not met | [E] `vitest.config.ts:13-15` |

## Evidence index

| Tag | File | Line(s) | Description |
|-----|------|---------|-------------|
| [E] | `vitest.config.ts` | 1 | `import { defineConfig } from 'vitest/config'` |
| [E] | `vitest.config.ts` | 1-18 | Full configuration object |
| [E] | `vitest.config.ts` | 5 | `globals: true` — global test APIs |
| [E] | `vitest.config.ts` | 6 | `environment: 'node'` |
| [E] | `vitest.config.ts` | 7 | `include: ['src/**/*.test.ts']` |
| [E] | `vitest.config.ts` | 9 | `provider: 'v8'` — coverage provider |
| [E] | `vitest.config.ts` | 10 | `include: ['src/**/*.ts']` — coverage scope |
| [E] | `vitest.config.ts` | 11 | `exclude: ['src/**/*.test.ts', 'src/index.ts']` — coverage exclusions |
| [E] | `vitest.config.ts` | 12 | `reporter: ['text', 'lcov']` — coverage output formats |
| [E] | `vitest.config.ts` | 13-15 | `thresholds: { lines: 50 }` — minimum coverage gate |
| [E] | `package.json` | 42-44 | npm scripts: `test`, `test:watch`, `test:coverage` |
| [E] | `package.json` | 65-66, 69 | Vitest and coverage-v8 dev dependencies |
| [E] | `src/index.ts` | 1-4 | Thin bootstrap excluded from coverage |

## Files

- `vitest.config.ts` (19 lines, typescript)

## Deeper splits

Not applicable. This scope contains a single configuration file with no internal complexity warranting further decomposition.

## Confidence and notes

- **Confidence:** HIGH — the configuration is straightforward and fully documented above.
- **Evidence coverage:** 13/13 verified
- **Last verified:** 2026-03-24
- **Drift risk:** Low. Changes would occur only if test infrastructure or coverage requirements are modified.

## Change history

- 2026-03-24: Initial scope generation via `mpga sync`
- 2026-03-24: Evidence-backed content added by scout agent
