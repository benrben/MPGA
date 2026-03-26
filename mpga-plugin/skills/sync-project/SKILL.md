---
name: mpga-sync-project
description: "[MERGED] This skill has been merged into map-codebase. Use /mpga:map instead."
---

## sync-project — MERGED

This skill has been merged into **map-codebase**. Use:

- `/mpga:map` — quick mode (same as the old sync-project behavior)
- `/mpga:map --deep` — full parallel mapping with scout agents

See `mpga-plugin/skills/map-codebase/SKILL.md` for the unified protocol.

## Voice announcement

If spoke is available (`${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke --help` exits 0), announce completion:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.
