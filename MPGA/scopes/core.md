# Scope: core

## Summary

The **core** module contains 5 files (591 lines).

<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code

Main entry points — open these first to understand this behavior:

- [E] `mpga-plugin/cli/src/core/config.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** interface, const, function
- **Frameworks:** Vitest

## Who and what triggers it

<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

**Called by scopes:**

- ← mpga-plugin
- ← board
- ← generators
- ← commands

## What happens

- **KnowledgeLayerConfig** (interface) — Optional INDEX.md content merged on sync (see renderIndexMd). [E] `mpga-plugin/cli/src/core/config.ts`

## Rules and edge cases

<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples

<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI

<!-- TODO: Screens or flows if relevant — intent, layout, interactions, data shown/submitted. Remove this section if not applicable. -->

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [board](./board.md)
- [evidence](./evidence.md)
- [generators](./generators.md)
- [commands](./commands.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depended on by:**

- ← [mpga-plugin](./mpga-plugin.md)
- ← [board](./board.md)
- ← [generators](./generators.md)
- ← [commands](./commands.md)

<!-- TODO: Shared concepts or data with other scopes -->

## Diagram

```mermaid
graph LR
    mpga_plugin --> core
    board --> core
    generators --> core
    commands --> core
```

## Traces

<!-- TODO: Step-by-step paths through the system. Use the table format below:

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | (layer) | (description) | [E] file:line |
-->

## Evidence index

| Claim | Evidence |
|-------|----------|
| `KnowledgeLayerConfig` (interface) | [E] mpga-plugin/cli/src/core/config.ts :: KnowledgeLayerConfig |
| `MpgaConfig` (interface) | [E] mpga-plugin/cli/src/core/config.ts :: MpgaConfig |
| `DEFAULT_CONFIG` (const) | [E] mpga-plugin/cli/src/core/config.ts :: DEFAULT_CONFIG |
| `findProjectRoot` (function) | [E] mpga-plugin/cli/src/core/config.ts :: findProjectRoot |
| `loadConfig` (function) | [E] mpga-plugin/cli/src/core/config.ts :: loadConfig |
| `saveConfig` (function) | [E] mpga-plugin/cli/src/core/config.ts :: saveConfig |
| `getConfigValue` (function) | [E] mpga-plugin/cli/src/core/config.ts :: getConfigValue |
| `setConfigValue` (function) | [E] mpga-plugin/cli/src/core/config.ts :: setConfigValue |
| `VERSION` (const) | [E] mpga-plugin/cli/src/core/logger.ts :: VERSION |
| `banner` (function) | [E] mpga-plugin/cli/src/core/logger.ts :: banner |
| `miniBanner` (function) | [E] mpga-plugin/cli/src/core/logger.ts :: miniBanner |
| `log` (const) | [E] mpga-plugin/cli/src/core/logger.ts :: log |
| `progressBar` (function) | [E] mpga-plugin/cli/src/core/logger.ts :: progressBar |
| `gradeColor` (function) | [E] mpga-plugin/cli/src/core/logger.ts :: gradeColor |
| `statusBadge` (function) | [E] mpga-plugin/cli/src/core/logger.ts :: statusBadge |
| `FileInfo` (interface) | [E] mpga-plugin/cli/src/core/scanner.ts :: FileInfo |
| `ScanResult` (interface) | [E] mpga-plugin/cli/src/core/scanner.ts :: ScanResult |
| `detectLanguage` (function) | [E] mpga-plugin/cli/src/core/scanner.ts :: detectLanguage |
| `countLines` (function) | [E] mpga-plugin/cli/src/core/scanner.ts :: countLines |
| `scan` (function) | [E] mpga-plugin/cli/src/core/scanner.ts :: scan |
| `detectProjectType` (function) | [E] mpga-plugin/cli/src/core/scanner.ts :: detectProjectType |
| `getTopLanguage` (function) | [E] mpga-plugin/cli/src/core/scanner.ts :: getTopLanguage |

## Files

- `mpga-plugin/cli/src/core/config.test.ts` (90 lines, typescript)
- `mpga-plugin/cli/src/core/config.ts` (196 lines, typescript)
- `mpga-plugin/cli/src/core/logger.test.ts` (40 lines, typescript)
- `mpga-plugin/cli/src/core/logger.ts` (101 lines, typescript)
- `mpga-plugin/cli/src/core/scanner.ts` (164 lines, typescript)

## Deeper splits

<!-- TODO: Pointers to smaller sub-topic scopes if this capability is large enough to split -->

## Confidence and notes

- **Confidence:** low — auto-generated, not yet verified
- **Evidence coverage:** 0/22 verified
- **Last verified:** 2026-03-23
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history

- 2026-03-23: Initial scope generation via `mpga sync`