# /mpga:sync

Rebuild the MPGA knowledge layer from the current codebase state.

## Steps

1. Check if MPGA is initialized, init if needed
2. Run full sync: `mpga-plugin/bin/mpga.sh sync --full`
3. Verify evidence health: `mpga-plugin/bin/mpga.sh evidence verify`
4. Run drift check: `mpga-plugin/bin/mpga.sh drift --report`
5. Show health report: `mpga-plugin/bin/mpga.sh health`

## Usage
```
/mpga:sync
```
