---
name: mpga-drift-check
description: Check for evidence drift and heal stale links — the GREATEST drift detection system ever built, believe me. Nobody catches drift like we do.
---

## drift-check

Evidence drift is never tolerated — stale links and unverified claims get caught and fixed.

**Trigger:** After file writes (automatic via hook), or on demand.

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read source files directly (delegates to appropriate agents)
- Write or edit source files directly (delegates to write-enabled agents)
- Run CLI commands other than `mpga` board/status/scope/session queries

If you find yourself writing implementation steps in a skill, STOP and delegate to an agent.

## Delegation

This skill is a thin wrapper around the **auditor agent's drift detection** capabilities. The auditor owns drift classification and severity tiers. This skill exists for convenience and hook integration.

## Protocol

1. **Invoke the auditor agent in drift mode** with the appropriate sub-mode:
   - Quick check (default, used by hooks): auditor runs `drift-quick` for the affected scope
   - Full drift review (on demand): auditor runs `drift` across all scopes
   - CI gate check: auditor runs `drift-ci` with threshold enforcement

2. The auditor will:
   a. Detect all drift findings
   b. Classify each by severity: CRITICAL, HIGH, MEDIUM, LOW
   c. Auto-heal LOW (cosmetic) findings
   d. Report everything else with recommended actions

3. Shortcut commands (these invoke the auditor under the hood):
   ```
   mpga drift --quick --scope <scope>
   mpga drift --quick
   mpga drift --ci --threshold 80
   ```

## Hook Integration

This skill is called automatically by the PostToolUse hook after Write/Edit operations.
In hook mode, output should be minimal — only warn if drift is detected.
The auditor runs in `drift-quick` mode during hooks for speed.

## Severity Tiers

- **CRITICAL**: broken evidence links to deleted files/functions — blocks shipping, fix immediately.
- **HIGH**: evidence links to renamed/moved symbols — needs healing.
- **MEDIUM**: stale evidence (>30 days old, file significantly changed) — should verify.
- **LOW**: cosmetic drift (whitespace, formatting) — auto-healable.

## Strict Rules
- NEVER modify source files — drift detection is READ ONLY
- NEVER auto-heal without explicit user invocation of drift-heal mode
- ALWAYS delegate drift detection to the `auditor` agent — the skill does not scan files itself
- ALWAYS report severity tiers for every finding — no unclassified drift
- If drift is found, present actionable heal commands — don't just report problems

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Output

Output comes from the auditor agent's drift report. See auditor agent for full output format:
- Number of findings per severity tier
- Number of links auto-healed (LOW tier)
- Links that need manual review (HIGH/CRITICAL)
- Overall health percentage
- Prefer scope-local drift checks during active work; reserve repo-wide reports for CI or explicit review
