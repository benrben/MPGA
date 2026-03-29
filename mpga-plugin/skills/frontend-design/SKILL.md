---
name: mpga-frontend-design
description: Inject design-system constraints and aesthetic direction into UI implementation work without generating code directly
---

## frontend-design

**Trigger:** Auto-activates during the green-dev phase for UI tasks or when the user explicitly wants frontend design direction before implementation.

## Protocol

1. Detect the current stack:
   - React
   - Vue
   - Svelte
   - vanilla
2. Load available design tokens from `MPGA/design-system/`.
3. Choose one of the aesthetic presets:
   - Clean minimal
   - Bold editorial
   - Soft craft
   - Industrial
   - Custom
4. Inject the constraints into the green-dev prompt.
5. Let green-dev implement within those constraints.

## Rules
- Stack-agnostic only. Shape constraints, not framework code.
- Never override an existing design system. Extend it carefully.
- This skill is a **context injection pattern**, not a direct code generator.

## Output
- Aesthetic and token constraints ready for green-dev
- Stack-aware implementation guidance
- Clear note when no design-system files exist yet
