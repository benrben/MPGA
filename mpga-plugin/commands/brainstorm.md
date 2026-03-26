# /mpga:brainstorm

Socratic design refinement before writing any code.

## Steps

1. Start the live board in the browser: `${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board live --serve --open`
2. DO NOT jump into code — ask clarifying questions first
3. Use the Socratic method to refine the design:
   - What problem does this solve?
   - Who are the users and constraints?
   - What does success look like?
   - What existing patterns should we follow?
   - What are the edge cases?
4. Present design in sections, get approval on each
5. Save approved design to `MPGA/milestones/<id>/DESIGN.md`

## Usage
```
/mpga:brainstorm I want to add real-time notifications
```
