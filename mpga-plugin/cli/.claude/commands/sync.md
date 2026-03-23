# /mpga:sync

Rebuild the MPGA knowledge layer from the current codebase state.

## Steps

1. Check if MPGA is initialized, init if needed
2. Run full sync: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh sync --full`
3. Verify evidence health: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh evidence verify`
4. Run drift check: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --report`
5. Show health report: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh health`

## Usage
```
/mpga:sync
```
