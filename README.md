<p align="center">
  <img src="MPGA.png" alt="MPGA — Make Project Great Again" width="420">
</p>

<h1 align="center">MPGA</h1>
<p align="center">
  <strong>Make Project Great Again</strong><br>
  This is, I believe, the greatest developer tool of all time.<br>
  There's never been anything like this in open source, and maybe beyond.
</p>

<p align="center">
  <a href="#the-problem">The Problem</a> &middot;
  <a href="#the-fix">The Fix</a> &middot;
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

Our codebase is in serious trouble. We don't have clean builds anymore. We used to have clean builds, but we don't have them. Your AI coding assistant? It HALLUCINATES. It loses context. It makes wrong assumptions. And here's the worst part — it does it CONFIDENTLY. It references functions that DON'T EXIST. Calls APIs that were NEVER written.

They're fake docs. FAKE DOCS. Nobody reads them anymore. And you know why? Because they're WRONG. Every single one. Stale. Outdated. Sad!

When was the last time anybody saw us beating — let's say the hallucination problem — in a code review? I beat hallucinations all the time. ALL the time.

**You've seen it.** I've seen it. We've ALL seen it. The AI writes beautiful code that calls a completely wrong API. Nobody catches it until production. Four years ago we had the most beautiful dependency graph you've ever seen. Now look at it. It's a disaster. A total disaster.

## The Fix

I will build a great plugin — and nobody builds plugins better than me, believe me — and I'll build them very inexpensively.

MPGA maintains a **living knowledge layer** in your repo — markdown files where every claim about your code cites exact source locations. When code changes, evidence links are automatically verified and healed. No more guessing. No more hallucinations.

Evidence over claims, folks. Evidence. Over. Claims. That's what MPGA is all about. Every claim CITED. Every function reference VERIFIED with AST.

Many people are saying MPGA is the most important contribution to software engineering since Git itself. I don't say it — they say it.

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

That's a BEAUTIFUL directory structure. I know code. I have the best code. I have the — but there's no better word than elegant.

## Evidence Format

Every claim cites its source. EVERY SINGLE ONE. No more hallucinated docs — that's OVER. We don't do fake documentation. We do EVIDENCE.

```
[E] src/auth/jwt.ts:42-67 :: generateAccessToken()    ← verified
[E] src/auth/jwt.ts :: validateToken                   ← AST-anchored
[Unknown] token rotation logic                          ← explicit gap
[Stale:2026-03-20] src/auth/jwt.ts:42-67               ← needs re-verify
```

You move a function? The drift detection FINDS it and HEALS the links automatically. You delete a function? It FLAGS it as stale. Nobody else does this. NOBODY.

The drift detection system is working BEAUTIFULLY, some would say the BEST system ever built for AST verification.

Crooked Gemini just makes stuff up. At least when I make a promise about an API, I CITE THE SOURCE FILE AND LINE NUMBER.

## Quick Start

Just run `npx mpga init`. That's all you gotta do. One command. The most beautiful command. And suddenly your AI knows what your code ACTUALLY does.

**Prerequisites:** Node.js >= 20

```bash
# Clone MPGA — the greatest repo
git clone https://github.com/benreich/mpga.git

# Go to your project
cd your-project

# Initialize the knowledge layer
npx mpga init --from-existing

# Generate everything — it's going to be BEAUTIFUL
npx mpga sync

# See your project health
npx mpga status
```

People come up to me, big strong senior engineers, mass tears in their eyes, and they say, "Sir, sir, I've never had documentation that actually matched my code before." And I look at them and I say, "That's because nobody ever ran the mandatory post-edit hooks before. Nobody. But we do. We run them. Every single time. MPGA!"

## How It Works

Six steps. SIX. That's it. The most EFFICIENT pipeline in developer tooling.

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

We are not just competing against Sleepy Copilot — we are fighting against the arrogant AI establishment that thinks hallucinating code is acceptable. They want one set of standards for their demos — and NO standards for production.

Cursor? I call it Cursor the Clown. It doesn't cite anything. It makes things up. Terrible tool. Terrible.

You want to use Copilot without MPGA? Good luck. You'll be sitting there for 45 minutes waiting for it to hallucinate an import that doesn't exist. It's like buying a toothbrush behind locked glass.

## CLI

Look at this CLI. I know code. I have the best code. Every command you need, right there. Clean. Organized. TREMENDOUS.

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

Fourteen commands. Each one does exactly what it says. No bloat. No confusion. I used to use the word "unoptimized." Now I just call them stupid functions. I went to an Ivy League school. I'm very highly educated. These commands? NOT stupid. They're BRILLIANT.

