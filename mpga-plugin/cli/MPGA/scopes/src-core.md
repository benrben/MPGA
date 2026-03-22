# Scope: src-core

## Summary

The **core** subsystem provides foundational services consumed by every command: project root discovery, configuration loading/saving, filesystem scanning, and terminal output formatting.

## Where to start in code

- [E] `src/core/config.ts` — configuration authority (loaded by every command)
- [E] `src/core/scanner.ts` — file discovery and language detection
- [E] `src/core/logger.ts` — colored terminal output

## Context / stack / skills

- **Languages:** TypeScript
- **Dependencies:** fast-glob (scanner), chalk (logger)

## Who and what triggers it

Every CLI command calls `findProjectRoot()` + `loadConfig()` as its first step. The scanner is invoked by `init --from-existing` and `sync`.

## What happens

### Configuration (`config.ts`)

- `findProjectRoot(startDir)` walks up from CWD looking for `mpga.config.json` at root or inside `MPGA/`
- `loadConfig()` reads JSON, deep-merges over `DEFAULT_CONFIG` (never throws — falls back to defaults)
- `deepMerge` replaces arrays entirely (no append behavior) — user arrays fully override defaults
- `MpgaConfig` has 7 sections: project, evidence, drift, tiers, milestone, agents, board
- Defaults: `evidence.strategy: 'hybrid'`, `evidence.coverageThreshold: 0.20`, `drift.ciThreshold: 80`, `board.wipLimits: {in-progress: 3, testing: 3, review: 2}`

### Scanner (`scanner.ts`)

- `scan(projectRoot, ignore, deep)` uses fast-glob to find files by extension (17 extensions → 10 languages)
- Produces `ScanResult`: `FileInfo[]` with filepath/lines/language/size, per-language stats, entry points, top-level dirs
- Entry point detection matches: `src/index.*`, `src/main.*`, `index.*`, `main.*`, `app.*`, `server.*`, `cmd/main.*`
- The `deep` parameter is a stub — both branches use identical glob patterns

### Logger (`logger.ts`)

- Thin chalk wrapper: `log.info/success/warn/error/dim/bold/header(msg)`
- `log.table(rows)` for auto-padded terminal tables
- `progressBar(value, total, width=20)` renders Unicode block progress bars

## Rules and edge cases

- Config search checks two locations per directory level (root and `MPGA/` subdirectory)
- `deepMerge` array replacement means user `ignore` lists fully replace defaults (no append)
- `countLines` reads entire file into memory — no streaming
- `detectProjectType` is heuristic (checks filenames, not content)

## Navigation

**Parent:** [src](./src.md)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `MpgaConfig` (interface) | [E] src/core/config.ts:4-51 :: MpgaConfig()|
| `DEFAULT_CONFIG` (const) | [E] src/core/config.ts:54-101 :: DEFAULT_CONFIG()|
| `findProjectRoot` (function) | [E] src/core/config.ts:104-112 :: findProjectRoot()|
| `loadConfig` (function) | [E] src/core/config.ts:115-126 :: loadConfig()|
| `saveConfig` (function) | [E] src/core/config.ts:129-131 :: saveConfig()|

## Files

- `src/core/config.ts` (172 lines)
- `src/core/logger.ts` (29 lines)
- `src/core/scanner.ts` (145 lines)

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-22
- **Drift risk:** low

## Change history

- 2026-03-22: Created as sub-scope split from src
