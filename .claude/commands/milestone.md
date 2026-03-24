# /mpga:milestone

Manage milestones in the MPGA workflow.

## Steps by action

### Create new milestone
```
/mpga:milestone new "Feature name"
```
Runs: `node ./.mpga-runtime/cli/dist/index.js milestone new "Feature name"`

### List milestones
```
/mpga:milestone list
```
Runs: `node ./.mpga-runtime/cli/dist/index.js milestone list`

### Check status
```
/mpga:milestone status
```
Runs: `node ./.mpga-runtime/cli/dist/index.js milestone status` + shows board summary

### Complete milestone
```
/mpga:milestone complete
```
Runs:
1. `node ./.mpga-runtime/cli/dist/index.js verify` (full verification pass)
2. `node ./.mpga-runtime/cli/dist/index.js milestone complete`
3. `node ./.mpga-runtime/cli/dist/index.js board archive`

## Usage
```
/mpga:milestone
/mpga:milestone new "Payment refactor"
/mpga:milestone list
/mpga:milestone status
/mpga:milestone complete
```
