# Diagnose — Bug and Quality Issue Detection

## Workflow

```mermaid
flowchart TD
    A[User invokes /mpga:diagnose] --> B{Target specified?}
    B -->|User specifies files| C[Use specified files/directories]
    B -->|Git diff has changes| D[Use changed files]
    B -->|No target| E[Use current scope or\nmost recently changed files]

    C --> F[Identify target files]
    D --> F
    E --> F

    F --> G[Spawn bug-hunter agent\nread-only / parallel]
    F --> H[Spawn optimizer agent\nread-only / parallel]

    G --> I["Bug-hunter checks:\n- Spec vs implementation\n- Edge cases / boundaries\n- Error handling paths\n- Logic errors / off-by-one\n- Type safety violations\n- Async/race conditions"]

    H --> J["Optimizer checks:\n- Cyclomatic complexity\n- Duplicated code\n- Dead code\n- Performance anti-patterns\n- Memory leak patterns\n- Dependency coupling"]

    I --> K[Collect results from both agents]
    J --> K

    K --> L["Produce unified diagnosis report:\n- Bugs table with severity + evidence\n- Quality issues table\n- Priority-ranked fix list\n- Summary with counts + effort estimates"]

    L --> M{User wants board tasks?}
    M -->|Yes| N[Create individual tasks for\nCRITICAL/HIGH findings]
    N --> O[Group LOW/MEDIUM into\nsingle cleanup task]
    M -->|No| P{Spoke available?}
    O --> P
    P -->|Yes| Q[mpga spoke announcement]
    P -->|No| R[Done]
    Q --> R
```

## Inputs
- Target files/directories (optional)
- Git diff changes (fallback)
- Current scope (fallback)

## Outputs
- Unified diagnosis report with bugs and quality issues
- Each finding has severity, file:line, evidence citation
- Priority-ranked fix list with effort estimates
- Optional board tasks for CRITICAL/HIGH findings
- No files modified (read-only skill)
