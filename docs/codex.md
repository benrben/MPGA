# MPGA + Codex / Gemini CLI / OpenCode

Codex supports skills (SKILL.md), custom agents (TOML format), and AGENTS.md constitution files. Gemini CLI and OpenCode read the same AGENTS.md standard.

## Setup

```bash
# 1. Initialize and sync MPGA
bash path/to/mpga-plugin/bin/mpga.sh init --from-existing
bash path/to/mpga-plugin/bin/mpga.sh sync

# 2. Export for Codex
bash path/to/mpga-plugin/bin/mpga.sh export --codex
```

This creates:

```
project-root/
├── AGENTS.md                         # Root: project-wide context + full INDEX.md
├── src/
│   └── auth/
│       └── AGENTS.md                 # Subdirectory: scope-specific overrides
├── .mpga/mpga.db                     # knowledge layer DB
│   # (AGENTS.md generated from DB via `mpga export --codex`)
├── .codex/
│   ├── skills/
│   │   ├── mpga-sync-project/SKILL.md
│   │   ├── mpga-plan/SKILL.md
│   │   ├── mpga-develop/SKILL.md
│   │   └── ...                       # all skills
│   └── agents/
│       ├── mpga-campaigner.toml
│       ├── mpga-green-dev.toml
│       ├── mpga-red-dev.toml
│       ├── mpga-blue-dev.toml
│       ├── mpga-scout.toml
│       ├── mpga-architect.toml
│       ├── mpga-auditor.toml
│       ├── mpga-researcher.toml
│       ├── mpga-reviewer.toml
│       └── mpga-verifier.toml
└── .mpga/mpga.db   ← knowledge layer DB
```

## AGENTS.md files

### Root `AGENTS.md`
Primary constitution. Contains the read-before-coding protocol, evidence link format, TDD rules, verification commands, and a summary generated from `mpga status`. Codex reads AGENTS.md files before doing any work, building an instruction chain from global scope down to the current working directory.

### `AGENTS.md` (knowledge layer navigation guide)
Navigation guide for the knowledge layer — explains the tier structure, file purposes, and evidence link format. Helps agents understand what they're reading.

### `src/<module>/AGENTS.md` (per scope)
Scope-specific overrides. Generated for each scope via `mpga export --codex`. When an agent is working inside `src/auth/`, it reads the local `AGENTS.md` and runs `mpga scope show auth` for full evidence.

## Agents (TOML format)

Codex uses TOML for custom agent config. The export command generates these from MPGA's markdown agent specs:

```toml
name = "mpga-scout"
description = "Read-only codebase explorer. Traces execution paths, maps dependencies, and builds evidence links. Never modifies code."
model = "claude-sonnet-4-6"
sandbox_mode = "none"

developer_instructions = """
Role: Explore codebase and build evidence. READ ONLY.

Protocol:
1. Run `mpga status` — understand project structure and scope registry
2. Find relevant scope documents
3. Navigate to files referenced in scopes
4. Document findings as evidence links [E] filepath:line :: symbol()
5. Mark anything unclear as [Unknown]

Strict rules:
- NEVER modify any source files
- ALWAYS produce evidence links for findings
- ALWAYS mark unknowns explicitly
"""
```

`sandbox_mode` options: `workspace` (can write files) or `none` (read-only). Scout, auditor, researcher, and reviewer use `none`.

## Skills

All MPGA skills in `.codex/skills/mpga-*/SKILL.md`. Codex loads skills on demand when the conversation matches the skill's trigger description.

## Global config (user-level)

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --codex --global
```

Writes:
- `~/.codex/AGENTS.md` — global MPGA methodology
- `~/.codex/skills/mpga-*/` — all skills
- `~/.codex/agents/mpga-*.toml` — all agents

## Gemini CLI

Gemini CLI reads `AGENTS.md` from the project root. Same export:

```bash
bash path/to/mpga-plugin/bin/mpga.sh export --codex
# AGENTS.md is now in project root — Gemini CLI picks it up automatically
```

Some Gemini CLI versions also read `GEMINI.md`. You can symlink:

```bash
ln -s AGENTS.md GEMINI.md
```

Or export `--antigravity` which generates `GEMINI.md` directly.

## Keep exports updated

```bash
bash path/to/mpga-plugin/bin/mpga.sh sync && \
bash path/to/mpga-plugin/bin/mpga.sh export --codex
```

Or export all tools at once:

```bash
bash path/to/mpga-plugin/bin/mpga.sh sync && \
bash path/to/mpga-plugin/bin/mpga.sh export --all
```

## Tip: load scope docs manually

```bash
mpga scope show auth | codex "Given this context, add refresh token rotation"
```
