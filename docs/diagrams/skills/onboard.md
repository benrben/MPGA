# Onboard — The GREATEST Codebase Tour You'll Ever Get

## Workflow

```mermaid
flowchart TD
    A[New developer arrives — very, very special] --> B[Run mpga status — Evidence First]
    B --> C["Present project identity:\nType, size, key languages — the BASICS"]
    C --> D["Walk through scope registry:\nPurpose, key files, responsibilities\nfor EVERY scope — THOROUGH"]
    D --> E[Read and present GRAPH.md\nShow the BEAUTIFUL dependency map]
    E --> F["Show active milestone\nand current board state — what's HAPPENING"]
    F --> G["Identify the BEST scopes\nfor the user's likely work"]
    G --> H["Ask the user:\nWhich area first? GREAT choices"]

    H --> I{User picks area}
    I --> J[Deep dive into chosen scope\nwith evidence — TREMENDOUS detail]

    subgraph "The WINNING Presentation Order"
        direction TB
        P1["1. Project identity — WHO we are"]
        P2["2. Architecture overview — the BIG picture"]
        P3["3. Key entry points — where it STARTS"]
        P4["4. Active work — what's HAPPENING now"]
        P5["5. Suggested starting points — GO time"]
        P1 --> P2 --> P3 --> P4 --> P5
    end

    J --> K{Scope docs stale?}
    K -->|Yes| L[Suggest mpga sync — REFRESH them]
    K -->|No| M[mpga spoke — if available]
    L --> M
```

## Inputs — The Foundation
- Project status via `mpga status` (scope registry and project identity) — the MASTER list
- Dependency graph via `mpga graph show` — the CONNECTION map
- Scope documents via `mpga scope list` — the DETAILED intel
- Active milestone and board state — what's IN PLAY

## Outputs — You'll Know EVERYTHING
- Sectioned codebase tour (presented incrementally, not all at once) — PACED perfectly
- Evidence-cited claims about the codebase — REAL facts, no guessing
- Suggested starting points for the user's work — get PRODUCTIVE fast
- Stale doc warnings with sync suggestions — we keep things CURRENT
- No files modified (read-only skill) — a SAFE tour, has a beautiful ring to it
