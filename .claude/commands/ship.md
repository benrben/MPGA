# /mpga:ship

Verify, commit, and update documentation after completing work.

## Steps

1. Run full test suite — must pass
2. Run `mpga-plugin/bin/mpga.sh evidence verify` — flag any new stale links
3. Update scope documents with new evidence links produced this session
4. Create atomic commit(s) with conventional commit messages
5. Update milestone status: `mpga-plugin/bin/mpga.sh milestone status`
6. Archive done tasks: `mpga-plugin/bin/mpga.sh board archive`
7. Offer options: merge / create PR / keep branch

## Usage
```
/mpga:ship
```

## Commit message format
Follow conventional commits:
- `feat: <description>` — new feature
- `fix: <description>` — bug fix
- `refactor: <description>` — refactoring
- `test: <description>` — tests only
- `docs: <description>` — documentation updates

## Pre-ship checklist
- [ ] All tests passing
- [ ] Test coverage at or above 80% (target 100%) — coverage below 80% blocks shipping
- [ ] No stubs or TODOs in committed code
- [ ] Scope evidence links updated
- [ ] Board tasks moved to done
- [ ] Milestone progress updated
