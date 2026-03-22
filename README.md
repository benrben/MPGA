<p align="center">
  <img src="MPGA.png" alt="MPGA — Make Project Great Again" width="420">
</p>

<h1 align="center">MPGA</h1>
<p align="center">
  <strong>Make Project Great Again</strong><br>
  Evidence-backed context engineering for AI-assisted development
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#cli">CLI</a> &middot;
  <a href="#integrations">Integrations</a> &middot;
  <a href="docs/">Docs</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node-%3E%3D20-brightgreen" alt="Node >= 20">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License">
  <img src="https://img.shields.io/badge/TypeScript-strict-blue" alt="TypeScript Strict">
  <img src="https://img.shields.io/badge/AI_tools-6+-orange" alt="6+ AI Tools">
</p>

---

## The Problem

AI coding assistants hallucinate on large codebases. They lose context, make wrong assumptions, and confidently reference functions that don't exist.

**You've seen it** — the AI writes beautiful code that calls a completely wrong API.

## The Fix

MPGA maintains a **living knowledge layer** in your repo — markdown files where every claim about your code cites exact source locations. When code changes, evidence links are automatically verified and healed.

```
your-project/
├── src/                    ← your code
├── MPGA/                   ← living knowledge layer
│   ├── INDEX.md            ← project identity (always loaded by AI)
│   ├── GRAPH.md            ← dependency map
│   ├── scopes/             ← per-module docs with evidence links
│   │   ├── auth.md
│   │   ├── api.md
│   │   └── database.md
│   ├── board/              ← task tracking
│   ├── milestones/         ← milestone history
│   └── sessions/           ← handoff docs between sessions
└── mpga.config.json
```

## Evidence Format

Every claim cites its source. No more hallucinated docs.

```
[E] src/auth/jwt.ts:42-67 :: generateAccessToken()    ← verified
[E] src/auth/jwt.ts :: validateToken                   ← AST-anchored
[Unknown] token rotation logic                          ← explicit gap
[Stale:2026-03-20] src/auth/jwt.ts:42-67               ← needs re-verify
```

Edit `jwt.ts` and MPGA checks if `generateAccessToken()` is still at lines 42-67. If it moved, the link heals. If it's gone, you know immediately.

## Quick Start

**Prerequisites:** Node.js >= 20

```bash
# Clone MPGA
git clone https://github.com/benreich/mpga.git

# Go to your project
cd your-project

# Initialize the knowledge layer
npx mpga init --from-existing

# Generate everything
npx mpga sync

# See your project health
npx mpga status
```

## How It Works

```
  ┌──────────┐     ┌──────────┐     ┌──────────────┐
  │  1. Scan  │────▶│ 2. Index  │────▶│ 3. Evidence  │
  │  files    │     │  & scope  │     │    links     │
  └──────────┘     └──────────┘     └──────┬───────┘
                                           │
  ┌──────────┐     ┌──────────┐     ┌──────▼───────┐
  │ 6. Export │◀────│ 5. Heal   │◀────│ 4. Drift    │
  │ to tools  │     │  stale    │     │   detect    │
  └──────────┘     └──────────┘     └──────────────┘
```

| Step | What happens |
|------|-------------|
| **Scan** | Analyze codebase: files, lines, languages, exports, imports |
| **Index & Scope** | Generate `INDEX.md`, `GRAPH.md`, and one scope doc per module |
| **Evidence links** | Every claim cites exact `file:line:symbol` locations |
| **Drift detection** | After each edit, verify evidence links still resolve |
| **Heal** | Auto-update line ranges when symbols move (AST-based) |
| **Export** | Convert knowledge layer to any AI tool's context format |

## CLI

```
$ mpga --help

                  ▄▄███████████▄▄
              ▄███               ███▄
           ▄██  MAKE  PROJECT     ██▄
          ██    GREAT  AGAIN        ██
         ██       M P G A            ██
        ██                            ██
  ▄▄▄▄▄███▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄███
  ████████████████████████████████████████
   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   ⚙
                                          </>

Usage: mpga [command] [options]

Commands:
  init          Bootstrap MPGA/ knowledge layer
  scan          Analyze codebase structure
  sync          Regenerate knowledge layer
  status        Project health dashboard
  health        Detailed health report with grades
  evidence      Verify/update evidence links
  drift         Check evidence integrity after edits
  scope         View/manage scope documents
  graph         Build dependency graphs
  board         Task board operations
  milestone     Milestone management
  session       Session handoff documents
  config        Configuration management
  export        Export for Cursor, Copilot, Gemini, Codex
```

## Integrations

MPGA is **tool-agnostic** — the `MPGA/` directory is plain markdown. It works with any AI tool, or just humans reading docs.

| Tool | How |
|------|-----|
| **Claude Code** | Full plugin: agents + skills + commands + hooks ([guide](docs/claude-code.md)) |
| **Cursor / Windsurf** | `.cursorrules` generated from knowledge layer ([guide](docs/cursor.md)) |
| **GitHub Copilot** | `.github/copilot-instructions.md` export ([guide](docs/copilot.md)) |
| **Gemini CLI** | `AGENTS.md` generated from INDEX.md ([guide](docs/gemini-cli.md)) |
| **Codex / OpenCode** | `.codex/` or `.opencode/` directory export ([guide](docs/codex.md)) |
| **Standalone** | CLI only — no AI tool needed ([guide](docs/standalone.md)) |
| **CI/CD** | GitHub Actions evidence health gate ([guide](docs/ci-cd.md)) |

### Claude Code (deepest integration)

```bash
# Load the plugin
claude --plugin-dir ./mpga-plugin

# Then use slash commands
/mpga:status        # health dashboard
/mpga:plan          # evidence-based task planning
/mpga:execute       # TDD cycle (green → red → blue → review)
/mpga:ship          # commit + update evidence + archive tasks
```

### Any other tool

```bash
# Generate context files for your tool
mpga export --cursorrules      # → .cursorrules
mpga export --copilot          # → .github/copilot-instructions.md
mpga export --gemini           # → AGENTS.md
mpga export --codex            # → .codex/
```

## Architecture

```
mpga-plugin/
├── cli/                    The engine (TypeScript, ~5k lines)
│   ├── src/
│   │   ├── commands/       14 CLI commands
│   │   ├── core/           Scanner, config, logger
│   │   ├── evidence/       AST extraction, drift, parser, resolver
│   │   ├── generators/     INDEX.md, GRAPH.md, scope.md generators
│   │   └── board/          Task board state management
│   ├── bin/mpga.js         Entry point
│   └── package.json
├── agents/                 9 specialized agents
├── skills/                 10 workflow skills
├── commands/               13 slash commands (/mpga:*)
└── hooks/                  PostToolUse drift checking
```

## Core Philosophy

| Principle | What it means |
|-----------|--------------|
| **Evidence over claims** | Every statement about code must cite a source |
| **Code truth > docs** | If the link says one thing and the prose says another, the link wins |
| **Mandatory workflows** | Drift detection runs on every file write — not optional |
| **Tool-agnostic** | Plain markdown works with any AI tool or just humans |
| **Explicit unknowns** | `[Unknown]` is better than a hallucinated answer |

## Contributing

```bash
git clone https://github.com/benreich/mpga.git
cd mpga/mpga-plugin/cli
npm install && npm run build
npm test
```

## License

MIT — see [LICENSE](LICENSE).
