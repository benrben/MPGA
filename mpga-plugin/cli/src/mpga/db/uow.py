"""Unit-of-work context manager for SQLite connections.

Wraps a connection with automatic commit on success and rollback on failure.
"""

from __future__ import annotations

import sqlite3
from types import TracebackType


class UnitOfWork:
    """Context manager that commits on clean exit and rolls back on exception.

    Usage::

        with UnitOfWork(conn) as uow:
            uow.conn.execute("INSERT ...")
        # auto-committed here

    If an exception propagates out of the ``with`` block the transaction
    is rolled back instead.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
