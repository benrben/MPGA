# /mpga:map

Parallel codebase mapping using multiple scout agents (one per scope).

## Steps

1. Run sync to generate scope scaffolds: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh sync --full`
2. List generated scope documents
3. Spawn one `scout` agent per scope in parallel — each fills its own scope doc
4. Wait for all scouts to complete
5. Spawn `architect` agent to review, fix, and verify cross-scope consistency
6. Report results: scopes enriched, coverage, unknowns

## Usage
```
/mpga:map
```
