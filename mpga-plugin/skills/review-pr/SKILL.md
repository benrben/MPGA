---
name: mpga-review-pr
description: Comprehensive PR review with multi-agent orchestration — reviewer + bug-hunter + security-auditor for a unified verdict
---

## review-pr

**Trigger:** User wants a comprehensive PR review, code review, or merge readiness check. Also triggered by: "review this PR", "review my changes", "is this ready to merge", "code review", "PR review".

## Delegation

This skill orchestrates three agents in parallel for comprehensive coverage:
- **reviewer agent** — code quality, style, architecture
- **bug-hunter agent** — correctness, logic errors, edge cases
- **security-auditor agent** — security vulnerabilities, secrets, injection risks

## Protocol

1. **Read PR diff** — determine the changeset:
   - If PR number given: `gh pr diff <number>`
   - If branch specified: `git diff <base-branch>...<feature-branch>`
   - If no args: `git diff main...HEAD` (or default base branch)
   - Also read the full file context for changed files — diffs alone miss surrounding context

2. **Spawn reviewer agent** (read-only) for code quality:
   - Code style consistency with project conventions
   - Architecture alignment — does this change fit the existing patterns?
   - Naming clarity and API design
   - Test coverage — are new code paths tested?
   - Documentation — are public APIs documented?
   - Commit hygiene — are commits atomic and well-messaged?
   - DRY violations — is there copy-pasted logic?

3. **Spawn bug-hunter agent** (read-only) in parallel for correctness:
   - Logic errors in new/changed code
   - Edge cases not handled (null, empty, boundary values)
   - Error handling gaps (missing try/catch, unhandled promise rejections)
   - Race conditions in async code
   - Type safety issues (implicit any, unsafe casts)
   - Regression risks — does this change break existing behavior?
   - Off-by-one errors in loops/slicing

4. **Spawn security-auditor agent** (read-only) in parallel for security:
   - Injection vulnerabilities in new code (SQL, shell, eval, template)
   - Secrets or credentials introduced in the diff
   - Auth/authz changes that weaken security
   - New dependencies with known vulnerabilities
   - CORS, CSP, or header misconfigurations
   - User input handling without sanitization

5. **Collect all findings into unified PR review**:

   ```
   # PR REVIEW

   ## Verdict: APPROVED / CHANGES REQUESTED / BLOCKED

   ## Summary
   - Files changed: N
   - Lines added: +X | Lines removed: -Y
   - Review findings: N (Critical: X, High: Y, Medium: Z, Low: W)

   ## Code Quality (from reviewer)
   | # | File:Line | Severity | Finding |
   |---|-----------|----------|---------|
   | 1 | ...       | MEDIUM   | ...     |

   ## Correctness (from bug-hunter)
   | # | File:Line | Severity | Finding |
   |---|-----------|----------|---------|
   | 1 | ...       | HIGH     | ...     |

   ## Security (from security-auditor)
   | # | File:Line | Severity | Finding |
   |---|-----------|----------|---------|
   | 1 | ...       | CRITICAL | ...     |

   ## Review Comments
   (file:line references for inline-style comments)

   ## Verdict Rationale
   Why this PR is approved/needs changes/blocked.
   ```

6. **Determine verdict** based on findings:
   - **APPROVED** — no CRITICAL or HIGH findings, code is ready to merge
   - **CHANGES REQUESTED** — HIGH findings that need fixes before merge, or multiple MEDIUM findings in the same area
   - **BLOCKED** — CRITICAL findings (security vulnerabilities, data loss risks, broken tests)

7. **Generate review comments** with file:line references:
   - Each finding maps to a specific location in the diff
   - Comments include: what's wrong, why it matters, and a suggested fix
   - Positive comments too — acknowledge good patterns and clever solutions

## Output Format

The review should be structured for easy consumption:
- Verdict at the top — don't bury the lede
- Summary stats next — quick overview
- Findings by category — organized, not a wall of text
- Inline comments last — the detailed feedback

## Strict Rules
- NEVER modify any project files during review — READ ONLY
- All three agents run in parallel — they're all read-only, so it's safe
- Every finding MUST cite file:line from the actual diff — no vague feedback
- ALWAYS read full file context, not just the diff — understand what surrounds the change
- If the PR is clean, say so — don't manufacture issues to justify the review
- Distinguish between "must fix" (CRITICAL/HIGH) and "consider" (MEDIUM/LOW)
- Credit good code — reviews should encourage, not just criticize
- If tests are missing for new code, that's always at least a MEDIUM finding
