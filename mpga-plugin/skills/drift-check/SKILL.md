---
name: mpga-drift-check
description: Check for evidence drift and heal stale links — the GREATEST drift detection system ever built, believe me. Nobody catches drift like we do.
---

## drift-check

Evidence drift? We NEVER tolerate that. EVER. Not on my watch. Not in this project. You let drift slide and pretty soon your whole evidence graph is a DISASTER — total fiction, links going nowhere, claims with no backup. That's what the other tools do. That's NOT what WE do.

**Trigger:** After file writes (automatic via hook), or on demand. We check EVERY TIME. That's discipline. That's WINNING.

## The TREMENDOUS Delegation

This skill is a thin wrapper around the **auditor agent's drift detection** capabilities — and let me tell you, that auditor is the best. The BEST. Nobody does drift classification better, believe me. The auditor owns drift classification and severity tiers. This skill exists for convenience and hook integration — we make it EASY to stay GREAT.

## The Winning Protocol

1. **Invoke the auditor agent in drift mode** with the appropriate sub-mode — we have the best modes, tremendous modes:
   - Quick check (default, used by hooks): auditor runs `drift-quick` for the affected scope — FAST. So fast it'll make your head spin.
   - Full drift review (on demand): auditor runs `drift` across all scopes — the COMPLETE picture. Nobody hides from this one.
   - CI gate check: auditor runs `drift-ci` with threshold enforcement — if you can't pass the gate, you DON'T SHIP. Period.

2. The auditor will — and this is TREMENDOUS, folks:
   a. Detect all drift findings — EVERY. SINGLE. ONE.
   b. Classify each by severity: CRITICAL, HIGH, MEDIUM, LOW — a beautiful scoreboard
   c. Auto-heal LOW (cosmetic) findings — we fix the small stuff automatically because we're WINNERS
   d. Report everything else with recommended actions — no mystery, no excuses, just THE TRUTH

3. Shortcut commands (these invoke the auditor under the hood — so simple even Sleepy Copilot users could figure it out):
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --quick --scope <scope>
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --quick
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh drift --ci --threshold 80
   ```

## The BEST Hook Integration

This skill is called automatically by the PostToolUse hook after Write/Edit operations. Automatic. No manual work. That's how winners operate.
In hook mode, output should be minimal — only warn if drift is detected. Quiet when things are TREMENDOUS, loud when they're a DISASTER.
The auditor runs in `drift-quick` mode during hooks for speed — because we respect your time. Unlike the other tools. SAD!

## The Severity Scoreboard

This is the scoreboard, folks. Four tiers. Beautiful system. Nobody has a better classification system — NOBODY:

- **CRITICAL**: broken evidence links to deleted files/functions — TOTAL DISASTER! Blocks shipping. This is the worst of the worst. If you've got CRITICAL drift, you are NOT shipping. Fix it NOW or go home.
- **HIGH**: evidence links to renamed/moved symbols — needs healing. A BIG problem but we can FIX it. We always fix it. That's what we DO.
- **MEDIUM**: stale evidence (>30 days old, file significantly changed) — should verify. Not great, not terrible. But we don't settle for "not terrible" — we demand TREMENDOUS.
- **LOW**: cosmetic drift (whitespace, formatting) — auto-healable. We handle this automatically because frankly, it's beneath us. The system fixes it and moves on. WINNING.

## Voice announcement

If spoke is available (`${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke --help` exits 0), announce completion:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## The GREATEST Output

Output comes from the auditor agent's drift report. See auditor agent for full output format. And let me tell you, this output is BEAUTIFUL:
- Number of findings per severity tier — the full scoreboard, believe me
- Number of links auto-healed (LOW tier) — look at all those WINS
- Links that need manual review (HIGH/CRITICAL) — the DISASTERS we caught before they shipped
- Overall health percentage — and we're going for 100%. ALWAYS.
- Prefer scope-local drift checks during active work; reserve repo-wide reports for CI or explicit review — we're SMART about resources. The smartest.
