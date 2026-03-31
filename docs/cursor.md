# MPGA + Cursor / Windsurf

Cursor supports skills (SKILL.md), custom subagents, MDC rules, hooks, and a plugin marketplace. MPGA generates all of these from your knowledge layer.

## Setup

```bash
# 1. Initialize MPGA (if not already done)
bash path/to/mpga-plugin/bin/mpga.sh init --from-existing
bash path/to/mpga-plugin/bin/mpga.sh sync

# 2. Export everything for Cursor
bash path/to/mpga-plugin/bin/mpga.sh export --cursor
```

This creates:

```
project-root/
├── .cursor/
│   ├── rules/
│   │   ├── mpga-project.mdc        # alwaysApply: true — project context
│   │   ├── mpga-evidence.mdc       # alwaysApply: true — evidence conventions
│   │   ├── mpga-tdd.mdc            # alwaysApply: true — TDD enforcement
│   │   └── mpga-scopes.mdc         # alwaysApply: false — scope lookup
│   ├── skills/
│   │   ├── mpga-sync-project/SKILL.md
│   │   ├── mpga-plan/SKILL.md
│   │   ├── mpga-develop/SKILL.md
│   │   └── ...                     # all skills
│   └── agents/
│       ├── mpga-campaigner.md      # readonly: true, is_background: true
│       ├── mpga-green-dev.md
│       ├── mpga-red-dev.md
│       ├── mpga-blue-dev.md
│       ├── mpga-scout.md           # readonly: true, is_background: true
│       ├── mpga-architect.md
│       ├── mpga-auditor.md         # readonly: true, is_background: true
│       ├── mpga-researcher.md
│       ├── mpga-reviewer.md
│       └── mpga-verifier.md
└── .mpga/mpga.db   ← knowledge layer DB
```

## Rules (always-on context)

Four MDC files in `.cursor/rules/`. Cursor injects the `alwaysApply: true` files into every conversation:

| File | alwaysApply | Content |
|------|-------------|---------|
| `mpga-project.mdc` | true | Project identity, read-before-coding protocol, `mpga status` reference |
| `mpga-evidence.mdc` | true | Evidence link format and verification commands |
| `mpga-tdd.mdc` | true | TDD enforcement — test first, implement second |
| `mpga-scopes.mdc` | false | Maps each scope via `mpga scope show <name>` — surfaced when relevant |

## Skills

All MPGA skills in `.cursor/skills/mpga-*/SKILL.md`. Same format as Claude Code — Cursor's Agent Skills support was added alongside the plugin system. Invoke with slash commands in Cursor chat (e.g. `/mpga-sync-project`, `/mpga-plan`).

## Subagents

All MPGA agents in `.cursor/agents/mpga-*.md`. Cursor agent format uses YAML frontmatter:

```markdown
---
name: mpga-scout
description: Read-only codebase explorer. Traces execution paths, maps dependencies, and builds evidence links. Never modifies files.
model: claude-sonnet-4-6
readonly: true
is_background: true
---

Role: Explore codebase and build evidence. READ ONLY.
...
```

Cursor-specific agent fields:
- `readonly: true` — agent cannot write files (campaigner, scout, auditor, researcher use this)
- `is_background: true` — can run in parallel without blocking foreground chat (campaigner, scout, auditor)
- `model` — per-agent model selection (architect and reviewer use opus)

Cursor routes to agents automatically based on the `description` field.

## Global config (user-level)

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --cursor --global
```

Writes `~/.cursor/skills/mpga-*/` and `~/.cursor/agents/mpga-*.md`, and prints the text to add to **Cursor Settings > General > Rules for AI**.

## Keep it updated

```bash
bash path/to/mpga-plugin/bin/mpga.sh sync && \
bash path/to/mpga-plugin/bin/mpga.sh export --cursor
```

Or in CI:

```yaml
- run: mpga sync --incremental && mpga export --cursor
- uses: stefanzweifel/git-auto-commit-action@v5
  with:
    commit_message: "chore: update .cursor/ from MPGA sync"
    file_pattern: ".cursor/rules/*.mdc"
```

## Cursor-specific tips

### Reference scope docs in chat

```
@mpga status  @mpga scope show auth
How does token refresh work?
```

### No special indexing needed

Scope data is served from the DB (`.mpga/mpga.db`) via CLI commands — no directory to add to `.cursorignore`.

## Windsurf

Windsurf reads `.cursor/rules/` and `.cursor/skills/` using the same convention. The same export works for both — no additional setup needed.
