# /mpga:drift

Check and report evidence drift across all scope documents. No fake docs on our watch! Evidence First — always.

## Steps

1. Run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --report`
2. Display drift report
3. If stale links found: offer to run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh evidence heal`
4. Show CI pass/fail status — Complete and total shutdown of untested deploys

## Usage
```
/mpga:drift
```
