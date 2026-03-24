# /mpga:scope

Load and display a scope document with evidence status.

## Steps

1. If scope name given: `node ./.mpga-runtime/cli/dist/index.js scope show <name>`
2. If no name: `node ./.mpga-runtime/cli/dist/index.js scope list` to show all scopes
3. Display scope content with evidence health highlighted
4. If evidence is stale: suggest `node ./.mpga-runtime/cli/dist/index.js evidence heal --scope <name>`

## Usage
```
/mpga:scope <name>
/mpga:scope auth
/mpga:scope           (lists all scopes)
```
