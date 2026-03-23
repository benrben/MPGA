# /mpga:scope

Load and display a scope document with evidence status.

## Steps

1. If scope name given: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh scope show <name>`
2. If no name: `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh scope list` to show all scopes
3. Display scope content with evidence health highlighted
4. If evidence is stale: suggest `/Users/benreich/MPGA/mpga-plugin/bin/mpga.sh evidence heal --scope <name>`

## Usage
```
/mpga:scope <name>
/mpga:scope auth
/mpga:scope           (lists all scopes)
```
