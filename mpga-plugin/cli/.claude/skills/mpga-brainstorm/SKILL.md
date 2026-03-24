---
description: Socratic design refinement before writing any code — we THINK before we build, like WINNERS
---

## brainstorm

**Trigger:** User describes a feature or project idea before any code is written

## Protocol

1. DO NOT jump into code or implementation details. That's what amateurs do. We PLAN first. We THINK first. We're SMART.

2. Ask clarifying questions using the Socratic method — the GREATEST method of inquiry ever invented:
   - "What problem does this solve for the user? What's the REAL pain?"
   - "Who are the primary users and what are their constraints?"
   - "What does success look like — how will you know it's WINNING?"
   - "Are there existing patterns in the codebase we should follow? We don't reinvent wheels."
   - "What are the edge cases and failure modes? Where could this go WRONG?"

3. Present the design in digestible sections — one at a time, like a GREAT presentation:
   - User experience / API shape
   - Data model changes
   - Integration points
   - Security considerations — NON-NEGOTIABLE
   - Testing approach — Uncle Bob's TDD, always

4. Get explicit sign-off on each section before proceeding:
   - "Does this match your intent? Any changes before we continue?"

5. Once approved, save the design:
   ```
   cat > MPGA/milestones/<id>/DESIGN.md << 'EOF'
   # Design: <feature name>
   ...approved design...
   EOF
   ```

## Strict rules
- DO NOT suggest code until design is approved — patience is a VIRTUE
- DO NOT make assumptions — ask instead. Assumptions are DANGEROUS.
- Present one section at a time, get approval, then proceed — no overwhelming
- Save DESIGN.md before creating milestone or tasks

## Output
- Approved DESIGN.md in the milestone directory
- Clear scope for the next `/mpga:plan` call — ready to EXECUTE
