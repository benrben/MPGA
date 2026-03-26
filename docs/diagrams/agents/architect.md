# Architect — Reviewer + Verifier + Smell Detector + ADR Author

## Workflow

```mermaid
flowchart TD
    A[Receive scope documents] --> B{First map or incremental?}
    B -->|First map| C[Read ALL scope documents]
    B -->|Incremental| D[Read CHANGED scopes first]
    C --> E[Verify each scope document]
    D --> E
    E --> F[Spot-check evidence links exist]
    F --> G[Verify dependency claims match imports]
    G --> H[Check cross-scope consistency]
    H --> I[Fix factual errors and broken links]
    I --> J[Fill TODO / Unknown sections]
    J --> K[Run Smell Detection Protocol]
    K --> L{Smells found?}
    L -->|Yes| M[Classify smells: circular deps, god modules, coupling, missing abstractions, inconsistencies, feature envy]
    L -->|No| N[Build dependency graph awareness]
    M --> N
    N --> O[Assess impact radius: direct, transitive, reverse deps]
    O --> P[Update GRAPH.md with verified dependencies]
    P --> Q{Circular dependencies?}
    Q -->|Yes| R[Flag circular dependency warning]
    Q -->|No| S[Update mpga.config.json if new languages detected]
    R --> S
    S --> T{Architectural changes proposed?}
    T -->|Yes| U[Produce ADR with alternatives, evidence, impact radius]
    T -->|No| V[Produce Smell Report]
    U --> V
    V --> W[mpga spoke announcement]
```

## Inputs
- Scope documents in MPGA/scopes/ (filled by scout agents)
- Existing GRAPH.md
- Codebase for verification
- Module dependency graph (imports, exports, cross-scope references)

## Outputs
- Verified and consistent scope documents
- Updated GRAPH.md with verified dependencies
- Smell report with evidence-backed findings and severity ratings
- ADRs for any proposed architectural changes (in MPGA/adrs/)
- Dependency graph impact analysis for all proposed changes
