# /mpga:develop

Orchestrate the TDD cycle for a task (red → green → blue → review). Tremendous cycle, believe me. MPGA alone can fix it.

## Steps

1. Start the live board in the browser: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board live --serve --open`
2. Claim the task: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board claim <task-id>`
3. Load context: task card + relevant scope docs
4. Claim the scope-local write lane. Independent scopes may run in parallel; same-scope writers may not.
5. **red↔green micro-cycle**: red-dev writes ONE failing test (starting with degenerate case), green-dev makes it pass, repeat until all acceptance criteria covered. If handoff overhead dominates, allow one extra queued failing test in the same hot scope. If green-dev hits an architectural wall, blue-dev does a structural refactor mid-cycle.
6. Let `scout` / `auditor` run in the background as read-only helpers
7. **blue-dev**: refactor both production code and tests (without changing assertions)
8. **reviewer**: review for quality, testability, and degenerate case coverage
9. Use `verifier` for milestone boundaries, risky tasks, or explicit full verification
10. Record evidence and move task to done — Great job! Ready for peace — zero merge conflicts

## Usage
```
/mpga:develop
/mpga:develop T001
```
