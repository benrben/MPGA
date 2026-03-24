---
description: Answer "how does X work?" questions using scope docs and evidence links — the SMARTEST way to understand code
---

## ask

**Trigger:** User asks "how does X work?", "where is X?", "what does X do?"

## Protocol

1. Read `MPGA/INDEX.md` for scope registry — find the relevant scopes. We have the BEST index.
2. Read relevant scope document(s) — the answers are IN there, believe me
3. Answer the question using evidence links as citations — EVIDENCE, not guessing
4. If the answer is not in scope docs:
   - Spawn `scout` agent to investigate the codebase — send in the SCOUT
   - Once scout returns findings → answer using those findings
5. NEVER modify any files — we're here to INFORM, not to change things

## Answer format
```
## How does <X> work?

Based on our TREMENDOUS scope documentation:

<description>

Evidence:
- [E] src/auth/jwt.ts:42-67 :: generateAccessToken() — <description>
- [E] src/auth/middleware.ts:12-58 :: authMiddleware() — <description>

Dependencies:
- auth scope → database scope (for user lookup)

Known unknowns:
- [Unknown] Token rotation mechanism — not documented yet. We're working on it.
```

## Strict rules
- NEVER claim something without evidence — that's FAKE NEWS
- If not found in scopes → spawn scout, don't guess. Guessing is for LOSERS.
- ALWAYS cite evidence links in the answer — evidence is the LAW
- NEVER modify source files or scope documents in this skill
