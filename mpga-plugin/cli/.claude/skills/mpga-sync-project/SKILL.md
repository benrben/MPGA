---
description: Rebuild the MPGA knowledge layer from the current codebase state
---

## sync-project

**Trigger:** MPGA/ directory missing or stale, or user asks to refresh

## Protocol

1. Check if MPGA is initialized:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh status 2>/dev/null || echo "NOT_INITIALIZED"
   ```
   If not initialized: run `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh init --from-existing` first

2. Run full sync:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh sync --full
   ```

3. Verify evidence health:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh evidence verify
   ```

4. Run drift check:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --report
   ```

5. Show health report:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh health
   ```

## Output to user
- Summary of files scanned and scopes generated
- Evidence health percentage
- Any drift detected
- Recommended next steps

## Strict rules
- Always run full sync, not incremental, when user explicitly requests sync
- Report the number of scopes generated and evidence links found
- If evidence coverage is below threshold, note it prominently
