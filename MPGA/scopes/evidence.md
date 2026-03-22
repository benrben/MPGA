# Scope: evidence

## Summary

The **evidence** module contains 5 files (662 lines).

<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code

Main entry points — open these first to understand this behavior:

- [E] `mpga-plugin/cli/src/evidence/parser.test.ts`

## Context / stack / skills

- **Languages:** typescript
- **Symbol types:** interface, function, type
- <!-- TODO: Add relevant frameworks, integrations, and expertise areas -->

## Who and what triggers it

<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

**Called by scopes:**

- ← commands

## What happens

<!-- TODO: Describe the flow in plain language: inputs, main steps, outputs or side effects -->

## Rules and edge cases

<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples

<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI

<!-- TODO: Screens or flows if relevant — intent, layout, interactions, data shown/submitted. Remove this section if not applicable. -->

## Navigation

**Sibling scopes:**

- [mpga-plugin](./mpga-plugin.md)
- [board](./board.md)
- [core](./core.md)
- [commands](./commands.md)
- [generators](./generators.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

**Depended on by:**

- ← [commands](./commands.md)

<!-- TODO: Shared concepts or data with other scopes -->

## Diagram

```mermaid
graph LR
    commands --> evidence
```

## Traces

<!-- TODO: Step-by-step paths through the system. Use the table format below:

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | (layer) | (description) | [E] file:line |
-->

## Evidence index

| Claim | Evidence |
|-------|----------|
| `SymbolLocation` (interface) | [E] mpga-plugin/cli/src/evidence/ast.ts :: SymbolLocation |
| `detectLanguage` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts :: detectLanguage |
| `extractSymbols` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts :: extractSymbols |
| `findSymbol` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts :: findSymbol |
| `verifyRange` (function) | [E] mpga-plugin/cli/src/evidence/ast.ts :: verifyRange |
| `ScopeDriftReport` (interface) | [E] mpga-plugin/cli/src/evidence/drift.ts :: ScopeDriftReport |
| `DriftReport` (interface) | [E] mpga-plugin/cli/src/evidence/drift.ts :: DriftReport |
| `runDriftCheck` (function) | [E] mpga-plugin/cli/src/evidence/drift.ts :: runDriftCheck |
| `healScopeFile` (function) | [E] mpga-plugin/cli/src/evidence/drift.ts :: healScopeFile |
| `EvidenceLinkType` (type) | [E] mpga-plugin/cli/src/evidence/parser.ts :: EvidenceLinkType |
| `EvidenceLink` (interface) | [E] mpga-plugin/cli/src/evidence/parser.ts :: EvidenceLink |
| `parseEvidenceLink` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts :: parseEvidenceLink |
| `parseEvidenceLinks` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts :: parseEvidenceLinks |
| `formatEvidenceLink` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts :: formatEvidenceLink |
| `evidenceStats` (function) | [E] mpga-plugin/cli/src/evidence/parser.ts :: evidenceStats |
| `ResolutionStatus` (type) | [E] mpga-plugin/cli/src/evidence/resolver.ts :: ResolutionStatus |
| `ResolvedEvidence` (interface) | [E] mpga-plugin/cli/src/evidence/resolver.ts :: ResolvedEvidence |
| `resolveEvidence` (function) | [E] mpga-plugin/cli/src/evidence/resolver.ts :: resolveEvidence |
| `VerifyResult` (interface) | [E] mpga-plugin/cli/src/evidence/resolver.ts :: VerifyResult |
| `verifyAllLinks` (function) | [E] mpga-plugin/cli/src/evidence/resolver.ts :: verifyAllLinks |

## Files

- `mpga-plugin/cli/src/evidence/ast.ts` (134 lines, typescript)
- `mpga-plugin/cli/src/evidence/drift.ts` (151 lines, typescript)
- `mpga-plugin/cli/src/evidence/parser.test.ts` (162 lines, typescript)
- `mpga-plugin/cli/src/evidence/parser.ts` (123 lines, typescript)
- `mpga-plugin/cli/src/evidence/resolver.ts` (92 lines, typescript)

## Deeper splits

<!-- TODO: Pointers to smaller sub-topic scopes if this capability is large enough to split -->

## Confidence and notes

- **Confidence:** low — auto-generated, not yet verified
- **Evidence coverage:** 0/20 verified
- **Last verified:** 2026-03-22
- **Drift risk:** unknown
- <!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history

- 2026-03-22: Initial scope generation via `mpga sync`