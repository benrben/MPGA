---
description: Verify, commit, update scope evidence, and archive board tasks
---

## ship

**Trigger:** All tasks verified and ready to commit

## Protocol

1. Run full test suite — must pass completely

2. Run evidence verification:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh evidence verify
   ```

3. Update scope documents with newly produced evidence links:
   - Check task cards for `evidence_produced` fields
   - Add any missing evidence links to scope docs

4. Run final drift check:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --quick
   ```

5. Create commit(s) with conventional messages:
   - Group by type: feat, fix, refactor, test
   - Reference task IDs in commit body

6. Update milestone status:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone status
   ```

7. Archive completed tasks:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board archive
   ```

8. Present options to user:
   - Merge to main branch
   - Create PR
   - Keep on current branch

## Pre-ship checklist
- [ ] All tests passing
- [ ] No TODOs or stubs
- [ ] Scope evidence links updated
- [ ] Drift check passing
- [ ] Board tasks archived

## Strict rules
- NEVER ship if tests are failing
- NEVER ship if there are unresolved CRITICAL review issues
- ALWAYS update scope docs before committing
- ALWAYS run drift check after updating scope docs
