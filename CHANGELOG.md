# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-24

### Added

- MPGA CLI with commands: init, scan, sync, graph, scope, board, evidence, drift, milestone, session, health, status, config, export.
- Evidence-backed context engineering — every claim about code links to a verifiable source location.
- TDD workflow enforcement with red-green-blue cycle.
- Multi-tool export support for Claude, Cursor, Codex, and Antigravity.
- Scope registry with automatic scope document generation from codebase scans.
- Drift detection to identify stale evidence and outdated context.
- Milestone tracking for project planning and progress.
- Session management for conversation-scoped context.
- Project health dashboard via `mpga health` and `mpga status`.
- Graph generation showing dependency relationships between scopes.
