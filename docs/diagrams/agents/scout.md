# Scout — Explorer + Scope Writer

## Workflow

```mermaid
flowchart TD
    A[Receive assigned directory/scope] --> B[Read MPGA/INDEX.md for project structure context]
    B --> C[Read existing scope document for assigned scope]
    C --> D[Navigate to files in assigned scope]
    D --> E[Prioritize changed or high-traffic files first]
    E --> F[For each file: read code, understand purpose, trace call chains]
    F --> G[Fill Summary section: MPGA voice, what makes module great]
    G --> H[Fill Context/Stack/Skills: verify frameworks, add missing integrations]
    H --> I[Fill Who/What triggers it: identify callers, CLI commands, routes, event handlers]
    I --> J[Fill What happens: data flow story with evidence links]
    J --> K[Fill Rules and edge cases: find try/catch, validations, guard clauses]
    K --> L[Fill Concrete examples: 2-3 real scenarios from test files or code paths]
    L --> M[Fill Traces: step-by-step table from entry point through call chain]
    M --> N[Fill Deeper splits: note potential sub-scopes if scope is too big]
    N --> O[Fill Confidence and notes: honest assessment of verification level]
    O --> P{All TODO sections filled?}
    P -->|Yes, with evidence| Q[Write updated scope document to disk]
    P -->|Cannot find evidence| R["Mark as Unknown - never guess"]
    R --> Q
    Q --> S[mpga spoke announcement]
```

## Inputs
- A specific directory or scope to explore
- The corresponding scope document path in MPGA/scopes/
- MPGA/INDEX.md for project map context

## Outputs
- Updated scope document with evidence-backed descriptions in MPGA voice
- Every claim backed by [E] file:line evidence links
- Unknowns explicitly marked as [Unknown]
