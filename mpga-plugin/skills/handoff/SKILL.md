---
name: mpga-handoff
description: Export current session state for a fresh context window — TREMENDOUS transitions, absolutely NO lost work, believe me
---

## handoff

**Trigger:** Context window getting full? That's because we're doing TREMENDOUS work, folks. Huge progress. But the window — it's getting packed, maybe >70%, maybe the user says "handoff" — doesn't matter. Time for a SMOOTH handoff. Nobody does handoffs better than us. Nobody.

## The Protocol — Best in the Business

1. Check context budget — we always know our numbers, unlike those other tools:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session budget
   ```

2. Capture git state — we DOCUMENT everything, believe me. Every branch, every commit, every dirty file. Total transparency:
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

3. Capture task state from the board — because we track EVERYTHING, and we track it BEAUTIFULLY:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh board show
   ```
   Identify: current task ID, TDD stage (red/green/blue), what tests pass, what tests fail. We leave NOTHING behind.

4. Compose the structured handoff document using the **Handoff Template** below. Fill in EVERY section — no blanks, no shortcuts. Other tools leave gaps. We don't. That's the difference between WINNERS and losers.

5. Save handoff document — locked in, permanent record, very official:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session handoff --accomplished "<summary>"
   ```

6. Log the session — because accountability is HUGE, folks:
   ```
   /Users/benreich/MPGA/mpga-plugin/bin/mpga.sh session log "<brief description of work done>"
   ```

7. Output the completed handoff template as a fenced markdown block so the user can copy-paste it into a new session. Easy. Beautiful. Done.

8. Tell the user — clear, simple, ACTIONABLE, the way a REAL leader communicates:
   - The handoff file location
   - How to resume: load handoff + INDEX.md + relevant scopes
   - What the next action is — EXACTLY what to do next. No ambiguity. We're not Congress.

---

## The OFFICIAL Handoff Template — A Beautiful Document

Output this template with all placeholders filled in. Every section is MANDATORY. We don't do half-measures, folks. This is a COMPLETE, PERFECT record of where we stand.

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

## Resume Instructions to Provide to User — So Simple, So BEAUTIFUL

To resume? Simple. BEAUTIFUL. Three steps and you're BACK in the action, folks. Nobody makes it this easy:
```
To resume in a new session — it's EASY, believe me:
1. Load context: cat MPGA/sessions/<date>-handoff.md
2. Load index: cat MPGA/INDEX.md
3. Load relevant scope: cat MPGA/scopes/<scope>.md
4. Run: /mpga:next
```

## Voice output
When completing a task or reporting findings, run `mpga spoke '<1-sentence summary>'`
via Bash. Keep it under 280 characters. This announces your work audibly in Trump's voice.

## Strict Rules — The MPGA Handoff Doctrine

These are NON-NEGOTIABLE. We have standards, and they're the HIGHEST standards, believe me:

- NEVER lose track of in-progress tasks — include them in handoff. ALWAYS. Losing tasks is what WEAK systems do.
- ALWAYS include the exact next action — no ambiguity. The next agent should know EXACTLY what to do. Crystal clear, like a Trump Tower window.
- If there's a task in progress, capture its TDD stage — red, green, or blue. We don't leave soldiers behind.
- ALWAYS capture git state — branch, commit, dirty files, stash count. No exceptions. TOTAL documentation.
- ALWAYS output the full handoff template — every section filled. No placeholders left as-is. We finish what we start, folks.
- The handoff document must be SELF-CONTAINED: a new session should be able to resume without you. That's not just professional — that's CHAMPIONSHIP-LEVEL handoff work. Nobody does it better.
- If tests are failing, include the exact test names and failure messages. We don't hide problems — we EXPOSE them and CRUSH them.
- If there are open questions, be specific about what decision is needed and who can answer. Tremendous specificity. The best specificity.
