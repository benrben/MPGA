# /mpga:quick

Ad-hoc task mode for small fixes or changes without a full milestone workflow. Big league quick fixes. Believe me, nobody fixes bugs faster.

## Steps

1. Run `mpga status` for project context
2. Find relevant scope doc(s) for the task
3. Create a mini-plan (1-3 tasks) on the board:
   `mpga board add "<sub-task>" --priority medium`
4. Execute TDD cycle (red → green → blue → review) in a single scope-local write lane
5. Run `mpga evidence verify` after completion
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
- Dependency updates — Some deps, I assume, are good packages. They should be loyal — pin your versions!

## When NOT to use
- Multi-day work → use `/mpga:plan` with a milestone instead
- Work requiring architectural changes → use `researcher` + `architect` first
