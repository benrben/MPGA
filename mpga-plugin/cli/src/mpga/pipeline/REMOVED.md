# REMOVED: pipeline module

This directory previously contained:

- `__init__.py` — re-exported `normalize` and `NormalizeResult`
- `normalizer.py` — drift verify → heal → re-verify → rewrite-health pipeline

## What it did

The `normalize(project_root, config)` function ran a 5-step pipeline:
1. First drift pass to collect stale/healable evidence links
2. Wrote healed items back to scope files
3. Downgraded stale items to valid line-range refs where possible
4. Second drift pass to get updated health statistics
5. Rewrote the `- **Health:**` line in each scope file

## Why it was removed

The pipeline/ abstraction layer was redundant — callers could invoke
`run_drift_check`, `heal_scope_file`, and `try_downgrade_stale` from
`mpga.evidence.drift` directly. Removing the indirection simplified the
codebase and eliminated the separate normalize step in the init/sync flow.

The functionality was inlined into the callers or removed as part of the
Python conversion refactor (see commit history for details).

## Replacement

Use `mpga.evidence.drift` directly:
- `run_drift_check(scope_file, project_root)` — check evidence links
- `heal_scope_file(scope_file, project_root)` — auto-heal stale links
- `try_downgrade_stale(link, project_root)` — downgrade stale to range ref
