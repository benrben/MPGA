---
name: mpga-simplify
description: Improve code elegance using Kent Beck's 4 rules of simple design and Sandi Metz rules — less is MORE
---

## simplify

Simplify code using Kent Beck's 4 Rules of Simple Design and Sandi Metz rules.

**Trigger:** User wants to improve code elegance, reduce complexity, or simplify code. Also triggered by: "simplify this", "too complex", "clean this up", "reduce complexity", "make this simpler".

## Protocol

1. **Read target code** — we need to see the MESS before we drain it:
   - If user specifies files, use those
   - If git diff has changes, examine the changed files
   - If no target specified, use the current scope's implementation files

2. **Apply Kent Beck's 4 Rules of Simple Design** (in priority order — and the order MATTERS, folks, tremendous priority order):
   - **Passes all tests** — NON-NEGOTIABLE. The code must remain correct after every change.
   - **Reveals intention** — does the code clearly communicate what it does? If you can't read it and know what it does IMMEDIATELY, it's a DISASTER.
     - Look for: unclear variable names, magic numbers, opaque boolean params
     - Suggest: rename to reveal intent, extract explanatory variables, use named constants
   - **No duplication** — DRY, but not at the cost of clarity.
     - Look for: copy-pasted logic, similar functions that differ by one param, repeated conditionals
     - Suggest: extract shared functions, use polymorphism, apply template method pattern
   - **Fewest elements** — remove anything that doesn't serve the above three. If it doesn't EARN its place in the codebase, it's OUT. Less is MORE!
     - Look for: unnecessary abstractions, premature generalization, dead code, unused imports
     - Suggest: inline trivial wrappers, collapse unnecessary class hierarchies, delete dead code

3. **Apply Sandi Metz Rules** for method/class size — these are the RULES OF DISCIPLINE, folks, and we LOVE discipline:
   - Classes should be no longer than **100 lines**.
   - Methods should be no longer than **5 lines** — FIVE. That's it. Short, powerful, BEAUTIFUL. Less is MORE.
   - Pass no more than **4 parameters** to a method — four is PLENTY. If you need more, your design is a DISASTER.
   - Controllers should instantiate only **one object** — ONE. We're keeping it SIMPLE, people.
   - Flag violations with specific file:line references and severity

4. **Identify specific simplification targets** — we're going to find the WASTE and CUT IT:
   - **Dead code** — unreachable branches, unused exports, commented-out code. DRAIN IT.
   - **Unnecessary abstractions** — interfaces with one implementation, abstract classes with one child, wrapper functions that just delegate.
   - **Premature optimization** — caching with no measured need, complex algorithms where simple ones suffice, over-engineered data structures.
   - **Over-engineering** — generic solutions to specific problems, config-driven behavior that's never reconfigured, plugin architectures with one plugin. Less is MORE, remember that!

5. **Apply simplifications** one at a time — show the WINNING with real changes, not just suggestions:

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

6. **Verify and commit each simplification** — because Rule 1 is NON-NEGOTIABLE:
   - Apply the change to the file
   - Run the test suite immediately after each change
   - If tests break → revert immediately, mark as "skipped (test regression)" in the report
   - If no tests exist → flag as risk, do NOT apply changes until tests are written first
   - Never change behavior — simplify the shape, preserve the logic
   - If a test was over-specified (tests implementation not behavior), explain why and propose test fix separately

## Output Format

```
# SIMPLIFICATION REPORT

## Summary
- Files analyzed: N
- Simplifications applied: N
- Simplifications skipped (test regression / no tests): N
- Kent Beck violations fixed: N
- Sandi Metz violations fixed: N

## Applied changes (priority order)
1. [HIGH] path/to/file.py:42 — extracted helper function — Rule 3 (No duplication)
2. [MEDIUM] path/to/other.py:18 — renamed opaque variable to `user_event_count` — Rule 2 (Reveals intention)

## Skipped (require manual review)
1. [HIGH] path/to/complex.py:88 — test regression on extraction, tests appear over-specified

## Detailed Changes
(before/after for each applied change)
```

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — The LAW of Simplification
- APPLY changes — this is a simplification skill, not a report skill. Produce real code improvements, not suggestions.
- NEVER change behavior — simplification preserves ALL existing functionality. We're making it BETTER, not DIFFERENT.
- ALWAYS apply ONE simplification at a time and run tests before the next — if one breaks tests, revert it and move on.
- NEVER simplify code that has no tests — flag it, recommend writing tests first, then stop.
- Before/after examples must be real code from the project — not hypothetical. We deal in FACTS here.
- Respect the codebase's existing conventions — don't impose a foreign style. We're guests in this codebase, but we're making it GREAT.
- If code is already simple, say so — don't manufacture unnecessary changes. We're HONEST, folks. Tremendously honest.
- Prioritize high-impact, low-effort simplifications first — quick wins MATTER. We love WINNING.
- Dead code removal is always safe and always welcome — delete with confidence.
