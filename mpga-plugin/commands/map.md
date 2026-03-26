# /mpga:map

Parallel codebase mapping using multiple scout agents (one per scope). No collusion between modules! Big league exploration, believe me.

## Steps

1. Run `sync --full` for first map, `sync --incremental` for changed-scope refreshes
2. List generated scope documents
3. Spawn one `scout` agent per new or changed scope in parallel — each fills its own scope doc
4. Wait for all scouts to complete
5. Run `auditor` in the background on touched scopes, then spawn `architect` to review, fix, and verify cross-scope consistency
6. Report results: scopes enriched, coverage, unknowns — Tremendous results, very, very special

## Usage
```
/mpga:map
```
