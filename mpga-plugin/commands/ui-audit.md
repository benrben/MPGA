# /mpga:ui-audit

Run the UI quality gate after builds, during review, or as a standalone check.

## Steps

1. Identify the changed UI files
2. Spawn `ui-auditor`
3. Collect the findings
4. Create follow-up tasks for CRITICAL and HIGH issues

## Usage
```
/mpga:ui-audit
/mpga:ui-audit src/ui --full
```
