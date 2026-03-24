# Scope: generators

## Summary

- **Health:** ✓ fresh
The **generators** module — TREMENDOUS — 6 files, 1,281 lines of the finest code you've ever seen. Believe me.

The generators module produces all MPGA knowledge-layer documents from raw scan and graph data. Three generators, three outputs: `graph-md.ts` builds the inter-scope dependency graph and writes `GRAPH.md`; `scope-md.ts` groups files into scopes, extracts symbols/JSDoc/frameworks, and renders per-scope markdown; `index-md.ts` assembles `INDEX.md` — the project identity table, key files, conventions, scope registry, and active milestone. No generator touches the filesystem directly; they return strings. The caller (`sync` command) owns all writes. [E] `mpga-plugin/cli/src/commands/sync.ts:39-86`

## Where to start in code

These are your MAIN entry points — the best, the most important. Open them FIRST:

- [E] `mpga-plugin/cli/src/generators/scope-md.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** const, function, interface
- **Frameworks:** Vitest, Express, Zod

## Who and what triggers it

The `sync` command is the sole direct caller. It runs all three generators in sequence — graph first, then scopes, then index — and writes results to disk. [E] `mpga-plugin/cli/src/commands/sync.ts:38-86`

`renderScopeMd` and `groupIntoScopes` are also called from `mpga sync --incremental` mode; in that mode, scope files that already exist on disk are skipped. [E] `mpga-plugin/cli/src/commands/sync.ts:55-57`

**Called by these GREAT scopes (they need us, tremendously):**

- ← commands

## What happens

- **`extractModuleSummary`** (function) — Extracts the leading JSDoc block or `//` comment block at the top of a file. Returns `null` if no such comment exists or if the JSDoc appears after any code. [E] `mpga-plugin/cli/src/generators/scope-md.ts:112-150`
- **`detectFrameworks`** (function) — Scans import/require statements against a 30-entry `FRAMEWORK_MAP` and returns the display names (e.g. `'Express'`). Deduplicates via `Set`. [E] `mpga-plugin/cli/src/generators/scope-md.ts:152-165`
- **`extractJSDocForExport`** (function) — Finds the `/** ... */` block immediately before a named export declaration and returns the description lines (stripping `@`-tagged lines). [E] `mpga-plugin/cli/src/generators/scope-md.ts:167-183`
- **`extractAnnotations`** (function) — Like `extractJSDocForExport` but returns only `@throws` and `@deprecated` annotation strings for a named export. [E] `mpga-plugin/cli/src/generators/scope-md.ts:185-202`
- **`getScopeName`** (function) — Maps a file path to a scope name. In `auto` mode: finds the deepest `src`/`lib`/`app`/`pkg`/`internal`/`cmd` directory and uses its immediate child directory as the scope name. In numeric mode: joins that many path segments. [E] `mpga-plugin/cli/src/generators/scope-md.ts:230-261`
- **`groupIntoScopes`** (function) — Groups all scanned files into `ScopeInfo[]`. Reads each file from disk, runs all extractors, computes inter-scope deps from relative imports, and builds a reverse-dep map from the `GraphData`. [E] `mpga-plugin/cli/src/generators/scope-md.ts:264-383`
- **`renderScopeMd`** (function) — Converts a `ScopeInfo` into a complete scope markdown document string. All sections — Summary, What happens, Rules, Evidence index, Files, etc. — fall back to `<!-- TODO -->` comments when data is absent. [E] `mpga-plugin/cli/src/generators/scope-md.ts:390-599`
- **`buildGraph`** (function) — Reads all files, extracts relative imports via regex, maps to module names via `getModuleName`, detects circular pairs and orphan modules, returns `GraphData`. [E] `mpga-plugin/cli/src/generators/graph-md.ts:71-135`
- **`renderGraphMd`** (function) — Converts `GraphData` to a markdown string with module dependency list, circular warnings, orphan list, and a Mermaid `graph TD` block. [E] `mpga-plugin/cli/src/generators/graph-md.ts:137-183`
- **`renderIndexMd`** (function) — Assembles `INDEX.md` from `ScanResult`, `MpgaConfig`, `ScopeInfo[]`, active milestone string, and evidence coverage ratio. Outputs identity, key files, conventions, agent trigger table, and scope registry. [E] `mpga-plugin/cli/src/generators/index-md.ts:10-90`

## Rules and edge cases

