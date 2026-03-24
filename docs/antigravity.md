# MPGA + Google Antigravity

Antigravity uses `.agent/` for skills, `.agents/` for workflows, `.antigravity/` for rules, and has a unique Knowledge Items system for cross-session persistence. MPGA generates all of these.

## Setup

```bash
# 1. Initialize MPGA (if not already done)
bash path/to/mpga-plugin/bin/mpga.sh init --from-existing
bash path/to/mpga-plugin/bin/mpga.sh sync

# 2. Export everything for Antigravity
bash path/to/mpga-plugin/bin/mpga.sh export --antigravity --workflows
```

This creates:

```
project-root/
├── GEMINI.md                          # Constitution (primary context file)
├── .agent/
│   └── skills/
│       ├── mpga-sync-project/SKILL.md
│       ├── mpga-plan/SKILL.md
│       ├── mpga-develop/SKILL.md
│       └── ...                        # all 11 skills
├── .agents/
│   └── workflows/
│       ├── mpga-plan.md               # Step-by-step planning workflow
│       ├── mpga-develop.md            # TDD cycle workflow
│       └── mpga-review.md             # Spec + code quality review
└── .antigravity/
    └── rules/
        ├── mpga-context.md            # Project context from INDEX.md
        ├── mpga-evidence.md           # Evidence link conventions
        └── mpga-tdd.md                # TDD enforcement
```

## `GEMINI.md` (constitution)

The primary always-on context file. Generated from `MPGA/INDEX.md`. Contains the read-before-coding protocol, evidence rules, TDD protocol, active milestone, and verification commands. Antigravity reads this at the start of every session.

Also generate `AGENTS.md` for tools that read it instead:

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --codex   # → AGENTS.md
bash path/to/mpga-plugin/bin/mpga.sh export --antigravity  # → GEMINI.md + .agent/ + .agents/ + .antigravity/
```

## Skills (`.agent/skills/`)

11 MPGA skills, same SKILL.md format as Claude Code and Cursor. Antigravity loads skills on demand based on relevance to the current task. Invoke with slash commands (e.g. `/mpga-sync-project`, `/mpga-develop`).

## Workflows (`.agents/workflows/`)

Antigravity's native step-by-step workflow format — its closest analog to Claude Code's skill orchestration. Three workflows:

| File | Trigger | Steps |
|------|---------|-------|
| `mpga-plan.md` | Milestone needs a plan | Read scopes → research gaps → break into tasks → save PLAN.md → add to board |
| `mpga-develop.md` | Implementing a board task | Read task card → load scopes → TDD cycle → update evidence → move task → drift check |
| `mpga-review.md` | Task in review column | Stage 1: spec compliance + evidence validity. Stage 2: code quality + security |

## Subagents

Antigravity doesn't use the same named-agent file model as Claude Code, Cursor, or Codex. Instead:
- MPGA exports the 11 workflow skills directly
- Multi-step orchestration happens via **workflows** (`.agents/workflows/mpga-develop.md` runs the full red → green → blue → review cycle)
- The agent responsibilities still exist conceptually, but they are encoded through the exported skills/workflows rather than separate agent files

## Knowledge Items

Antigravity's unique cross-session persistence system. Seed Knowledge Items from your MPGA scope docs:

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --antigravity --knowledge
```

This writes `.antigravity/knowledge/mpga-<scope>.md` files for each scope. Antigravity loads relevant Knowledge Items automatically when starting new sessions — the evidence links and scope summaries are available without re-reading the full MPGA layer.

## Global config (user-level)

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --antigravity --global
```

Writes:
- `~/.gemini/antigravity/skills/mpga-*/` — 11 skills (global)
- `~/.antigravity/rules/mpga-global.md` — MPGA methodology for all projects

## Keep it updated

```bash
bash path/to/mpga-plugin/bin/mpga.sh sync && \
bash path/to/mpga-plugin/bin/mpga.sh export --antigravity --workflows
```

Or export all tools at once:

```bash
bash path/to/mpga-plugin/bin/mpga.sh sync && \
bash path/to/mpga-plugin/bin/mpga.sh export --all --workflows
```
