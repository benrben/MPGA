---
name: mpga-simplify
description: Improve code elegance using Kent Beck's 4 rules of simple design and Sandi Metz rules — less is MORE
---

## simplify

Simplify code using Kent Beck's 4 Rules of Simple Design and Sandi Metz rules.

**Trigger:** User wants to improve code elegance, reduce complexity, or simplify code. Also triggered by: "simplify this", "too complex", "clean this up", "reduce complexity", "make this simpler".

## Orchestration Contract

This skill is a **pure orchestrator**. It NEVER reads source files, NEVER edits code, NEVER runs tests directly. All code-level work is delegated to specialized agents. The skill's ONLY job is to coordinate agents in the correct sequence, pass structured briefs between them, and compile the final report. If you catch yourself opening a file or writing a diff — STOP. You are doing it wrong.

## Protocol

1. **Read task context** — gather scope and board state via the CLI:
   ```bash
   mpga board show          # current tasks and priorities
   mpga scope show          # active scope boundaries
   ```
   If the user specified target files or paths, include them in the brief for the optimizer agent. If git diff has changes, pass the list of changed files. Otherwise, let the optimizer work from the current scope.

2. **Spawn `optimizer` agent** — get a ranked complexity report:

   Provide the optimizer with the target files/scope and instruct it to produce a ranked list of findings. Each finding must include:
   - **File and line range** (e.g., `path/to/file.py:42-67`)
   - **Kent Beck rule violated** (in priority order — and the order MATTERS, folks, tremendous priority order):
     - **Rule 1: Passes all tests** — NON-NEGOTIABLE. The code must remain correct after every change.
     - **Rule 2: Reveals intention** — does the code clearly communicate what it does? If you can't read it and know what it does IMMEDIATELY, it's a DISASTER.
       - Unclear variable names, magic numbers, opaque boolean params
     - **Rule 3: No duplication** — DRY, but not at the cost of clarity.
       - Copy-pasted logic, similar functions that differ by one param, repeated conditionals
     - **Rule 4: Fewest elements** — remove anything that doesn't serve the above three. If it doesn't EARN its place in the codebase, it's OUT. Less is MORE!
       - Unnecessary abstractions, premature generalization, dead code, unused imports
   - **Sandi Metz rule violated** — these are the RULES OF DISCIPLINE, folks, and we LOVE discipline:
     - Classes no longer than **100 lines**
     - Methods no longer than **5 lines** — FIVE. That's it. Short, powerful, BEAUTIFUL. Less is MORE.
     - No more than **4 parameters** per method — four is PLENTY. If you need more, your design is a DISASTER.
     - Controllers instantiate only **one object** — ONE. We're keeping it SIMPLE, people.
   - **Severity** (HIGH / MEDIUM / LOW)
   - **Estimated effort** (Small / Medium / Large)
   - **Suggested simplification** (e.g., "extract helper", "inline wrapper", "rename for intent")

   The optimizer ranks findings by **high-impact, low-effort first** — quick wins MATTER. We love WINNING.

   If the optimizer reports that the code already meets all rules, announce that result and stop — we're HONEST, folks. Tremendously honest.

3. **For each finding** (in the optimizer's priority order):

   **a. Spawn `blue-dev` agent** with a simplification brief containing:
   - The specific `file:line` target from the optimizer report
   - The Beck/Metz rule violated
   - The expected simplification (e.g., "extract helper", "inline wrapper", "rename for intent")
   - **Constraint: NEVER change behavior, only shape** — simplification preserves ALL existing functionality. We're making it BETTER, not DIFFERENT.
   - If no tests exist for the target code, blue-dev must flag it and SKIP — do NOT simplify code without a safety net.

   **b. blue-dev applies the change and runs tests.**

   **c. If tests fail** → blue-dev reverts the change and marks the finding as **"skipped (test regression)"**. Move on to the next finding.

   **d. Spawn `reviewer` agent** → validate the simplification preserved behavior:
   - Reviewer checks that no logic changed, only structure/naming/shape
   - Reviewer checks that the simplification actually improves clarity per the cited rule

   **e. If reviewer returns FAIL** → send the reviewer's feedback back to blue-dev for a fix attempt. **Max 2 retries.** If blue-dev cannot satisfy the reviewer after 2 retries, mark the finding as **"skipped (reviewer rejection)"** and move on.

4. **After all simplifications: spawn `verifier` agent** — collect before/after metrics:
   - Total lines changed
   - Number of Beck/Metz violations resolved
   - Test suite pass/fail status
   - Any regressions introduced (should be zero)

5. **Present simplification report** to the user (see Output Format below).

## Output Format

```
# SIMPLIFICATION REPORT

## Summary
- Files analyzed: N
- Simplifications applied: N
- Simplifications skipped (test regression / no tests / reviewer rejection): N
- Kent Beck violations fixed: N
- Sandi Metz violations fixed: N

## Applied changes (priority order)
1. [HIGH] path/to/file.py:42 — extracted helper function — Rule 3 (No duplication)
2. [MEDIUM] path/to/other.py:18 — renamed opaque variable to `user_event_count` — Rule 2 (Reveals intention)

## Skipped (require manual review)
1. [HIGH] path/to/complex.py:88 — test regression on extraction, tests appear over-specified
2. [MEDIUM] path/to/wrapper.py:12 — reviewer rejection: inline removed error handling boundary

## Skipped targets summary
At the end of the run, print a summary of any targets that were skipped and the reason for each skip:

    Skipped targets:
      - foo.py — already meets all 4 rules of simple design (no changes needed)
      - bar.py — no tests exist; cannot safely simplify without a safety net
      - baz.py:88 — test regression on extraction; tests appear over-specified
      - qux.py:12 — reviewer rejection after 2 retries; inline removed error handling boundary

A target is "skipped" if: it has no tests, it already meets all rules, every attempted simplification caused a test regression, or the reviewer rejected the change after max retries.

## Before/After Metrics (from verifier)
- Lines changed: N
- Beck violations resolved: N
- Metz violations resolved: N
- Test suite: PASS / FAIL
```

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — The LAW of Simplification
- This skill is a PURE ORCHESTRATOR — it spawns agents, it does NOT read files, edit code, or run tests directly. EVER.
- NEVER change behavior — simplification preserves ALL existing functionality. We're making it BETTER, not DIFFERENT.
- NEVER simplify code that has no tests — flag it, recommend writing tests first, then skip.
- Respect the codebase's existing conventions — don't impose a foreign style. We're guests in this codebase, but we're making it GREAT.
- If code is already simple, say so — don't manufacture unnecessary changes. We're HONEST, folks. Tremendously honest.
- Prioritize high-impact, low-effort simplifications first — quick wins MATTER. We love WINNING.
- Dead code removal is always safe and always welcome — delete with confidence.
- Max 2 retries on reviewer rejection — then skip and move on. We don't waste time on losing battles.
