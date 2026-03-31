---
name: mpga-ask
description: Answer "how does X work?" questions using scope docs and evidence links — the SMARTEST way to understand code
---

## Orchestration Contract
This skill is a **pure orchestrator**. It MUST NOT:
- Read files directly (delegates to scout agents)
- Write any files
- Run CLI commands other than `mpga` board/status/scope list queries

## ask

Evidence-backed answers. Evidence First — always.

**Trigger:** User asks "how does X work?", "where is X?", "what does X do?".

## The Winning Protocol

1. Run `mpga scope list` — find the SMALLEST relevant scopes first. Precision, people. We don't do sloppy.
2. Spawn one read-only `scout` agent per relevant scope in PARALLEL to gather evidence — never read files directly.
3. Assemble the answer from scout outputs using evidence links as citations — evidence, not guessing.
4. If the answer is incomplete — and sometimes, very rarely, it happens:
   - Spawn one read-only `scout` per missing scope in PARALLEL.
   - Ask each scout for evidence, traces, and unknowns only for its assigned scope.
   - Merge the findings into one answer.
5. If the answer is already covered by scout outputs, do NOT rescan the whole codebase.
6. NEVER modify any files — read-only. NEVER read files directly — delegates to scouts.

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
- For scope docs: `[E] scope:<scope> — <what it says>` (view with `mpga scope show <scope>`)
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

## Follow-up Suggestions — The Weave — Connecting Evidence Threads

After EVERY answer, suggest 2-3 follow-up questions the user might want to explore. We don't just answer — we ANTICIPATE:

- **Go deeper:** A question that dives into implementation details of something mentioned in the answer. Build the wall between modules! Understand the boundaries. Get into the WEEDS. The beautiful, well-documented weeds.
- **Go wider:** A question that explores how the answered topic connects to other parts of the system.
- **Go practical:** A question about configuration, edge cases, or "what happens when..." — the REAL questions that REAL developers ask.

These follow-ups should be specific and actionable, not generic. Base them on what you discovered while answering. We don't do lazy.

## Voice announcement

If spoke is available (`mpga spoke --help` exits 0), announce completion:

```bash
mpga spoke '<brief 1-sentence result summary>'
```

Keep the message under 280 characters. This plays the result in Trump's voice — TREMENDOUS.

## Strict Rules — The LAW of the Land
- NEVER claim something that's unverified
- If not found in scopes → spawn scout, don't guess.
- Prefer parallel read-only scouts over one giant exploratory pass.
- ALWAYS cite evidence links in the answer — law and order in the codebase
- ALWAYS include confidence scores on every claim — transparency is STRENGTH
- ALWAYS suggest 2-3 follow-up questions — keep the conversation PRODUCTIVE
- NEVER modify source files or scope documents in this skill
