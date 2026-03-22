# Scope: generators

## Summary

The **generators** module contains 3 files (610 lines).

<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code

Main entry points — open these first to understand this behavior:

- [E] `mpga-plugin/cli/src/generators/scope-md.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** interface, function
- <!-- TODO: Add relevant frameworks, integrations, and expertise areas -->

## Who and what triggers it

<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

**Called by scopes:**

- ← commands

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

<!-- TODO: Shared concepts or data with other scopes -->

## Diagram

```mermaid
graph LR
    generators --> core
    commands --> generators
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
| `Dependency` (interface) | [E] mpga-plugin/cli/src/generators/graph-md.ts :: Dependency |
| `GraphData` (interface) | [E] mpga-plugin/cli/src/generators/graph-md.ts :: GraphData |
| `buildGraph` (function) | [E] mpga-plugin/cli/src/generators/graph-md.ts :: buildGraph |
| `renderGraphMd` (function) | [E] mpga-plugin/cli/src/generators/graph-md.ts :: renderGraphMd |
| `renderIndexMd` (function) | [E] mpga-plugin/cli/src/generators/index-md.ts :: renderIndexMd |
| `ScopeInfo` (interface) | [E] mpga-plugin/cli/src/generators/scope-md.ts :: ScopeInfo |
| `getScopeName` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts :: getScopeName |
| `groupIntoScopes` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts :: groupIntoScopes |
| `renderScopeMd` (function) | [E] mpga-plugin/cli/src/generators/scope-md.ts :: renderScopeMd |

## Files

- `mpga-plugin/cli/src/generators/graph-md.ts` (177 lines, typescript)
- `mpga-plugin/cli/src/generators/index-md.ts` (77 lines, typescript)
- `mpga-plugin/cli/src/generators/scope-md.ts` (356 lines, typescript)

## Deeper splits

<!-- TODO: Pointers to smaller sub-topic scopes if this capability is large enough to split -->

## Confidence and notes

- **Confidence:** low — auto-generated, not yet verified
- **Evidence coverage:** 0/9 verified
- **Last verified:** 2026-03-22
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history

- 2026-03-22: Initial scope generation via `mpga sync`