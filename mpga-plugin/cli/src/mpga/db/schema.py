"""Schema creation for MPGA SQLite + FTS5 database."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_CORE_TABLES = """
-- Scanned file metadata
CREATE TABLE IF NOT EXISTS file_info (
    filepath TEXT PRIMARY KEY,
    language TEXT,
    lines INT,
    size INT,
    content_hash TEXT,
    last_scanned TEXT NOT NULL
);

-- AST symbols
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL REFERENCES file_info(filepath) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT,
    start_line INT,
    end_line INT
);

-- Dependency graph edges
CREATE TABLE IF NOT EXISTS graph_edges (
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    type TEXT DEFAULT 'import',
    PRIMARY KEY (source, target, type)
);

-- Scopes
CREATE TABLE IF NOT EXISTS scopes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    status TEXT DEFAULT 'fresh',
    evidence_total INT DEFAULT 0,
    evidence_valid INT DEFAULT 0,
    last_verified TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    column_ TEXT NOT NULL DEFAULT 'backlog',
    status TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    milestone TEXT,
    phase INT,
    assigned TEXT,
    tdd_stage TEXT,
    lane_id TEXT,
    run_status TEXT DEFAULT 'queued',
    current_agent TEXT,
    time_estimate TEXT DEFAULT '5min',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    heartbeat_at TEXT
);

-- Task junction tables
CREATE TABLE IF NOT EXISTS task_scopes (
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    scope_id TEXT,
    PRIMARY KEY (task_id, scope_id)
);

CREATE TABLE IF NOT EXISTS task_tags (
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    tag TEXT,
    PRIMARY KEY (task_id, tag)
);

CREATE TABLE IF NOT EXISTS task_deps (
    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on TEXT,
    PRIMARY KEY (task_id, depends_on)
);

-- Evidence links
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw TEXT NOT NULL,
    type TEXT NOT NULL,
    filepath TEXT,
    start_line INT,
    end_line INT,
    symbol TEXT,
    symbol_type TEXT,
    description TEXT,
    confidence REAL DEFAULT 1.0,
    stale_date TEXT,
    last_verified TEXT,
    scope_id TEXT,
    task_id TEXT,
    created_at TEXT
);

-- Milestones
CREATE TABLE IF NOT EXISTS milestones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    design TEXT,
    summary TEXT,
    plan TEXT,
    context TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

-- Design tokens
CREATE TABLE IF NOT EXISTS design_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    source_file TEXT,
    UNIQUE(category, name)
);

-- Architecture Decision Records
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'accepted',
    content TEXT,
    created_at TEXT NOT NULL
);

-- Develop scheduler: lanes
CREATE TABLE IF NOT EXISTS lanes (
    id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'queued',
    scope TEXT,
    current_agent TEXT,
    updated_at TEXT NOT NULL
);

-- Develop scheduler: runs
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    lane_id TEXT REFERENCES lanes(id) ON DELETE CASCADE,
    task_id TEXT REFERENCES tasks(id),
    status TEXT DEFAULT 'queued',
    agent TEXT,
    started_at TEXT,
    finished_at TEXT
);

-- File locks
CREATE TABLE IF NOT EXISTS file_locks (
    filepath TEXT NOT NULL,
    task_id TEXT NOT NULL,
    lane_id TEXT,
    agent TEXT,
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT,
    PRIMARY KEY (filepath, task_id)
);

-- Scope locks
CREATE TABLE IF NOT EXISTS scope_locks (
    scope TEXT NOT NULL,
    task_id TEXT NOT NULL,
    lane_id TEXT,
    agent TEXT,
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT,
    PRIMARY KEY (scope, task_id)
);

-- Session tracking (context window continuity)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_root TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    model TEXT,
    status TEXT DEFAULT 'active',
    task_snapshot TEXT
);

-- Event log
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    input_summary TEXT,
    output_summary TEXT,
    full_output TEXT,
    metadata TEXT
);

-- Context artifacts (ctx_* sandbox tool storage)
CREATE TABLE IF NOT EXISTS ctx_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    content_bytes INT DEFAULT 0,
    summary_bytes INT DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Context command usage and savings telemetry
CREATE TABLE IF NOT EXISTS ctx_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tool TEXT NOT NULL,
    source TEXT,
    raw_bytes INT DEFAULT 0,
    emitted_bytes INT DEFAULT 0,
    indexed_count INT DEFAULT 0
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
"""

_FTS5_TABLES = """
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    title, body,
    content=tasks, content_rowid=rowid
);

CREATE VIRTUAL TABLE IF NOT EXISTS scopes_fts USING fts5(
    name, summary, content,
    content=scopes, content_rowid=rowid
);

CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
    raw, filepath, symbol, description,
    content=evidence, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
    name, type, filepath,
    content=symbols, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    title, content,
    content=decisions, content_rowid=rowid
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    event_type, entity_type, action,
    input_summary, output_summary,
    content=events, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS global_fts USING fts5(
    entity_type, entity_id, title, content
);

CREATE VIRTUAL TABLE IF NOT EXISTS ctx_artifacts_fts USING fts5(
    source, content, summary,
    content=ctx_artifacts, content_rowid=id
);
"""


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and FTS5 virtual tables. Idempotent."""
    # Always run CREATE IF NOT EXISTS to backfill newly added objects safely.
    conn.executescript(_CORE_TABLES)
    conn.executescript(_FTS5_TABLES)

    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version, applied_at, description) "
        "VALUES (?, datetime('now'), ?)",
        (SCHEMA_VERSION, "Initial schema: M008 SQLite + FTS5 context engine"),
    )
    conn.commit()

    # Backfill new milestone columns for existing databases
    for col_def in ("plan TEXT", "context TEXT"):
        col_name = col_def.split()[0]
        try:
            conn.execute(f"ALTER TABLE milestones ADD COLUMN {col_def}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
