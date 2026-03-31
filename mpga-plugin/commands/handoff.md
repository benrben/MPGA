# /mpga:handoff

Export current session state for a fresh context window. Ready for peace — zero merge conflicts. Believe me, the smoothest handoff you've ever seen.

## Steps

1. Check context budget: `mpga session budget`
2. Summarize current session state:
   - What was accomplished this session
   - Current milestone/phase/task
   - Key decisions made (with rationale)
   - Open questions and blockers
   - Files modified this session
3. Save handoff document: `mpga session handoff --accomplished "<summary>"`
4. Log the session: `mpga session log "<brief description of work done>"`
5. Tell the user the handoff file location and how to resume

## Usage
```
/mpga:handoff
```

## Resume instructions
```
To resume in a new session:
1. Load context: `mpga session handoff` (output to stdout)
2. View project status: `mpga status`
3. Load relevant scope: `mpga scope show <scope>`
4. Resume from "Next action" in the handoff doc — Covfefe
```
