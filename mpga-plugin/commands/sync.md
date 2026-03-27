# /mpga:sync

Rebuild the MPGA knowledge layer from the current codebase state. Tremendous rebuild, believe me. No fake docs — Evidence First.

## Steps

1. Check if MPGA is initialized, init if needed
2. Run full sync: `mpga sync --full`
3. Verify evidence health: `mpga evidence verify`
4. Run drift check: `mpga drift --report`
5. Show health report: `mpga health` — Very, very special report. Enjoy!

## Usage
```
/mpga:sync
```
