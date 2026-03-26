# Onboard — Guided Codebase Tour

## Workflow

```mermaid
flowchart TD
    A[User is new to codebase\nor unfamiliar area] --> B[Read MPGA/INDEX.md]
    B --> C["Present project identity:\nType, size, key languages"]
    C --> D["Walk through scope registry:\nFor each scope - purpose,\nkey files, responsibilities"]
    D --> E[Read and present GRAPH.md\nShow dependency connections]
    E --> F["Show active milestone\nand current board state"]
    F --> G["Identify most relevant scopes\nfor user's likely work"]
    G --> H["Ask user:\nWhich area to explore first?"]

    H --> I{User picks area}
    I --> J[Deep dive into chosen scope\nwith evidence citations]

    subgraph "Presentation Order"
        direction TB
        P1["1. Project identity"]
        P2["2. Architecture overview"]
        P3["3. Key entry points"]
        P4["4. Active work"]
        P5["5. Suggested starting points"]
        P1 --> P2 --> P3 --> P4 --> P5
    end

    J --> K{Scope docs stale?}
    K -->|Yes| L[Suggest mpga sync to refresh]
    K -->|No| M{Spoke available?}
    L --> M
    M -->|Yes| N[mpga spoke announcement]
    M -->|No| O[Done]
    N --> O
```

## Inputs
- MPGA/INDEX.md (scope registry and project identity)
- MPGA/GRAPH.md (dependency graph)
- Scope documents in MPGA/scopes/
- Active milestone and board state

## Outputs
- Sectioned codebase tour (presented incrementally, not all at once)
- Evidence-cited claims about the codebase
- Suggested starting points for the user's work
- Stale doc warnings with sync suggestions
- No files modified (read-only skill)
