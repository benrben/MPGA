# Brainstorm — Socratic Design Refinement

## Workflow

```mermaid
flowchart TD
    A[User describes feature/project idea] --> B[Start live board server\nmpga board live --serve --open]
    B --> C[Read MPGA/INDEX.md and relevant scope docs]

    C --> D["Phase 1: Clarify Scope\nSocratic questions about problem,\nusers, constraints, success criteria"]
    D --> E["Phase 2: Explore Alternatives\nPropose 2-3 approaches with\nevidence citations from codebase"]
    E --> F["Phase 3: Challenge Assumptions\nStress-test leading design:\nscale, dependencies, blast radius"]
    F --> G["Phase 4: Converge on Design\nPresent sections one at a time"]

    G --> H[User experience / API shape]
    H --> I{User approves section?}
    I -->|No| H
    I -->|Yes| J[Data model changes]
    J --> K{User approves?}
    K -->|No| J
    K -->|Yes| L[Integration points + Security + Testing]
    L --> M{User approves?}
    M -->|No| L
    M -->|Yes| N[Save DESIGN.md to\nMPGA/milestones/id/DESIGN.md]
    N --> O{Spoke available?}
    O -->|Yes| P[mpga spoke announcement]
    O -->|No| Q[Ready for /mpga:plan]
    P --> Q
```

## Inputs
- Feature or project idea description
- MPGA/INDEX.md and relevant scope documents
- Existing code patterns as evidence

## Outputs
- Approved DESIGN.md in the milestone directory (structured template with Problem, Constraints, Alternatives, Decision, Consequences, Implementation Outline)
- Clear scope ready for /mpga:plan
- No code written (design phase only)
