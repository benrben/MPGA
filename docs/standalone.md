# MPGA Standalone (CLI only)

Use MPGA without any AI tool — just the CLI and plain markdown. Useful for teams, CI pipelines, and non-Claude workflows.

The recommended execution model is the same everywhere:
- one writer per scope
- read-only discovery and audits in parallel
- quick drift during active work, full verification at milestone boundaries

See [workflow.md](workflow.md).

## Install

```bash
# Option A: Link from this repo
cd your-project
alias mpga="bash path/to/mpga-plugin/bin/mpga.sh"

# Option B: npm global (when published)
pip install mpga
```

## Initialize a project

```bash
cd your-project

# New project (no existing code)
mpga init --from-zero

# Existing project (scan and map)
mpga init --from-existing
mpga sync
```

## Core CLI commands

### Knowledge layer

```bash
mpga sync               # Regenerate INDEX.md, GRAPH.md, scope docs
mpga sync --incremental # Only update changed files
mpga status             # Dashboard: health, board, config
mpga health --verbose   # Full health report per scope
```

### Evidence management

```bash
mpga evidence verify           # Check all evidence links resolve
mpga evidence verify --scope auth  # Check one scope
mpga evidence heal             # Auto-fix stale links via AST
mpga evidence coverage         # Report evidence-to-code ratio
mpga evidence add auth "[E] src/auth/jwt.ts:42-67 :: generateAccessToken()"
```

### Drift detection

```bash
mpga drift --quick     # Fast check (for hooks/scripts)
mpga drift --report    # Full staleness report
mpga drift --ci        # CI mode (exit 1 if below threshold)
mpga drift --fix       # Report + auto-heal
```

### Scope management

```bash
mpga scope list            # All scopes with health status
mpga scope show auth       # Display a scope with evidence
mpga scope add payments    # Create new empty scope doc
mpga scope query "login"   # Search scopes for keyword
```

### Database migrations

```bash
mpga migrate        # Apply pending SQL migrations to .mpga/mpga.db
```

### Task board

```bash
mpga board show                         # View kanban board
mpga board add "Implement JWT rotation" --priority high --scope auth
mpga board move T001 in-progress
mpga board update T001 --tdd-stage red
mpga board block T001 "waiting for DB schema decision"
mpga board stats
```

### Milestones

```bash
mpga milestone new "Auth refactor"
mpga milestone list
mpga milestone status
mpga milestone complete
```

### Configuration

All project configuration is stored in the SQLite DB (`.mpga/mpga.db`) — no scattered config files:

```bash
mpga config show                              # Show all settings
mpga config get evidence.min_coverage         # Get a single value
mpga config set evidence.min_coverage 90      # Set a value
mpga config set drift.ciThreshold 80          # Set CI drift threshold
mpga config reset                             # Reset to defaults
```

### Session handoff

```bash
mpga session handoff --accomplished "Implemented JWT rotation"
mpga session resume    # Print most recent handoff
mpga session budget    # Context window usage estimate
```

### Export for AI tools

```bash
mpga export --claude        # → CLAUDE.md (Claude Code project scope)
mpga export --cursor        # → .cursor/rules/*.mdc (Cursor MDC format)
mpga export --codex         # → AGENTS.md (Codex / Gemini CLI / OpenCode)
mpga export --antigravity   # → .antigravity/rules/*.md (Google Antigravity)
mpga export --all           # → all of the above

# Global (user-level) configs
mpga export --claude --global       # prints text to append to ~/.claude/CLAUDE.md
mpga export --cursor --global       # prints text to add to Cursor > Rules for AI
mpga export --codex --global        # → ~/.codex/AGENTS.md
mpga export --antigravity --global  # → ~/.antigravity/rules/mpga-global.md

# With optional workflow files (Antigravity)
mpga export --antigravity --workflows
```

### Dependency graph

```bash
mpga graph show
mpga graph export --mermaid
mpga graph export --json
```

## Reading the knowledge layer

The knowledge layer lives in the DB (`.mpga/mpga.db`) — query it with CLI commands:

```bash
# What is this project?
mpga status

# How does auth work?
mpga scope show auth

# What are we building now?
mpga board show

# What happened in the last session?
mpga session handoff
```

## Git integration

Commit the `.mpga/` directory with your code:

```gitignore
# .gitignore — do NOT ignore .mpga/
# The knowledge layer DB is part of the project
```

```bash
git add .mpga/mpga.db
git commit -m "chore: update MPGA knowledge layer"
```

On branches, each developer's sync may differ. Run `mpga sync` after merging to reconcile.

## Shell alias

Add to your `.zshrc` / `.bashrc`:

```bash
# MPGA CLI via plugin wrapper
mpga() {
  bash "$(git rev-parse --show-toplevel)/mpga-plugin/bin/mpga.sh" "$@"
}
```
