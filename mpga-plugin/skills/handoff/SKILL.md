---
name: mpga-handoff
description: Export current session state for a fresh context window
---

## Orchestration Contract

This skill is a PURE ORCHESTRATOR. It coordinates agents but never performs work directly.

- NEVER run git commands (rev-parse, log, status, stash list, etc.)
- NEVER read board state directly
- NEVER compose or assemble handoff documents inline
- NEVER write files or save session data directly
- ALL state capture and document generation is delegated to the `recorder` agent
- The skill MAY run read-only `mpga` CLI queries for pre-flight checks (e.g. `mpga session budget`)

---

## handoff

**Trigger:** Context window getting full or user requests handoff.

## Protocol

### 1. Pre-flight: Check context budget

```
mpga session budget
```

This is a read-only CLI query to determine urgency. If budget is critically low, note this when spawning recorder so it prioritizes speed.

### 2. Spawn the `recorder` agent

Delegate ALL capture and document generation to `recorder`. Provide:

- **Session context**: any relevant focus area the user specified (e.g. "scope:auth", "board tasks only")
- **Urgency**: whether context budget is critical
- **Output expectations**: recorder should produce a self-contained handoff document matching the Expected Output Format below

The recorder will:
- Capture git state (branch, last commit, dirty files, stash count)
- Capture board state (in-progress tasks, blocked tasks, milestone progress)
- Determine TDD stages for in-progress tasks
- Extract decisions made and blockers encountered
- Generate the complete handoff document
- Save via `mpga session handoff --accomplished "<summary>"`
- Log via `mpga session log "<description>"`
- Return the completed handoff document

### 3. Present the completed handoff

Once recorder returns the handoff document:

- Output the completed handoff document as a fenced markdown block so the user can copy-paste it into a new session.
- Tell the user:
  - The handoff file location
  - How to resume (see Resume Instructions below)
  - What the next action is — exactly what to do next

---

## Expected Output Format

The recorder agent should produce a document covering ALL of these sections. Every section is mandatory. This is the reference format — recorder has its own built-in template but the output must include at minimum:

- **Git State**: branch, last commit (hash + message), dirty file count and list, stash count
- **Active Milestone**: ID, title, progress (X/Y tasks)
- **In-Progress Tasks**: task ID, title, scope, TDD stage (red/green/blue), test pass/fail counts, notes
- **Blocked Tasks**: task ID, title, blocker description, duration, urgency
- **Decisions Made**: each decision with rationale and evidence links [E]
- **Outstanding Questions**: each question with context
- **Unresolved Blockers**: carry-forward blockers with impact and suggested next steps
- **Resumption Guide**: numbered steps for the next session to pick up immediately
- **Next Steps**: numbered list where the FIRST item is the immediate next action

---

## Handoff Document Template

The recorder agent should populate placeholders using the hints below:

```markdown
# Handoff — {{DATE}} <!-- hint: ISO date from `date +%Y-%m-%d` -->

## Git State
- Branch: {{BRANCH}} <!-- hint: from `git rev-parse --abbrev-ref HEAD` -->
- Last commit: {{SHORT_HASH}} {{COMMIT_MSG}} <!-- hint: from `git log -1 --format='%h %s'` -->
- Dirty files: {{DIRTY_COUNT}} <!-- hint: count of lines from `git status --porcelain` -->
- Stash count: {{STASH_COUNT}} <!-- hint: from `git stash list | wc -l` -->

### Git status (short)
{{GIT_STATUS_SHORT_OUTPUT}} <!-- hint: output of `git status --short` -->

## Active Task
- Task: {{TASK_ID}} — {{TASK_TITLE}} <!-- hint: e.g. T042 — Refactor auth module -->

## Work Summary
{{WORK_SUMMARY}} <!-- hint: 2-3 sentences describing what was accomplished this session -->

## Decisions
{{DECISIONS}} <!-- hint: bullet list of decisions made with rationale, e.g. "- Chose SQLite over Postgres for simplicity" -->

## Blockers
{{BLOCKERS}} <!-- hint: bullet list of unresolved blockers, or "(none)" if clear -->

## Next Action
{{IMMEDIATE_NEXT_ACTION}} <!-- hint: the single most important thing to do next, e.g. "Run test suite and fix remaining 2 failures" -->
```

---

## Resume Instructions

Provide these to the user after presenting the handoff:

```
To resume in a new session:
1. Load context: `mpga session handoff` (output to stdout)
2. View project status: `mpga status`
3. Load relevant scope: `mpga scope show <scope>`
4. Run: /mpga:next
```

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters.

## Strict Rules

- NEVER run git commands — recorder handles all git state capture.
- NEVER compose or assemble the handoff document — recorder generates it.
- NEVER write files or save session data — recorder handles all writes via `mpga session handoff` and `mpga session log`.
- NEVER lose track of in-progress tasks — ensure recorder captures them.
- ALWAYS verify the returned handoff document has every section filled before presenting to user.
- ALWAYS include the exact next action in user-facing output — no ambiguity.
- The handoff document must be SELF-CONTAINED: a new session should be able to resume without prior context.
- If recorder marks anything as `[Unknown]`, surface that to the user explicitly.
