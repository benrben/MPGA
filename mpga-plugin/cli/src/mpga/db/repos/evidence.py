"""EvidenceRepo — CRUD + FTS5 for evidence links."""

from __future__ import annotations

import sqlite3

from mpga.evidence.parser import EvidenceLink, EvidenceStats


class EvidenceRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_link(self, row: tuple) -> EvidenceLink:
        (
            _id, raw, type_, filepath, start_line, end_line,
            symbol, symbol_type, description, confidence,
            stale_date, last_verified, _scope_id, _task_id,
        ) = row
        return EvidenceLink(
            raw=raw,
            type=type_,
            confidence=confidence if confidence is not None else 1.0,
            filepath=filepath,
            start_line=start_line,
            end_line=end_line,
            symbol=symbol,
            symbol_type=symbol_type,
            description=description,
            stale_date=stale_date,
            last_verified=last_verified,
        )

    def _sync_fts_insert(self, evidence_id: int) -> None:
        row = self._conn.execute(
            "SELECT id, raw, filepath, symbol, description FROM evidence WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return
        eid, raw, filepath, symbol, description = row
        self._conn.execute(
            "INSERT INTO evidence_fts(rowid, raw, filepath, symbol, description) VALUES (?, ?, ?, ?, ?)",
            (eid, raw or "", filepath or "", symbol or "", description or ""),
        )

    def _sync_fts_delete(self, evidence_id: int) -> None:
        # For FTS5 content tables, use the special 'delete' command.
        # The row must still exist in the backing table when this runs.
        row = self._conn.execute(
            "SELECT id, raw, filepath, symbol, description FROM evidence WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return
        eid, raw, filepath, symbol, description = row
        self._conn.execute(
            "INSERT INTO evidence_fts(evidence_fts, rowid, raw, filepath, symbol, description) "
            "VALUES ('delete', ?, ?, ?, ?, ?)",
            (eid, raw or "", filepath or "", symbol or "", description or ""),
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        link: EvidenceLink,
        scope_id: str | None,
        task_id: str | None,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO evidence
                (raw, type, filepath, start_line, end_line, symbol, symbol_type,
                 description, confidence, stale_date, last_verified, scope_id, task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link.raw,
                link.type,
                link.filepath,
                link.start_line,
                link.end_line,
                link.symbol,
                link.symbol_type,
                link.description,
                link.confidence,
                link.stale_date,
                link.last_verified,
                scope_id,
                task_id,
            ),
        )
        self._conn.commit()
        eid = cur.lastrowid
        self._sync_fts_insert(eid)
        self._conn.commit()
        return eid

    def get(self, evidence_id: int) -> EvidenceLink | None:
        row = self._conn.execute(
            """
            SELECT id, raw, type, filepath, start_line, end_line,
                   symbol, symbol_type, description, confidence,
                   stale_date, last_verified, scope_id, task_id
            FROM evidence WHERE id = ?
            """,
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_link(row)

    def delete(self, evidence_id: int) -> None:
        self._sync_fts_delete(evidence_id)
        self._conn.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
        self._conn.commit()

    def update_resolution(
        self,
        *,
        scope_id: str,
        original_raw: str,
        updated_link: EvidenceLink,
    ) -> None:
        row = self._conn.execute(
            "SELECT id FROM evidence WHERE scope_id = ? AND raw = ? ORDER BY id LIMIT 1",
            (scope_id, original_raw),
        ).fetchone()
        if row is None:
            return

        evidence_id = row[0]
        self._sync_fts_delete(evidence_id)
        self._conn.execute(
            """
            UPDATE evidence
            SET raw = ?, type = ?, filepath = ?, start_line = ?, end_line = ?,
                symbol = ?, symbol_type = ?, description = ?, confidence = ?,
                stale_date = ?, last_verified = ?
            WHERE id = ?
            """,
            (
                updated_link.raw,
                updated_link.type,
                updated_link.filepath,
                updated_link.start_line,
                updated_link.end_line,
                updated_link.symbol,
                updated_link.symbol_type,
                updated_link.description,
                updated_link.confidence,
                updated_link.stale_date,
                updated_link.last_verified,
                evidence_id,
            ),
        )
        self._conn.commit()
        self._sync_fts_insert(evidence_id)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def find(
        self,
        type: str | None = None,
        scope_id: str | None = None,
        filepath: str | None = None,
        limit: int = 100,
    ) -> list[EvidenceLink]:
        clauses = []
        params: list = []
        if type is not None:
            clauses.append("type = ?")
            params.append(type)
        if scope_id is not None:
            clauses.append("scope_id = ?")
            params.append(scope_id)
        if filepath is not None:
            clauses.append("filepath = ?")
            params.append(filepath)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT id, raw, type, filepath, start_line, end_line,
                   symbol, symbol_type, description, confidence,
                   stale_date, last_verified, scope_id, task_id
            FROM evidence {where} LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_link(r) for r in rows]

    def search(self, query: str, limit: int = 10) -> list[EvidenceLink]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.raw, e.type, e.filepath, e.start_line, e.end_line,
                   e.symbol, e.symbol_type, e.description, e.confidence,
                   e.stale_date, e.last_verified, e.scope_id, e.task_id
            FROM evidence_fts
            JOIN evidence e ON evidence_fts.rowid = e.id
            WHERE evidence_fts MATCH ?
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [self._row_to_link(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self, scope_id: str | None = None) -> EvidenceStats:
        if scope_id is not None:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN type='valid' THEN 1 ELSE 0 END) as valid,
                    SUM(CASE WHEN type='stale' THEN 1 ELSE 0 END) as stale,
                    SUM(CASE WHEN type='unknown' THEN 1 ELSE 0 END) as unknown,
                    SUM(CASE WHEN type='deprecated' THEN 1 ELSE 0 END) as deprecated
                FROM evidence WHERE scope_id = ?
                """,
                (scope_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN type='valid' THEN 1 ELSE 0 END) as valid,
                    SUM(CASE WHEN type='stale' THEN 1 ELSE 0 END) as stale,
                    SUM(CASE WHEN type='unknown' THEN 1 ELSE 0 END) as unknown,
                    SUM(CASE WHEN type='deprecated' THEN 1 ELSE 0 END) as deprecated
                FROM evidence
                """,
            ).fetchone()

        total, valid, stale, unknown, deprecated = row
        total = total or 0
        valid = valid or 0
        stale = stale or 0
        unknown = unknown or 0
        deprecated = deprecated or 0
        health_pct = 100 if total == 0 else round((valid / total) * 100)
        return EvidenceStats(
            total=total,
            valid=valid,
            stale=stale,
            unknown=unknown,
            deprecated=deprecated,
            health_pct=health_pct,
        )
