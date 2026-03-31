---
name: mpga-ui-audit
description: Run a focused UI quality audit after builds, during review, or as a standalone gate
---

## ui-audit

**Trigger:** After a build, during review, or as a standalone audit when UI quality needs a hard check.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

## Protocol

1. Identify the changed UI files or artifact paths.
2. Spawn the `ui-auditor` agent.
3. Collect the findings and group them by severity.
4. Auto-create board tasks for any `CRITICAL` or `HIGH` findings.
5. Report the verdict and recommended next action.

## Standalone usage
`/mpga:ui-audit [path] [--full]`

## Strict Rules
- ALWAYS use the `ui-auditor` agent for execution — NEVER inspect UI files directly.
- ALWAYS prefer changed UI files first, then full-repo UI review if needed.
- NEVER modify source files — the audit is READ ONLY and evidence-backed.
- ALWAYS group findings by severity and auto-create board tasks for CRITICAL/HIGH issues.

## Voice announcement
If spoke is available:
```bash
mpga spoke '<brief 1-sentence result summary>'
```

## Output
- Ranked UI findings
- Board follow-up tasks for CRITICAL/HIGH issues
- Final verdict
