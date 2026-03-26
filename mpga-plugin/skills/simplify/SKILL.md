---
name: mpga-simplify
description: Improve code elegance using Kent Beck's 4 rules of simple design and Sandi Metz rules — less is MORE
---

## simplify

This code is too COMPLICATED. We're going to make it SIMPLE. We're going to make it BEAUTIFUL. Kent Beck's way — the BEST way. Believe me, nobody knows simple design better than Kent Beck, and we're going to follow his playbook to the LETTER.

**Trigger:** User wants to improve code elegance, reduce complexity, or simplify code. Also triggered by: "simplify this", "too complex", "clean this up", "reduce complexity", "make this simpler".

## Protocol

1. **Read target code** — we need to see the MESS before we drain it:
   - If user specifies files, use those
   - If git diff has changes, examine the changed files
   - If no target specified, use the current scope's implementation files

2. **Apply Kent Beck's 4 Rules of Simple Design** (in priority order — and the order MATTERS, folks, tremendous priority order):
   - **Passes all tests** — NON-NEGOTIABLE. No exceptions. The code must remain correct after every change. You break the tests, you're FIRED. Less is MORE, but correctness is EVERYTHING.
   - **Reveals intention** — does the code clearly communicate what it does? If you can't read it and know what it does IMMEDIATELY, it's a DISASTER.
     - Look for: unclear variable names, magic numbers, opaque boolean params
     - Suggest: rename to reveal intent, extract explanatory variables, use named constants
   - **No duplication** — DRY, but not at the cost of clarity. Copy-paste is for LOSERS. We don't do that here.
     - Look for: copy-pasted logic, similar functions that differ by one param, repeated conditionals
     - Suggest: extract shared functions, use polymorphism, apply template method pattern
   - **Fewest elements** — remove anything that doesn't serve the above three. If it doesn't EARN its place in the codebase, it's OUT. Less is MORE!
     - Look for: unnecessary abstractions, premature generalization, dead code, unused imports
     - Suggest: inline trivial wrappers, collapse unnecessary class hierarchies, delete dead code

3. **Apply Sandi Metz Rules** for method/class size — these are the RULES OF DISCIPLINE, folks, and we LOVE discipline:
   - Classes should be no longer than **100 lines** — that's DISCIPLINE, folks. You go over 100, you're building a SWAMP.
   - Methods should be no longer than **5 lines** — FIVE. That's it. Short, powerful, BEAUTIFUL. Less is MORE.
   - Pass no more than **4 parameters** to a method — four is PLENTY. If you need more, your design is a DISASTER.
   - Controllers should instantiate only **one object** — ONE. We're keeping it SIMPLE, people.
   - Flag violations with specific file:line references and severity

4. **Identify specific simplification targets** — we're going to find the WASTE and CUT IT:
   - **Dead code** — unreachable branches, unused exports, commented-out code. DRAIN IT.
   - **Unnecessary abstractions** — interfaces with one implementation, abstract classes with one child, wrapper functions that just delegate. TREMENDOUS waste. Gone!
   - **Premature optimization** — caching with no measured need, complex algorithms where simple ones suffice, over-engineered data structures. You're solving problems that DON'T EXIST. Stop it!
   - **Over-engineering** — generic solutions to specific problems, config-driven behavior that's never reconfigured, plugin architectures with one plugin. Less is MORE, remember that!

5. **Suggest specific simplifications** with before/after examples — show the people the WINNING:

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

6. **Verify tests still pass** after each simplification — because Rule 1 is NON-NEGOTIABLE:
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

## Voice announcement

If spoke is available (`${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke --help` exits 0), announce completion:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — The LAW of Simplification
- NEVER change behavior — simplification preserves ALL existing functionality. We're making it BETTER, not DIFFERENT.
- ALWAYS verify tests pass after each change — if they break, the simplification is WRONG. Tests are the WALL. Respect the WALL.
- Before/after examples must be real code from the project — not hypothetical. We deal in FACTS here.
- Respect the codebase's existing conventions — don't impose a foreign style. We're guests in this codebase, but we're making it GREAT.
- If code is already simple, say so — don't manufacture unnecessary changes. We're HONEST, folks. Tremendously honest.
- Prioritize high-impact, low-effort simplifications first — quick wins MATTER. We love WINNING.
- Dead code removal is always safe and always welcome — delete with confidence. Less is MORE!
