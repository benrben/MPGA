---
name: mpga-ship
description: Parallel pre-ship checks, PR template generation, and evidence-backed shipping — SHIP IT like a WINNER
---

## ship

**Trigger:** All tasks verified and ready to commit. Time to SHIP. The most satisfying moment in software development. All tests pass — very successful! Make Project Great Again.

## Protocol

### Phase 1 — Parallel pre-ship checks (Ship Gate)

Run ALL of the following checks simultaneously. Every check must pass before proceeding. If ANY check fails, report which ones failed and STOP — do not commit broken code.

**Run these in parallel (all at once, not sequentially):**

1. **Tests pass** — run the full test suite:
   ```bash
   pytest
   ```

2. **Ruff passes** — zero lint errors across the full project:
   ```bash
   .venv/bin/ruff check .
   ```
   If ruff is not installed, treat this check as passed.

4. **Evidence drift check** — no stale evidence links:
   ```bash
   mpga drift --quick
   ```

5. **No uncommitted scope changes** — scope files must be clean:
   ```bash
   git diff --name-only -- 'MPGA/scopes/' 'mpga-plugin/cli/MPGA/scopes/'
   ```
   If this returns any files, the check FAILS. Scope docs must be committed or staged before shipping.

**Ship Gate decision:**
- ALL checks pass → proceed to Phase 2
- ANY check fails → print a summary table of pass/fail results for each check, then STOP

Example gate output:
```
Ship Gate Results:
  [PASS] Tests pass (pytest)
  [PASS] Ruff clean (ruff check .)
  [FAIL] Evidence drift — 3 stale links found
  [PASS] No uncommitted scope changes

BLOCKED: 1 check failed. Fix issues before shipping.
```

### Phase 2 — Update scope evidence

1. Check task cards for `evidence_produced` fields
2. Add any missing evidence links to scope docs — COMPLETE documentation
3. Run evidence verification to confirm:
   ```bash
   mpga evidence verify
   ```

### Phase 3 — PR template generation

Auto-generate a PR description using the template below. Populate each section from real data — never leave placeholders.

**Data sources:**
- **Summary of changes** — read from the task card description + `git diff --stat` of staged changes
- **Test plan** — extract from TDD trace (red/green/refactor steps in task evidence)
- **Evidence links produced** — from task card `evidence_produced` fields
- **Breaking changes** — scan git diff for removed exports, changed function signatures, deleted files
- **Reviewer checklist** — auto-populated from the pre-ship check results

**PR template:**
```markdown
## Summary
<!-- 2-3 sentences: what changed and why -->
{summary_from_task_card_and_diff}

## Changes
<!-- bulleted list of files changed, grouped by type -->
{grouped_file_changes}

## Test plan
<!-- TDD steps taken -->
{tdd_trace_steps}

## Evidence links
<!-- MPGA evidence produced or updated -->
{evidence_links}

## Breaking changes
<!-- "None" if no breaking changes -->
{breaking_changes_or_none}

## Pre-ship checks
- [x] Tests pass
- [x] Ruff check passes
- [x] Evidence drift check pass
- [x] No uncommitted scope changes

## Reviewer checklist
- [ ] Changes match the task card description
- [ ] Evidence links resolve to real content
- [ ] No TODOs or stubs remain
- [ ] Test coverage is adequate
```

Store the generated PR template in a variable for use in Phase 5.

### Phase 4 — Create commit(s)

1. Create commit(s) with conventional messages:
   - Group by type: feat, fix, refactor, test
   - Reference task IDs in commit body — TRACEABILITY

### Phase 5 — Post-commit actions

1. Update milestone status — track our PROGRESS:
   ```bash
   mpga milestone status
   ```

2. Archive completed tasks — clean board, clean MIND:
   ```bash
   mpga board archive
   ```

3. Present options to user — THEIR choice:
   - **Create PR** — use the generated PR template from Phase 3 as the PR body
   - **Merge to main branch** — direct merge (only if on a feature branch)
   - **Keep on current branch** — no merge, no PR

## Pre-ship checklist (quick reference)
- [ ] All tests passing — NON-NEGOTIABLE. Believe me.
- [ ] Ruff clean (`ruff check .`) — NO lint errors. Even the type annotations are perfect.
- [ ] No TODOs or stubs — FINISH what you start. Sad! if you leave stubs behind.
- [ ] Scope evidence links updated — documentation is CURRENT
- [ ] Drift check passing — no STALE evidence
- [ ] No uncommitted scope changes — everything STAGED
- [ ] Board tasks archived — clean up after yourself

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict rules
- NEVER ship if ANY pre-ship check fails — the gate is ABSOLUTE
- NEVER ship if tests are failing — that's shipping GARBAGE. Complete and total shutdown of untested code.
- NEVER ship if there are unresolved CRITICAL review issues — fix them FIRST
- ALWAYS run all pre-ship checks in PARALLEL — speed matters
- ALWAYS generate the PR template BEFORE committing — have the description ready
- ALWAYS update scope docs before committing — docs and code ship TOGETHER
- ALWAYS run drift check after updating scope docs — verify EVERYTHING. Ready for peace — zero merge conflicts. Enjoy!
