---
name: mpga-memory
description: Progressive-disclosure memory retrieval — search, context, and get commands for observations
---

## Memory Commands

MPGA memory provides three-layer progressive-disclosure retrieval for observations captured during development sessions.

### Layer 1: Search — `mpga memory search`

Find observations matching a query. Returns compact index entries.

```bash
mpga memory search "database migration"
mpga memory search "auth" --type tool_output --limit 10
```

**Options:**
- `--type` — Filter by observation type (e.g. `tool_output`, `decision`, `insight`)
- `--limit` — Max results (default 20)

### Layer 2: Context — `mpga memory context`

Show an observation with its surrounding timeline for situational awareness.

```bash
mpga memory context 42
mpga memory context 42 --window 10
```

**Options:**
- `--window` — Number of observations before/after to display (default 5)

### Layer 3: Full Detail — `mpga memory get`

Retrieve the complete observation record including narrative, facts, concepts, and file references.

```bash
mpga memory get 42
mpga memory get 42 --json
```

**Options:**
- `--json` — Output as JSON for programmatic use

### Linking — `mpga memory link`

Create an evidence link from an observation, bridging memory into the evidence system.

```bash
mpga memory link 42
```

## Typical Workflow

1. `mpga memory search "auth"` — Find relevant observations
2. `mpga memory context 15` — Understand the timeline around a match
3. `mpga memory get 15` — Read the full observation details
4. `mpga memory link 15` — Promote to an evidence link
