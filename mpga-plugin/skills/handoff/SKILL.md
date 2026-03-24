---
name: mpga-handoff
description: Export current session state for a fresh context window — smooth TRANSITIONS, no lost work
---

## handoff

**Trigger:** Context window getting full (>70%), or user explicitly requests handoff. Smart handoffs are how WINNERS manage long sessions.

## Protocol

1. Check context budget:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget
   ```

2. Capture git state — run these commands and record the output:
   ```bash
   # Current branch
   git rev-parse --abbrev-ref HEAD
   # Last commit hash + message
   git log -1 --oneline
   # Dirty files (staged + unstaged + untracked)
   git status --short
   # Stash count
   git stash list | wc -l
   ```

3. Capture task state from the board:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board show
   ```
   Identify: current task ID, TDD stage (red/green/blue), what tests pass, what tests fail.

4. Compose the structured handoff document using the **Handoff Template** below. Fill in EVERY section — no blanks, no shortcuts.

5. Save handoff document:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session handoff --accomplished "<summary>"
   ```

6. Log the session:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session log "<brief description of work done>"
   ```

7. Output the completed handoff template as a fenced markdown block so the user can copy-paste it into a new session.

8. Tell the user — clear, simple, ACTIONABLE:
   - The handoff file location
   - How to resume: load handoff + INDEX.md + relevant scopes
   - What the next action is — EXACTLY what to do next

---

## Handoff Template

Output this template with all placeholders filled in. Every section is MANDATORY.

````markdown
# Session Handoff — {{DATE}}

## Git State
| Field | Value |
|-------|-------|
| **Branch** | `{{BRANCH}}` |
| **Last commit** | `{{SHORT_HASH}} {{COMMIT_MSG}}` |
| **Dirty files** | {{DIRTY_COUNT}} files (see list below) |
| **Stash count** | {{STASH_COUNT}} |

### Dirty file list
```
{{GIT_STATUS_SHORT_OUTPUT}}
```

## Task State
| Field | Value |
|-------|-------|
| **Current task** | `{{TASK_ID}}` — {{TASK_TITLE}} |
| **TDD stage** | {{red / green / blue / n/a}} |
| **Passing tests** | {{LIST_OR_COUNT}} |
| **Failing tests** | {{LIST_OR_COUNT_OR_NONE}} |
| **Milestone** | {{MILESTONE_ID_OR_NONE}} |

## Context Summary

### What was being worked on
<!-- 2-4 sentences describing the current focus area -->
{{WORK_SUMMARY}}

### Key decisions made
<!-- Bullet list of decisions WITH rationale -->
{{DECISIONS}}

### Blockers encountered
<!-- Bullet list, or "None" if clear -->
{{BLOCKERS}}

## Next Steps
<!-- Numbered list — the FIRST item is what the next session should do IMMEDIATELY -->
1. {{IMMEDIATE_NEXT_ACTION}}
2. {{FOLLOW_UP_ACTION}}
3. {{FURTHER_ACTION}}

## Open Questions
<!-- Anything unresolved that needs human input. "None" if clear. -->
{{OPEN_QUESTIONS}}

---

### Resume instructions
```
To resume in a new session:
1. Paste this entire handoff document into the new session
2. Load index: cat MPGA/INDEX.md
3. Load relevant scope: cat MPGA/scopes/<scope>.md
4. Run: /mpga:next
```
````

---

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
- ALWAYS capture git state — branch, commit, dirty files, stash count. No exceptions.
- ALWAYS output the full handoff template — every section filled. No placeholders left as-is.
- The handoff document must be SELF-CONTAINED: a new session should be able to resume without you. That's PROFESSIONAL.
- If tests are failing, include the exact test names and failure messages.
- If there are open questions, be specific about what decision is needed and who can answer.
