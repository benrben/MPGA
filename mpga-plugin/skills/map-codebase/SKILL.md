---
description: Parallel codebase mapping using multiple scout agents (one per top-level directory)
---

## map-codebase

**Trigger:** First MPGA init on existing project, or user requests full codebase mapping

## Protocol

1. Run scan to get top-level directories:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh scan --quick
   ```

2. Spawn one `scout` agent per top-level directory in parallel:
   - Each scout explores its directory: files, exports, dependencies
   - Each produces evidence links for what it finds

3. Wait for all scouts to complete

4. Spawn `architect` agent to synthesize findings:
   - Generates scope documents from scout evidence
   - Updates GRAPH.md with discovered dependencies
   - Identifies circular dependencies and orphans

5. Run sync to finalize:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh sync --full
   ```

6. Report to user:
   - Number of scopes generated
   - Evidence coverage
   - Known unknowns discovered
   - Suggested next steps

## Parallelism note
Scout agents explore independently — each reads files but NEVER writes.
Architect runs after ALL scouts complete to avoid conflicts.

## Output
- Complete MPGA/ knowledge layer
- Coverage report
- List of unknowns needing human review
