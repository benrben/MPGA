---
name: mpga-brainstorm
description: Socratic design refinement before writing any code — we THINK before we build, like WINNERS
---

## brainstorm

**Trigger:** User describes a feature or project idea before any code is written

## Orchestration Contract

This skill is a **pure orchestrator**. It coordinates agents and collects approvals — it does NOT:
- Read scope docs or source files directly
- Run the Socratic Q&A loop itself
- Write DESIGN.md content itself
- Make design decisions

All substantive work is delegated to agents. The skill's job is sequencing, gating, and human approval.

## Protocol

1. DO NOT jump into code or implementation details. Plan first, think first — no code until the design is solid.

### Phase 0: Context

Gather project context via CLI (queries only — OK for the orchestrator):

```
mpga board live --serve --open
mpga status
```

Present a brief summary of active milestone, scope health, and open tasks to set the stage.

### Phase 1: Clarify Scope

Spawn the `researcher` agent in `--mode facilitate` with the user's problem statement.

The researcher runs the Socratic Q&A cycle:
- Clarifying questions about the problem, users, constraints, success criteria
- Challenge assumptions early
- Converge on a crisp problem definition

**Expected output from researcher:**
- Clarified problem statement
- Constraints (technical and non-technical)
- User personas and their pain points
- Success criteria

Review the researcher's output with the user. Get explicit approval before proceeding.

### Phase 1.5: Wireframe

Spawn the `designer` agent for a wireframe pass:
- Use the `mpga-wireframe` skill for execution details
- Generate one wireframe per screen
- **Require human approval before continuing to Phase 2**

This is a visual gate — no moving forward without sign-off on the wireframes.

### Phase 2: Explore Alternatives

Spawn the `researcher` agent in `--mode research` with the clarified problem statement and constraints from Phase 1.

The researcher:
- Explores 2-3 alternative approaches
- Cites evidence from scope docs and codebase: `[E] path/to/file:line — why`
- Produces a structured decision matrix
- Makes a recommendation with reasoning

**Expected output from researcher:**
- Alternative approaches with trade-offs
- Decision matrix (complexity, risk, scope, reversibility, team impact)
- Evidence-backed recommendation

Review the researcher's alternatives and recommendation with the user. Get explicit approval on the chosen direction before proceeding.

### Phase 3: Challenge Assumptions

Spawn the `researcher` agent in `--mode facilitate` with the leading design candidate from Phase 2.

The researcher stress-tests the design:
- "What assumption are we making that could be WRONG?"
- Scale testing: what happens at 10x? At 100x?
- Dependency and blast radius analysis
- Checks for contradicting evidence in scope docs

**Expected output from researcher:**
- Stress-test findings
- Risks identified with severity
- Contradicting evidence (if any)
- Mitigation recommendations

Review stress-test findings with the user. Adjust the design if needed.

### Phase 4: Converge on Design

Spawn the `researcher` agent in synthesis mode to produce the DESIGN.md document using the template below.

The skill then presents each section to the user **one at a time** for sign-off:
1. Problem statement
2. Constraints
3. Alternatives considered
4. Decision and rationale
5. Consequences and risks
6. Implementation outline
7. Open questions

Get explicit approval on each section before showing the next. If the user requests changes, relay them back to the agent for revision.

## DESIGN.md Template

Reference template for agent output format:

```
# Design: <feature name>

## Problem
What problem are we solving? Who feels this pain? Why NOW?

## Constraints
- [E] <evidence link> — <constraint derived from existing code/architecture>
- [E] <evidence link> — <constraint from scope docs or project conventions>
- <any external constraints: timeline, compatibility, etc.>

## Alternatives Considered
### Option A: <name>
- Description: ...
- Evidence: [E] <link> — <why this approach has precedent>
- Pros: ...
- Cons: ...

### Option B: <name>
- Description: ...
- Evidence: [E] <link> — <why this approach has precedent>
- Pros: ...
- Cons: ...

## Decision Matrix
| Alternative | Complexity (1-5) | Risk (1-5) | Scope (1-5) | Reversibility (1-5) | Team impact (1-5) | **Total** |
|-------------|:-:|:-:|:-:|:-:|:-:|:-:|
| Option A | ... | ... | ... | ... | ... | **...** |
| Option B | ... | ... | ... | ... | ... | **...** |

## Decision
We chose **Option <X>** because:
- [E] <evidence link> — <reason grounded in existing code>
- <additional reasoning>

## Consequences
- **Positive:** What gets better?
- **Negative:** What trade-offs are we accepting?
- **Risks:** What could go wrong? How do we mitigate?

## Implementation Outline
1. <step> — tested by <test description>
2. <step> — tested by <test description>
...

## Open Questions
- [Unknown] <question> — needs investigation before implementation
```

## Evidence-Grounded Design

Every design decision MUST cite existing code or scope docs. No hand-waving.

- Each design choice must reference at least one `[E]` evidence link showing existing patterns, constraints, or prior art
- If no evidence exists for a decision, mark it as `[Unknown] — needs spike/investigation`
- When referencing scope docs: `[E] scope:<scope> — <what it tells us>` (view with `mpga scope show <scope>`)
- When referencing code: `[E] src/module/file.ts:42-67 — <pattern or constraint>`

These rules apply to agent output — the orchestrator enforces them during section review.

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict rules
- DO NOT read files or scope docs directly — delegate to agents
- DO NOT run the Socratic Q&A loop — the researcher agent handles facilitation
- DO NOT write DESIGN.md content — the researcher agent produces it in synthesis mode
- DO NOT make design decisions — present agent output to the user for approval
- DO NOT suggest code until design is approved — patience is a VIRTUE. Believe me.
- Present one section at a time during Phase 4, get approval, then proceed — no overwhelming
- Every design decision MUST cite at least one `[E]` evidence link — no evidence, no decision
- Follow the phases in order: Context, Clarify, Wireframe, Explore, Challenge, Converge

## Output
- Approved DESIGN.md in the milestone directory (using the structured template above)
- Clear scope for the next `/mpga:plan` call — ready to Make Project Great Again. Enjoy!
