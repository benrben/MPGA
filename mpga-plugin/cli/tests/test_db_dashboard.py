"""Unit tests for database dashboard Flask routes and API endpoints.

Coverage checklist for: T002 — Write Unit Tests for Flask Routes (RED Phase)

Acceptance criteria -> Test status
──────────────────────────────────
[ ] AC1: GET /db/api/scopes returns 200 with JSON list
         -> test_scopes_endpoint_returns_json
[ ] AC2: GET /db/api/evidence?page=1&limit=50 returns (at most) 50 items
         -> test_evidence_pagination_returns_50_items
[ ] AC3: GET /db/api/schema returns table definitions for all tables
         -> test_schema_introspection_returns_all_tables
[ ] AC4: GET /db returns HTML with <html> and <body> tags
         -> test_dashboard_html_loads
[ ] AC5: GET /db/api/evidence?q=test performs parameterized search
         -> test_evidence_search_parameterized

Untested branches / edge cases:
- [ ] Dashboard HTML includes <div id="content"> placeholder
- [ ] Scopes response fields: id, name, status, evidence_valid, evidence_total
- [ ] Schema response includes foreign key relationships
- [ ] Evidence search SQL-injection resistance (OWASP AC from acceptance criteria)
- [ ] /db/api/evidence with no params returns JSON (degenerate case)
- [ ] /db/api/scopes with empty DB returns empty list (degenerate)

Evidence: [Unknown] mpga.web.flask_app does not exist yet — this is the target module.
The existing stdlib server lives at mpga.commands.serve (http.server-based).
The Flask blueprint to be created: mpga/web/flask_app.py :: create_db_blueprint()
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from mpga.db.schema import create_schema

# Soft import: the module does not exist yet.  Tests will fail at the fixture
# level (not at collection time) with a clear message pointing green-dev to the
# missing implementation.
try:
    from mpga.web.flask_app import create_db_app
    _FLASK_APP_MISSING = False
except ImportError:
    create_db_app = None  # type: ignore[assignment]
    _FLASK_APP_MISSING = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn():
    """In-memory SQLite connection with full schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def client(db_conn):
    """Flask test client for the /db dashboard app, backed by an in-memory DB.

    Fails with a clear message until green-dev creates mpga/web/flask_app.py
    and implements create_db_app(conn) -> Flask.
    """
    if _FLASK_APP_MISSING:
        pytest.fail(
            "mpga.web.flask_app does not exist yet. "
            "green-dev: create mpga/web/flask_app.py and implement "
            "create_db_app(conn: sqlite3.Connection) -> Flask"
        )
    app = create_db_app(db_conn)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# TPP step 1: degenerate — does the app respond at all?
# ---------------------------------------------------------------------------


class TestDashboardRoutes:
    """Test dashboard HTML and navigation routes.

    Degenerate case first: a bare GET /db should return a 200 with an HTML
    document structure.  No data in the DB is required.
    """

    def test_dashboard_html_loads(self, client):
        """GET /db returns an HTML document with html and body tags."""
        # Arrange — empty DB, no setup required

        # Act
        response = client.get("/db")

        # Assert
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "<html" in body.lower()
        assert "<body" in body.lower()

    def test_dashboard_includes_content_placeholder(self, client):
        """Dashboard HTML includes a <div id='content'> mount point for the SPA."""
        # Arrange — no data needed (structural HTML test)

        # Act
        response = client.get("/db")

        # Assert
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'id="content"' in body or "id='content'" in body


# ---------------------------------------------------------------------------
# TPP step 2: constant -> variable — /db/api/scopes with empty DB returns list
# ---------------------------------------------------------------------------


