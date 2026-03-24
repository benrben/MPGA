---
name: mpga-simplify
description: Improve code elegance using Kent Beck's 4 rules of simple design and Sandi Metz rules — less is MORE
---

## simplify

**Trigger:** User wants to improve code elegance, reduce complexity, or simplify code. Also triggered by: "simplify this", "too complex", "clean this up", "reduce complexity", "make this simpler".

## Protocol

1. **Read target code** — determine what to simplify:
   - If user specifies files, use those
   - If git diff has changes, examine the changed files
   - If no target specified, use the current scope's implementation files

2. **Apply Kent Beck's 4 Rules of Simple Design** (in priority order):
   - **Passes all tests** — the code must remain correct after every change
   - **Reveals intention** — does the code clearly communicate what it does?
     - Look for: unclear variable names, magic numbers, opaque boolean params
     - Suggest: rename to reveal intent, extract explanatory variables, use named constants
   - **No duplication** — DRY, but not at the cost of clarity
     - Look for: copy-pasted logic, similar functions that differ by one param, repeated conditionals
     - Suggest: extract shared functions, use polymorphism, apply template method pattern
   - **Fewest elements** — remove anything that doesn't serve the above three
     - Look for: unnecessary abstractions, premature generalization, dead code, unused imports
     - Suggest: inline trivial wrappers, collapse unnecessary class hierarchies, delete dead code

3. **Apply Sandi Metz Rules** for method/class size:
   - Classes should be no longer than **100 lines**
   - Methods should be no longer than **5 lines**
   - Pass no more than **4 parameters** to a method
   - Controllers should instantiate only **one object**
   - Flag violations with specific file:line references and severity

4. **Identify specific simplification targets**:
   - **Dead code** — unreachable branches, unused exports, commented-out code
   - **Unnecessary abstractions** — interfaces with one implementation, abstract classes with one child, wrapper functions that just delegate
   - **Premature optimization** — caching with no measured need, complex algorithms where simple ones suffice, over-engineered data structures
   - **Over-engineering** — generic solutions to specific problems, config-driven behavior that's never reconfigured, plugin architectures with one plugin

5. **Suggest specific simplifications** with before/after examples:

   ```
   # SIMPLIFICATION REPORT

   ## Simplification #1: [Title]
   **Rule violated:** Kent Beck Rule 4 (Fewest Elements) / Sandi Metz (>5 lines)
   **File:** path/to/file.ts:42-67
   **Effort:** Small (< 30 min)

   ### Before
   ```typescript
   // the current code
   ```

   ### After
   ```typescript
   // the simplified code
   ```

   ### Why
   Brief explanation of why this is simpler and what it preserves.
   ```

6. **Verify tests still pass** after each simplification:
   - If tests exist, run them after suggesting each change
   - If no tests exist, flag this as a risk and suggest writing tests first
   - Never suggest a simplification that would change behavior — simplify, don't modify
   - If a simplification requires a test change, explain why the test was over-specified

## Output Format

```
# SIMPLIFICATION REPORT

## Summary
- Files analyzed: N
- Simplifications found: N
- Estimated total effort: Xh
- Kent Beck violations: N
- Sandi Metz violations: N

## Simplifications (priority order)
1. [HIGH] ... — effort: Small
2. [MEDIUM] ... — effort: Medium
3. [LOW] ... — effort: Small

## Detailed Suggestions
(before/after for each)
```

## Strict Rules
- NEVER change behavior — simplification preserves ALL existing functionality
- ALWAYS verify tests pass after each change — if they break, the simplification is WRONG
- Before/after examples must be real code from the project — not hypothetical
- Respect the codebase's existing conventions — don't impose a foreign style
- If code is already simple, say so — don't manufacture unnecessary changes
- Prioritize high-impact, low-effort simplifications first — quick wins MATTER
- Dead code removal is always safe and always welcome — delete with confidence
