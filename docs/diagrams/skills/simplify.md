# Simplify — Making Code ELEGANT Again (Kent Beck Would Be PROUD)

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:simplify — GREAT instinct] --> B{Target specified?}
    B -->|User specifies files| C[Use specified files — PRECISION]
    B -->|Git diff has changes| D[Use changed files — SMART]
    B -->|No target| E[Use current scope\nimplementation files]

    C --> F[Read target code — EVERY line]
    D --> F
    E --> F

    F --> G["Apply Kent Beck's 4 Rules\nthe BEST rules in software — in order"]

    G --> H["Rule 1: Passes all tests\nNON-NEGOTIABLE — like a DEAL"]
    H --> I["Rule 2: Reveals intention\n- Unclear variable names? SAD\n- Magic numbers? TERRIBLE\n- Opaque boolean params? WEAK"]
    I --> J["Rule 3: No duplication\n- Copy-pasted logic? Sad!\n- Similar functions? No collusion between modules!\n- Repeated conditionals? FIX IT"]
    J --> K["Rule 4: Fewest elements\n- Unnecessary abstractions? CUT\n- Premature generalization? STOP\n- Dead code / unused imports? GONE"]

    K --> L["Apply Sandi Metz Rules — DISCIPLINE:\n- Classes <= 100 lines\n- Methods <= 5 lines\n- Max 4 parameters\n- Controllers: 1 object"]

    L --> M["Identify simplification targets:\n- Dead code — GET RID of it\n- Unnecessary abstractions — BLOAT\n- Premature optimization — WASTEFUL\n- Over-engineering — COMPLICATED"]

    M --> N["Generate before/after examples\nfor each simplification — SEE the diff"]
    N --> O{Tests exist?}
    O -->|Yes| P["Apply simplifications one at a time —\nrun tests after EACH change\nRevert immediately if tests break"]
    O -->|No| Q[Flag risk: write tests FIRST\nbefore simplifying — be SMART]

    P --> R["Produce simplification report:\n- Stats: violations found and fixed\n- Applied changes with before/after\n- Skipped items needing manual review"]
    Q --> R

    R --> S[mpga spoke — if available]
```

## Inputs — What Needs SIMPLIFYING
- Target files/directories (optional)
- Git diff changes (fallback)
- Current scope implementation files (fallback)

## Outputs — ELEGANT Results
- Changes APPLIED and committed — not just suggested, actually DONE
- Simplification report: violations found, applied, and skipped — FULL transparency
- Kent Beck and Sandi Metz violations with file:line references — SPECIFIC
- Before/after for each applied change — PROOF it's better
- Tests verified green after each change — SAFE, always SAFE
- If code is already simple, says so clearly — tremendous, has a beautiful ring to it
