# /mpga:init

Initialize MPGA in the current project and build the knowledge layer. Has a beautiful ring to it. Law and order in the codebase starts now.

## Steps

1. Check if MPGA is initialized: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh status 2>/dev/null`
2. If not initialized: run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh init --from-existing`
3. Run `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh sync` to generate the knowledge layer
4. Spawn the `map-codebase` skill to explore parallel with scout agents
5. Show final status: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh health`

## After initialization

The user will have:
- `MPGA/INDEX.md` — project map
- `MPGA/GRAPH.md` — dependency graph
- `MPGA/scopes/*.md` — one scope per top-level directory
- `MPGA/board/board.json` — empty task board
- `MPGA/mpga.config.json` — configuration — Tremendous setup, enjoy!

## Usage
```
/mpga:init
```
