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
The knowledge layer lives in the DB (`.mpga/mpga.db`) — query it with CLI commands.

## Before suggesting code

1. Run `mpga status` for project conventions and scope registry
2. Find the relevant scope via `mpga scope show <name>`
3. Evidence format: `[E] filepath:startLine-endLine :: symbolName()`

## Key conventions
<!-- run `mpga status` and paste the Conventions section -->

## Key files
<!-- run `mpga status` and paste the Key files section -->
```

## Copilot Chat with scope context

In Copilot Chat, use `#file` to load scope docs explicitly:

```
#output of: mpga scope show auth
How does token refresh work? Should I add rotation?
```

```
#output of: mpga status  #output of: mpga scope show payments
Plan a refactor of the payment flow to support multi-currency
```

## VS Code workspace settings

Add scope docs to Copilot's preferred context files:

```json
// .vscode/settings.json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".mpga/mpga.db" }  // use `mpga status` to read project context
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

If using Copilot Workspaces, reference scope data via CLI commands in your task description:

```
Based on `mpga scope show auth`, implement JWT refresh token rotation.
The acceptance criteria are in `mpga milestone show M003-auth`.
```
