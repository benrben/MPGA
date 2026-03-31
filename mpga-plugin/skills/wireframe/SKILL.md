---
name: mpga-wireframe
description: Visualize a feature before coding with renderer-aware wireframes and staged approval
---

## wireframe

**Trigger:** The user wants to visualize a feature before coding, compare layouts, or get a quick UI checkpoint before implementation begins.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

## Protocol

1. Detect the best renderer available:
   - Excalidraw if the MCP is connected
   - HTML if local browser preview is available
   - SVG if a portable image is better
   - ASCII as the final always-works fallback
2. Ask how many screens are needed if the request is ambiguous.
3. Spawn the `designer` agent to produce one wireframe per screen.
4. Present each screen for human approval before moving forward.
5. Save approved artifacts to the milestone design directory (`mpga milestone show <id>`).
6. Offer prototype escalation once the wireframes are approved.

## Designer handoff
- Use the `designer` agent for execution.
- Keep all artifacts stack-agnostic and local-first.

## Evidence rules
- Run `mpga status` and read the relevant scope docs before proposing structure.
- Capture any concrete design constraints with `[E]` links when they come from the codebase.
- Mark unknown design constraints as `[Unknown]`.

## Strict rules
- NO implementation code until the wireframe is approved.
- Every substantial design claim should be grounded in evidence when the codebase already implies a constraint.
- Keep the artifacts local, safe, and reviewable offline.

## Voice announcement
If spoke is available:
```bash
mpga spoke '<brief 1-sentence result summary>'
```

## Output
- Approved wireframes in the milestone design directory (`mpga milestone show <id>`)
- Renderer choice summary
- Clear next step: approve, revise, or escalate to prototype
