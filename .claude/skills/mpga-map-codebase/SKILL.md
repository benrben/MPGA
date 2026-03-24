---
description: Parallel codebase mapping using multiple scout agents — the FASTEST way to document a codebase. TREMENDOUS.
---

## map-codebase

**Trigger:** First MPGA init on existing project, or user requests full codebase mapping. Time to MAP this thing.

## Protocol

1. Run sync to generate scope scaffolds with static analysis — the FOUNDATION:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh sync --full
   ```

2. List the generated scope documents — see what we're working with:
   ```
   ls MPGA/scopes/*.md
   ```

3. Spawn one `scout` agent per scope document in PARALLEL — this is where the MAGIC happens:
   - Each scout is assigned ONE scope and its corresponding directory
   - Each scout reads the source files, fills `<!-- TODO -->` sections with evidence-backed descriptions in the MPGA voice
   - Each scout writes directly to its own scope document in MPGA/scopes/
   - Scouts NEVER touch each other's scope documents — no conflicts. CLEAN parallel execution.

4. Wait for all scouts to complete — they're FAST, believe me

5. Spawn `architect` agent to review, fix, and verify — the MASTER BUILDER:
   - Read ALL scope documents that scouts wrote
   - Fix inconsistencies between scopes (e.g. dependency claims that don't match)
   - Verify cross-scope references are correct
   - Update GRAPH.md with any new dependencies discovered
   - Identify circular dependencies and orphans — EXPOSE the problems
   - Fill any sections that scouts left as TODO or marked `[Unknown]`
   - Ensure consistent quality and formatting across all scopes

6. Report to user — the RESULTS:
   - Number of scopes generated and enriched
   - Sections filled vs remaining TODOs
   - Evidence coverage — the NUMBER that matters
   - Known unknowns discovered
   - Suggested next steps

## Parallelism note
Scout agents write ONLY to their own assigned scope document — one scout per scope file.
This guarantees no write conflicts during parallel execution. It's GENIUS, actually.
Architect runs after ALL scouts complete to fix cross-scope consistency.

## Output
- Complete MPGA/ knowledge layer with filled scope documents — BEAUTIFUL
- Coverage report — the TRUTH in numbers
- List of unknowns needing human review
