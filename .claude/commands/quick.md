# /mpga:quick

Ad-hoc task mode for small fixes or changes without a full milestone workflow.

## Steps

1. Read `MPGA/INDEX.md` for project context
2. Find relevant scope doc(s) for the task
3. Create a mini-plan (1-3 tasks) on the board:
   `node ./.mpga-runtime/cli/dist/index.js board add "<sub-task>" --priority medium`
4. Execute TDD cycle (red → green → blue → review) in a single scope-local write lane
5. Run `node ./.mpga-runtime/cli/dist/index.js evidence verify` after completion
6. Commit with descriptive message

## Usage
```
/mpga:quick "Fix the login button not responding on mobile Safari"
/mpga:quick "Add email validation to the registration form"
```

## When to use
- Bug fixes
- Small feature additions
- Configuration changes
- Dependency updates

## When NOT to use
- Multi-day work → use `/mpga:plan` with a milestone instead
- Work requiring architectural changes → use `researcher` + `architect` first
