# /mpga:verify

Run full verification pass on completed work.

## Steps

1. Spawn `verifier` agent
2. Verifier will:
   - Run full test suite
   - Check for stubs/incomplete implementations
   - Verify evidence links are updated
   - Run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh drift --quick`
   - Confirm milestone progress
3. Display verification report
4. If passed: suggest `/mpga:ship`

## Fast path
- For small, isolated tasks, rely on `reviewer` + quick drift during execution
- Use full `verifier` runs for milestone boundaries, risky work, or explicit verification

## Usage
```
/mpga:verify
/mpga:verify T001     (verify specific task)
```
