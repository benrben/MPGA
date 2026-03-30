"""Minimal Flask app for the MPGA database dashboard.

Implements create_db_app(conn) -> Flask with routes:
  GET /db                  — HTML dashboard shell
  GET /db/api/scopes       — JSON list of scopes
  GET /db/api/evidence     — JSON paginated evidence (with optional ?q= search)
  GET /db/api/schema       — JSON database schema (tables + columns)
"""

from __future__ import annotations

import sqlite3

from flask import Flask, Response, jsonify, request


# ---------------------------------------------------------------------------
# Schema introspection helpers (Extract Function — Fowler)
# ---------------------------------------------------------------------------


def _fetch_columns(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Return column metadata for *table* using ``PRAGMA table_info``.

    Each entry contains: ``cid``, ``name``, ``type``, ``notnull``,
    ``dflt_value``, and ``pk``.
    """
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [
        {
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": r[3],
            "dflt_value": r[4],
            "pk": r[5],
        }
        for r in cursor.fetchall()
    ]


def _fetch_foreign_keys(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Return foreign key metadata for *table* using ``PRAGMA foreign_key_list``.

    Each entry contains: ``id``, ``seq``, ``table``, ``from``, and ``to``.
    """
    cursor = conn.execute(f"PRAGMA foreign_key_list({table})")
    return [
        {
            "id": r[0],
            "seq": r[1],
            "table": r[2],
            "from": r[3],
            "to": r[4],
        }
        for r in cursor.fetchall()
    ]


def create_db_app(conn: sqlite3.Connection) -> Flask:
    """Create and return a Flask app backed by the given SQLite connection."""
    app = Flask(__name__)

    @app.route("/db")
    def dashboard() -> Response:
        """Return the HTML shell for the database dashboard SPA.

        The page contains a single mount point ``<div id="content">`` that the
        front-end JavaScript will populate with live data from the API routes.
        """
        return (
            "<html><body>"
            '<div id="content"></div>'
            "</body></html>"
        )

    @app.route("/db/api/scopes")
    def api_scopes() -> Response:
        """Return all scopes as a JSON list.

        Response shape::

            {"scopes": [{"id": ..., "name": ..., "status": ...,
                         "evidence_valid": ..., "evidence_total": ...}]}
        """
        cursor = conn.execute(
            "SELECT id, name, status, evidence_valid, evidence_total FROM scopes"
        )
        rows = cursor.fetchall()
        scopes = [
            {
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "evidence_valid": row[3],
                "evidence_total": row[4],
            }
            for row in rows
        ]
        return jsonify({"scopes": scopes})

    @app.route("/db/api/evidence")
    def api_evidence() -> Response:
        """Return a paginated list of evidence rows, optionally filtered by a search term.

        Query parameters:
            page  (int, default 1)   — 1-based page number.
            limit (int, default 50)  — rows per page; capped at 50.
            q     (str, optional)    — substring to match against ``description``.
                                       Uses a parameterized LIKE query to prevent
                                       SQL injection.

        Response shape::

            {"evidence": [{<column>: <value>, ...}]}
        """
        page = max(1, int(request.args.get("page", 1)))
        limit = min(max(1, int(request.args.get("limit", 50))), 50)
        offset = (page - 1) * limit
        q = request.args.get("q", None)

        if q:
            sql = "SELECT * FROM evidence WHERE description LIKE ? LIMIT ? OFFSET ?"
            params: tuple = (f"%{q}%", limit, offset)
        else:
            sql = "SELECT * FROM evidence LIMIT ? OFFSET ?"
            params = (limit, offset)

        cursor = conn.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        evidence = [dict(zip(cols, row)) for row in rows]
        return jsonify({"evidence": evidence})

    @app.route("/db/api/schema")
    def api_schema() -> Response:
        """Return the database schema as a JSON object.

        Introspects ``sqlite_master`` for all tables, then uses SQLite PRAGMA
        statements to collect column definitions and foreign key relationships.

        Response shape::

            {
              "tables": [
                {
                  "name": "<table>",
                  "columns": [{"cid": ..., "name": ..., "type": ...,
                               "notnull": ..., "dflt_value": ..., "pk": ...}],
                  "foreign_keys": [{"id": ..., "seq": ..., "table": ...,
                                    "from": ..., "to": ...}]
                }
              ]
            }
        """
        tables_cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [row[0] for row in tables_cursor.fetchall()]

        tables = []
        for name in table_names:
            columns = _fetch_columns(conn, name)
            foreign_keys = _fetch_foreign_keys(conn, name)
            tables.append({"name": name, "columns": columns, "foreign_keys": foreign_keys})

        return jsonify({"tables": tables})

    return app
