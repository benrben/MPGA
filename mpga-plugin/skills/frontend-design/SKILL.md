---
name: mpga-frontend-design
description: Inject design-system constraints and aesthetic direction into UI implementation work without generating code directly
---

## frontend-design

**Trigger:** Auto-activates during the green-dev phase for UI tasks or when the user explicitly wants frontend design direction before implementation.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read files directly (delegates to scout agents)
- Write any files (context injection only)
- Run CLI commands other than `mpga` board/status/scope queries

## Protocol

1. **Spawn `scout` agent** in read-only mode on the project root.
   - Returns: detected stack (React / Vue / Svelte / vanilla), framework config files found.
2. **Spawn `token-auditor` agent** (or query `mpga design-system list`) to retrieve available design tokens from the DB.
   - Returns: token categories, values, and any existing theme metadata.
3. **Select aesthetic preset** based on scout findings + user preference:
   - Clean minimal
   - Bold editorial
   - Soft craft
   - Industrial
   - Custom
4. **Assemble constraint context object** from agent outputs — stack info, tokens, and chosen preset merged into a single structured context.
5. **Pass constraint context** to `mpga-develop` / green-dev as input. Let green-dev implement within those constraints.

## Output
- Aesthetic and token constraints ready for green-dev
- Stack-aware implementation guidance
- Clear note when no design-system files exist yet

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters.

## Strict Rules
- NEVER read project files directly — `scout` handles stack detection, `token-auditor` handles token reads
- NEVER write code or generate components — this is a context injection pattern, not a code generator
- Stack-agnostic constraints ONLY — shape constraints, not framework code
- NEVER override an existing design system — extend it carefully
- ALWAYS pass constraints to green-dev as structured input — the skill produces context, not implementation
