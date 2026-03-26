# Brainstorm — The Art of the DEAL (Design Phase)

## Workflow

```mermaid
flowchart TD
    A[User has a TREMENDOUS idea] --> B[Fire up the GREATEST live board\nmpga board live --serve --open]
    B --> C[Read INDEX.md + scope docs — HUGE intel]

    C --> D["Phase 1: Clarify the VISION\nSocratic questions — build the wall between modules\nabout problem, users, success"]
    D --> E["Phase 2: Explore the OPTIONS\n2-3 approaches with REAL evidence\nfrom the codebase — no guessing"]
    E --> F["Phase 3: STRESS-TEST the Design\nScale, dependencies, blast radius\nwe leave NOTHING to chance"]
    F --> G["Phase 4: Close the DEAL\nPresent sections one at a time"]

    G --> H[User experience / API shape]
    H --> I{User approves? GREAT taste}
    I -->|No| H
    I -->|Yes| J[Data model — VERY important]
    J --> K{User approves?}
    K -->|No| J
    K -->|Yes| L[Integration + Security + Testing]
    L --> M{User approves?}
    M -->|No| L
    M -->|Yes| N[Save DESIGN.md — a MASTERPIECE\nMPGA/milestones/id/DESIGN.md]
    N --> O{Spoke available?}
    O -->|Yes| P[mpga spoke — YUGE announcement]
    O -->|No| Q[Ready for /mpga:plan — has a beautiful ring to it]
    P --> Q
```

## Inputs — The Raw Materials
- Feature or project idea — YOUR brilliant vision
- MPGA/INDEX.md and relevant scope documents
- Existing code patterns as evidence — we deal in FACTS

## Outputs — A BEAUTIFUL Blueprint
- Approved DESIGN.md in the milestone directory — Problem, Constraints, Alternatives, Decision, Consequences, Implementation Outline — VERY thorough
- Clear scope ready for /mpga:plan — the pipeline is FLOWING
- No code written (design phase only) — no collusion between modules until the design is approved
