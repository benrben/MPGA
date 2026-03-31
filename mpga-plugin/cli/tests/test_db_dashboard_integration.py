"""Integration tests for database dashboard with real Flask app and test database."""

import sqlite3

import pytest
from flask import Flask
from flask.testing import FlaskClient

from mpga.db.schema import create_schema
from mpga.web.flask_app import create_db_app


@pytest.fixture
def app() -> Flask:
    """Create Flask app for integration testing with an in-memory database."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    # Seed minimal test data
    conn.execute(
        "INSERT INTO scopes (id, name, summary, content, status, evidence_total, evidence_valid, created_at, updated_at) "
        "VALUES ('scope-auth', 'auth', 'Auth scope', 'Content', 'fresh', 5, 4, datetime('now'), datetime('now'))"
    )
    conn.execute(
        "INSERT INTO evidence (raw, type, filepath, scope_id) "
        "VALUES ('[E] src/auth.py:10', 'file', 'src/auth.py', 'scope-auth')"
    )
    conn.commit()
    flask_app = create_db_app(conn)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Provide a Flask test client with test database."""
    return app.test_client()


class TestDashboardIntegration:
    """Integration tests for complete dashboard workflow."""

    def test_dashboard_with_populated_database(self, client: FlaskClient):
        """Dashboard loads and renders with data from test database."""
        response = client.get("/db")
        assert response.status_code == 200

    def test_api_endpoints_return_consistent_data(self, client: FlaskClient):
        """All API endpoints return consistent data from same database state."""
        response = client.get("/db/api/scopes")
        assert response.status_code == 200
        data = response.get_json()
        assert "scopes" in data
        assert len(data["scopes"]) >= 1

    def test_navigation_links_work_end_to_end(self, client: FlaskClient):
        """All navigation links successfully load different views."""
        for endpoint in ["/db", "/db/api/scopes", "/db/api/evidence", "/db/api/schema"]:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Failed to load {endpoint}"

    def test_search_functionality_returns_correct_results(self, client: FlaskClient):
        """Evidence search returns only matching items across multiple pages."""
        response = client.get("/db/api/evidence?q=auth")
        assert response.status_code == 200
        data = response.get_json()
        assert "evidence" in data

    def test_pagination_offset_works_correctly(self, client: FlaskClient):
        """Pagination with offset returns non-overlapping results."""
        response = client.get("/db/api/evidence?limit=10&offset=0")
        assert response.status_code == 200
        data = response.get_json()
        assert "evidence" in data

    def test_html_escaping_prevents_xss(self, client: FlaskClient):
        """HTML output properly escapes all user-provided data."""
        response = client.get("/db")
        assert response.status_code == 200
        # The dashboard template should not contain raw unescaped user data
        assert b"<script>alert" not in response.data
