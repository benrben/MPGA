---
name: mpga-ui-audit
description: Run a focused UI quality audit after builds, during review, or as a standalone gate
---

## ui-audit

**Trigger:** After a build, during review, or as a standalone audit when UI quality needs a hard check.

## Protocol

1. Identify the changed UI files or artifact paths.
2. Spawn the `ui-auditor` agent.
3. Collect the findings and group them by severity.
4. Auto-create board tasks for any `CRITICAL` or `HIGH` findings.
5. Report the verdict and recommended next action.

## Standalone usage
`/mpga:ui-audit [path] [--full]`

## Rules
- Use the `ui-auditor` agent for execution.
- Prefer changed UI files first, then full-repo UI review if needed.
- Keep the audit read-only and evidence-backed.

## Voice announcement
If spoke is available:
```bash
mpga spoke 'UI audit complete. Findings ranked and ready for action.'
```

## Output
- Ranked UI findings
- Board follow-up tasks for CRITICAL/HIGH issues
- Final verdict
