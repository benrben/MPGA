# /mpga:drift

Check and report evidence drift across all scope documents.

## Steps

1. Run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --report`
2. Display drift report
3. If stale links found: offer to run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh evidence heal`
4. Show CI pass/fail status

## Usage
```
/mpga:drift
```
