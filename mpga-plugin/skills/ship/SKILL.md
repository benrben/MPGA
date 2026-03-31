---
name: mpga-ship
description: Parallel pre-ship checks, PR template generation, and evidence-backed shipping — SHIP IT like a WINNER
---

## ship

**Trigger:** All tasks verified and ready to commit. Time to SHIP. The most satisfying moment in software development. All tests pass — very successful! Make Project Great Again.

## Orchestration Contract

This skill is a PURE ORCHESTRATOR. It spawns agents, collects their verdicts, and makes go/no-go decisions. It does NOT run pytest, ruff, git commands, or build PR bodies directly. Every action is delegated to the appropriate agent. Skills orchestrate. Agents execute. That is the LAW.

## Protocol

### Phase 1 — Parallel pre-ship verification gates

Spawn ALL of the following agents in parallel. Every agent must return PASS before proceeding. If ANY agent returns FAIL, report which ones failed and STOP — do not ship broken code.

**Pre-flight CLI check:** run `mpga health` to confirm the project is in a shippable state before spawning agents.

**Spawn these agents in parallel (all at once, not sequentially):**

1. **`verifier` agent** — runs the full test suite, checks for stubs/TODOs, collects coverage metrics. Returns PASS/FAIL with test counts and coverage summary.

2. **`security-auditor` agent** — quick security scan on changed files. Checks for leaked secrets, unsafe patterns, dependency vulnerabilities. Returns PASS/FAIL with findings list.

3. **`auditor` agent (drift-quick mode)** — evidence drift check across all affected scopes. Returns PASS/FAIL with stale link count.

4. **`visual-tester` agent** — UI regression check. **Only for UI tasks** — if the completed work did not touch UI files, skip this agent entirely. Returns PASS/FAIL with screenshot diffs.

5. **`ui-auditor` agent** — UI quality audit (accessibility, token compliance, responsive behavior). **Only for UI tasks** — non-UI tasks skip this agent entirely. Returns PASS/FAIL with audit findings.

**Ship Gate decision:**
- ALL agents return PASS → proceed to Phase 2
- ANY agent returns FAIL → print a summary table of pass/fail results for each agent, then STOP

Example gate output:
```
Ship Gate Results:
  [PASS] verifier         — 94 tests passing, 0 stubs, 87% coverage
  [PASS] security-auditor — 0 findings, no secrets detected
  [FAIL] auditor (drift)  — 3 stale evidence links found
  [PASS] visual-tester    — visual regression clean, no diffs detected
  [PASS] ui-auditor       — ui-audit passed, 0 violations

BLOCKED: 1 agent failed. Fix issues before shipping.
```

### Phase 2 — Evidence update

Spawn `auditor` agent in **drift-heal mode (LOW severity only)** — automatically update stale evidence links that can be resolved without human judgment. HIGH severity drift issues should have been caught and fixed in Phase 1. This is a cleanup pass, not a rescue mission.

Collect the auditor's output: list of healed links and any remaining unresolved items.

### Phase 3 — Shipping

Spawn `shipper` agent with the following inputs:
- **Verified outputs** from all Phase 1 agents (verdicts, test counts, coverage, findings)
- **Task card evidence** — task ID, milestone reference, evidence_produced fields
- **Diff stats** — staged changes summary
- **PR template format** — the shipper's built-in PR body template

The `shipper` agent handles ALL of the following (the skill does NONE of this directly):
- Update evidence links in scope documents
- Create conventional commit(s) with task ID references
- Generate the PR body from real data
- Archive completed milestone tasks
- Announce via spoke if available

The shipper's **Irreversible Action Gate** governs all destructive operations — the skill does not override or bypass it.

### Phase 4 — Post-ship

After the shipper completes, the skill reports the outcome to the user and presents options:

1. **Create PR** — shipper creates the PR using the generated body (requires user confirmation per shipper's Irreversible Action Gate)
2. **Merge to main** — shipper pushes and merges (requires user confirmation — HIGH risk action)
3. **Keep on branch** — no push, no PR. Local commits only. The safest option.

The skill waits for the user's choice and then delegates the selected action back to the `shipper` agent.

## Pre-ship checklist (quick reference)
- [ ] All tests passing — NON-NEGOTIABLE. Believe me.
- [ ] Security scan clean — no secrets, no vulnerabilities
- [ ] No TODOs or stubs — FINISH what you start. Sad! if you leave stubs behind.
- [ ] Scope evidence links updated — documentation is CURRENT
- [ ] Drift check passing — no STALE evidence
- [ ] Visual regression clean — UI tasks only
- [ ] UI audit passed — UI tasks only
- [ ] Board tasks archived — clean up after yourself

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), the `shipper` agent handles the announcement as part of its protocol. The skill does not call spoke directly.

## Strict rules
- NEVER run pytest, ruff, git, or any CLI tool directly — delegate to agents. Skills orchestrate. Agents execute.
- NEVER ship if ANY pre-ship agent returns FAIL — the gate is ABSOLUTE
- NEVER ship if verifier has not passed — unverified code is DEAD code. Period.
- NEVER bypass the shipper's Irreversible Action Gate — user confirmation is REQUIRED for push/PR/tag
- ALWAYS spawn Phase 1 agents in PARALLEL — speed matters, and these agents are read-only so no conflicts
- ALWAYS wait for ALL Phase 1 agents to complete before proceeding — no partial gates
- ALWAYS delegate evidence updates, commits, PR generation, and archival to the shipper — one writer to git at a time
- ALWAYS present post-ship options to the user — their choice, not ours