class TestScopesEndpoint:
    """Test /db/api/scopes endpoint.

    Evidence: [Unknown] endpoint to be created at mpga/web/flask_app.py
    """

    def test_scopes_endpoint_returns_json(self, client):
        """GET /db/api/scopes returns 200 with a JSON object containing a 'scopes' list."""
        # Arrange — empty database; the list will just be empty

        # Act
        response = client.get("/db/api/scopes")

        # Assert
        assert response.status_code == 200
        assert response.content_type.startswith("application/json")
        payload = json.loads(response.data)
        assert "scopes" in payload
        assert isinstance(payload["scopes"], list)

    def test_scopes_includes_required_fields(self, client, db_conn):
        """Each scope object in the response contains id, name, status, evidence_valid, evidence_total."""
        # Arrange — seed one scope directly so the endpoint has data to return
        db_conn.execute(
            """
            INSERT INTO scopes
                (id, name, summary, status, evidence_total, evidence_valid, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("SC-core", "core", "Core module", "fresh", 5, 3, "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        db_conn.commit()

        # Act
        response = client.get("/db/api/scopes")

        # Assert
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert len(payload["scopes"]) == 1
        scope = payload["scopes"][0]
        for field in ("id", "name", "status", "evidence_valid", "evidence_total"):
            assert field in scope, f"Missing required field '{field}' in scope object"


# ---------------------------------------------------------------------------
# TPP step 3: selection — pagination boundary
# ---------------------------------------------------------------------------


class TestEvidenceEndpoint:
    """Test /db/api/evidence endpoint with pagination and search.

    Evidence: [Unknown] endpoint to be created at mpga/web/flask_app.py
    """

    def test_evidence_pagination_returns_50_items(self, client, db_conn):
        """GET /db/api/evidence?page=1&limit=50 returns at most 50 evidence items."""
        # Arrange — seed 60 evidence rows so pagination is exercised
        rows = [
            (
                f"[E] src/foo.py:{i}",
                "file",
                "src/foo.py",
                i,
                i,
                None,
                f"evidence item {i}",
                1.0,
                "SC-core",
                "2026-01-01T00:00:00",
            )
            for i in range(1, 61)
        ]
        db_conn.executemany(
            """
            INSERT INTO evidence
                (raw, type, filepath, start_line, end_line, symbol, description,
                 confidence, scope_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        db_conn.commit()

        # Act
        response = client.get("/db/api/evidence?page=1&limit=50")

        # Assert
        assert response.status_code == 200
        assert response.content_type.startswith("application/json")
        payload = json.loads(response.data)
        assert "evidence" in payload
        assert isinstance(payload["evidence"], list)
        assert len(payload["evidence"]) <= 50

    def test_evidence_search_parameterized(self, client, db_conn):
        """GET /db/api/evidence?q=test returns only evidence whose description contains 'test'."""
        # Arrange — seed two rows, only one should match
        db_conn.executemany(
            """
            INSERT INTO evidence
                (raw, type, filepath, start_line, end_line, symbol, description,
                 confidence, scope_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("[E] src/a.py:1", "file", "src/a.py", 1, 1, None, "test helper", 1.0, "SC-core", "2026-01-01T00:00:00"),
                ("[E] src/b.py:2", "file", "src/b.py", 2, 2, None, "unrelated fixture", 1.0, "SC-core", "2026-01-01T00:00:00"),
            ],
        )
        db_conn.commit()

        # Act
        response = client.get("/db/api/evidence?q=test")

        # Assert
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert "evidence" in payload
        descriptions = [item["description"] for item in payload["evidence"]]
        assert any("test" in (d or "").lower() for d in descriptions), (
            "Expected at least one evidence item matching 'test' in description"
        )
        assert all("unrelated" not in (d or "").lower() for d in descriptions), (
            "Non-matching evidence item 'unrelated fixture' should not appear in results"
        )

    def test_evidence_search_prevents_sql_injection(self, client, db_conn):
        """Evidence search using a SQL injection string prevents SQL injection bypass."""
        # Arrange — seed two rows: one matching 'safe' and one with 'unrelated' description
        db_conn.executemany(
            """
            INSERT INTO evidence
                (raw, type, filepath, start_line, end_line, symbol, description,
                 confidence, scope_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("[E] src/safe.py:10", "file", "src/safe.py", 10, 10, None,
                 "safe description", 1.0, "SC-core", "2026-01-01T00:00:00"),
                ("[E] src/unrelated.py:20", "file", "src/unrelated.py", 20, 20, None,
                 "unrelated description", 1.0, "SC-core", "2026-01-01T00:00:00"),
            ],
        )
        db_conn.commit()

        # Act — query with SQL injection attempt: the WHERE clause becomes
        # WHERE description LIKE '%' OR '1'='1%' — if parameterized, this is a literal string search
        injection_query = "' OR '1'='1"
        response = client.get(f"/db/api/evidence?q={injection_query}")

        # Assert — parameterized query should treat the injection as a literal string to search
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert "evidence" in payload
        # The injection query should match zero rows (not bypass the WHERE clause)
        assert len(payload["evidence"]) == 0, (
            "SQL injection query should not match any rows. "
            "If it returned rows, the query is not parameterized."
        )


# ---------------------------------------------------------------------------
# TPP step 4: collection — schema introspection
# ---------------------------------------------------------------------------


class TestSchemaEndpoint:
    """Test /db/api/schema endpoint.

    The schema endpoint exposes SQLite table definitions so the dashboard can
    render an entity-relationship view.

    Evidence: [Unknown] endpoint to be created at mpga/web/flask_app.py
    """

    def test_schema_introspection_returns_all_tables(self, client):
        """GET /db/api/schema returns a 'tables' list that includes the core MPGA tables."""
        # Arrange — schema is already applied by the db_conn fixture

        # Act
        response = client.get("/db/api/schema")

        # Assert
        assert response.status_code == 200
        assert response.content_type.startswith("application/json")
        payload = json.loads(response.data)
        assert "tables" in payload
        assert isinstance(payload["tables"], list)

        table_names = [t["name"] for t in payload["tables"]]
        for expected in ("scopes", "tasks", "evidence"):
            assert expected in table_names, (
                f"Expected core table '{expected}' in schema response, got: {table_names}"
            )

    def test_schema_includes_relationships(self, client):
        """GET /db/api/schema response includes foreign key information per table."""
        # Arrange — no additional data required

        # Act
        response = client.get("/db/api/schema")

        # Assert
        assert response.status_code == 200
        payload = json.loads(response.data)
        assert "tables" in payload
        # Each table entry must have at least a 'columns' key
        for table in payload["tables"]:
            assert "columns" in table, (
                f"Table '{table.get('name')}' is missing 'columns' key in schema response"
            )
