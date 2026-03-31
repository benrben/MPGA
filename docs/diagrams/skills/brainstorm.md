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

    G --> H["Present design sections ONE at a time —\n1. User experience / API shape\n2. Data model\n3. Integration + Security + Testing\nRevise each until approved before moving on"]
    H --> I{Section approved?}
    I -->|No — revise| H
    I -->|Yes| J{More sections?}
    J -->|Yes| H
    J -->|No — all approved| K[Save DESIGN.md — a MASTERPIECE\nstored in DB via mpga milestone show]
    K --> O[mpga spoke — if available]
```

## Inputs — The Raw Materials
- Feature or project idea — YOUR brilliant vision
- `mpga status` and relevant scope documents via `mpga scope show`
- Existing code patterns as evidence — we deal in FACTS

## Outputs — A BEAUTIFUL Blueprint
- Approved DESIGN.md in the milestone directory — Problem, Constraints, Alternatives, Decision, Consequences, Implementation Outline — VERY thorough
- Clear scope ready for /mpga:plan — the pipeline is FLOWING
- No code written (design phase only) — no collusion between modules until the design is approved
