# Scope: mpga-plugin

## Summary

The **mpga-plugin** module contains 8 files (182 lines).

<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code

Main entry points — open these first to understand this behavior:

- [E] `mpga-plugin/cli/src/cli.ts`
- [E] `mpga-plugin/cli/src/index.ts`

## Context / stack / skills

- **Languages:** shell, typescript, javascript
- **Symbol types:** function
- <!-- TODO: Add relevant frameworks, integrations, and expertise areas -->

## Who and what triggers it

<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

## What happens

<!-- TODO: Describe the flow in plain language: inputs, main steps, outputs or side effects -->

## Rules and edge cases

<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples

<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI

<!-- TODO: Screens or flows if relevant — intent, layout, interactions, data shown/submitted. Remove this section if not applicable. -->

## Navigation

**Sibling scopes:**

- [board](./board.md)
- [core](./core.md)
- [evidence](./evidence.md)
- [commands](./commands.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depends on:**

- → [core](./core.md)
- → [commands](./commands.md)

<!-- TODO: Shared concepts or data with other scopes -->

## Diagram

```mermaid
graph LR
    mpga_plugin --> core
    mpga_plugin --> commands
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
| `createCli` (function) | [E] mpga-plugin/cli/src/cli.ts :: createCli |

## Files

- `mpga-plugin/bin/mpga.sh` (17 lines, shell)
- `mpga-plugin/cli/vitest.config.ts` (19 lines, typescript)
- `mpga-plugin/scripts/check-cli.sh` (20 lines, shell)
- `mpga-plugin/scripts/format-evidence.sh` (16 lines, shell)
- `mpga-plugin/scripts/setup.sh` (28 lines, shell)
- `mpga-plugin/cli/bin/mpga.js` (4 lines, javascript)
- `mpga-plugin/cli/src/cli.ts` (73 lines, typescript)
- `mpga-plugin/cli/src/index.ts` (5 lines, typescript)

## Deeper splits

<!-- TODO: Pointers to smaller sub-topic scopes if this capability is large enough to split -->

## Confidence and notes

- **Confidence:** low — auto-generated, not yet verified
- **Evidence coverage:** 0/1 verified
- **Last verified:** 2026-03-22
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history

- 2026-03-22: Initial scope generation via `mpga sync`