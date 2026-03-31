---
name: mpga-map-codebase
description: Unified codebase mapping and sync — quick refresh or deep parallel mapping. The ONLY map skill you need. TREMENDOUS.
---

## map-codebase

**Trigger:** User runs `/mpga:map`, asks to map or sync the codebase, or the DB (`.mpga/mpga.db`) is stale. Time to MAP this thing.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

**Exception:** This skill MAY run these `mpga` commands directly (infrastructure / read-only project shape, **no** source edits):
`sync`, `evidence verify`, `drift`, `health`, `status`, `scope list`, `scope show`, `scan` (`--json`/`--quick` as needed), `graph show`, `graph export`.

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

### Orchestration hygiene (fixes common workflow bugs)
- **Never** run `sqlite3` against `.mpga/mpga.db` (or ad-hoc SQL) for routine inspection — that bypasses the supported surface. Use `mpga scope list`, `mpga scope show <name> --full`, `mpga scope show <name> --json`, `mpga status`, `mpga health`, `mpga scan --json`.
- **Scout hand-off:** scouts persist scope bodies **only** via `mpga scope update <name> --file …` or **stdin** with the **full** document (`mpga scope update --help`). Flags like `--description` or `--field` do **not** exist — see agent `scout.md`.
- **Do not** tell scouts to leave `enriched.md` (or similar) in the **repo root**; temp paths under `/tmp` or pipes are fine.
- **Architect / graph:** prefer `mpga graph show` and `mpga graph export`; do not assume `GRAPH.md` exists on disk. Scope fixes use the same `mpga scope update` contract as scouts.

**Agent brief:** Scope list from CLI, file boundaries from scanner, change detection from git/sync.
**Expected output:** Enriched scope documents with evidence links, coverage metrics, and unknowns list.

## Modes

| Mode | Flag | When to use | Speed |
|------|------|-------------|-------|
| **Quick** (default) | (none) | Everyday refresh — rebuild INDEX.md, scope files, evidence links | ~30 seconds |
| **Deep** | `--deep` | First init, major refactors, or user wants parallel scout mapping of the RELEVANT authored scopes | Minutes |

Default is **quick** — fast and sufficient for everyday use. Use `--deep` when you need the FULL treatment.

---

## Quick Mode Protocol (default)

Fast rebuild of the MPGA knowledge layer from current codebase state — a FRESH start, TREMENDOUS results. Make Project Great Again, one scope at a time.

1. Check if MPGA is initialized:
   ```
   mpga status 2>/dev/null || echo "NOT_INITIALIZED"
   ```
   If not initialized: run `mpga init --from-existing` first — gotta lay the FOUNDATION

2. Run full sync — regenerate EVERYTHING:
   ```
   mpga sync --full --skip-if-fresh 10
   ```
   Skips sync if the DB was synced less than 10 minutes ago — avoids redundant work during rapid iteration

3. Verify evidence health — check the INTEGRITY:
   ```
   mpga evidence verify
   ```

4. Run drift check — find the PROBLEMS:
   ```
   mpga drift --report
   ```

5. Show health report — the SCOREBOARD:
   ```
   mpga health
   ```

### Quick mode output
- Summary of files scanned and scopes generated — the NUMBERS
- Evidence health percentage — our SCORE
- Any drift detected — what needs FIXING
- Recommended next steps — the PATH FORWARD

### Quick mode rules
- Always run full sync, not incremental, when user explicitly requests sync — go BIG
- Report the number of scopes generated and evidence links found — TRANSPARENCY
- If evidence coverage is below threshold, note it prominently — Fake docs detected! We don't hide BAD numbers, we FIX them

---

## Deep Mode Protocol (`--deep`)

Focused parallel codebase mapping using multiple scout agents — the FASTEST way to document the parts that actually matter.

1. Run sync with changed-scope detection — the FOUNDATION:
   ```
   SYNC_OUTPUT=$(mpga sync --output-changed-scopes --skip-if-fresh 10)
   echo "$SYNC_OUTPUT"
   ```
   Parse the output:
   - If sync was skipped (no `---CHANGED-SCOPES---` sentinel in output): skip scouting entirely and report "Sync was skipped (fresh) — nothing to scout"
   - If sentinel is present, capture the lines after `---CHANGED-SCOPES---` as `CHANGED_SCOPES`
   - If `CHANGED_SCOPES` is empty: skip scouting and report "No scopes changed — nothing to scout"
   - If `CHANGED_SCOPES` is non-empty: proceed to step 4 using ONLY those scope names

2. List the generated scope documents — see what we're working with:
   ```
   mpga scope list
   ```

