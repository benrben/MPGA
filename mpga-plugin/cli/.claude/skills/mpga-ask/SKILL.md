---
description: Answer "how does X work?" questions using scope docs and evidence links
---

## ask

**Trigger:** User asks "how does X work?", "where is X?", "what does X do?"

## Protocol

1. Read `MPGA/INDEX.md` for scope registry — find relevant scopes
2. Read relevant scope document(s)
3. Answer the question using evidence links as citations
4. If the answer is not in scope docs:
   - Spawn `scout` agent to investigate the codebase
   - Once scout returns findings → answer using those findings
5. NEVER modify any files

## Answer format
```
## How does <X> work?

Based on the scope documentation:

<description>

Evidence:
- [E] src/auth/jwt.ts:42-67 :: generateAccessToken() — <description>
- [E] src/auth/middleware.ts:12-58 :: authMiddleware() — <description>

Dependencies:
- auth scope → database scope (for user lookup)

Known unknowns:
- [Unknown] Token rotation mechanism — not documented
```

## Strict rules
- NEVER claim something without evidence
- If not found in scopes → spawn scout, don't guess
- ALWAYS cite evidence links in the answer
- NEVER modify source files or scope documents in this skill
