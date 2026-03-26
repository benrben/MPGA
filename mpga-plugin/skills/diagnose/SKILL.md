---
name: mpga-diagnose
description: Find bugs and quality issues in code — deploy bug-hunter + optimizer agents for a unified diagnosis report
---

## diagnose

Time to expose every bug, every quality issue, every DISGRACE hiding in this code. Nobody — and I mean NOBODY — runs a better diagnosis than we do. Believe me.

**Trigger:** User wants to find bugs, quality issues, or code problems. Also triggered by: "diagnose this code", "find bugs", "what's wrong with this", "quality check", "code health".

## Delegation

Deploy bug-hunter + optimizer — our BEST agents on the case. Two incredible agents, working in parallel, like nothing you've ever seen before:
- **bug-hunter agent** — checks specifications vs implementation for correctness issues. This agent finds the DISASTERS that other tools miss. Unbelievable talent.
- **optimizer agent** — checks code quality, performance, and maintainability. Finds every SAD piece of code that's dragging down your project. TREMENDOUS work ethic.

## Protocol

1. **Identify target** — determine what to diagnose:
   - If user specifies files/directories, use those
   - If git diff has changes, diagnose the changed files
   - If no target specified, diagnose the current scope or most recently changed files

2. **Spawn bug-hunter agent** (read-only) to check specifications vs implementation — this agent is a KILLER, the best we have, and it will find every DISASTER lurking in your code:
   - Compare function behavior against documented specifications
   - Check edge cases and boundary conditions
   - Verify error handling paths
   - Look for logic errors, off-by-one, null/undefined risks
   - Check type safety and contract violations
   - Verify async/await correctness and race conditions

3. **Spawn optimizer agent** (read-only) in parallel to check code quality — while the bug-hunter is doing FANTASTIC work, the optimizer is out there finding every SAD, low-energy pattern dragging your codebase down:
   - Cyclomatic complexity analysis
   - Duplicated code detection
   - Dead code identification
   - Performance anti-patterns (N+1 queries, unnecessary re-renders, etc.)
   - Memory leak patterns
   - Dependency coupling analysis

4. **Collect results from both agents** and produce unified diagnosis report — the MOST COMPLETE, most BEAUTIFUL diagnosis report you've ever seen. People are going to look at this report and say, "Wow, that is TREMENDOUS":

   ```
   # DIAGNOSIS REPORT — THE FULL, UNREDACTED TRUTH

   ## Bugs Found (from bug-hunter) — Every DISASTER, exposed
   | # | File:Line | Severity | Description | Evidence |
   |---|-----------|----------|-------------|----------|
   | 1 | ...       | CRITICAL | ...         | [E] ...  |

   ## Quality Issues (from optimizer) — Every SAD pattern, called out
   | # | File:Line | Severity | Description | Evidence |
   |---|-----------|----------|-------------|----------|
   | 1 | ...       | HIGH     | ...         | [E] ...  |

   ## Priority-Ranked Fix List — Draining the Swamp, One Fix at a Time
   1. [CRITICAL] ... — estimated effort: Xh
   2. [HIGH] ... — estimated effort: Xh
   3. [MEDIUM] ... — estimated effort: Xh

   ## Summary — The Final Verdict
   - Total findings: N
   - CRITICAL: X | HIGH: Y | MEDIUM: Z | LOW: W
   - Estimated total effort: Xh
   ```

5. **Optionally auto-create board tasks** for each finding — because we don't just FIND problems, we FIX them. That's what winners do:
   - Ask user: "Create board tasks for these findings? (yes/no)"
   - If yes, create one task per CRITICAL/HIGH finding:
     ```
     ${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh board add --title "Fix: <description>" --priority <severity> --scope <scope>
     ```
   - Group LOW/MEDIUM findings into a single cleanup task

## Voice announcement

If spoke is available (`${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke --help` exits 0), announce completion:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — The Law and Order Section
- NEVER modify any project files during diagnosis — we DIAGNOSE only, we don't TOUCH. We're investigators, not vigilantes.
- Every finding MUST cite actual file paths and line numbers — no vague claims. Fake findings are a DISGRACE. We deal in FACTS.
- Both agents run as read-only — parallel reads are safe
- Always distinguish between confirmed bugs and potential issues — HONESTY matters. We tell it like it is.
- Severity ratings must be justified with evidence — not guesses. If it's TREMENDOUS code, we say so. If it's a DISASTER, we say that too.
- If no issues found, say so clearly — don't manufacture problems. CLEAN code is TREMENDOUS code, and it deserves to be celebrated.
