# Scope: src-generators

## Summary

The **generators** subsystem produces the three markdown artifacts that form the MPGA knowledge layer: scope documents (`scopes/*.md`), dependency graph (`GRAPH.md`), and project index (`INDEX.md`).

## Where to start in code

- [E] `src/generators/scope-md.ts` — scope document generation with evidence index
- [E] `src/generators/graph-md.ts` — module dependency graph + Mermaid diagram

## Context / stack / skills

- **Languages:** TypeScript
- **Output format:** Markdown with Mermaid diagrams

## Who and what triggers it

- `mpga sync` invokes all three generators in sequence
- `mpga graph` invokes only the graph generator

## What happens

### Scope generation (`scope-md.ts`)

1. `groupIntoScopes(scanResult, graph?)` groups files by top-level directory
2. For each group: extracts exported symbols (TS/JS/Python/Go regex), detects entry points, identifies inter-scope imports
3. `renderScopeMd(scope)` generates a 13-section markdown template:
   - Auto-populated: Summary, Where to start, Context, Evidence index (up to 40 symbols), Files (up to 30), Navigation, Relationships, Diagram
   - TODO placeholders: Who triggers it, What happens, Rules, Examples, UI, Traces, Deeper splits, Confidence

Evidence index uses the evidence link format (`filepath :: symbol`) without line numbers at generation time — line ranges are added later by `evidence heal`.

### Graph generation (`graph-md.ts`)

1. `buildGraph(scanResult)` groups files by top-level dir as "modules"
2. Extracts imports via regex (TS/JS `import/require`, Python `from/import`)
3. Resolves relative imports to module names, builds directed dependency map
4. Circular dep detection: pairwise reverse-edge check (not full DFS cycle detection)
5. `renderGraphMd(graph)` outputs dependency list, circular warnings, orphan list, Mermaid `graph TD` (capped at 30 edges)

### Index generation (`index-md.ts`)

`renderIndexMd()` generates the top-level `INDEX.md` with: identity section (type, size, language breakdown), key files table (top 10 by size), conventions placeholder, agent trigger table (5 example rows), scope registry, active milestone, known unknowns.

Note: `evidenceCoverage` is always passed as `0` from `sync.ts` — it is never actually computed during sync.

## Rules and edge cases

- Scope grouping: single-path-component files go into `root` group, others group by `parts[0]`
- Entry point detection tries 8 patterns; if none match, picks largest file by line count
- Graph orphan detection uses basename (not module name) — likely buggy for real orphan detection
- `renderScopeMd` never writes a `**Health:**` line, causing `scope list` to always show `? unknown`
- Mermaid output caps at 30 edges to prevent overwhelming diagrams

## Navigation

**Parent:** [src](./src.md)

**Used by:** [src-commands](./src-commands.md) (sync, graph, scope commands)

**Depends on:** [src-core](./src-core.md) (scanner provides file data)

## Evidence index

| Claim | Evidence |
|-------|----------|
| `groupIntoScopes` | [E] src/generators/scope-md.ts |
| `renderScopeMd` | [E] src/generators/scope-md.ts |
| `buildGraph` | [E] src/generators/graph-md.ts |
| `renderGraphMd` | [E] src/generators/graph-md.ts |
| `renderIndexMd` | [E] src/generators/index-md.ts |

## Files

- `src/generators/scope-md.ts` (322 lines)
- `src/generators/graph-md.ts` (158 lines)
- `src/generators/index-md.ts` (77 lines)

## Confidence and notes

- **Confidence:** high — manually verified
- **Last verified:** 2026-03-22
- **Drift risk:** low
- `evidenceCoverage` always `0` during sync is a known gap

## Change history

- 2026-03-22: Created as sub-scope split from src
