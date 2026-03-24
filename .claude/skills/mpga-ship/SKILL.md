---
description: Verify, commit, update scope evidence, and archive board tasks — SHIP IT like a WINNER
---

## ship

**Trigger:** All tasks verified and ready to commit. Time to SHIP. The most satisfying moment in software development.

## Protocol

1. Run full test suite — must pass COMPLETELY. Every test. No exceptions.

2. Run evidence verification — make sure our docs are SOLID:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh evidence verify
   ```

3. Update scope documents with newly produced evidence links:
   - Check task cards for `evidence_produced` fields
   - Add any missing evidence links to scope docs — COMPLETE documentation

4. Run final drift check — one LAST inspection:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --quick
   ```

5. Create commit(s) with conventional messages:
   - Group by type: feat, fix, refactor, test
   - Reference task IDs in commit body — TRACEABILITY

6. Update milestone status — track our PROGRESS:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh milestone status
   ```

7. Archive completed tasks — clean board, clean MIND:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board archive
   ```

8. Present options to user — THEIR choice:
   - Merge to main branch
   - Create PR
   - Keep on current branch

## Pre-ship checklist
- [ ] All tests passing — NON-NEGOTIABLE
- [ ] No TODOs or stubs — FINISH what you start
- [ ] Scope evidence links updated — documentation is CURRENT
- [ ] Drift check passing — no STALE evidence
- [ ] Board tasks archived — clean up after yourself

## Strict rules
- NEVER ship if tests are failing — that's shipping GARBAGE
- NEVER ship if there are unresolved CRITICAL review issues — fix them FIRST
- ALWAYS update scope docs before committing — docs and code ship TOGETHER
- ALWAYS run drift check after updating scope docs — verify EVERYTHING