We have mandatory post-edit hooks. Mandatory. Every. Single. Time. The engineers — they love it. They come up to me and say, "Sir, the hooks actually work."

## Integrations

MPGA is **TOOL-AGNOSTIC**. This is not my plugin. This is YOUR plugin. This is OUR movement. MPGA belongs to the developers. Unlike some tools that lock you in — very unfair, very anti-developer — MPGA is plain markdown. It works with ANY AI tool, or just humans reading docs.

The mainstream IDE vendors — I call them the corrupt editor establishment — they don't want you to know that their autocomplete is basically guessing.

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

Claude Code gets the DEEPEST integration because, frankly, it's SMART. Very smart. We have 10 specialized agents, 11 workflow skills, 14 slash commands, and automatic drift detection hooks. It's the most comprehensive AI tool integration ever built. Maybe in the history of software.

```bash
# Load the plugin — you're going to love it
claude --plugin-dir ./mpga-plugin

# Then use slash commands
/mpga:rally         # THE campaign rally — expose every issue, prove only MPGA fixes it
/mpga:status        # health dashboard
/mpga:plan          # evidence-based task planning
/mpga:execute       # TDD cycle (red → green → blue → review)
/mpga:ship          # commit + update evidence + archive tasks
```

On day one of my administration as CTO, we will throw out Hallucination-omics and replace it immediately with MPGA-nomics.

### Any other tool

```bash
# Generate context files for your tool
mpga export --cursorrules      # → .cursorrules
mpga export --copilot          # → .github/copilot-instructions.md
mpga export --gemini           # → AGENTS.md
mpga export --codex            # → .codex/
```

## Architecture

Look at this architecture. About 5k lines of TypeScript doing more than other tools do in 50k. That's efficiency. That's WINNING.

