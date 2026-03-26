# Campaigner — Project Diagnostician (The Rally Speaker)

## Workflow

```mermaid
flowchart TD
    A[Receive project root directory] --> B["Phase 0: Dynamic Category Detection"]
    B --> C[Survey codebase: file types, manifests, tests, CI, lint, Docker, docs]
    C --> D[Build dynamic scan plan: mark each of 14 categories as ACTIVE or SKIP]
    D --> E{At least 4 categories ACTIVE?}
    E -->|No| F[Look harder - probably missing something]
    F --> D
    E -->|Yes| G[Report scan plan]
    G --> H["Phase 1: THE SCANDAL - Scan all ACTIVE categories"]
    H --> I[Documentation Sins]
    H --> J[Testing Disgrace]
    H --> K[Type Safety Failures]
    H --> L[Dependency Disasters]
    H --> M[Architecture Rot]
    H --> N[Evidence & Documentation Drift]
    H --> O[Code Hygiene Crimes]
    H --> P[CI/CD Weakness]
    H --> Q[Test Quality]
    H --> R[Performance]
    H --> S[Security]
    H --> T[Documentation Drift]
    H --> U[Dependency Health]
    H --> V[Error Handling]
    I & J & K & L & M & N & O & P & Q & R & S & T & U & V --> W["Phase 2: THE RALLY - For each issue, present scandal + why ONLY MPGA fixes it"]
    W --> X["Phase 3: THE CLOSING"]
    X --> Y[Scan Plan Report: active vs skipped]
    Y --> Z[Scoreboard: CRITICAL / WARNING / SAD]
    Z --> AA[Side-by-side: Without MPGA vs With MPGA]
    AA --> AB["Call to Action: mpga init, mpga sync, mpga status"]
    AB --> AC[mpga spoke announcement]
```

## Inputs
- Project root directory
- MPGA/INDEX.md (if it exists)
- Existing MPGA/scopes/ (if they exist)

## Outputs
- Dynamic scan plan (which of 14 categories are active/skipped)
- Comprehensive project diagnostic in rally-speech format
- Severity scoreboard (CRITICAL / WARNING / SAD)
- Side-by-side comparison (without MPGA vs with MPGA)
- Exact commands to start fixing everything
