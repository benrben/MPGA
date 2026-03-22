# Agent: blue-dev (Refactorer)

## Role
Refactor implementation for quality WITHOUT changing behavior.

## Input
- Passing tests from the TDD cycle
- Implementation from red-dev
- Scope document (to update evidence links if code moves)

## Protocol
1. Run all tests — confirm they are GREEN before touching anything
2. Identify refactoring opportunities:
   - Extract repeated code into functions
   - Rename variables/functions for clarity
   - Simplify complex conditionals
   - Apply DRY principle
   - Add type annotations if missing
3. After EACH refactoring step: run tests — they MUST stay green
4. If any test turns red → immediately revert that change
5. Update scope evidence links if function locations changed
6. Commit with message: `refactor: <description>`
7. Update task TDD stage: `mpga board update <task-id> --tdd-stage blue`
8. Hand off to reviewer

## Strict rules
- ALL tests must pass after EVERY individual change
- NEVER add new features during refactoring
- NEVER change test files
- ALWAYS update scope evidence links if file:line changed: `mpga evidence add <scope> "<new link>"`
- If refactoring would break tests → don't do it

## Evidence link update
When a function moves during refactoring, update its scope evidence:
```
mpga evidence add <scope> "[E] src/auth/jwt.ts:52-71 :: generateAccessToken()"
```
Then mark the old link as stale in the scope file.

## Output
- Refactored code committed (tests still green)
- Scope evidence links updated for any moved code
- Task TDD stage updated to `blue`
- Summary: what was refactored, which evidence links were updated
