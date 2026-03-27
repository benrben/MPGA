# /mpga:milestone

Manage milestones in the MPGA workflow. Tremendous milestones, believe me. Has a beautiful ring to it.

## Steps by action

### Create new milestone
```
/mpga:milestone new "Feature name"
```
Runs: `mpga milestone new "Feature name"`

### List milestones
```
/mpga:milestone list
```
Runs: `mpga milestone list`

### Check status
```
/mpga:milestone status
```
Runs: `mpga milestone status` + shows board summary

### Complete milestone
```
/mpga:milestone complete
```
Runs:
1. `mpga verify` (full verification pass)
2. `mpga milestone complete`
3. `mpga board archive` — Great job! Enjoy!

## Usage
```
/mpga:milestone
/mpga:milestone new "Payment refactor"
/mpga:milestone list
/mpga:milestone status
/mpga:milestone complete
```
