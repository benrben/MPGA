-- v001: ensure schema_version table exists (created by schema.py; this is a no-op placeholder)
CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
