---
description: Export current session state for a fresh context window
---

## handoff

**Trigger:** Context window getting full (>70%), or user explicitly requests handoff

## Protocol

1. Check context budget:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget
   ```

2. Summarize current session state:
   - What was accomplished this session
   - Current milestone/phase/task
   - Key decisions made (with rationale)
   - Open questions and blockers
   - Files modified this session

3. Save handoff document:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session handoff --accomplished "<summary>"
   ```

4. Log the session:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session log "<brief description of work done>"
   ```

5. Tell the user:
   - The handoff file location
   - How to resume: load handoff + INDEX.md + relevant scopes
   - What the next action is

## Resume instructions to provide to user
```
To resume in a new session:
1. Load context: cat MPGA/sessions/<date>-handoff.md
2. Load index: cat MPGA/INDEX.md
3. Load relevant scope: cat MPGA/scopes/<scope>.md
4. Run: /mpga:next
```

## Strict rules
- NEVER lose track of in-progress tasks — always include them in handoff
- ALWAYS include the exact next action in the handoff doc
- If there's a task in progress, capture its TDD stage
- Handoff should be self-contained: a new session should be able to resume without you