3. Build the DEEP candidate list before spawning anybody — very important, very smart:
   - Start from the `CHANGED_SCOPES` list captured in step 1, then FILTER HARD
   - Skip scopes whose files live mostly under `.gitignore`, `mpga.config.json` ignore entries, or obvious junk / generated / dependency roots
   - Always skip vendored and generated trees unless the user EXPLICITLY asks for them: `node_modules/`, `dist/`, `build/`, `.venv/`, `venv/`, `site-packages/`, coverage outputs, caches, exported configs, generated MPGA artifacts
   - If a scope is technically present but logically not worth enriching, SKIP IT. Example: giant dependency buckets like `python3.12`, vendored test suites, generated runtime folders
   - If every changed scope is ignored / vendored / generated, do NOT spawn scouts just to make noise. Report the skip and recommend tightening scan config or doing a focused source-only map

4. Spawn one `scout` agent per ELIGIBLE scope in `CHANGED_SCOPES` in PARALLEL — this is where the MAGIC happens:
   - Only scopes that appeared after `---CHANGED-SCOPES---` in the sync output are eligible — unchanged scopes are SKIPPED
   - Each scout is assigned ONE scope and its corresponding authored directory
   - Each scout reads the source files, fills `<!-- TODO -->` sections with evidence-backed descriptions in the MPGA voice
   - Each scout writes directly to its own scope document in the DB (`.mpga/mpga.db`)
   - Scouts NEVER touch each other's scope documents — no conflicts. CLEAN parallel execution.

5. Wait for all scouts to complete — they're FAST, believe me

6. Spawn `auditor` in the background on the changed scopes, then spawn `architect` to review, fix, and verify — the MASTER BUILDER:
   - Read the changed scope documents that scouts wrote
   - Fix inconsistencies between scopes (e.g. dependency claims that don't match)
   - Verify cross-scope references are correct
   - Align dependency narrative with `mpga graph export` / scope docs (and any project-owned graph artifact — not necessarily `GRAPH.md`)
   - Identify circular dependencies and orphans — EXPOSE the problems
   - Fill any sections that scouts left as TODO or marked `[Unknown]`
   - Make sure no skipped vendor / ignored scope accidentally slipped into the deep pass
   - Ensure consistent quality and formatting across all scopes

7. Run quick-mode verification steps (evidence verify, drift check, health report) — FINISH STRONG

8. Report to user — the RESULTS:
   - Number of scopes generated and enriched
   - Number of scopes intentionally skipped, and WHY
   - Sections filled vs remaining TODOs
   - Evidence coverage — the NUMBER that matters
   - Known unknowns discovered
   - Suggested next steps

## Parallelism note
Scout agents write ONLY to their own assigned scope document — one scout per eligible scope file. Build the wall between modules!
This guarantees no write conflicts during parallel execution. It's GENIUS, actually. No collusion between modules!
Auditor can inspect those same scopes in parallel because it is read-only.
Architect runs after the scouts to fix cross-scope consistency.

## Deep mode scope filter

Before deep enrichment, ask: "Is this OUR code, or somebody else's baggage?"

- Include authored source scopes with real TODOs, drift, or recent change
- Skip anything dominated by ignored or generated paths
- Skip dependency megascopes unless the user explicitly asks for vendor mapping
- Use `.gitignore`, `mpga.config.json`, and local project logic together — not just raw file presence
- When in doubt, bias toward focused authored scopes over broad dependency directories
- Call out every skipped scope in the final report so the user sees the decision

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Output
- Complete knowledge layer with filled scope documents in the DB (`.mpga/mpga.db`) — BEAUTIFUL. Even the type annotations are perfect.
- Deep mode focuses on relevant project scopes, not vendored or ignored dependency forests.
- Coverage report — the TRUTH in numbers. Big league results.
- List of unknowns needing human review — who can figure out this spaghetti? The scouts will.

## Strict Rules
- NEVER read source files directly — scouts own ALL file reading and evidence extraction
- NEVER write scope bodies by hand in the repo or with raw SQL — scouts and architect use **`mpga scope update`** only
- NEVER use `sqlite3` on `.mpga/mpga.db` for orchestration queries — use **`mpga scope`** / **`mpga status`** / **`mpga scan`** / **`mpga graph`**
- mpga CLI commands listed under **Exception** and **Orchestration hygiene** are permitted for the orchestrator
- ALWAYS skip vendored, generated, and dependency scopes unless user explicitly asks for them
- ALWAYS report skipped scopes with reasons — TRANSPARENCY
- One scout per scope. No scout touches another scout's scope document. CLEAN parallel execution.
