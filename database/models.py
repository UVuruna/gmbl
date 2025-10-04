# database_creator.py

from config import AppConstants
from database.database import Database
from logger import AviatorLogger

import sqlite3


class DatabaseCreator(Database):
    """
    This class manages SQLite database table creation.
    """
    
    # Table schemas as class constants
    TABLE_SCHEMAS = {
        'rounds': """
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                bookmaker TEXT NOT NULL,
                score REAL,
                total_win REAL,
                total_players INTEGER,
                CHECK (score > 0),
                CHECK (total_win >= 0),
                CHECK (total_players >= 0)
            )
        """,
        'snapshots': """
            CREATE TABLE IF NOT EXISTS snapshots (
                round_ID INTEGER NOT NULL,
                current_score REAL NOT NULL,
                current_players INTEGER,
                current_players_win REAL,
                PRIMARY KEY (round_ID, current_score),
                FOREIGN KEY (round_ID) REFERENCES rounds(id) ON DELETE CASCADE,
                CHECK (current_score > 0),
                CHECK (current_players >= 0),
                CHECK (current_players_win >= 0)
            )
        """,
        'earnings': """
            CREATE TABLE IF NOT EXISTS earnings (
                round_ID INTEGER PRIMARY KEY,
                bet_amount REAL NOT NULL,
                auto_stop REAL NOT NULL,
                balance REAL NOT NULL,
                FOREIGN KEY (round_ID) REFERENCES rounds(id) ON DELETE CASCADE,
                CHECK (bet_amount > 0),
                CHECK (auto_stop > 0),
                CHECK (balance >= 0)
            )
        """
    }
    
    # Empty because Insert speed is prioritized over read speed.
    INDEXES = [] 

    def __init__(self, db_name: str = AppConstants.database):
        super().__init__(db_name)
        self.logger = AviatorLogger.get_logger("DatabaseCreator")
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Configure connection for table creation."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        conn.commit()
    
    def create_tables(self) -> None:
        """Create all necessary tables if they do not exist."""
        try:
            with self.transaction():
                # Create tables
                for table_name, schema in self.TABLE_SCHEMAS.items():
                    self._create_single_table(table_name, schema)
                
                # Create indexes
                for index_sql in self.INDEXES:
                    self.cursor.execute(index_sql)
                    
            self.logger.info(f"All database tables ({len(self.TABLE_SCHEMAS)}) and indexes ({len(self.INDEXES)}) created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}", exc_info=True)
            raise
    
    def _create_single_table(self, table_name: str, schema: str) -> None:
        """Create a single table with given schema."""
        self.cursor.execute(schema)
        self.logger.debug(f"Table '{table_name}' created or verified")
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        return self.cursor.fetchone() is not None