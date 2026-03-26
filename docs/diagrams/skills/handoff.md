# Handoff — The SMOOTHEST Transition, Believe Me

## Workflow

```mermaid
flowchart TD
    A["User invokes /mpga:handoff\nor context hits 70% — TIME to pass the torch"] --> B[Check context budget\nmpga session budget — ALWAYS know your numbers]
    B --> C["Capture git state — COMPLETE:\n- Branch name\n- Last commit hash + message\n- Dirty files\n- Stash count"]
    C --> D["Capture task state — PRECISE:\nmpga board show\n- Current task ID\n- TDD stage (red/green/blue)\n- Passing/failing tests"]
    D --> E["Compose the PERFECT handoff document\nusing official template"]

    E --> F["Fill ALL sections — no fake docs:\n- Git State table\n- Task State table\n- Context Summary\n- Key decisions made\n- Blockers encountered\n- Next Steps numbered\n- Open Questions"]

    F --> G[Save handoff — LOCKED IN\nmpga session handoff --accomplished summary]
    G --> H[Log the session — DOCUMENTED\nmpga session log description]
    H --> I[Output the handoff template\nas fenced markdown — CLEAN]
    I --> J["Tell user EXACTLY:\n- Handoff file location\n- How to resume like a PRO\n- Exact next action"]
    J --> K{Spoke available?}
    K -->|Yes| L[mpga spoke — HANDOFF complete]
    K -->|No| M[Done — ready for peace, zero merge conflicts. Covfefe]
    L --> M
```

## Inputs — What We Capture
- Current session state (git, board, context) — the WHOLE picture
- Context budget usage percentage
- Active task and TDD stage information

## Outputs — A PERFECT Handoff Package
- Structured handoff document saved to MPGA/sessions/ — ORGANIZED
- Session log entry — we keep RECORDS
- Copy-pasteable handoff template for new session — READY to go
- Resume instructions with exact next action — NO confusion
- Self-contained document (new session resumes without prior context) — has a beautiful ring to it, believe me