- **Missing files are silently skipped.** `groupIntoScopes` checks `fs.existsSync` before reading each file; read failures are caught and the file is skipped. [E] `mpga-plugin/cli/src/generators/scope-md.ts:310-316`
- **No-entry-point fallback.** If no file in a scope matches the conventional entry-point patterns (`index.*`, `main.*`, `app.*`, etc.), `detectEntryPoints` picks the largest file by line count. [E] `mpga-plugin/cli/src/generators/scope-md.ts:222-227`
- **Scope name collision guard.** `getScopeName` with `scopeDepth='auto'` maps every file under a `src/`-like dir to the *immediate* sub-directory name. Files outside those dirs collapse to the top-level directory, preventing deep path bleed-through. [E] `mpga-plugin/cli/src/generators/scope-md.ts:240-261`
- **`extractModuleSummary` only uses the file-top comment.** A JSDoc block that appears after any code or import is rejected (`beforeComment === ''` check). [E] `mpga-plugin/cli/src/generators/scope-md.ts:115-127`
- **`detectFrameworks` deduplicates within a single call** using an internal `Set`, but cross-file deduplication in `groupIntoScopes` is done with a second `new Set(allFrameworks)` when building `ScopeInfo`. [E] `mpga-plugin/cli/src/generators/scope-md.ts:153-165`, `mpga-plugin/cli/src/generators/scope-md.ts:376`
- **Evidence index is capped at 40 entries; file list at 30.** Constants `MAX_EVIDENCE_INDEX_ENTRIES` and `MAX_FILE_LIST_ENTRIES` prevent scope docs from becoming unreadable for large scopes. [E] `mpga-plugin/cli/src/generators/scope-md.ts:386-388`
- **Mermaid output is capped at 30 dependencies** in `renderGraphMd` via `MAX_MERMAID_DEPENDENCIES`. [E] `mpga-plugin/cli/src/generators/graph-md.ts:9`, `mpga-plugin/cli/src/generators/graph-md.ts:170`
- **Orphan detection is at module level, not file level.** A module is an orphan if it has no incoming *and* no outgoing edges. Individual files within an orphan module are reported (up to `MAX_ORPHAN_FILES = 10`). [E] `mpga-plugin/cli/src/generators/graph-md.ts:7`, `mpga-plugin/cli/src/generators/graph-md.ts:124-132`
- **Circular detection is a simple direct-edge check**, not a full DFS. Only pairs where A→B and B→A both exist as direct edges are flagged; longer cycles are not detected. [E] `mpga-plugin/cli/src/generators/graph-md.ts:112-122`
- **`extractAnnotations` only captures `@throws` and `@deprecated`**; other JSDoc tags (`@param`, `@returns`, etc.) are ignored. [E] `mpga-plugin/cli/src/generators/scope-md.ts:196-200`
- **`renderIndexMd` falls back to `(describe role)` and placeholder conventions** when `config.knowledgeLayer` is absent or empty. [E] `mpga-plugin/cli/src/generators/index-md.ts:43-60`

## Concrete examples

**`mpga sync` full pipeline:**
1. `scan()` returns a `ScanResult` (files + metadata). [E] `mpga-plugin/cli/src/commands/sync.ts:32`
2. `buildGraph(scanResult, config)` reads each file, extracts relative imports via regex, maps files to scope names, and returns `{ dependencies, circular, orphans, modules }`. [E] `mpga-plugin/cli/src/generators/graph-md.ts:71-135`
3. `renderGraphMd(graph)` converts that data into a markdown string with a module list, circular warning section, and a Mermaid `graph TD` block. [E] `mpga-plugin/cli/src/generators/graph-md.ts:137-183`
4. `groupIntoScopes(scanResult, graph, config)` groups files by `getScopeName`, reads each file for exports/JSDoc/frameworks, builds reverse-dep map from graph, and returns `ScopeInfo[]`. [E] `mpga-plugin/cli/src/generators/scope-md.ts:264-383`
5. For each `ScopeInfo`, `renderScopeMd(scope, projectRoot)` produces a full scope markdown document — Summary, Where to start, What happens, Rules, Evidence index, Files, etc. [E] `mpga-plugin/cli/src/generators/scope-md.ts:390-599`
6. `renderIndexMd(scanResult, config, scopes, activeMilestone, evidenceCoverage)` assembles `INDEX.md` with identity, key files table, conventions, agent trigger table, and scope registry. [E] `mpga-plugin/cli/src/generators/index-md.ts:10-90`

