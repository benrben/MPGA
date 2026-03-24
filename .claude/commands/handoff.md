# /mpga:handoff

Export current session state for a fresh context window.

## Steps

1. Check context budget: `node ./.mpga-runtime/cli/dist/index.js session budget`
2. Summarize current session state:
   - What was accomplished this session
   - Current milestone/phase/task
   - Key decisions made (with rationale)
   - Open questions and blockers
   - Files modified this session
3. Save handoff document: `node ./.mpga-runtime/cli/dist/index.js session handoff --accomplished "<summary>"`
4. Log the session: `node ./.mpga-runtime/cli/dist/index.js session log "<brief description of work done>"`
5. Tell the user the handoff file location and how to resume

## Usage
```
/mpga:handoff
```

## Resume instructions
```
To resume in a new session:
1. Load context: cat MPGA/sessions/<date>-handoff.md
2. Load index: cat MPGA/INDEX.md
3. Load relevant scope: cat MPGA/scopes/<scope>.md
4. Resume from "Next action" in the handoff doc
```
