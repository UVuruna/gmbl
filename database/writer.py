# database_writer.py

from config import AppConstants
from database.database import Database
from logger import AviatorLogger

import sqlite3
import threading
from typing import Optional, Dict, List, Any


class DatabaseWriter(Database):
    """
    This class manages SQLite database operations for storing game data.
    Uses thread-local connections for thread safety.
    """
    
    def __init__(
        self,
        db_name: str = AppConstants.database
    ):
        super().__init__(db_name)
        self.lock = threading.Lock()
        self._local = threading.local()
        self.logger = AviatorLogger.get_logger("DatabaseWriter")
    
    @property 
    def conn(self):
        """Get thread-local connection with proper configuration."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_name)
            self._configure_connection(self._local.conn)
        return self._local.conn
    
    @property
    def cursor(self):
        """Get cursor for thread-local connection."""
        if not hasattr(self._local, 'cursor'):
            self._local.cursor = self.conn.cursor()
        return self._local.cursor
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Configure connection for optimal write performance."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA cache_size = -64000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA mmap_size = 268435456")
        conn.commit()
    
    def insert_round(self, data: Dict[str, Any]) -> Optional[int]:
        """Insert a new round of data into the database."""
        try:
            with self.lock:
                with self.transaction():
                    self._validate_round_data(data)
                    
                    round_id = self._insert_main_round(data['main'])
                    self._insert_snapshots(round_id, data.get('snapshots', []))
                    self._insert_earnings(round_id, data['earnings'])
                    
                    self.logger.debug(f"Inserted round {round_id} for {data['main']['bookmaker']}")
                    return round_id
                    
        except Exception as e:
            self.logger.error(f"Insert error: {e}", exc_info=True)
            return None
    
    def _validate_round_data(self, data: Dict[str, Any]) -> None:
        """Validate the structure and content of round data."""
        required_keys = ['main', 'earnings']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        
        main_required = ['bookmaker', 'score', 'total_win', 'total_players']
        for key in main_required:
            if key not in data['main']:
                raise ValueError(f"Missing required key in main data: {key}")
        
        earnings_required = ['bet_amount', 'auto_stop', 'balance']
        for key in earnings_required:
            if key not in data['earnings']:
                raise ValueError(f"Missing required key in earnings data: {key}")
    
    def _insert_main_round(self, main_data: Dict[str, Any]) -> int:
        """Insert main round data and return the round ID."""
        self.cursor.execute("""
            INSERT INTO rounds (bookmaker, score, total_win, total_players)
            VALUES (?, ?, ?, ?)
        """, (
            main_data['bookmaker'],
            main_data['score'],
            main_data['total_win'],
            main_data['total_players']
        ))
        
        round_id = self.cursor.lastrowid
        if round_id is None:
            raise sqlite3.Error("Failed to get round ID after insert")
        
        return round_id
    
    def _insert_snapshots(self, round_id: int, snapshots_data: List[Dict[str, Any]]) -> None:
        """Insert snapshot data for the round."""
        if not snapshots_data:
            return
        
        snapshots = [
            (round_id, snapshot['current_score'], 
             snapshot['current_players'], snapshot['current_players_win'])
            for snapshot in snapshots_data
        ]
        
        self.cursor.executemany("""
            INSERT INTO snapshots (round_ID, current_score, current_players, current_players_win)
            VALUES (?, ?, ?, ?)
        """, snapshots)
        
        self.logger.debug(f"Inserted {len(snapshots)} snapshots for round {round_id}")
    
    def _insert_earnings(self, round_id: int, earnings_data: Dict[str, Any]) -> None:
        """Insert earnings data for the round."""
        self.cursor.execute("""
            INSERT INTO earnings (round_ID, bet_amount, auto_stop, balance)
            VALUES (?, ?, ?, ?)
        """, (
            round_id,
            earnings_data['bet_amount'],
            earnings_data['auto_stop'],
            earnings_data['balance']
        ))
    
    def insert_batch_rounds(self, rounds_data: List[Dict[str, Any]]) -> List[Optional[int]]:
        """Insert multiple rounds in a single transaction."""
        round_ids = []
        
        try:
            with self.lock:
                with self.transaction():
                    for round_data in rounds_data:
                        try:
                            self._validate_round_data(round_data)
                            round_id = self._insert_main_round(round_data['main'])
                            self._insert_snapshots(round_id, round_data.get('snapshots', []))
                            self._insert_earnings(round_id, round_data['earnings'])
                            round_ids.append(round_id)
                        except Exception as e:
                            self.logger.error(f"Error inserting individual round: {e}")
                            round_ids.append(None)
                    
                    self.logger.info(f"Batch insert: {len([r for r in round_ids if r])}/{len(rounds_data)} successful")
                            
        except Exception as e:
            self.logger.error(f"Batch insert error: {e}", exc_info=True)
            round_ids = [None] * len(rounds_data)
        
        return round_ids
    
    def close(self) -> None:
        """Close thread-local connections."""
        if hasattr(self._local, 'cursor') and self._local.cursor:
            self._local.cursor.close()
            delattr(self._local, 'cursor')
        
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            delattr(self._local, 'conn')
        
        self.logger.debug("Database writer closed")