**Framework detection example:** a file containing `import express from 'express'` causes `detectFrameworks` to match `express` against `FRAMEWORK_MAP` and return `['Express']`. [E] `mpga-plugin/cli/src/generators/scope-md.ts:153-165`, `mpga-plugin/cli/src/generators/scope-md.test.ts:47-51`

**JSDoc extraction example:** `extractJSDocForExport(content, 'loadBoard')` finds the `/** ... */` block immediately preceding `export function loadBoard` and returns the description with `@param`/`@returns` tags stripped. [E] `mpga-plugin/cli/src/generators/scope-md.ts:167-183`, `mpga-plugin/cli/src/generators/scope-md.test.ts:82-84`

**Evidence coverage in INDEX:** the ratio `driftReport.validLinks / driftReport.totalLinks` is passed as `evidenceCoverage` to `renderIndexMd`, which rounds it to a percentage. [E] `mpga-plugin/cli/src/commands/sync.ts:74-76`, `mpga-plugin/cli/src/generators/index-md.ts:35`

## UI

No UI. This scope is pure data transformation — strings in, markdown strings out.

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [commands](./commands.md)
- [board](./board.md)
- [core](./core.md)
- [evidence](./evidence.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depends on:**

- → [core](./core.md)

**Depended on by:**

- ← [commands](./commands.md)

**Contract with `core`:** generators import `ScanResult` and `FileInfo` from `scanner.ts`, and `MpgaConfig` from `config.ts`. They only *read* from these types — they do not mutate scan results. [E] `mpga-plugin/cli/src/generators/scope-md.ts:3-5`, `mpga-plugin/cli/src/generators/graph-md.ts:3-4`

**Contract with `commands`:** generators expose pure functions (`buildGraph`, `renderGraphMd`, `groupIntoScopes`, `renderScopeMd`, `renderIndexMd`). The `sync` command owns all filesystem writes; generators never write to disk themselves. [E] `mpga-plugin/cli/src/commands/sync.ts:39-86`

Note: the `postbuild` npm script in `package.json` invokes `dist/index.js export --claude` after each build, but this is a build-system hook — not a source-level import. Generators have no code-level dependency on `mpga-plugin`. [E] `mpga-plugin/cli/package.json:38`

## Diagram

```mermaid
graph LR
    generators --> core
    commands --> generators
```

## Traces

**Trace: `mpga sync` — full knowledge layer rebuild**

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | commands | `registerSync` action fires; `scan()` called with project root and ignore list | [E] `mpga-plugin/cli/src/commands/sync.ts:32` |
| 2 | generators | `buildGraph(scanResult, config)` iterates all files, extracts relative imports via regex, maps each to a module name via `getModuleName` | [E] `mpga-plugin/cli/src/generators/graph-md.ts:71-99` |
| 3 | generators | Direct circular pairs detected; orphan modules identified (no in or out edges) | [E] `mpga-plugin/cli/src/generators/graph-md.ts:111-132` |
| 4 | generators | `renderGraphMd(graph)` serialises graph to markdown + Mermaid block; `sync` writes to `MPGA/GRAPH.md` | [E] `mpga-plugin/cli/src/generators/graph-md.ts:137-183`, `mpga-plugin/cli/src/commands/sync.ts:40-41` |
| 5 | generators | `groupIntoScopes(scanResult, graph, config)` groups files by `getScopeName`, reads each file, extracts exports/JSDoc/frameworks/deps | [E] `mpga-plugin/cli/src/generators/scope-md.ts:264-383` |
| 6 | generators | For each scope, `renderScopeMd(scope, root)` builds the full scope markdown string | [E] `mpga-plugin/cli/src/generators/scope-md.ts:390-599` |
| 7 | commands | `sync` writes each scope doc to `MPGA/scopes/<name>.md` (skipped in `--incremental` if file exists) | [E] `mpga-plugin/cli/src/commands/sync.ts:52-58` |
| 8 | evidence | `runDriftCheck` returns `validLinks/totalLinks` for evidence coverage ratio | [E] `mpga-plugin/cli/src/commands/sync.ts:74-76` |
| 9 | generators | `renderIndexMd(scanResult, config, scopes, activeMilestone, evidenceCoverage)` assembles `INDEX.md` string | [E] `mpga-plugin/cli/src/generators/index-md.ts:10-90` |
| 10 | commands | `sync` writes `MPGA/INDEX.md` to disk | [E] `mpga-plugin/cli/src/commands/sync.ts:85` |

## Evidence index

| Claim | Evidence |
|-------|----------|
| `x` (const) | [E] mpga-plugin/cli/src/generators/graph-md.test.ts:1-20 :: x()|
| `help` (function) | [E] mpga-plugin/cli/src/generators/graph-md.test.ts:44-63 :: help()|
| `solo` (const) | [E] mpga-plugin/cli/src/generators/graph-md.test.ts:66-82 :: solo()|
| `Dependency` (interface) | [E] mpga-plugin/cli/src/generators/graph-md.ts:11-13 :: Dependency()|
| `GraphData` (interface) | [E] mpga-plugin/cli/src/generators/graph-md.ts:16-20 :: GraphData()|
| `buildGraph` (function) | [E] mpga-plugin/cli/src/generators/graph-md.ts:71-134 :: buildGraph()|
| `renderGraphMd` (function) | [E] mpga-plugin/cli/src/generators/graph-md.ts:137-182 :: renderGraphMd()|
| `renderIndexMd` (function) | [E] mpga-plugin/cli/src/generators/index-md.ts:10-15 :: renderIndexMd()|
| `foo` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:39-58 :: foo()|
| `loadBoard` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:83-102 :: loadBoard()|
| `saveBoard` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:88-107 :: saveBoard()|
| `noDoc` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:95-114 :: noDoc()|
| `exists` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:33-52 :: exists()|
| `scan` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:105-124 :: scan()|
| `doThing` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:114-133 :: doThing()|
| `oldFunc` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:120-139 :: oldFunc()|
| `simple` (function) | [E] mpga-plugin/cli/src/generators/scope-md.test.ts:126-145 :: simple()|
| `ScopeInfo` (interface) | [E] mpga-plugin/cli/src/generators/scope-md.ts:11-38 :: ScopeInfo()|
| `extractModuleSummary` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:130-166 :: extractModuleSummary()|
| `detectFrameworks` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:170-181 :: detectFrameworks()|
| `extractJSDocForExport` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:185-199 :: extractJSDocForExport()|
| `extractAnnotations` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:203-218 :: extractAnnotations()|
| `getScopeName` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:257-281 :: getScopeName()|
| `groupIntoScopes` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:294-297 :: groupIntoScopes()|
| `renderScopeMd` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts:428-627 :: renderScopeMd()|

## Files

- `mpga-plugin/cli/src/generators/graph-md.test.ts` (82 lines, typescript)
- `mpga-plugin/cli/src/generators/graph-md.ts` (184 lines, typescript)
- `mpga-plugin/cli/src/generators/index-md.test.ts` (76 lines, typescript)
- `mpga-plugin/cli/src/generators/index-md.ts` (91 lines, typescript)
- `mpga-plugin/cli/src/generators/scope-md.test.ts` (248 lines, typescript)
- `mpga-plugin/cli/src/generators/scope-md.ts` (600 lines, typescript)

## Deeper splits

`scope-md.ts` at 600 lines could be split: the extraction helpers (`extractModuleSummary`, `detectFrameworks`, `extractJSDocForExport`, `extractAnnotations`, `extractExports`) are stateless utilities that could live in a dedicated `scope-extract.ts`. `groupIntoScopes` and `renderScopeMd` would remain in `scope-md.ts`. No split is required yet — the file is well-organised — but watch for growth beyond ~800 lines. [E] `mpga-plugin/cli/src/generators/scope-md.ts:113-202`

## Confidence and notes

- **Confidence:** HIGH — all 6 files read directly; evidence links verified against source line numbers by SCOUT.
- **Evidence coverage:** 25/25 verified
- **Last verified:** 2026-03-24
- **Drift risk:** low — generators are pure functions; changes are visible in tests.
- The circular dependency detector only finds *direct* A↔B pairs. Multi-hop cycles (A→B→C→A) are not detected. [Unknown] whether this is intentional or a known gap.
- `getScopeName` with a numeric `scopeDepth` joins path segments with `/` — the resulting scope name may contain slashes, which could cause issues if used as a filename without sanitisation. [E] `mpga-plugin/cli/src/generators/scope-md.ts:259-261`

## Change history

- 2026-03-24: Initial scope generation via `mpga sync` — Making this scope GREAT!