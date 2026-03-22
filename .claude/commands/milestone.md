# /mpga:milestone

Manage milestones in the MPGA workflow.

## Steps by action

### Create new milestone
```
/mpga:milestone new "Feature name"
```
Runs: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone new "Feature name"`

### List milestones
```
/mpga:milestone list
```
Runs: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone list`

### Check status
```
/mpga:milestone status
```
Runs: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone status` + shows board summary

### Complete milestone
```
/mpga:milestone complete
```
Runs:
1. `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh verify` (full verification pass)
2. `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh milestone complete`
3. `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board archive`

## Usage
```
/mpga:milestone
/mpga:milestone new "Payment refactor"
/mpga:milestone list
/mpga:milestone status
/mpga:milestone complete
```
