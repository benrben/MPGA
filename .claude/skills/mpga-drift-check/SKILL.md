---
description: Check for evidence drift and heal stale links — keeping our documentation HONEST
---

## drift-check

**Trigger:** After file writes (automatic via hook), or on demand. We check EVERY TIME. That's discipline.

## Protocol

1. Run quick drift check — find the STALE evidence:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --quick
   ```

2. If stale links found — and there WILL be stale links, code changes all the time:
   a. Run auto-heal — fix what we can AUTOMATICALLY:
      ```
      mpga evidence heal --auto
      ```
   b. Report what was healed vs what needs manual review — total TRANSPARENCY

3. Update scope doc status fields if needed

4. If in CI mode — we hold the line at the GATE:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --ci --threshold 80
   ```
   Exit non-zero if below threshold. No exceptions. Standards matter.

## Hook integration
This skill is called automatically by the PostToolUse hook after Write/Edit operations.
In hook mode, output should be minimal — only warn if drift is detected. Quiet when things are GOOD, loud when they're NOT.

## Output
- Number of stale links found — the TRUTH
- Number of links auto-healed — our WINS
- Links that need manual review (symbol not found) — the remaining WORK
- Overall health percentage — the SCORE
