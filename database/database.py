# database.py

from config import AppConstants

import sqlite3
from abc import ABC
from contextlib import contextmanager
from typing import Optional



class Database(ABC):
    """
    Abstract base class for database operations.
    Provides common connection management functionality.
    """
    
    def __init__(self, db_name: str = AppConstants.database):
        self.db_name = db_name
        self._conn: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection property. Can be overridden in subclasses."""
        if self._conn is None:
            self._conn = self._create_connection()
        return self._conn
    
    @property
    def cursor(self) -> sqlite3.Cursor:
        """Lazy cursor property. Can be overridden in subclasses."""
        if self._cursor is None:
            self._cursor = self.conn.cursor()
        return self._cursor
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create and configure database connection."""
        conn = sqlite3.connect(self.db_name)
        self._configure_connection(conn)
        return conn
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Configure connection settings. Override in subclasses if needed."""
        pass
    
    @contextmanager
    def transaction(self):
        """Simple transaction context manager."""
        try:
            self.conn.execute("BEGIN")
            yield
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def close(self) -> None:
        """Close database connection and cursor."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()