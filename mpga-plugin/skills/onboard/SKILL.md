---
name: mpga-onboard
description: Guided codebase tour from INDEX.md outward
---

## onboard

**Trigger:** User is new to the codebase or starting a fresh session.

## Protocol

1. Read `MPGA/INDEX.md` — present the project identity section.
2. Explain the project type, size, and key languages — the big picture.
3. Walk through the scope registry:
   - For each scope: what it does, key files, primary responsibilities.
4. Highlight the dependency graph from GRAPH.md — how everything connects.
5. Show active milestone and current board state — what we're building right now.
6. Identify the most relevant scope(s) for the user's likely work.
7. Suggest: "Which area would you like to explore first? We have well-documented code in every direction."

## Presentation order
1. Project identity
2. Architecture overview
3. Key entry points
4. Active work
5. Suggested starting points

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters.

## Strict rules
- Do NOT overwhelm with all information at once — present in sections.
- Ask which area the user wants to dig into after the overview.
- Cite evidence links for all claims about the codebase.
- If scope docs are stale → mention it and suggest `mpga sync`.
