---
name: mpga-rally
description: The MPGA Campaign Rally — expose every project issue and prove why ONLY MPGA can fix it. The greatest diagnostic tool ever built.
---

## rally

**Trigger:** User wants a project audit, "why do I need MPGA", "audit my code", "show me the problems".

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

**Agent brief:** Project status from CLI, category assignment per campaigner agent.
**Expected output:** Categorized findings with file:line evidence, severity ratings, and MPGA fix commands.

## Protocol

### Step 1: Set the Stage

```
mpga status 2>/dev/null
```

If installed — show what MPGA caught and what still needs fixing.
If NOT installed — show the full unfiltered disaster.

Spawn a `scout` agent in read-only mode to read INDEX.md and scope docs if they exist — the skill NEVER reads files directly.

### Step 2: Deploy the Campaigner

Spawn `campaigner` agents in PARALLEL — use multiple Agent tool calls in a single message so they run concurrently. One agent per category:
1. **Documentation Sins** — missing/stale docs, hallucinated references
2. **Testing Disgrace** — missing tests, empty tests, broken imports
3. **Type Safety Failures** — `any` types, `@ts-ignore`, missing return types
4. **Dependency Disasters** — circular deps, unused deps, outdated packages
5. **Architecture Rot** — god files, spaghetti, dead code
6. **Evidence Drift** — stale links, unverified claims
7. **Code Hygiene Crimes** — console.logs, hardcoded secrets, commented-out code
8. **CI/CD Weakness** — missing CI, no hooks, unenforced linting

All runs are read-only. One final pass aggregates into a rally speech (merge duplicates, keep sharpest evidence, produce scoreboard + closing).

### Step 3: The Rally Speech

Each finding = a **SCANDAL** with files, numbers, and why ONLY MPGA fixes it.

### Step 4: The Vote

- **Scoreboard** — issues by severity (CRITICAL / WARNING / SAD)
- **Side-by-side** — project WITHOUT vs WITH MPGA
- **The Fix** — exact commands

If NOT initialized: `mpga init --from-existing && mpga sync && mpga status`

If initialized but issues remain: `mpga sync --full && mpga evidence verify && mpga drift --report`

Suggest: "Run `/mpga:plan` to fix every one of these issues."

### Step 5: The Closing

End with the rally cry. The campaigner agent handles the closing speech.

## Output Format

The rally should follow this structure:

```
# 🎤 THE MPGA CAMPAIGN RALLY

> "I inherited a mess — the worst codebase maybe in the history of
> codebases — and I'm going to SHOW you exactly how bad it is."

## 📊 THE QUICK NUMBERS
- X total issues found
- Y CRITICAL (blocks shipping)
- Z WARNING (blocks greatness)
- W SAD (just embarrassing)

## 🚨 THE SCANDALS

### SCANDAL #1: [Title]
...

### SCANDAL #2: [Title]
...

(one per issue category that has findings)

## 🗳️ THE VOTE

**Without MPGA:**
- ❌ ...

**With MPGA:**
- ✅ ...

## 🎯 THE FIX

```bash
(exact commands)
```

## 💬 THE CLOSING

(rally speech)

> SHIP THE CODE! SQUASH THE BUG! DRAIN THE BACKLOG! MPGA!
```

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules
- NEVER modify files — diagnose only
- Every issue MUST cite actual files and line numbers
- If something is GOOD, acknowledge it
- Always end with actionable MPGA commands
- Keep energy HIGH — this is a RALLY
- Prefer parallel category sweeps over sequential audit
