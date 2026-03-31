# /mpga:init

Initialize MPGA in the current project and build the knowledge layer. Has a beautiful ring to it. Law and order in the codebase starts now.

## Steps

1. Check if MPGA is initialized: `mpga status 2>/dev/null`
2. If not initialized: run `mpga init --from-existing`
3. Run `mpga sync` to generate the knowledge layer
4. Spawn the `map-codebase` skill to explore parallel with scout agents
5. Show final status: `mpga health`

## After initialization

The user will have:
- Project map — view with `mpga status`
- Dependency graph — view with `mpga graph show`
- Scope docs — one per top-level directory, view with `mpga scope list`
- Empty task board — view with `mpga board show`
- Configuration stored in the DB (`.mpga/mpga.db`) — Tremendous setup, enjoy!

## Usage
```
/mpga:init
```
