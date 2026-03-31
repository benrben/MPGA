---
name: mpga-onboard
description: Guided codebase tour from INDEX.md outward
---

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read files directly (delegates to scout and architect agents)
- Write any files
- Run CLI commands other than `mpga` board/status/scope list queries

## onboard

**Trigger:** User is new to the codebase or starting a fresh session.

## Protocol

### Step 1 — CLI queries (skill runs directly)

1. Run `mpga status` — capture project identity, health, active milestone.
2. Run `mpga scope list` — capture the list of all scopes.
3. Run `mpga board show` — capture active milestone and board state.

### Step 2 — Spawn scout agents in PARALLEL (read-only)

For each scope returned by `mpga scope list`, spawn a **scout** agent:
- Mode: read-only
- Task: Investigate the scope and return:
  - **Scope purpose** — one-sentence summary of what this scope does
  - **Key files** — the most important files in the scope
  - **Primary responsibilities** — what this scope owns
  - **Health status** — evidence quality, staleness, any drift

All scouts run in parallel. Wait for all to complete before proceeding.

### Step 3 — Spawn architect agent (read-only)

Spawn a single **architect** agent:
- Mode: read-only
- Task: Analyze the project and return:
  - **Dependency graph** — how scopes depend on each other
  - **Cross-scope connections** — shared interfaces, data flows, integration points
  - **Architectural overview** — system structure, key patterns, design philosophy

### Step 4 — Assemble the guided tour

Combine agent outputs into a structured tour following the Presentation order below.
Order the scope-by-scope walkthrough by dependency (foundations first, dependents later),
using the architect's dependency graph.

### Step 5 — Present the tour in sections

Present one section at a time — do NOT overwhelm with all information at once.

### Step 6 — Invite exploration

Ask: "Which area would you like to explore first?"

## Presentation order
1. Project identity (from `mpga status`)
2. Architecture overview (from architect agent)
3. Scope-by-scope walkthrough (from scout agents, ordered by dependency)
4. Active milestone and board state (from `mpga board show`)
5. Suggested starting points (skill's judgment based on agent outputs)

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters.

## Strict rules
- NEVER read files directly — delegate to scout/architect agents.
- Do NOT overwhelm with all information at once — present in sections.
- Ask which area the user wants to dig into after the overview.
- Cite evidence links for all claims about the codebase.
- If scope docs are stale, mention it and suggest `mpga sync`.
