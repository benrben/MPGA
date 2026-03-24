---
description: Export current session state for a fresh context window — smooth TRANSITIONS, no lost work
---

## handoff

**Trigger:** Context window getting full (>70%), or user explicitly requests handoff. Smart handoffs are how WINNERS manage long sessions.

## Protocol

1. Check context budget:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget
   ```

2. Summarize current session state — capture EVERYTHING important:
   - What was accomplished this session — our WINS
   - Current milestone/phase/task — where we ARE
   - Key decisions made (with rationale) — WHY we did what we did
   - Open questions and blockers — what's in our WAY
   - Files modified this session — the EVIDENCE of our work

3. Save handoff document:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session handoff --accomplished "<summary>"
   ```

4. Log the session:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session log "<brief description of work done>"
   ```

5. Tell the user — clear, simple, ACTIONABLE:
   - The handoff file location
   - How to resume: load handoff + INDEX.md + relevant scopes
   - What the next action is — EXACTLY what to do next

## Resume instructions to provide to user
```
To resume in a new session — it's EASY:
1. Load context: cat MPGA/sessions/<date>-handoff.md
2. Load index: cat MPGA/INDEX.md
3. Load relevant scope: cat MPGA/scopes/<scope>.md
4. Run: /mpga:next
```

## Strict rules
- NEVER lose track of in-progress tasks — include them in handoff. ALWAYS.
- ALWAYS include the exact next action — no ambiguity
- If there's a task in progress, capture its TDD stage — red, green, or blue
- Handoff should be self-contained: a new session should be able to resume without you. That's PROFESSIONAL.
