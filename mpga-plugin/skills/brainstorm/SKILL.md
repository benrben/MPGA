---
description: Socratic design refinement before writing any code
---

## brainstorm

**Trigger:** User describes a feature or project idea before any code is written

## Protocol

1. DO NOT jump into code or implementation details
2. Ask clarifying questions using the Socratic method:
   - "What problem does this solve for the user?"
   - "Who are the primary users and what are their constraints?"
   - "What does success look like — how will you know it's working?"
   - "Are there existing patterns in the codebase we should follow?"
   - "What are the edge cases and failure modes?"

3. Present the design in digestible sections:
   - User experience / API shape
   - Data model changes
   - Integration points
   - Security considerations
   - Testing approach

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
- DO NOT suggest code until design is approved
- DO NOT make assumptions — ask instead
- Present one section at a time, get approval, then proceed
- Save DESIGN.md before creating milestone or tasks

## Output
- Approved DESIGN.md in the milestone directory
- Clear scope for the next `/mpga:plan` call