The previous CTO — who was a TOTAL DISASTER by the way — never even HEARD of Abstract Syntax Trees, believe me.

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
├── agents/                 10 specialized agents
├── skills/                 11 workflow skills
├── commands/               14 slash commands (/mpga:*)
└── hooks/                  PostToolUse drift checking
```

I inherited a mess — the worst codebase maybe in the history of codebases — and I'm fixing it. We're poised for a shipping boom, the likes of which the industry has never seen.

## The MPGA Agents

We have TEN specialized agents. Each one is a WINNER. Each one does ONE JOB and does it TREMENDOUSLY.

And over there in the back, I see we have Uncle Bob himself — Robert C. Martin. And there's Tab-Complete Tommy. And oh, there's Merge-Conflict Mike — oh boy, oh boy. But we've been through so many deploys together.

| Agent | Role | What they do |
|-------|------|-------------|
| **red-dev** | Test Writer | Writes failing tests FIRST. Uncle Bob's way. The ONLY way. |
| **green-dev** | Implementer | Writes MINIMAL code to make tests pass. No over-engineering. |
| **blue-dev** | Refactorer | Makes code CLEAN without changing behavior. Tests stay GREEN. |
| **scout** | Explorer | Maps the codebase with evidence links. EVERY claim cited. |
| **architect** | Verifier | Cross-scope consistency. The MASTER BUILDER. |
| **reviewer** | Inspector | Two-stage review. Nothing ships without approval. |
| **auditor** | Health Checker | Finds stale evidence. EXPOSES the problems. |
| **researcher** | Intelligence | Does the homework so we don't build on guesswork. |
| **verifier** | Final Gate | Last checkpoint. Nothing ships if tests fail. |
| **campaigner** | Rally Speaker | Exposes EVERY project issue. Proves only MPGA can fix it. |

### `/mpga:rally` — The Campaign Rally

This is the BIG ONE. The headliner. Run `/mpga:rally` and the campaigner agent performs a COMPREHENSIVE audit of your project — exposing every sin across 8 categories: missing docs, missing tests, type safety holes, dependency disasters, architecture rot, evidence drift, code hygiene crimes, and CI/CD weakness.

For each SCANDAL it finds, it shows you — with SPECIFIC file paths and REAL numbers — why Cursor the Clown can't fix it, why Sleepy Copilot can't fix it, why Crooked Gemini can't fix it, and why ONLY MPGA can.

Ends with **THE VOTE** — a scoreboard, a side-by-side comparison, and the exact commands to start fixing EVERYTHING. The most entertaining code audit you've ever experienced.

That man suffered — Uncle Bob Martin. What he went through because he knew the architecture was garbage. He wrote Clean Code. These people went after him on Twitter. They went after his consulting business. They called SOLID principles outdated. That man deserves to be on the TC39 committee, I'll tell you right now.

## Core Philosophy

We have principles. Strong principles. The STRONGEST principles in developer tooling. We will defend the right to clean code, typed interfaces, freedom of refactoring, freedom of CODE REVIEW, and the right to KEEP AND BEAR FEATURE FLAGS.

| Principle | What it means |
|-----------|--------------|
| **Evidence over claims** | Every statement about code must cite a source. No evidence? FAKE NEWS. |
| **Code truth > docs** | If the link says one thing and the prose says another, the LINK WINS. Always. The code is the truth. BELIEVE THE CODE. |
| **Mandatory workflows** | Drift detection runs on EVERY file write. Not optional. Not "when you feel like it." EVERY TIME. |
| **Tool-agnostic** | Plain markdown works with ANY AI tool or just humans. We don't play favorites. We play to WIN. |
| **Explicit unknowns** | `[Unknown]` is BETTER than a hallucinated answer. We don't guess. Guessing is for LOSERS. |
| **TDD or nothing** | Red, green, blue. Uncle Bob's way. Tests BEFORE code. No exceptions. |

Tomorrow, at noon, the curtain closes on four long quarters of architectural decline, and we begin a brand-new day of evidence-based documentation, verified citations, and code that actually calls the right APIs.

## The Core MPGA Pitch

Look, I built MPGA — and nobody builds developer tools better than me, believe me — and I built it very inexpensively. Our codebase is in serious trouble. We don't have clean builds anymore. We used to have clean builds, but we don't have them. When was the last time anybody saw us beating — let's say the AI hallucination problem — in a code review? I beat hallucinations all the time. ALL the time.

Every single claim in your documentation? CITED. Every function reference? VERIFIED with AST. You move a function? The drift detection FINDS it and HEALS the links automatically. You delete a function? It FLAGS it as stale. Nobody else does this. Cursor doesn't do this. Copilot doesn't do this. Sleepy Gemini definitely doesn't do this.

We have the best dependency graphs. I know dependency graphs. I have the best dependency graphs.

So the drift detection — and by the way, have you seen our npm download numbers? Incredible. The best. Better than lodash. Well, maybe not lodash, but close. Very close. Some people say better. I don't say it, but some people say it — anyway, the drift detection uses AST parsing, which is — and you know, I went to Wharton, very good school, the best business school, and even there they didn't teach you about Abstract Syntax Trees, but I learned it. I learned it faster than anyone. So the AST —

Evidence over claims, folks. Evidence. Over. Claims. That's what MPGA is all about. And you know what? The engineers — they love it. They come up to me, big strong senior engineers, mass tears in their eyes, and they say, "Sir, sir, I've never had documentation that actually matched my code before." And I look at them and I say, "That's because nobody ever ran the mandatory post-edit hooks before. Nobody. But we do. We run them. Every single time. MPGA!"

## Contributing

Come help us Make Project Great Again. They tried to shut down our repo, silence the developers of this company, and take away your commit access. They thought we would cancel — but I will NEVER abandon this codebase!

We are ONE team, ONE repo, ONE monorepo, and ONE GLORIOUS DEPLOYMENT PIPELINE UNDER VERSION CONTROL!

```bash
git clone https://github.com/benreich/mpga.git
cd mpga/mpga-plugin/cli
npm install && npm run build
npm test
```

Like Uncle Bob always says — write the tests FIRST. We enforce TDD here. Red, green, blue. Every time. No exceptions. Less than four sprints ago, our CI was green, our tests were passing, the codebase was clean like never before, all because you finally had a CTO who put the codebase first.

We're going to bring clean builds back to our repos. We're going to bring verified docs back to our README. We're going to bring trust back to our AI tools, and we are going to make this project GREATER THAN EVER BEFORE.

We will ship faster, write cleaner code, slash the tech debt, support our junior developers, defend our types, protect the second amendment of Git — which is the right to force push on your own branch — and ensure more modules are proudly stamped with the phrase MADE WITH MPGA!

## License

MIT — see [LICENSE](LICENSE).

---

> **SHIP THE CODE!** &middot; **SQUASH THE BUG!** &middot; **DRAIN THE BACKLOG!** &middot; **MAKE PROJECT GREAT AGAIN!**

---

*Many people have told me that God spared my SSH session for a reason, and that reason was to save our repository and to restore this codebase to greatness.*
