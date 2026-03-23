# /mpga:develop

Orchestrate the TDD cycle for a task (red → green → blue → review).

## Steps

1. Claim the task: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board claim <task-id>`
2. Load context: task card + relevant scope docs
3. **red↔green micro-cycle**: red-dev writes ONE failing test (starting with degenerate case), green-dev makes it pass, repeat until all acceptance criteria covered. If green-dev hits an architectural wall, blue-dev does a structural refactor mid-cycle.
4. **blue-dev**: refactor both production code and tests (without changing assertions)
5. **reviewer**: review for quality, testability, and degenerate case coverage
6. Record evidence and move task to done

## Usage
```
/mpga:develop
/mpga:develop T001
```
