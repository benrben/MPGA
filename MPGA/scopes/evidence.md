# Scope: evidence

## Summary

- **Health:** ✓ fresh
The **evidence** module — TREMENDOUS — 8 files, 2,067 lines of the finest code you've ever seen. Believe me.

The **evidence** module is the truth engine of MPGA. It parses, resolves, and heals evidence links (`[E]`, `[Unknown]`, `[Stale:date]`, `[Deprecated]`) found in scope `.md` files. It also runs drift checks — scanning every scope file in `MPGA/scopes/` to find stale evidence links and auto-heals line ranges when symbols have moved.

**In scope:** parsing evidence link syntax, AST-based symbol extraction (regex-based, multi-language), evidence resolution with confidence scoring, drift check across all scope files, scope file healing.

**Out of scope:** generating scope files (that's generators), board logic, writing final results back to disk (callers own that).

## Where to start in code

These are your MAIN entry points — the best, the most important. Open them FIRST:

- [E] `mpga-plugin/cli/src/evidence/ast.test.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** function, class, type, interface, const
- **Frameworks:** Vitest

## Who and what triggers it

Five command handlers import from this module directly:

- `commands/evidence.ts` — imports `formatEvidenceLink` (parser) + `runDriftCheck`, `healScopeFile` (drift). [E] mpga-plugin/cli/src/commands/evidence.ts:7-8
- `commands/drift.ts` — imports `runDriftCheck`, `healScopeFile` (drift). [E] mpga-plugin/cli/src/commands/drift.ts:6
- `commands/sync.ts` — imports `runDriftCheck` (drift) to gate syncs on evidence health. [E] mpga-plugin/cli/src/commands/sync.ts:10
- `commands/health.ts` — imports `runDriftCheck` (drift) for the health dashboard. [E] mpga-plugin/cli/src/commands/health.ts:7
- `commands/scope.ts` — imports `parseEvidenceLinks`, `evidenceStats` (parser) to report per-scope stats. [E] mpga-plugin/cli/src/commands/scope.ts:6

**Called by these GREAT scopes (they need us, tremendously):**

- ← commands

## What happens

**parser.ts** — Parsing pipeline for a single line or full markdown document:

1. Input: a raw string line (or multi-line document content).
2. `parseEvidenceLink(line)` runs four regexes in priority order: `[E]`, `[Unknown]`, `[Stale:date]`, `[Deprecated]`. [E] mpga-plugin/cli/src/evidence/parser.ts:24-86
3. Returns an `EvidenceLink` struct with `type`, `filepath`, `startLine`, `endLine`, `symbol`, `confidence`. [E] mpga-plugin/cli/src/evidence/parser.ts:3-15
4. `parseEvidenceLinks(content)` splits on newlines and filters nulls, returning all links found. [E] mpga-plugin/cli/src/evidence/parser.ts:88-93
5. `formatEvidenceLink(link)` serialises a struct back to canonical string form. [E] mpga-plugin/cli/src/evidence/parser.ts:95-114
6. `evidenceStats(links)` counts valid/stale/unknown/deprecated and computes `healthPct = valid/total * 100`. [E] mpga-plugin/cli/src/evidence/parser.ts:116-131

**ast.ts** — Symbol extraction from source files:

1. Input: relative filepath + project root.
2. `detectLanguage(filepath)` maps extension to language string (ts/js/py/go/rust/java/cs/rb/php). [E] mpga-plugin/cli/src/evidence/ast.ts:15-32
3. `extractSymbols(filepath, projectRoot)` reads the file, runs `extractSymbolsRegex` with language-specific patterns. [E] mpga-plugin/cli/src/evidence/ast.ts:132-145
4. `findSymbol(filepath, symbolName, projectRoot)` returns the first `SymbolLocation` with a matching name, or `null`. [E] mpga-plugin/cli/src/evidence/ast.ts:147-154
5. `verifyRange(filepath, startLine, endLine, symbol, projectRoot)` checks that the text at those lines contains the symbol name. [E] mpga-plugin/cli/src/evidence/ast.ts:157-175

**resolver.ts** — 4-step confidence resolution for a single evidence link:

1. No filepath → `{ status: 'stale', confidence: 0 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:28-30
2. File missing from disk → `{ status: 'stale', confidence: 0 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:33-35
3. File-only link (no symbol, no lines) → `{ status: 'valid', confidence: 0.8 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:38-40
4. Step 1 — exact line range via `verifyRange` → `{ status: 'valid', confidence: 1.0 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:43-54
5. Step 2 — AST anchor via `findSymbol`; if lines shifted → `{ status: 'healed', confidence: 0.9 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:57-71
6. Step 3 — fuzzy text search across lines → `{ status: 'healed', confidence: 0.6 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:74-92
7. Step 4 — symbol not found anywhere → `{ status: 'stale', confidence: 0 }`. [E] mpga-plugin/cli/src/evidence/resolver.ts:95

**drift.ts** — Project-wide drift check and healing:

1. `runDriftCheck(projectRoot, ciThreshold, scopeFilter?)` reads all `.md` files in `MPGA/scopes/`, parses evidence links, resolves each via `verifyAllLinks`, aggregates `ScopeDriftReport` per file and a top-level `DriftReport`. Sets `ciPass = overallHealthPct >= ciThreshold`. [E] mpga-plugin/cli/src/evidence/drift.ts:29-122
2. `healScopeFile(report)` reads the scope file content, replaces stale line ranges with healed ones using a regex rewrite, returns updated content and count of healed links. Callers own writing the result back to disk. [E] mpga-plugin/cli/src/evidence/drift.ts:125-154

## Rules and edge cases

- `parseEvidenceLink` returns `null` (not an exception) for any line that matches no known pattern — non-evidence lines are silently dropped. [E] mpga-plugin/cli/src/evidence/parser.ts:85
- Backticks and trailing markdown table pipes are stripped from filepath and symbol values via `cleanParsed()` so links embedded in markdown tables parse cleanly. [E] mpga-plugin/cli/src/evidence/parser.ts:30-35
- `[Unknown]` links get `confidence: 0` and no filepath — they are never passed to the resolver. [E] mpga-plugin/cli/src/evidence/parser.ts:54-55
- `[Deprecated]` links get `confidence: 0.5` and are **filtered out** by `verifyAllLinks` (only `valid` and `stale` types are resolved). [E] mpga-plugin/cli/src/evidence/resolver.ts:105-106
- `extractSymbolsRegex` guards against keyword false-positives: names matching `if|for|while|switch|return|const|let|var` are skipped. [E] mpga-plugin/cli/src/evidence/ast.ts:109
- Block-end scanning in `extractSymbolsRegex` is capped at `MAX_BLOCK_SCAN_LINES = 200` lines to avoid runaway loops on large files. [E] mpga-plugin/cli/src/evidence/ast.ts:12
- `extractSymbols` and `verifyRange` return empty/false on any file I/O error (try/catch, no rethrow). [E] mpga-plugin/cli/src/evidence/ast.ts:136-141, mpga-plugin/cli/src/evidence/ast.ts:167-174
- `runDriftCheck` returns a 100%-health empty report (not an error) when `MPGA/scopes/` does not exist. [E] mpga-plugin/cli/src/evidence/drift.ts:40-51
- `healScopeFile` sorts healed items by symbol length descending before rewriting, preventing shorter symbol names from incorrectly matching inside longer ones. [E] mpga-plugin/cli/src/evidence/drift.ts:131-133
- `healthPct` treats an empty link set as 100% — no evidence is not bad evidence. [E] mpga-plugin/cli/src/evidence/parser.ts:129

## Concrete examples

**Parsing a full link:**
Input: `[E] src/auth/jwt.ts:42-67 :: generateAccessToken()`
→ `{ type: 'valid', filepath: 'src/auth/jwt.ts', startLine: 42, endLine: 67, symbol: 'generateAccessToken', confidence: 1.0 }`
[E] mpga-plugin/cli/src/evidence/parser.test.ts:11-22

**Parsing a stale link:**
Input: `[Stale:2026-03-20] src/auth/jwt.ts:42-67`
→ `{ type: 'stale', staleDate: '2026-03-20', filepath: 'src/auth/jwt.ts', startLine: 42, endLine: 67, confidence: 0 }`
[E] mpga-plugin/cli/src/evidence/parser.test.ts:54-63

**Resolving a healed link (function moved):**
Evidence says `greet` is at lines 2-4, but it's now at lines 5-7. `verifyRange` fails, `findSymbol` locates it at the new position.
→ `{ status: 'healed', confidence: 0.9, startLine: 5, healedFrom: 'line range changed: was 2-4, now 5-7' }`
[E] mpga-plugin/cli/src/evidence/resolver.test.ts:79-105

**Resolving via fuzzy match (symbol not top-level):**
Symbol `mySpecialHandler` exists only as an object key — AST misses it, fuzzy text scan finds it at line 3.
→ `{ status: 'healed', confidence: 0.6, startLine: 3, healedFrom: 'fuzzy match at line 3 (was 10-15)' }`
[E] mpga-plugin/cli/src/evidence/resolver.test.ts:107-132

**Drift check with CI gate:**
`runDriftCheck('/project', 80)` scans all `.md` files, finds 10 links: 8 valid, 2 stale → `overallHealthPct = 80`, `ciPass = true`.
[E] mpga-plugin/cli/src/evidence/drift.ts:108-120

**Healing a scope file:**
`healScopeFile(report)` rewrites `[E] src/foo.ts:10-15 :: greet()` → `[E] src/foo.ts:20-25 :: greet()` when AST found `greet` at the new lines.
[E] mpga-plugin/cli/src/evidence/drift.ts:125-154

## UI

No UI. This module is pure library code — no CLI output, no rendering. Callers in `commands/` format and print results.

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [commands](./commands.md)
- [board](./board.md)
- [core](./core.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depended on by:**

- ← [commands](./commands.md)

**Provides to commands:**
- `parser.ts` exports: `parseEvidenceLink`, `parseEvidenceLinks`, `formatEvidenceLink`, `evidenceStats`, `EvidenceLink`, `EvidenceLinkType`. [E] mpga-plugin/cli/src/evidence/parser.ts:1-131
- `drift.ts` exports: `runDriftCheck`, `healScopeFile`, `DriftReport`, `ScopeDriftReport`. [E] mpga-plugin/cli/src/evidence/drift.ts:6-27
- `resolver.ts` exports: `resolveEvidence`, `verifyAllLinks`, `ResolvedEvidence`, `VerifyResult`. [E] mpga-plugin/cli/src/evidence/resolver.ts:17-107
- `ast.ts` exports: `detectLanguage`, `extractSymbols`, `findSymbol`, `verifyRange`, `SymbolLocation`. [E] mpga-plugin/cli/src/evidence/ast.ts:4-175

**Internal dependency chain:**
`drift.ts` → `resolver.ts` → `ast.ts`; `drift.ts` → `parser.ts`; `resolver.ts` → `parser.ts` (type import only). [E] mpga-plugin/cli/src/evidence/drift.ts:3-4, mpga-plugin/cli/src/evidence/resolver.ts:3-4

## Diagram

```mermaid
graph LR
    commands --> evidence
```

## Traces

**Trace: `mpga drift` command healing a stale link**

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | commands/drift.ts | Command calls `runDriftCheck(projectRoot, ciThreshold)` | [E] mpga-plugin/cli/src/commands/drift.ts:6 |
| 2 | drift.ts | Reads all `.md` files from `MPGA/scopes/` | [E] mpga-plugin/cli/src/evidence/drift.ts:53-57 |
| 3 | parser.ts | `parseEvidenceLinks(content)` extracts all `[E]`/`[Stale]` links from each file | [E] mpga-plugin/cli/src/evidence/drift.ts:62 |
| 4 | resolver.ts | `verifyAllLinks(links, projectRoot)` resolves each link (filters unknown/deprecated) | [E] mpga-plugin/cli/src/evidence/drift.ts:66 |
| 5 | resolver.ts | For each link: tries exact range → AST anchor → fuzzy match → stale | [E] mpga-plugin/cli/src/evidence/resolver.ts:42-95 |
| 6 | ast.ts | `findSymbol` runs `extractSymbolsRegex` with language-matched patterns, returns `SymbolLocation` | [E] mpga-plugin/cli/src/evidence/ast.ts:147-154 |
| 7 | drift.ts | `ScopeDriftReport` built: valid/healed/stale counts, `healthPct` | [E] mpga-plugin/cli/src/evidence/drift.ts:68-105 |
| 8 | drift.ts | `ciPass = overallHealthPct >= ciThreshold` computed on aggregated totals | [E] mpga-plugin/cli/src/evidence/drift.ts:119 |
| 9 | commands/drift.ts | If heal flag set, calls `healScopeFile(report)` → gets updated content | [E] mpga-plugin/cli/src/evidence/drift.ts:125-154 |
| 10 | commands/drift.ts | Caller writes healed content back to disk (drift.ts never writes files) | [E] mpga-plugin/cli/src/evidence/drift.ts:125 |

## Evidence index

| Claim | Evidence |
|-------|----------|
| `greet` (function) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:85-104 :: greet()|
| `fetchData` (function) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:106-125 :: fetchData()|
| `UserService` (class) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:119-138 :: UserService()|
| `UserId` (type) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:143-162 :: UserId()|
| `Config` (interface) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:145-164 :: Config()|
| `add` (const) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:168-187 :: add()|
| `handler` (const) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:187-206 :: handler()|
| `MAX_RETRIES` (const) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:199-218 :: MAX_RETRIES()|
| `alpha` (function) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:398-417 :: alpha()|
| `beta` (function) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:402-421 :: beta()|
| `targetSymbol` (function) | [E] mpga-plugin/cli/src/evidence/ast.test.ts:483-492 :: targetSymbol()|
| `SymbolLocation` (interface) | [E] mpga-plugin/cli/src/evidence/ast.ts:4-8 :: SymbolLocation()|
| `detectLanguage` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts:15-31 :: detectLanguage()|
| `extractSymbols` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts:132-144 :: extractSymbols()|
| `findSymbol` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts:147-150 :: findSymbol()|
| `verifyRange` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts:157-162 :: verifyRange()|
| `myFunction` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:58-77 :: myFunction()|
| `x` (const) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:1-20 :: x()|
| `unrelated` (const) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:112-131 :: unrelated()|
| `movedFunc` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:126-145 :: movedFunc()|
| `funcA` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:142-161 :: funcA()|
| `funcB` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:143-162 :: funcB()|
| `okFunc` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:162-181 :: okFunc()|
| `goodFunc` (function) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:179-198 :: goodFunc()|
| `v` (const) | [E] mpga-plugin/cli/src/evidence/drift.test.ts:1-20 :: v()|
| `ScopeDriftReport` (interface) | [E] mpga-plugin/cli/src/evidence/drift.ts:10-28 :: ScopeDriftReport()|
| `DriftReport` (interface) | [E] mpga-plugin/cli/src/evidence/drift.ts:35-51 :: DriftReport()|
| `runDriftCheck` (function) | [E] mpga-plugin/cli/src/evidence/drift.ts:63-66 :: runDriftCheck()|
| `healScopeFile` (function) | [E] mpga-plugin/cli/src/evidence/drift.ts:165-193 :: healScopeFile()|
| `EvidenceLinkType` (type) | [E] mpga-plugin/cli/src/evidence/parser.ts:14-36 :: EvidenceLink()Type()|
| `EvidenceLink` (interface) | [E] mpga-plugin/cli/src/evidence/parser.ts :: EvidenceLink |
| `parseEvidenceLink` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts:66-114 :: parseEvidenceLink()|
| `parseEvidenceLinks` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts:124-128 :: parseEvidenceLinks()|
| `formatEvidenceLink` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts:138-156 :: formatEvidenceLink()|
| `evidenceStats` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts:166-172 :: evidenceStats()|
| `x` (const) | [E] mpga-plugin/cli/src/evidence/resolver.test.ts:1-20 :: x()|
| `greet` (function) | [E] mpga-plugin/cli/src/evidence/resolver.test.ts:59-78 :: greet()|
| `unrelatedFunction` (function) | [E] mpga-plugin/cli/src/evidence/resolver.test.ts:135-154 :: unrelatedFunction()|
| `doWork` (function) | [E] mpga-plugin/cli/src/evidence/resolver.test.ts:165-184 :: doWork()|
| `compute` (function) | [E] mpga-plugin/cli/src/evidence/resolver.test.ts:183-202 :: compute()|
| ... | 9 more symbols |

## Files

- `mpga-plugin/cli/src/evidence/ast.test.ts` (519 lines, typescript)
- `mpga-plugin/cli/src/evidence/ast.ts` (176 lines, typescript)
- `mpga-plugin/cli/src/evidence/drift.test.ts` (494 lines, typescript)
- `mpga-plugin/cli/src/evidence/drift.ts` (155 lines, typescript)
- `mpga-plugin/cli/src/evidence/parser.test.ts` (178 lines, typescript)
- `mpga-plugin/cli/src/evidence/parser.ts` (132 lines, typescript)
- `mpga-plugin/cli/src/evidence/resolver.test.ts` (305 lines, typescript)
- `mpga-plugin/cli/src/evidence/resolver.ts` (108 lines, typescript)

## Deeper splits

8 files, 2,067 lines total. The four source files are well-separated by responsibility (parse / AST / resolve / drift) with no overlapping concerns. No split needed — the module is already lean at its natural seams.

## Confidence and notes

- **Confidence:** HIGH — all four source files read and verified by SCOUT agent.
- **Evidence coverage:** 49/49 symbols indexed; all key behaviors cited with `[E]` links.
- **Last verified:** 2026-03-24
- **Drift risk:** LOW — module boundaries are stable; regex-based AST is the main fragility point.
- AST extraction is regex-based (not a real AST parser) — complex patterns like decorators, generic type parameters, or multi-line arrow functions may be missed. [Unknown] TypeScript decorator and generic coverage.
- `healScopeFile` uses string replacement; duplicate filepath+symbol entries in one scope file may not all be healed. [E] mpga-plugin/cli/src/evidence/drift.ts:146-149
- Callers own writing healed content to disk — `drift.ts` never writes files itself. Both `commands/drift.ts` and `commands/evidence.ts` correctly call `fs.writeFileSync(scope.scopePath, content)` after receiving healed content from `healScopeFile`. [E] mpga-plugin/cli/src/commands/drift.ts:86-88 [E] mpga-plugin/cli/src/commands/evidence.ts:97-99

## Change history

- 2026-03-24: Initial scope generation via `mpga sync` — Making this scope GREAT!
- 2026-03-24: SCOUT agent filled all TODO sections — full evidence-backed content for all four source files.