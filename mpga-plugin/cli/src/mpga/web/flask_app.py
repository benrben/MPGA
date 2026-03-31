"""Minimal Flask app for the MPGA database dashboard.

**SECURITY WARNING:** This app exposes the entire SQLite database at localhost:5000/db.
Do NOT run this on a public network or use in production without proper access controls.
This is intended for local development and internal use only.

Implements create_db_app(conn) -> Flask with routes:
  GET /db                  — HTML dashboard shell (SPA)
  GET /db/api/scopes       — JSON list of scopes
  GET /db/api/evidence     — JSON paginated evidence (with optional ?q= search)
  GET /db/api/schema       — JSON database schema (tables + columns)

Usage:
  from mpga.db.connection import get_connection
  from mpga.web.flask_app import create_db_app

  conn = get_connection("path/to/.mpga/mpga.db")
  app = create_db_app(conn)
  app.run(debug=False, host="127.0.0.1", port=5000)
  # Then open browser to http://localhost:5000/db
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request


# ---------------------------------------------------------------------------
# Schema introspection helpers (Extract Function — Fowler)
# ---------------------------------------------------------------------------

# A valid SQLite identifier: letters, digits, and underscores only.
# This pattern is intentionally strict to prevent PRAGMA injection.
_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_table_name(table: str) -> None:
    """Raise ``ValueError`` if *table* is not a safe SQLite identifier.

    Rejects anything that is not composed solely of ASCII letters, digits,
    and underscores — the minimal set needed for valid table names.  This
    prevents PRAGMA injection via malformed table name strings.
    """
    if not _VALID_IDENTIFIER_RE.match(table):
        raise ValueError(
            f"Invalid table name {table!r}: table names must contain only "
            "letters, digits, and underscores."
        )


def _fetch_columns(conn: sqlite3.Connection, table: str, allowed_tables: set[str] | None = None) -> list[dict]:
    """Return column metadata for *table* using ``PRAGMA table_info``.

    Each entry contains: ``cid``, ``name``, ``type``, ``notnull``,
    ``dflt_value``, and ``pk``.

    Args:
        conn: SQLite connection
        table: Table name (validated against allowed_tables if provided)
        allowed_tables: Set of valid table names. Must be provided (not None);
            passing None raises ValueError to prevent accidental whitelist bypass.

    Raises:
        ValueError: If *allowed_tables* is None, if *table* is not in
            *allowed_tables*, or if *table* contains unsafe characters.
    """
    if allowed_tables is None:
        raise ValueError(
            "allowed_tables must be an explicit set of permitted table names. "
            "Passing None is not allowed — it would bypass the whitelist guard."
        )
    _validate_table_name(table)
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' is not in the allowed list")

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


def _fetch_foreign_keys(conn: sqlite3.Connection, table: str, allowed_tables: set[str] | None = None) -> list[dict]:
    """Return foreign key metadata for *table* using ``PRAGMA foreign_key_list``.

    Each entry contains: ``id``, ``seq``, ``table``, ``from``, and ``to``.

    Args:
        conn: SQLite connection
        table: Table name (validated against allowed_tables if provided)
        allowed_tables: Set of valid table names. Must be provided (not None);
            passing None raises ValueError to prevent accidental whitelist bypass.

    Raises:
        ValueError: If *allowed_tables* is None, if *table* is not in
            *allowed_tables*, or if *table* contains unsafe characters.
    """
    if allowed_tables is None:
        raise ValueError(
            "allowed_tables must be an explicit set of permitted table names. "
            "Passing None is not allowed — it would bypass the whitelist guard."
        )
    _validate_table_name(table)
    if table not in allowed_tables:
        raise ValueError(f"Table '{table}' is not in the allowed list")

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
    """Create and return a Flask app backed by the given SQLite connection.

    **IMPORTANT:** The provided connection must not be shared across threads.
    SQLite connections are not thread-safe. Use this app with a single-threaded
    WSGI server (e.g., Flask development server) or create a connection pool for
    multi-threaded use (e.g., Gunicorn with sync workers + connection pooling).
    """
    # Configure Flask to find templates in the correct directory
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    @app.route("/db")
    def dashboard() -> Response:
        """Return the HTML shell for the database dashboard SPA.

        Renders the db_dashboard.html template which provides the UI shell,
        navigation, and JavaScript for fetching data from the API routes.
        """
        return render_template("db_dashboard.html")

    @app.route("/db/api/scopes")
    def api_scopes() -> Response:
        """Return all project scopes as a JSON list.

        This endpoint queries the 'scopes' table and returns metadata about each
        scope including validation status and evidence counts.

        Returns:
            JSON response with shape:
                {"scopes": [
                    {"id": str, "name": str, "status": str,
                     "evidence_valid": int, "evidence_total": int},
                    ...
                ]}

        Status codes:
            200: Success
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
        """Return a paginated list of evidence rows, optionally filtered by search.

        Query parameters:
            page  (int, default 1)   — 1-based page number (1, 2, 3, ...)
            limit (int, default 50)  — rows per page (capped at 50 for safety)
            q     (str, optional)    — substring to search in description field.
                                       Uses parameterized LIKE query (SQL injection safe).

        Returns:
            JSON response with shape:
                {"evidence": [
                    {"raw": str, "type": str, "filepath": str,
                     "start_line": int, "end_line": int, "symbol": str|null,
                     "description": str, "confidence": float,
                     "scope_id": str, "created_at": str},
                    ...
                ]}

        Examples:
            GET /db/api/evidence?page=1&limit=50
            GET /db/api/evidence?page=2&limit=50
            GET /db/api/evidence?q=api&page=1
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
        """Return the database schema including tables, columns, and relationships.

        Dynamically introspects the SQLite database using sqlite_master and PRAGMA
        statements to discover all tables, their columns, and foreign key constraints.
        No hardcoded table names — the schema is fully discovered at runtime.

        Returns:
            JSON response with shape:
                {
                  "tables": [
                    {
                      "name": str,
                      "columns": [
                        {
                          "cid": int,           # column ID
                          "name": str,          # column name
                          "type": str,          # data type (TEXT, INTEGER, etc.)
                          "notnull": int,       # 1 = NOT NULL constraint
                          "dflt_value": str|null,  # default value
                          "pk": int             # 1 = primary key
                        },
                        ...
                      ],
                      "foreign_keys": [
                        {
                          "id": int,
                          "seq": int,           # constraint sequence
                          "table": str,         # referenced table
                          "from": str,          # local column
                          "to": str             # referenced column
                        },
                        ...
                      ]
                    }
                  ]
                }

        Examples:
            GET /db/api/schema
        """
        tables_cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        # Filter to only names that pass identifier validation — this excludes
        # any unusual internal tables and prevents _fetch_columns from raising.
        table_names = [
            row[0]
            for row in tables_cursor.fetchall()
            if _VALID_IDENTIFIER_RE.match(row[0])
        ]
        allowed_tables = set(table_names)

        tables = []
        for name in table_names:
            columns = _fetch_columns(conn, name, allowed_tables)
            foreign_keys = _fetch_foreign_keys(conn, name, allowed_tables)
            tables.append({"name": name, "columns": columns, "foreign_keys": foreign_keys})

        return jsonify({"tables": tables})

    return app
