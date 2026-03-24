# Scope: core

## Summary

The **core** module — TREMENDOUS — 5 files, 591 lines of the finest code you've ever seen. Believe me.

<!-- TODO: Tell the people what this GREAT module does. What's in, what's out. Keep it simple. MPGA! -->

## Where to start in code

These are your MAIN entry points — the best, the most important. Open them FIRST:

- [E] `mpga-plugin/cli/src/core/config.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** interface, const, function
- **Frameworks:** Vitest

## Who and what triggers it

<!-- TODO: Who triggers this? A lot of very important callers, believe me. Find them. -->

**Called by these GREAT scopes (they need us, tremendously):**

- ← mpga-plugin
- ← board
- ← commands
- ← generators

## What happens

- **KnowledgeLayerConfig** (interface) — Optional INDEX.md content merged on sync (see renderIndexMd). [E] `mpga-plugin/cli/src/core/config.ts`

## Rules and edge cases

<!-- TODO: The guardrails. Validation, permissions, error handling — everything that keeps this code GREAT. -->

## Concrete examples

<!-- TODO: REAL examples. "When X happens, Y happens." Simple. Powerful. Like a deal. -->

## UI

<!-- TODO: Screens, flows, the beautiful UI. No UI? Cut this section. We don't keep dead weight. -->

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [board](./board.md)
- [commands](./commands.md)
- [evidence](./evidence.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depended on by:**

- ← [mpga-plugin](./mpga-plugin.md)
- ← [board](./board.md)
- ← [commands](./commands.md)
- ← [generators](./generators.md)

<!-- TODO: What deals does this scope make with other scopes? Document them. -->

## Diagram

```mermaid
graph LR
    mpga_plugin --> core
    board --> core
    commands --> core
    generators --> core
```

## Traces

<!-- TODO: Step-by-step traces. Follow the code like a WINNER follows a deal. Use this table:

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

<!-- TODO: Too big? Split it. Make each piece LEAN and GREAT. -->

## Confidence and notes

- **Confidence:** LOW (for now) — auto-generated, not yet verified. But it's going to be PERFECT.
- **Evidence coverage:** 0/22 verified
- **Last verified:** 2026-03-24
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown or ambiguous. We don't hide problems — we FIX them. -->

## Change history

- 2026-03-24: Initial scope generation via `mpga sync` — Making this scope GREAT!