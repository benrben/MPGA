"""MPGA Python SDK for agent access to the knowledge base.

This module enables agents and other Python processes to directly query and update
MPGA scopes without needing CLI access. Agents can import this instead of shelling out.

Example:
    from mpga.bridge.sdk import MpgaClient
    from pathlib import Path

    client = MpgaClient(project_root=Path.cwd())

    # List all scopes
    scopes = client.list_scopes()
    for scope in scopes:
        print(f"{scope.id}: {scope.summary}")

    # Get a specific scope
    scope = client.get_scope("mpga-plugin")
    print(scope.content)

    # Update a scope with enriched content
    scope.content = "# Updated content..."
    scope.status = "enriched"
    client.update_scope(scope)
"""

from __future__ import annotations

from pathlib import Path

from mpga.db.connection import get_connection
from mpga.db.repos.scopes import Scope, ScopeRepo
from mpga.db.schema import create_schema


class MpgaClient:
    """Direct Python access to MPGA knowledge base without CLI overhead."""

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the MPGA client.

        Args:
            project_root: Path to the project root. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.db_path = str(self.project_root / ".mpga" / "mpga.db")
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure the database exists and is properly initialized."""
        conn = get_connection(self.db_path)
        try:
            create_schema(conn)
        finally:
            conn.close()

    def _get_repo(self) -> tuple[object, ScopeRepo]:
        """Get a scope repository with open connection."""
        conn = get_connection(self.db_path)
        return conn, ScopeRepo(conn)

    def list_scopes(self) -> list[Scope]:
        """Get all scopes.

        Returns:
            List of Scope objects ordered by ID.
        """
        conn, repo = self._get_repo()
        try:
            return repo.list_all()
        finally:
            conn.close()

    def get_scope(self, scope_id: str) -> Scope | None:
        """Get a single scope by ID.

        Args:
            scope_id: The scope identifier.

        Returns:
            Scope object or None if not found.
        """
        conn, repo = self._get_repo()
        try:
            return repo.get(scope_id)
        finally:
            conn.close()

    def create_scope(
        self,
        scope_id: str,
        name: str,
        summary: str | None = None,
        content: str | None = None,
        status: str = "fresh",
    ) -> Scope:
        """Create a new scope.

        Args:
            scope_id: Unique identifier for the scope.
            name: Display name for the scope.
            summary: Brief description (extracted from content if not provided).
            content: Full markdown content of the scope.
            status: Status flag ('fresh', 'enriched', etc).

        Returns:
            The created Scope object.
        """
        scope = Scope(
            id=scope_id,
            name=name,
            summary=summary,
            content=content,
            status=status,
        )
        conn, repo = self._get_repo()
        try:
            return repo.create(scope)
        finally:
            conn.close()

    def update_scope(self, scope: Scope) -> Scope:
        """Update an existing scope.

        Args:
            scope: The Scope object with updated fields.

        Returns:
            The updated Scope object with timestamps.
        """
        conn, repo = self._get_repo()
        try:
            return repo.update(scope)
        finally:
            conn.close()

    def delete_scope(self, scope_id: str) -> None:
        """Delete a scope by ID.

        Args:
            scope_id: The scope identifier.
        """
        conn, repo = self._get_repo()
        try:
            repo.delete(scope_id)
        finally:
            conn.close()

    def search_scopes(
        self,
        query: str,
        limit: int = 10,
        scope_id: str | None = None,
    ) -> list[tuple[Scope, str]]:
        """Search scopes using full-text search.

        Args:
            query: Search terms.
            limit: Maximum results to return.
            scope_id: Optional scope to limit search to.

        Returns:
            List of (Scope, snippet) tuples ranked by relevance.
        """
        conn, repo = self._get_repo()
        try:
            return repo.search(query, limit=limit, scope_id=scope_id)
        finally:
            conn.close()
