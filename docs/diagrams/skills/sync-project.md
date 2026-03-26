# Sync-Project — [MERGED into Map-Codebase]

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:sync-project] --> B[REDIRECTED]
    B --> C["/mpga:map (quick mode)\nSame as old sync-project behavior"]
    B --> D["/mpga:map --deep\nFull parallel mapping with scouts"]

    C --> E["See map-codebase skill\nfor full workflow"]
    D --> E
```

## Note
This skill has been merged into **map-codebase**. Use:
- `/mpga:map` -- quick mode (same as the old sync-project behavior)
- `/mpga:map --deep` -- full parallel mapping with scout agents

See [map-codebase.md](map-codebase.md) for the unified protocol.

## Inputs
- Same as map-codebase

## Outputs
- Same as map-codebase
