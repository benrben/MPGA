# Scope: src-evidence

## Summary

The **evidence** subsystem parses, resolves, and heals evidence links in scope documents. It is the core differentiator of MPGA — ensuring that claims about code are backed by verifiable pointers to actual source locations.

## Where to start in code

- [E] `src/evidence/resolver.ts` — the 4-stage resolution pipeline
- [E] `src/evidence/parser.ts` — regex-based evidence link parsing

## Context / stack / skills

- **Languages:** TypeScript
- **Approach:** Regex-based symbol extraction (no AST library despite filename `ast.ts`)

## Who and what triggers it

- `mpga evidence verify|heal|coverage|add` commands
- `mpga drift --report|--quick|--ci|--fix` commands
- PostToolUse git hook runs `mpga drift --quick` after Write/Edit

## What happens

### Evidence link format

Four types recognized in scope markdown:

- **Valid:** `src/foo.ts:10-20 :: symbolName()` → confidence 1.0
- **Unknown:** `description` → confidence 0
- **Stale:** `2026-03-20 src/foo.ts:10-20` → confidence 0
- **Deprecated:** `src/foo.ts:10-20` → confidence 0.5

Links appear both standalone (`- [E] ...`) and inside markdown tables (`| [E] ... |`).

### Resolution pipeline (`resolver.ts`)

For each evidence link, `resolveEvidence()` runs in order:

1. **File-only check** — if no symbol and no line range, file existence is enough → `valid` (0.8)
2. **Exact line range** — `verifyRange()` checks if the symbol appears in the specified lines → `valid` (1.0)
3. **AST anchor** — `findSymbol()` searches the file for the symbol definition → `healed` (0.9) if found at different lines
4. **Fuzzy search** — substring match anywhere in file → `healed` (0.6) with 20-line window
5. **Not found** → `stale` (0)

### Symbol extraction (`ast.ts`)

Regex patterns for 5 language families: TS/JS, Python, Go, Rust, Java/C#. Uses indentation heuristic to find block end (walks up to 200 lines for closing brace/dedent).

### Drift orchestration (`drift.ts`)

`runDriftCheck()` reads all `MPGA/scopes/*.md`, parses evidence links, resolves them, produces per-scope and overall health reports. `healScopeFile()` uses regex replacement to update line ranges in the markdown source — sorts by symbol length to prevent shorter symbols from colliding with longer ones.

## Rules and edge cases

- Parser strips backticks and trailing markdown table pipes from captured values (`cleanParsed()`)
- `evidenceStats()` counts only `valid` in health %; `runDriftCheck()` counts `valid + healed` — two different health metrics
- Heal sorts replacements by symbol length (longest first) to prevent `Task` from matching inside `TaskStatus`
- Stale reason distinguishes "File not found" from "Symbol not found" for better debugging
- Keyword guard in `ast.ts` skips `if|for|while|switch|return|const|let|var` as symbol names

## Navigation

**Parent:** [src](./src.md)

**Used by:** [src-commands](./src-commands.md) (evidence, drift commands)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `parseEvidenceLink` parser | [E] src/evidence/parser.ts |
| `resolveEvidence` pipeline | [E] src/evidence/resolver.ts |
| `findSymbol` AST search | [E] src/evidence/ast.ts |
| `runDriftCheck` orchestrator | [E] src/evidence/drift.ts |
| `healScopeFile` rewriter | [E] src/evidence/drift.ts |

## Files

- `src/evidence/parser.ts` (118 lines)
- `src/evidence/resolver.ts` (87 lines)
- `src/evidence/ast.ts` (134 lines)
- `src/evidence/drift.ts` (138 lines)

## Confidence and notes

- **Confidence:** high — manually verified, bugs found and fixed in this session
- **Last verified:** 2026-03-22
- **Drift risk:** low
- Fixed: backtick and table pipe stripping in parser (was causing 2% health)
- Fixed: heal collision between short/long symbol names
- Fixed: file-only links (no symbol) now resolve as valid

## Change history

- 2026-03-22: Created as sub-scope split from src
- 2026-03-22: Bug fixes to parser (backticks, table pipes), resolver (file-only links), drift (error messages, heal collisions)
