# Handoff — Session State Export for Context Continuity

## Workflow

```mermaid
flowchart TD
    A["User invokes /mpga:handoff\n(or context > 70%)"] --> B[Check context budget\nmpga session budget]
    B --> C["Capture git state:\n- Branch name\n- Last commit hash + message\n- Dirty files (staged/unstaged/untracked)\n- Stash count"]
    C --> D["Capture task state:\nmpga board show\n- Current task ID\n- TDD stage (red/green/blue)\n- Passing/failing tests"]
    D --> E["Compose structured handoff document\nusing official template"]

    E --> F["Fill all sections:\n- Git State table\n- Task State table\n- Context Summary\n- Key decisions made\n- Blockers encountered\n- Next Steps (numbered)\n- Open Questions"]

    F --> G[Save handoff document\nmpga session handoff --accomplished summary]
    G --> H[Log the session\nmpga session log description]
    H --> I[Output completed handoff template\nas fenced markdown block]
    I --> J["Tell user:\n- Handoff file location\n- How to resume (load handoff + INDEX.md + scopes)\n- Exact next action"]
    J --> K{Spoke available?}
    K -->|Yes| L[mpga spoke announcement]
    K -->|No| M[Done]
    L --> M
```

## Inputs
- Current session state (git, board, context)
- Context budget usage percentage
- Active task and TDD stage information

## Outputs
- Structured handoff document saved to MPGA/sessions/
- Session log entry
- Copy-pasteable handoff template for new session
- Resume instructions with exact next action
- Self-contained document (new session can resume without prior context)
