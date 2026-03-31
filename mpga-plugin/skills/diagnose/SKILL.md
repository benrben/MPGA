---
name: mpga-diagnose
description: Find bugs and quality issues in code — deploy bug-hunter + optimizer agents for a unified diagnosis report
---

## diagnose

Find bugs and quality issues by deploying bug-hunter and optimizer agents in parallel.

**Trigger:** User wants to find bugs, quality issues, or code problems. Also triggered by: "diagnose this code", "find bugs", "what's wrong with this", "quality check", "code health".

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

**Agent brief:** Target files/scope from user input or git diff, acceptance criteria from board task.
**Expected output:** Structured verdict (PASS/FAIL) with file:line references and severity ratings.

## Delegation

Deploy bug-hunter + optimizer agents in parallel:
- **bug-hunter agent** — checks specifications vs implementation for correctness issues.
- **optimizer agent** — checks code quality, performance, and maintainability.

## Protocol

1. **Identify target** — determine what to diagnose:
   - If user specifies files/directories, use those
   - If git diff has changes, diagnose the changed files
   - If no target specified, diagnose the current scope or most recently changed files

2. **Spawn bug-hunter agent** (read-only) to check specifications vs implementation:
   - Compare function behavior against documented specifications
   - Check edge cases and boundary conditions
   - Verify error handling paths
   - Look for logic errors, off-by-one, null/undefined risks
   - Check type safety and contract violations
   - Verify async/await correctness and race conditions

3. **Spawn optimizer agent** (read-only) in parallel to check code quality:
   - Cyclomatic complexity analysis
   - Duplicated code detection
   - Dead code identification
   - Performance anti-patterns (N+1 queries, unnecessary re-renders, etc.)
   - Memory leak patterns
   - Dependency coupling analysis

4. **Collect results from both agents** and produce unified diagnosis report:

   ```
   # DIAGNOSIS REPORT

   ## Bugs Found (from bug-hunter)
   | # | File:Line | Severity | Description | Evidence |
   |---|-----------|----------|-------------|----------|
   | 1 | ...       | CRITICAL | ...         | [E] ...  |

   ## Quality Issues (from optimizer)
   | # | File:Line | Severity | Description | Evidence |
   |---|-----------|----------|-------------|----------|
   | 1 | ...       | HIGH     | ...         | [E] ...  |

   ## Priority-Ranked Fix List
   1. [CRITICAL] ... — estimated effort: Xh
   2. [HIGH] ... — estimated effort: Xh
   3. [MEDIUM] ... — estimated effort: Xh

   ## Summary
   - Total findings: N
   - CRITICAL: X | HIGH: Y | MEDIUM: Z | LOW: W
   - Estimated total effort: Xh
   ```

5. **Optionally auto-create board tasks** for each finding:
   - Ask user: "Create board tasks for these findings? (yes/no)"
   - If yes, create one task per CRITICAL/HIGH finding:
     ```
     mpga board add --title "Fix: <description>" --priority <severity> --scope <scope>
     ```
   - Group LOW/MEDIUM findings into a single cleanup task

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters.

## Strict Rules
- NEVER modify any project files during diagnosis — diagnose only.
- Every finding MUST cite actual file paths and line numbers — no vague claims.
- Both agents run as read-only — parallel reads are safe.
- Always distinguish between confirmed bugs and potential issues.
- Severity ratings must be justified with evidence — not guesses.
- If no issues found, say so clearly — don't manufacture problems.
