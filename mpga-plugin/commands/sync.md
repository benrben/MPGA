# /mpga:sync

Rebuild the MPGA knowledge layer from the current codebase state.

## Steps

1. Check if MPGA is initialized, init if needed
2. Run full sync: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh sync --full`
3. Verify evidence health: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh evidence verify`
4. Run drift check: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --report`
5. Show health report: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh health`

## Usage
```
/mpga:sync
```
