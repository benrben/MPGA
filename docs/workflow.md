# MPGA Workflow Model

This document describes the cleaned-up execution model used by MPGA's skills, agents, and tool exports.

## Core rule

Parallelize reads, not writes.

- One writer per scope at a time
- Read-only helpers like `scout`, `auditor`, and `campaigner` can run in parallel
- Plans should isolate independent scopes into separate task lanes

## Execution model

| Stage | Primary actors | Parallel-safe | Notes |
|------|----------------|--------------|------|
| Discovery | `sync-project`, `map-codebase`, `scout`, `architect`, `auditor` | High | Fan out scouts by scope, then consolidate with architect |
| Planning | `plan`, `researcher`, `scout` | Medium | Research and scope discovery can run in parallel before task synthesis |
| Delivery | `develop`, `red-dev`, `green-dev`, `blue-dev`, `reviewer` | Medium | Independent scopes may move in parallel, but each scope keeps one write lane |
| Verification | `drift-check`, `reviewer`, `verifier` | Medium | Quick drift during active work, full verifier at risk boundaries |
| Diagnostics | `rally`, `campaigner` | High | Split by scandal category, then aggregate |
| Continuity | `handoff`, `onboard`, `ask` | Low | Reuse the MPGA layer instead of rescanning the repo |

## Skills

| Skill | Purpose | Parallel guidance |
|------|---------|-------------------|
| `sync-project` | Refresh the MPGA layer | Prefer incremental sync on partial changes |
| `brainstorm` | Design refinement | Usually serial |
| `plan` | Build milestone tasks | Run `researcher` + read-only `scout`s in parallel |
| `develop` | Execute TDD tasks | One write lane per scope |
| `drift-check` | Keep evidence healthy | Scope-local quick checks during active work |
| `ask` | Answer code questions | Spawn parallel `scout`s only for missing scope evidence |
| `onboard` | Guided project tour | Usually serial |
| `rally` | Full diagnostic audit | Parallelize by scandal category |
| `ship` | Finalize and archive | Usually serial |
| `handoff` | Transfer session state | Usually serial |
| `map-codebase` | Populate scopes | One `scout` per scope in parallel |

## Agents

| Agent | Writes files | Parallel-safe | Main use |
|------|---------------|--------------|---------|
| `campaigner` | No | Yes | Category-based rally diagnostics |
| `scout` | Scope docs only | Yes | Read-only codebase exploration by scope |
| `architect` | Yes | No | Cross-scope consolidation |
| `auditor` | No | Yes | Background evidence health checks |
| `researcher` | No | Yes | Options and tradeoff analysis |
| `red-dev` | Tests only | No | Write failing tests inside the active scope lane |
| `green-dev` | Source only | No | Minimal implementation inside the active scope lane |
| `blue-dev` | Yes | No | Refactor after tests are green |
| `reviewer` | No | Yes | Diff-focused review |
| `verifier` | No | Yes | Heavy final gate for risky work or milestone close |

## Fast path

For small, isolated tasks:

1. Load `INDEX.md` and the relevant scope
2. Claim the scope-local write lane
3. Run `red-dev -> green-dev -> blue-dev`
4. Let `scout` / `auditor` run in background if helpful
5. Use `reviewer` + quick drift
6. Reserve `verifier` for milestone close or higher-risk changes

## Slow path

Use the full heavyweight flow when:

- a change touches multiple scopes
- the milestone is closing
- evidence is already stale
- the task is high-risk or security-sensitive
- the user explicitly asks for a full verification pass
