# /mpga:sync

Rebuild the MPGA knowledge layer from the current codebase state.

## Steps

1. Check if MPGA is initialized, init if needed
2. Run full sync: `node ./.mpga-runtime/cli/dist/index.js sync --full`
3. Verify evidence health: `node ./.mpga-runtime/cli/dist/index.js evidence verify`
4. Run drift check: `node ./.mpga-runtime/cli/dist/index.js drift --report`
5. Show health report: `node ./.mpga-runtime/cli/dist/index.js health`

## Usage
```
/mpga:sync
```
