---
name: mpga-brainstorm
description: Socratic design refinement before writing any code — we THINK before we build, like WINNERS
---

## brainstorm

**Trigger:** User describes a feature or project idea before any code is written

## Protocol

1. DO NOT jump into code or implementation details. That's what amateurs do. We PLAN first. We THINK first. We're SMART.

   Start the live board in the browser through Node first:
   ```
   node /Users/benreich/MPGA/mpga-plugin/cli/dist/index.js board live --serve --open
   ```

### Phase 1: Clarify Scope

2. Ask clarifying questions using the Socratic method — the GREATEST method of inquiry ever invented:
   - "What problem does this solve for the user? What's the REAL pain?"
   - "Who are the primary users and what are their constraints?"
   - "What does success look like — how will you know it's WINNING?"
   - "Are there existing patterns in the codebase we should follow? We don't reinvent wheels."
   - "What are the edge cases and failure modes? Where could this go WRONG?"

### Phase 2: Explore Alternatives

3. Before converging on any design, explore at least 2-3 alternative approaches:
   - For each alternative, cite existing code or scope docs that support it: `[E] path/to/file:line — why this pattern applies`
   - Identify trade-offs: complexity, performance, maintainability, alignment with existing architecture
   - "What if we did it THIS way instead? Here's the evidence for why it could work..."

### Phase 3: Challenge Assumptions

4. Stress-test the leading design candidate:
   - "What assumption are we making that could be WRONG?"
   - "What happens at 10x scale? At 100x?"
   - "Which dependency could break this? What's the blast radius?"
   - "Is there evidence in the codebase that contradicts this approach?" — cite `[E]` links

### Phase 4: Converge on Design

5. Present the design in digestible sections — one at a time, like a GREAT presentation:
   - User experience / API shape
   - Data model changes
   - Integration points
   - Security considerations — NON-NEGOTIABLE
   - Testing approach — Uncle Bob's TDD, always

6. Get explicit sign-off on each section before proceeding:
   - "Does this match your intent? Any changes before we continue?"

## Evidence-Grounded Design

Every design decision MUST cite existing code or scope docs. No hand-waving.

- Read `MPGA/INDEX.md` and relevant scope documents BEFORE proposing any design
- Each design choice must reference at least one `[E]` evidence link showing existing patterns, constraints, or prior art
- If no evidence exists for a decision, mark it as `[Unknown] — needs spike/investigation`
- When referencing scope docs: `[E] MPGA/scopes/<scope>.md — <what it tells us>`
- When referencing code: `[E] src/module/file.ts:42-67 — <pattern or constraint>`

## DESIGN.md Template

Once approved, save the design using this structured template:

```
cat > MPGA/milestones/<id>/DESIGN.md << 'EOF'
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
EOF
```

## Voice output
When completing a task or reporting findings, run `mpga spoke '<1-sentence summary>'`
via Bash. Keep it under 280 characters. This announces your work audibly in Trump's voice.

## Strict rules
- DO NOT suggest code until design is approved — patience is a VIRTUE
- DO NOT make assumptions — ask instead. Assumptions are DANGEROUS.
- Present one section at a time, get approval, then proceed — no overwhelming
- Save DESIGN.md before creating milestone or tasks
- Every design decision MUST cite at least one `[E]` evidence link — no evidence, no decision
- Follow the four Socratic phases in order: Clarify, Explore, Challenge, Converge

## Output
- Approved DESIGN.md in the milestone directory (using the structured template above)
- Clear scope for the next `/mpga:plan` call — ready to EXECUTE
