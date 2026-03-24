# /mpga:drift

Check and report evidence drift across all scope documents.

## Steps

1. Run `node ./.mpga-runtime/cli/dist/index.js drift --report`
2. Display drift report
3. If stale links found: offer to run `node ./.mpga-runtime/cli/dist/index.js evidence heal`
4. Show CI pass/fail status

## Usage
```
/mpga:drift
```
