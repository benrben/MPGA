# MPGA — Claude Code Plugin

Make Project Great Again: evidence-backed context engineering for AI-assisted development.

The CLI is **bundled inside this plugin** — no separate install needed. It is built automatically on first use.

## Structure

```
mpga-plugin/
├── .claude-plugin/
│   └── plugin.json         # Plugin manifest
├── cli/                    # Bundled MPGA CLI (Python)
│   ├── src/                # Python source
│   └── pyproject.toml
├── bin/
│   └── mpga.sh             # Auto-installing CLI wrapper
├── scripts/
│   ├── setup.sh            # Installs the CLI (venv + pip install)
│   ├── check-cli.sh        # Ensures CLI is built before hooks run
│   └── format-evidence.sh  # Evidence link formatter
├── agents/                 # 14 agent definitions
├── commands/               # 21 slash commands (/mpga:*)
├── skills/                 # 14 skill definitions
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

After running `install.sh`, the `mpga` command is available system-wide:

```bash
mpga --help
mpga status
mpga board show
```

The plugin's `bin/mpga.sh` wrapper is used by hooks and auto-installs the CLI if needed.

## How auto-install works

1. `bin/mpga.sh` checks if `cli/.venv/bin/mpga` exists
2. If not: runs `scripts/setup.sh` which does `python3 -m venv .venv && pip install -e .` in `cli/`
3. Proceeds to run the CLI

The hook in `hooks/hooks.json` calls `bin/mpga.sh drift --quick` after every Write/Edit — drift checking is always available with no user setup.

## Agent boundaries

Each agent has a clear domain. Understanding boundaries prevents overlap and wasted work.

### Write agents (modify code/docs — one per scope at a time)
| Agent | Domain | When to use |
|-------|--------|-------------|
| **red-dev** | Write failing tests (TDD red phase) | During `/mpga:develop` cycle |
| **green-dev** | Write minimal implementation (TDD green phase) | After red-dev produces failing tests |
| **blue-dev** | Refactor without changing behavior (TDD blue phase) | After green-dev makes tests pass |

### Read-only analysis agents (can run in parallel)
| Agent | Domain | Boundary |
|-------|--------|----------|
| **scout** | Explore code, fill scope docs | One scope per scout. Never modifies source code or GRAPH.md. |
| **auditor** | Verify evidence links, detect drift | Owns drift detection and severity classification. Never modifies source code. |
| **reviewer** | Diff-scoped code review | Surface-level security/performance. For deep analysis, delegates to specialized agents. |
| **bug-hunter** | Spec vs implementation comparison | Finds correctness bugs. Does NOT fix them. |
| **optimizer** | File-level code quality | Spaghetti, duplication, complexity within files. Does NOT handle cross-scope architecture. |
| **security-auditor** | OWASP, deps, secrets | Deep security analysis. Reviewer handles surface-level security in diffs. |
| **researcher** | Domain research, option analysis | Time-boxed. Produces decision matrices. Does NOT write code. |
| **campaigner** | Project-wide quality audit | Delegates to optimizer/security-auditor/auditor for their domains. Adds rally presentation. |

### Coordination agents
| Agent | Domain | Boundary |
|-------|--------|----------|
| **architect** | Cross-scope consistency, ADRs, dependency graphs | Architectural smells only. File-level smells are optimizer's domain. |
| **orchestrator** | Lane management, scheduling, WIP limits | Enforces one-writer-per-scope rule. Does NOT do code analysis. |
| **verifier** | Post-execution verification | Quantitative metrics + pass/fail thresholds. Final gate before done. |

### Key delegation rules
- **Security**: reviewer catches surface issues in diffs → security-auditor for deep audits
- **Architecture**: reviewer catches layer violations in diffs → architect for cross-scope analysis
- **Code quality**: reviewer catches smells in diffs → optimizer for full codebase analysis
- **Campaigner**: delegates to optimizer, security-auditor, auditor — does NOT re-implement their checks

## Workflow model

- One writer per scope at a time
- Read-only agents (scout, auditor, campaigner, optimizer, bug-hunter, researcher, security-auditor) can fan out in parallel
- Plans should isolate independent scopes into separate task lanes

See [workflow.md](../docs/workflow.md) for the detailed matrix.
