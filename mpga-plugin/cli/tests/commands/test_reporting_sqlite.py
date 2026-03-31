"""Tests for SQLite-backed status, health, and metrics reporting."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _write_config(root: Path) -> None:
    mpga = root / "MPGA"
    mpga.mkdir(parents=True, exist_ok=True)
    config = {
        "version": "1.0.0",
        "project": {
            "name": "sqlite-project",
            "languages": ["python"],
            "entryPoints": [],
            "ignore": [],
        },
        "evidence": {
            "strategy": "hybrid",
            "lineRanges": True,
            "astAnchors": True,
            "autoHeal": True,
            "coverageThreshold": 0.2,
        },
        "drift": {"ciThreshold": 80, "hookMode": "quick", "autoSync": False},
    }
    (mpga / "mpga.config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _seed_sqlite(root: Path) -> None:
    db_path = root / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        conn.execute(
            """
            INSERT INTO tasks
                (id, title, body, column_, status, priority, milestone, phase,
                 assigned, tdd_stage, lane_id, run_status, current_agent,
                 time_estimate, created_at, updated_at, started_at,
                 finished_at, heartbeat_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "T001",
                "Done task",
                "Body",
                "done",
                None,
                "high",
                "M001",
                None,
                None,
                "done",
                None,
                "done",
                None,
                "5min",
                "2026-01-01T00:00:00",
                "2026-01-02T00:00:00",
                "2026-01-01T00:00:00",
                "2026-01-02T00:00:00",
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO tasks
                (id, title, body, column_, status, priority, milestone, phase,
                 assigned, tdd_stage, lane_id, run_status, current_agent,
                 time_estimate, created_at, updated_at, started_at,
                 finished_at, heartbeat_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "T002",
                "In progress task",
                "Body",
                "in-progress",
                None,
                "medium",
                None,
                None,
                None,
                "green",
                None,
                "running",
                None,
                "5min",
                "2026-01-03T00:00:00",
                "2026-01-03T00:00:00",
                None,
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO tasks
                (id, title, body, column_, status, priority, milestone, phase,
                 assigned, tdd_stage, lane_id, run_status, current_agent,
                 time_estimate, created_at, updated_at, started_at,
                 finished_at, heartbeat_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "T003",
                "Blocked task",
                "Body",
                "backlog",
                "blocked",
                "low",
                None,
                None,
                None,
                None,
                None,
                "queued",
                None,
                "5min",
                "2026-01-04T00:00:00",
                "2026-01-04T00:00:00",
                None,
                None,
                None,
            ),
        )
        conn.execute(
            """
            INSERT INTO scopes
                (id, name, summary, content, status, evidence_total, evidence_valid,
                 last_verified, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "scope-a",
                "scope-a",
                "A scope",
                "A scope body",
                "fresh",
                1,
                1,
                "2026-01-05T00:00:00",
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO scopes
                (id, name, summary, content, status, evidence_total, evidence_valid,
                 last_verified, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "scope-b",
                "scope-b",
                "B scope",
                "B scope body",
                "fresh",
                0,
                0,
                None,
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
            ),
        )
        conn.execute(
            "INSERT INTO file_info (filepath, language, lines, size, content_hash, last_scanned) VALUES (?, ?, ?, ?, ?, ?)",
            ("src/app.py", "python", 10, 120, "abc123", "2026-04-01T00:00:00"),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_markdown_tasks(root: Path) -> None:
    tasks_dir = root / "MPGA" / "board" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "T001-done-task.md").write_text(
        """---
id: "T001"
title: "Done task"
status: "active"
column: "done"
priority: "high"
milestone: "M001"
phase: null
created: "2026-01-01T00:00:00"
updated: "2026-01-02T00:00:00"
assigned: null
depends_on: []
blocks: []
scopes: []
tdd_stage: "done"
lane_id: null
run_status: "done"
current_agent: null
file_locks: []
scope_locks: []
started_at: "2026-01-01T00:00:00"
finished_at: "2026-01-02T00:00:00"
heartbeat_at: null
evidence_expected: ["[E] src/app.py"]
evidence_produced: ["[E] src/app.py"]
tags: []
time_estimate: "5min"
---

# T001: Done task
""",
        encoding="utf-8",
    )


class TestSqliteStatusHealth:
    def test_status_uses_sqlite_mirror_when_present(self, tmp_path: Path, monkeypatch):
        _write_config(tmp_path)
        _seed_sqlite(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.status import status_cmd

        result = CliRunner().invoke(status_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["scopes"] == 2
        assert parsed["board"]["total"] == 3
        assert parsed["board"]["done"] == 1
        assert parsed["board"]["in_flight"] == 1
        assert parsed["board"]["blocked"] == 1
        assert parsed["lastSync"] == "2026-04-01T00:00:00"

    def test_health_uses_sqlite_mirror_when_present(self, tmp_path: Path, monkeypatch):
        _write_config(tmp_path)
        _seed_sqlite(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.evidence.drift import DriftReport
        from mpga.commands.health import health_cmd

        mock_report = DriftReport(
            timestamp="2026-04-01T00:00:00",
            project_root=str(tmp_path),
            overall_health_pct=88,
            ci_pass=True,
            scopes=[],
            total_links=0,
            valid_links=0,
            ci_threshold=80,
        )
        monkeypatch.setattr("mpga.commands.health.run_drift_check", lambda *a, **kw: mock_report)

        result = CliRunner().invoke(health_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["scopes"] == 2
        assert parsed["board"]["total"] == 3
        assert parsed["board"]["done"] == 1
        assert parsed["lastSync"] == "2026-04-01T00:00:00"
        assert parsed["overallGrade"] == "B"


class TestSqliteMetrics:
    def test_metrics_prefers_sqlite_counts_and_merges_markdown_evidence(self, tmp_path: Path, monkeypatch):
        _write_config(tmp_path)
        _seed_sqlite(tmp_path)
        _seed_markdown_tasks(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.metrics import metrics_cmd

        result = CliRunner().invoke(metrics_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["total"] == 3
        assert parsed["done"] == 1
        assert parsed["in_progress"] == 1
        assert parsed["blocked"] == 1
        assert parsed["evidence_coverage"] == "100%"
        assert parsed["tdd_adherence"] == "100%"
