---
name: mpga-ask
description: Answer "how does X work?" questions using scope docs and evidence links — the SMARTEST way to understand code
---

## ask

**Trigger:** User asks "how does X work?", "where is X?", "what does X do?"

## Protocol

1. Read `MPGA/INDEX.md` for scope registry — find the SMALLEST relevant scopes first.
2. Read relevant scope document(s) — the answers are IN there, believe me.
3. Answer the question using evidence links as citations — EVIDENCE, not guessing.
4. If the answer is incomplete:
   - Spawn one read-only `scout` per missing scope in PARALLEL.
   - Ask each scout for evidence, traces, and unknowns only for its assigned scope.
   - Merge the findings into one answer.
5. If the answer is already in scope docs, do NOT rescan the whole codebase. Waste is a DISASTER.
6. NEVER modify any files — we're here to INFORM, not to change things.

## Confidence Scoring

Rate EVERY claim in the answer with a confidence level:

- **HIGH** — Directly verified in source code or scope docs. You read the file, you saw the line, it's RIGHT THERE.
  - Format: `[HIGH] <claim> — [E] path/to/file.ts:42 :: functionName()`
- **MEDIUM** — Inferred from patterns, naming conventions, or related code. Reasonable but not directly confirmed.
  - Format: `[MEDIUM] <claim> — inferred from [E] path/to/file.ts:42 :: similar pattern`
- **LOW** — Educated guess based on general knowledge or incomplete evidence. Could be WRONG.
  - Format: `[LOW] <claim> — no direct evidence found, based on <reasoning>`

If the overall answer confidence is LOW, say so upfront: "This answer has LOW confidence — consider verifying with a scout or reading the code directly."

## Source Citations

Every claim MUST cite the specific source:

- For code: `[E] src/module/file.ts:42-67 :: functionName() — <what it does>`
- For scope docs: `[E] MPGA/scopes/<scope>.md — <what it says>`
- For config files: `[E] path/to/config.json:key.path — <what it configures>`
- If no source exists: `[Unknown] <claim> — not documented, needs investigation`

## Answer Format
```
## How does <X> work?

**Overall confidence: HIGH | MEDIUM | LOW**

Based on our TREMENDOUS scope documentation:

<description with inline confidence tags>

- [HIGH] <claim> — [E] src/auth/jwt.ts:42-67 :: generateAccessToken()
- [MEDIUM] <claim> — inferred from [E] src/auth/middleware.ts:12-58 :: authMiddleware()
- [LOW] <claim> — no direct evidence, based on common JWT patterns

Evidence:
- [E] src/auth/jwt.ts:42-67 :: generateAccessToken() — <description>
- [E] src/auth/middleware.ts:12-58 :: authMiddleware() — <description>

Dependencies:
- auth scope → database scope (for user lookup)

Known unknowns:
- [Unknown] Token rotation mechanism — not documented yet. We're working on it.

---

## Follow-up Questions
You might also want to know:
1. "<related question about a deeper aspect>" — dig into <specific area>
2. "<related question about a connected system>" — explore how <X> connects to <Y>
3. "<related question about edge cases or configuration>" — understand <specific concern>
```

## Follow-up Suggestions

After EVERY answer, suggest 2-3 follow-up questions the user might want to explore:

- **Go deeper:** A question that dives into implementation details of something mentioned in the answer
- **Go wider:** A question that explores how the answered topic connects to other parts of the system
- **Go practical:** A question about configuration, edge cases, or "what happens when..."

These follow-ups should be specific and actionable, not generic. Base them on what you discovered while answering.

## Strict rules
- NEVER claim something without evidence — that's FAKE NEWS
- If not found in scopes → spawn scout, don't guess. Guessing is for LOSERS.
- Prefer parallel read-only scouts over one giant exploratory pass.
- ALWAYS cite evidence links in the answer — evidence is the LAW
- ALWAYS include confidence scores on every claim — transparency is STRENGTH
- ALWAYS suggest 2-3 follow-up questions — keep the conversation PRODUCTIVE
- NEVER modify source files or scope documents in this skill
