# MPGA + GitHub Copilot

GitHub Copilot reads `.github/copilot-instructions.md` for repository-level context. MPGA generates the source `AGENTS.md`, which you can copy into Copilot's instructions file.

## Setup

```bash
# 1. Initialize and sync MPGA
bash path/to/mpga-plugin/bin/mpga.sh init --from-existing
bash path/to/mpga-plugin/bin/mpga.sh sync

# 2. Generate copilot-instructions.md
mkdir -p .github
bash path/to/mpga-plugin/bin/mpga.sh export --codex   # generates AGENTS.md
cp AGENTS.md .github/copilot-instructions.md
```

Or create `.github/copilot-instructions.md` manually:

```markdown
# Project context (powered by MPGA)

This project uses MPGA for evidence-backed context engineering.
The knowledge layer is in the `MPGA/` directory.

## Before suggesting code

1. Check `MPGA/INDEX.md` for project conventions and scope registry
2. Find the relevant scope in `MPGA/scopes/<name>.md`
3. Evidence format: `[E] filepath:startLine-endLine :: symbolName()`

## Key conventions
<!-- paste content from MPGA/INDEX.md ## Conventions section -->

## Key files
<!-- paste content from MPGA/INDEX.md ## Key files section -->
```

## Copilot Chat with scope context

In Copilot Chat, use `#file` to load scope docs explicitly:

```
#file:MPGA/scopes/auth.md
How does token refresh work? Should I add rotation?
```

```
#file:MPGA/INDEX.md #file:MPGA/scopes/payments.md
Plan a refactor of the payment flow to support multi-currency
```

## VS Code workspace settings

Add scope docs to Copilot's preferred context files:

```json
// .vscode/settings.json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": "MPGA/INDEX.md" }
  ]
}
```

## Keep updated

```bash
# After syncing MPGA, regenerate copilot instructions
bash path/to/mpga-plugin/bin/mpga.sh sync
bash path/to/mpga-plugin/bin/mpga.sh export --codex
cp AGENTS.md .github/copilot-instructions.md
```

## Copilot Workspaces

If using Copilot Workspaces, the `MPGA/` directory is automatically indexed. Reference scope docs in your task description:

```
Referring to MPGA/scopes/auth.md, implement JWT refresh token rotation.
The acceptance criteria are in MPGA/milestones/M003-auth/PLAN.md.
```
