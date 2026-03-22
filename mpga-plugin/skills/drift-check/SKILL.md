---
description: Check for evidence drift and attempt to heal stale links
---

## drift-check

**Trigger:** After file writes (automatic via hook), or on demand

## Protocol

1. Run quick drift check:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --quick
   ```

2. If stale links found:
   a. Run auto-heal:
      ```
      mpga evidence heal --auto
      ```
   b. Report what was healed vs what needs manual review

3. Update scope doc status fields if needed

4. If in CI mode:
   ```
   ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --ci --threshold 80
   ```
   Exit non-zero if below threshold.

## Hook integration
This skill is called automatically by the PostToolUse hook after Write/Edit operations.
In hook mode, output should be minimal — only warn if drift is detected.

## Output
- Number of stale links found
- Number of links auto-healed
- Links that need manual review (symbol not found)
- Overall health percentage
