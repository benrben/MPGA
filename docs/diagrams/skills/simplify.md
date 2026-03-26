# Simplify — Code Elegance via Kent Beck and Sandi Metz Rules

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:simplify] --> B{Target specified?}
    B -->|User specifies files| C[Use specified files]
    B -->|Git diff has changes| D[Use changed files]
    B -->|No target| E[Use current scope\nimplementation files]

    C --> F[Read target code]
    D --> F
    E --> F

    F --> G["Apply Kent Beck's 4 Rules\n(in priority order)"]

    G --> H["Rule 1: Passes all tests\n(NON-NEGOTIABLE)"]
    H --> I["Rule 2: Reveals intention\n- Unclear variable names?\n- Magic numbers?\n- Opaque boolean params?"]
    I --> J["Rule 3: No duplication\n- Copy-pasted logic?\n- Similar functions differing by one param?\n- Repeated conditionals?"]
    J --> K["Rule 4: Fewest elements\n- Unnecessary abstractions?\n- Premature generalization?\n- Dead code / unused imports?"]

    K --> L["Apply Sandi Metz Rules:\n- Classes <= 100 lines\n- Methods <= 5 lines\n- Max 4 parameters\n- Controllers: 1 object"]

    L --> M["Identify simplification targets:\n- Dead code\n- Unnecessary abstractions\n- Premature optimization\n- Over-engineering"]

    M --> N["Generate before/after examples\nfor each simplification"]
    N --> O{Tests exist?}
    O -->|Yes| P[Verify tests still pass\nafter each change]
    O -->|No| Q[Flag risk: suggest writing\ntests first]

    P --> R["Produce simplification report:\n- Summary stats\n- Prioritized list (HIGH/MED/LOW)\n- Detailed before/after for each"]
    Q --> R

    R --> S{Spoke available?}
    S -->|Yes| T[mpga spoke announcement]
    S -->|No| U[Done]
    T --> U
```

## Inputs
- Target files/directories (optional)
- Git diff changes (fallback)
- Current scope implementation files (fallback)

## Outputs
- Simplification report with summary stats
- Kent Beck rule violations identified
- Sandi Metz rule violations with file:line references
- Before/after code examples for each suggestion
- Priority-ranked simplifications (HIGH impact + LOW effort first)
- Behavior preserved (no functional changes)
- If code is already simple, says so clearly
