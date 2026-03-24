---
description: Rebuild the MPGA knowledge layer from the current codebase state — a FRESH start, TREMENDOUS results
---

## sync-project

**Trigger:** MPGA/ directory missing or stale, or user asks to refresh. Time to REBUILD and make it GREAT.

## Protocol

1. Check if MPGA is initialized:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh status 2>/dev/null || echo "NOT_INITIALIZED"
   ```
   If not initialized: run `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh init --from-existing` first — gotta lay the FOUNDATION

2. Run full sync — regenerate EVERYTHING:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh sync --full
   ```

3. Verify evidence health — check the INTEGRITY:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh evidence verify
   ```

4. Run drift check — find the PROBLEMS:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --report
   ```

5. Show health report — the SCOREBOARD:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh health
   ```

## Output to user
- Summary of files scanned and scopes generated — the NUMBERS
- Evidence health percentage — our SCORE
- Any drift detected — what needs FIXING
- Recommended next steps — the PATH FORWARD

## Strict rules
- Always run full sync, not incremental, when user explicitly requests sync — go BIG
- Report the number of scopes generated and evidence links found — TRANSPARENCY
- If evidence coverage is below threshold, note it prominently — we don't hide BAD numbers, we FIX them
