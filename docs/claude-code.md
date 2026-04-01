# MPGA + Claude Code

The deepest integration: native plugin with agents, skills, slash commands, hooks, and automatic drift-checking.

## Install

```bash
# Load the plugin for your session
claude --plugin-dir path/to/mpga-plugin

# Or add to your project's .claude/settings.json
```

```json
// .claude/settings.json
{
  "plugins": [
    { "dir": "path/to/mpga-plugin" }
  ]
}
```

The CLI is bundled — it builds automatically on first use. No separate install needed.

## First-time setup

```
/mpga:init
```

This runs:
1. `mpga init --from-existing` — initializes the DB (`.mpga/mpga.db`) and populates the knowledge layer
2. `mpga sync` — scans codebase, generates INDEX.md, GRAPH.md, and scope docs
3. `mpga health` — shows initial health report

Board state, task state, scope docs, milestones, and configuration are all stored in the SQLite DB (`.mpga/mpga.db`). Access everything through `mpga` CLI commands — never read or write the DB directly.

## What gets installed

### Plugin (shared, install once)

The plugin provides agents, commands, and hooks:

```
mpga-plugin/
├── agents/           # 17 agents: campaigner, red-dev, green-dev, blue-dev, scout, ...
├── commands/         # 26 /mpga:* commands
├── hooks/            # PostToolUse drift check (triggers mpga drift --quick)
└── skills/           # 18+ skill definitions (source of truth)
```

### Per-project export

```bash
mpga export --claude
```

This generates:

```
project-root/
├── CLAUDE.md                 # Project context (generated from `mpga export --claude`)
└── .claude/
    ├── skills/
    │   ├── mpga-sync-project/SKILL.md
    │   ├── mpga-brainstorm/SKILL.md
    │   ├── mpga-plan/SKILL.md
    │   ├── mpga-develop/SKILL.md
    │   ├── mpga-drift-check/SKILL.md
    │   ├── mpga-ask/SKILL.md
    │   ├── mpga-onboard/SKILL.md
    │   ├── mpga-rally/SKILL.md
    │   ├── mpga-ship/SKILL.md
    │   ├── mpga-handoff/SKILL.md
    │   └── mpga-map-codebase/SKILL.md
    ├── agents/               # all exported agent specs
    ├── commands/             # all exported /mpga:* command specs
    └── settings.json         # drift hook configuration
```

### Global export (user-level)

```bash
mpga export --claude --global
```

- Copies all skills to `~/.claude/skills/mpga-*/`
- Prints the MPGA global rules section to append to `~/.claude/CLAUDE.md`

## Daily workflow

### Start a session
```
/mpga:status          ← dashboard: evidence health, board state, active milestone
/mpga:next            ← auto-detects what to do next
```

### Explore the codebase
```
/mpga:scope auth      ← load the auth scope document
/mpga:health          ← full health report with per-scope breakdown
```

### Plan and build
```
/mpga:milestone new "Payment refactor"
/mpga:plan            ← generates evidence-based task breakdown on the board
/mpga:execute         ← runs TDD cycle: red-dev → green-dev → blue-dev → reviewer
/mpga:ship            ← verify + commit + update evidence + archive tasks
```

### Parallel workflow
MPGA's fast path is:
- one writer per scope
- read-only `scout` / `auditor` in background
- independent scopes planned as separate lanes
- `verifier` reserved for milestone boundaries or risky work

See [workflow.md](workflow.md).

### Ad-hoc fixes
```
/mpga:quick "Fix the login redirect on mobile Safari"
```

### End of session
```
/mpga:handoff         ← exports session state; next session loads it fresh
```

## Agents

| Agent | Role | Readonly |
|-------|------|---------|
| `campaigner` | Read-only rally diagnostician for full project audits | Yes |
| `red-dev` | Writes failing tests first; never writes implementation | No |
| `green-dev` | Writes minimal implementation to pass the tests | No |
| `blue-dev` | Refactors without changing behavior; updates evidence links | No |
| `scout` | Read-only codebase explorer; produces evidence links | Yes |
| `architect` | Generates/updates scope docs and GRAPH.md | No |
| `auditor` | Verifies evidence integrity; flags stale links | Yes |
| `researcher` | Domain research before planning begins | Yes |
| `reviewer` | Two-stage review: spec compliance + code quality | Yes |
| `verifier` | Post-execution: tests pass, no stubs, evidence updated | Yes |

## Hooks

After every `Write` or `Edit` tool call, the PostToolUse hook automatically runs:

```bash
mpga drift --quick
```

If stale evidence links are detected, you'll see a warning. Run `mpga evidence heal` to auto-fix.

## Commands reference

| Command | Description |
|---------|-------------|
| `/mpga:init` | Bootstrap knowledge layer |
| `/mpga:status` | Health dashboard |
| `/mpga:rally` | Full diagnostic rally audit |
| `/mpga:scope <name>` | Load a scope document |
| `/mpga:drift` | Full drift report |
| `/mpga:map` | Parallel scope mapping |
| `/mpga:plan` | Generate task plan from milestone |
| `/mpga:execute [task-id]` | Run TDD cycle (→ redirects to `/mpga:develop`) |
| `/mpga:verify` | Full verification pass |
| `/mpga:ship` | Commit + update evidence + archive |
| `/mpga:quick "<task>"` | Ad-hoc fix |
| `/mpga:milestone` | Milestone management |
| `/mpga:board` | Task board view |
| `/mpga:next` | Auto-detect next action |
| `/mpga:health` | Detailed health report |

## Context budget

MPGA uses a tiered loading strategy to keep token usage low:

| Tier | Content | Tokens (approx) |
|------|---------|-----------------|
| Hot (always) | INDEX.md | ~2,000 |
| Warm (per task) | 1-3 scope docs | ~3,600 |
| Cold (on demand) | Sessions, milestones | varies |
| **Total** | vs. 24K lines naive | **~5,600 vs ~96,000** |

Run `mpga session budget` to see actual usage.
