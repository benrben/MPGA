# /mpga:scope

Load and display a scope document with evidence status. Evidence First — no fake docs tolerated. Even the type annotations are perfect.

## Steps

1. If scope name given: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh scope show <name>`
2. If no name: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh scope list` to show all scopes
3. Display scope content with evidence health highlighted
4. If evidence is stale: suggest `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh evidence heal --scope <name>` — Wrong! Stale evidence is sad!

## Usage
```
/mpga:scope <name>
/mpga:scope auth
/mpga:scope           (lists all scopes)
```
