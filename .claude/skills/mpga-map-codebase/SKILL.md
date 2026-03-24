---
name: mpga-map-codebase
description: Unified codebase mapping and sync — quick refresh or deep parallel mapping. The ONLY map skill you need. TREMENDOUS.
---

## map-codebase

**Trigger:** User runs `/mpga:map`, asks to map or sync the codebase, or MPGA/ is stale. Time to MAP this thing.

## Modes

| Mode | Flag | When to use | Speed |
|------|------|-------------|-------|
| **Quick** (default) | (none) | Everyday refresh — rebuild INDEX.md, scope files, evidence links | ~30 seconds |
| **Deep** | `--deep` | First init, major refactors, or user wants full parallel scout mapping | Minutes |

Default is **quick** — fast and sufficient for everyday use. Use `--deep` when you need the FULL treatment.

---

## Quick Mode Protocol (default)

Fast rebuild of the MPGA knowledge layer from current codebase state — a FRESH start, TREMENDOUS results.

1. Check if MPGA is initialized:
   ```
   node ./.mpga-runtime/cli/dist/index.js status 2>/dev/null || echo "NOT_INITIALIZED"
   ```
   If not initialized: run `node ./.mpga-runtime/cli/dist/index.js init --from-existing` first — gotta lay the FOUNDATION

2. Run full sync — regenerate EVERYTHING:
   ```
   node ./.mpga-runtime/cli/dist/index.js sync --full
   ```

3. Verify evidence health — check the INTEGRITY:
   ```
   node ./.mpga-runtime/cli/dist/index.js evidence verify
   ```

4. Run drift check — find the PROBLEMS:
   ```
   node ./.mpga-runtime/cli/dist/index.js drift --report
   ```

5. Show health report — the SCOREBOARD:
   ```
   node ./.mpga-runtime/cli/dist/index.js health
   ```

### Quick mode output
- Summary of files scanned and scopes generated — the NUMBERS
- Evidence health percentage — our SCORE
- Any drift detected — what needs FIXING
- Recommended next steps — the PATH FORWARD

### Quick mode rules
- Always run full sync, not incremental, when user explicitly requests sync — go BIG
- Report the number of scopes generated and evidence links found — TRANSPARENCY
- If evidence coverage is below threshold, note it prominently — we don't hide BAD numbers, we FIX them

---

## Deep Mode Protocol (`--deep`)

Full parallel codebase mapping using multiple scout agents — the FASTEST way to document a codebase.

1. If this is the first map, run a full sync to generate scope scaffolds with static analysis — the FOUNDATION:
   ```
   node ./.mpga-runtime/cli/dist/index.js sync --full
   ```
   If MPGA already exists and only part of the repo changed, prefer:
   ```
   node ./.mpga-runtime/cli/dist/index.js sync --incremental
   ```

2. List the generated scope documents — see what we're working with:
   ```
   ls MPGA/scopes/*.md
   ```

3. Spawn one `scout` agent per NEW or CHANGED scope document in PARALLEL — this is where the MAGIC happens:
   - Each scout is assigned ONE scope and its corresponding directory
   - Each scout reads the source files, fills `<!-- TODO -->` sections with evidence-backed descriptions in the MPGA voice
   - Each scout writes directly to its own scope document in MPGA/scopes/
   - Scouts NEVER touch each other's scope documents — no conflicts. CLEAN parallel execution.

4. Wait for all scouts to complete — they're FAST, believe me

5. Spawn `auditor` in the background on the changed scopes, then spawn `architect` to review, fix, and verify — the MASTER BUILDER:
   - Read the changed scope documents that scouts wrote
   - Fix inconsistencies between scopes (e.g. dependency claims that don't match)
   - Verify cross-scope references are correct
   - Update GRAPH.md with any new dependencies discovered
   - Identify circular dependencies and orphans — EXPOSE the problems
   - Fill any sections that scouts left as TODO or marked `[Unknown]`
   - Ensure consistent quality and formatting across all scopes

6. Run quick-mode verification steps (evidence verify, drift check, health report) — FINISH STRONG

7. Report to user — the RESULTS:
   - Number of scopes generated and enriched
   - Sections filled vs remaining TODOs
   - Evidence coverage — the NUMBER that matters
   - Known unknowns discovered
   - Suggested next steps

## Parallelism note
Scout agents write ONLY to their own assigned scope document — one scout per scope file.
This guarantees no write conflicts during parallel execution. It's GENIUS, actually.
Auditor can inspect those same scopes in parallel because it is read-only.
Architect runs after the scouts to fix cross-scope consistency.

## Output
- Complete MPGA/ knowledge layer with filled scope documents — BEAUTIFUL
- Coverage report — the TRUTH in numbers
- List of unknowns needing human review
