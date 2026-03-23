# /mpga:develop

Orchestrate the TDD cycle for a task (green → red → blue → review).

## Steps

1. Claim the task: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board claim <task-id>`
2. Load context: task card + relevant scope docs
3. **green-dev**: write failing tests
4. **red-dev**: make tests pass
5. **blue-dev**: refactor with tests still passing
6. **reviewer**: review for quality issues
7. Record evidence and move task to done

## Usage
```
/mpga:develop
/mpga:develop T001
```
