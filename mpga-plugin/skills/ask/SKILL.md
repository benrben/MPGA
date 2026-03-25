---
name: mpga-ask
description: Answer "how does X work?" questions using scope docs and evidence links — the SMARTEST way to understand code
---

## ask — The Greatest Question-Answering Skill Ever Built

You want answers? We've got answers. TREMENDOUS answers backed by EVIDENCE.

**Trigger:** User asks "how does X work?", "where is X?", "what does X do?" — and they DESERVE a PERFECT answer, frankly.

## The Winning Protocol

1. Read `MPGA/INDEX.md` for scope registry — find the SMALLEST relevant scopes first. Precision, people. We don't do sloppy.
2. Read relevant scope document(s) — the answers are IN there, believe me. Our scope docs are INCREDIBLE.
3. Answer the question using evidence links as citations — EVIDENCE, not guessing. We leave the guessing to the other guys.
4. If the answer is incomplete — and sometimes, very rarely, it happens:
   - Spawn one read-only `scout` per missing scope in PARALLEL. We deploy scouts like nobody's ever seen before.
   - Ask each scout for evidence, traces, and unknowns only for its assigned scope. Focused. Disciplined. BEAUTIFUL.
   - Merge the findings into one answer. One PERFECT, unified answer.
5. If the answer is already in scope docs, do NOT rescan the whole codebase. Waste is a DISASTER. We run a TIGHT operation.
6. NEVER modify any files — we're here to INFORM, not to change things. Read-only. Very classy, very elegant.

## Confidence Scoring — We Rate EVERYTHING, Total Transparency

Rate EVERY claim in the answer with a confidence level — because we don't hide, we don't hedge, we SCORE:

- **HIGH** — Directly verified in source code or scope docs. You read the file, you saw the line, it's RIGHT THERE.
  - Format: `[HIGH] <claim> — [E] path/to/file.ts:42 :: functionName()`
- **MEDIUM** — Inferred from patterns, naming conventions, or related code. Reasonable but not directly confirmed.
  - Format: `[MEDIUM] <claim> — inferred from [E] path/to/file.ts:42 :: similar pattern`
- **LOW** — Educated guess based on general knowledge or incomplete evidence. Could be WRONG.
  - Format: `[LOW] <claim> — no direct evidence found, based on <reasoning>`

If the overall answer confidence is LOW, say so upfront: "This answer has LOW confidence — consider verifying with a scout or reading the code directly."

## Source Citations — Show Your Receipts, Always

Every claim MUST cite the specific source — no citations, no credibility. It's very simple:

- For code: `[E] src/module/file.ts:42-67 :: functionName() — <what it does>`
- For scope docs: `[E] MPGA/scopes/<scope>.md — <what it says>`
- For config files: `[E] path/to/config.json:key.path — <what it configures>`
- If no source exists: `[Unknown] <claim> — not documented, needs investigation`

## Answer Format — The Gold Standard
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

## Follow-up Suggestions — Keep the Winning Going

After EVERY answer, suggest 2-3 follow-up questions the user might want to explore. We don't just answer — we ANTICIPATE:

- **Go deeper:** A question that dives into implementation details of something mentioned in the answer. Get into the WEEDS. The beautiful, well-documented weeds.
- **Go wider:** A question that explores how the answered topic connects to other parts of the system. Because EVERYTHING is connected, folks. It's a MAGNIFICENT system.
- **Go practical:** A question about configuration, edge cases, or "what happens when..." — the REAL questions that REAL developers ask.

These follow-ups should be specific and actionable, not generic. Base them on what you discovered while answering. We don't do lazy.

## Strict Rules — The LAW of the Land
- NEVER claim something without evidence — that's FAKE NEWS
- If not found in scopes → spawn scout, don't guess. Guessing is for LOSERS.
- Prefer parallel read-only scouts over one giant exploratory pass.
- ALWAYS cite evidence links in the answer — evidence is the LAW
- ALWAYS include confidence scores on every claim — transparency is STRENGTH
- ALWAYS suggest 2-3 follow-up questions — keep the conversation PRODUCTIVE
- NEVER modify source files or scope documents in this skill
