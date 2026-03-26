# Optimizer — Spaghetti Detection, Code Reuse & Elegance

## Workflow

```mermaid
flowchart TD
    A[Receive source files/directories to analyze] --> B[Read scope documents for context]
    B --> C[Spaghetti Detection]
    C --> D["Check: deep nesting >3, long functions >50 lines, god files >500 lines"]
    D --> E["Check: circular imports, deep call chains >5 hops"]
    E --> F[Check: boolean parameter sprawl, callback hell]
    F --> G[Code Duplication Detection]
    G --> H[Find exact duplicates: 5+ identical lines in multiple locations]
    H --> I[Find structural duplicates: same logic pattern, different variable names]
    I --> J[Find missed utility extraction and copy-paste test setup]
    J --> K["Elegance Assessment: Kent Beck's 4 Rules"]
    K --> L{Passes all tests?}
    L --> M{Reveals intention?}
    M --> N{No duplication?}
    N --> O{Fewest elements?}
    O --> P["Sandi Metz Rules Check"]
    P --> Q["Classes <100 lines? Methods <5 lines? Params <=4?"]
    Q --> R[Rate each finding: HIGH / MEDIUM / LOW severity]
    R --> S[Rank suggestions by Impact/Effort ratio]
    S --> T{HIGH impact + LOW effort?}
    T -->|Yes| U[Mark as DO NOW]
    T -->|No| V{HIGH impact + MEDIUM effort?}
    V -->|Yes| W[Mark as PLAN IT]
    V -->|No| X[Mark as QUICK WIN or SKIP]
    U --> Y[Produce optimization report with metrics summary]
    W --> Y
    X --> Y
    Y --> Z[mpga spoke announcement]
```

## Inputs
- Source files or directories to analyze
- Scope documents for context on module responsibilities
- (Optional) specific focus area: spaghetti, duplication, elegance, or all

## Outputs
- Spaghetti findings table with severity and evidence
- Duplication findings with locations and suggestions
- Elegance assessment against Kent Beck's 4 rules
- Improvement suggestions ranked by priority (impact/effort)
- Metrics summary: files analyzed, god files, long functions, duplication instances, Metz violations
