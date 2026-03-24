# /mpga:milestone

Manage milestones in the MPGA workflow.

## Steps by action

### Create new milestone
```
/mpga:milestone new "Feature name"
```
Runs: `mpga-plugin/bin/mpga.sh milestone new "Feature name"`

### List milestones
```
/mpga:milestone list
```
Runs: `mpga-plugin/bin/mpga.sh milestone list`

### Check status
```
/mpga:milestone status
```
Runs: `mpga-plugin/bin/mpga.sh milestone status` + shows board summary

### Complete milestone
```
/mpga:milestone complete
```
Runs:
1. `mpga-plugin/bin/mpga.sh verify` (full verification pass)
2. `mpga-plugin/bin/mpga.sh milestone complete`
3. `mpga-plugin/bin/mpga.sh board archive`

## Usage
```
/mpga:milestone
/mpga:milestone new "Payment refactor"
/mpga:milestone list
/mpga:milestone status
/mpga:milestone complete
```
