# MPGA — Claude Code Plugin

Make Project Great Again: evidence-backed context engineering for AI-assisted development.

The CLI is **bundled inside this plugin** — no separate install needed. It is built automatically on first use.

## Structure

```
mpga-plugin/
├── .claude-plugin/
│   └── plugin.json         # Plugin manifest
├── cli/                    # Bundled MPGA CLI (TypeScript source)
│   ├── src/                # TypeScript source
│   ├── package.json
│   └── tsconfig.json
├── bin/
│   └── mpga.sh             # Auto-installing CLI wrapper
├── scripts/
│   ├── setup.sh            # Builds the CLI (npm install + tsc)
│   ├── check-cli.sh        # Ensures CLI is built before hooks run
│   └── format-evidence.sh  # Evidence link formatter
├── agents/                 # 10 agent definitions
├── commands/               # 21 slash commands (/mpga:*)
├── skills/                 # 11 skill definitions
└── hooks/
    └── hooks.json          # PostToolUse drift check
```

## Quick Start

### Load the plugin

```bash
claude --plugin-dir ./mpga-plugin
```

The CLI is built automatically on first use. Or pre-build manually:

```bash
bash mpga-plugin/scripts/setup.sh
```

### Initialize a project

```
/mpga:init
```

This runs `mpga init --from-existing`, scans the codebase, and generates the full `MPGA/` knowledge layer.

### Commands

| Command | Description |
|---------|-------------|
| `/mpga:init` | Bootstrap MPGA knowledge layer |
| `/mpga:status` | Health dashboard |
| `/mpga:scope <name>` | View scope document |
| `/mpga:drift` | Check evidence drift |
| `/mpga:plan` | Generate evidence-based task plan |
| `/mpga:execute` | Run TDD cycle (red → green → blue → review) |
| `/mpga:verify` | Full verification pass |
| `/mpga:ship` | Commit + update evidence + archive tasks |
| `/mpga:quick "<task>"` | Ad-hoc fix without full milestone |
| `/mpga:milestone` | Milestone management |
| `/mpga:board` | Task board view |
| `/mpga:next` | Auto-detect next action |
| `/mpga:health` | Detailed health report |

## CLI reference

The bundled CLI is always invoked via `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh`. When run directly:

```bash
# From project root after setup
./mpga-plugin/bin/mpga.sh --help
./mpga-plugin/bin/mpga.sh status
./mpga-plugin/bin/mpga.sh board show
```

## How auto-install works

1. `bin/mpga.sh` checks if `cli/dist/index.js` exists
2. If not: runs `scripts/setup.sh` which does `npm install && npm run build` in `cli/`
3. Proceeds to run the CLI

The hook in `hooks/hooks.json` calls `bin/mpga.sh drift --quick` after every Write/Edit — drift checking is always available with no user setup.

## Workflow model

- One writer per scope at a time
- Read-only helpers (`scout`, `auditor`, `campaigner`) can fan out in parallel
- Plans should isolate independent scopes into separate task lanes

See [workflow.md](../docs/workflow.md) for the detailed matrix.
