# Ask — Evidence-Based Question Answering

## Workflow

```mermaid
flowchart TD
    A[User asks how/where/what question] --> B[Read MPGA/INDEX.md for scope registry]
    B --> C[Identify smallest relevant scopes]
    C --> D[Read relevant scope documents]
    D --> E{Answer complete from scope docs?}
    E -->|Yes| F[Compose answer with evidence citations]
    E -->|No| G[Spawn read-only scout agents in parallel\none per missing scope]
    G --> H[Each scout gathers evidence, traces, unknowns\nfor its assigned scope]
    H --> I[Merge scout findings into unified answer]
    I --> F
    F --> J[Rate every claim with confidence score\nHIGH / MEDIUM / LOW]
    J --> K[Add source citations to every claim\nE links to file:line]
    K --> L[Suggest 2-3 follow-up questions\ndeeper / wider / practical]
    L --> M{Spoke available?}
    M -->|Yes| N[mpga spoke announcement]
    M -->|No| O[Done]
    N --> O
```

## Inputs
- User question (how does X work, where is X, what does X do)
- MPGA/INDEX.md scope registry
- Relevant scope documents

## Outputs
- Evidence-backed answer with confidence scores (HIGH/MEDIUM/LOW) on every claim
- Source citations ([E] file:line references) for all claims
- Known unknowns flagged
- 2-3 follow-up question suggestions
- No files modified (read-only skill)
