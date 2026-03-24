# /mpga:verify

Run full verification pass on completed work.

## Steps

1. Spawn `verifier` agent
2. Verifier will:
   - Run full test suite
   - Check for stubs/incomplete implementations
   - Verify evidence links are updated
   - Run `mpga-plugin/bin/mpga.sh drift --quick`
   - Confirm milestone progress
3. Display verification report
4. If passed: suggest `/mpga:ship`

## Usage
```
/mpga:verify
/mpga:verify T001     (verify specific task)
```
