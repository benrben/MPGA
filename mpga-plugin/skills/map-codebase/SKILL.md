---
description: Parallel codebase mapping using multiple scout agents (one per top-level directory)
---

## map-codebase

**Trigger:** First MPGA init on existing project, or user requests full codebase mapping

## Protocol

1. Run sync to generate scope scaffolds with static analysis:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh sync --full
   ```

2. List the generated scope documents:
   ```
   ls MPGA/scopes/*.md
   ```

3. Spawn one `scout` agent per scope document in parallel:
   - Each scout is assigned ONE scope and its corresponding directory
   - Each scout reads the source files, fills `<!-- TODO -->` sections with evidence-backed descriptions
   - Each scout writes directly to its own scope document in MPGA/scopes/
   - Scouts NEVER touch each other's scope documents — no conflicts

4. Wait for all scouts to complete

5. Spawn `architect` agent to review, fix, and verify:
   - Read ALL scope documents that scouts wrote
   - Fix inconsistencies between scopes (e.g. dependency claims that don't match)
   - Verify cross-scope references are correct
   - Update GRAPH.md with any new dependencies discovered
   - Identify circular dependencies and orphans
   - Fill any sections that scouts left as TODO or marked `[Unknown]`
   - Ensure consistent quality and formatting across all scopes

6. Report to user:
   - Number of scopes generated and enriched
   - Sections filled vs remaining TODOs
   - Evidence coverage
   - Known unknowns discovered
   - Suggested next steps

## Parallelism note
Scout agents write ONLY to their own assigned scope document — one scout per scope file.
This guarantees no write conflicts during parallel execution.
Architect runs after ALL scouts complete to fix cross-scope consistency.

## Output
- Complete MPGA/ knowledge layer with filled scope documents
- Coverage report
- List of unknowns needing human review
