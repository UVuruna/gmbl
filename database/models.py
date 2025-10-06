# database/models.py
# VERSION: 5.0 - Database schemas for all three applications
# Separate databases: main_game_data, rgb_training_data, betting_history

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from logger import AviatorLogger


class DatabaseModel:
    """Base database model with common functionality."""
    
    def __init__(self, db_path: Path, db_name: str):
        self.db_path = db_path
        self.db_name = db_name
        self.logger = AviatorLogger.get_logger(f"DB-{db_name}")
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimizations."""
        conn = sqlite3.connect(self.db_path)
        
        # Apply pragma optimizations
        cursor = conn.cursor()
        for pragma in config.database.pragma_statements:
            cursor.execute(pragma)
        
        return conn
    
    def execute_script(self, script: str) -> None:
        """Execute SQL script."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.executescript(script)
            conn.commit()
            self.logger.info("Script executed successfully")
        except Exception as e:
            self.logger.error(f"Script execution error: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        
        result = cursor.fetchone() is not None
        conn.close()
        
        return result
    
    def get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count


class MainGameDatabase(DatabaseModel):
    """
    Main game data database.
    
    Tables:
    - rounds: Complete round data (end of round)
    - threshold_scores: Score snapshots at thresholds
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        final_score REAL,
        total_players INTEGER,
        left_players INTEGER,
        total_money REAL,
        duration_seconds REAL,
        
        CONSTRAINT chk_score CHECK (final_score >= 1.0),
        CONSTRAINT chk_players CHECK (total_players >= 0)
    );
    
    CREATE INDEX IF NOT EXISTS idx_rounds_bookmaker 
    ON rounds(bookmaker, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_rounds_score 
    ON rounds(final_score);
    
    -- Threshold data table
    CREATE TABLE IF NOT EXISTS threshold_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        threshold REAL NOT NULL,
        current_players INTEGER,
        current_money REAL,
        
        CONSTRAINT chk_threshold CHECK (threshold > 1.0)
    );
    
    CREATE INDEX IF NOT EXISTS idx_threshold_bookmaker 
    ON threshold_scores(bookmaker, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_threshold_value 
    ON threshold_scores(threshold);
    
    -- Statistics view
    CREATE VIEW IF NOT EXISTS round_statistics AS
    SELECT 
        bookmaker,
        COUNT(*) as total_rounds,
        AVG(final_score) as avg_score,
        MIN(final_score) as min_score,
        MAX(final_score) as max_score,
        AVG(total_players) as avg_players,
        AVG(total_money) as avg_money
    FROM rounds
    GROUP BY bookmaker;
    """
    
    def __init__(self):
        super().__init__(config.paths.main_game_db, "MainGame")
    
    def initialize(self) -> None:
        """Create tables if they don't exist."""
        self.logger.info("Initializing main game database...")
        self.execute_script(self.SCHEMA)
        self.logger.info("Main game database ready")
    
    def insert_round(
        self,
        bookmaker: str,
        final_score: float,
        total_players: Optional[int] = None,
        left_players: Optional[int] = None,
        total_money: Optional[float] = None,
        duration_seconds: Optional[float] = None
    ) -> int:
        """Insert a single round record."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rounds 
            (bookmaker, timestamp, final_score, total_players, left_players, 
             total_money, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            bookmaker,
            datetime.now().isoformat(),
            final_score,
            total_players,
            left_players,
            total_money,
            duration_seconds
        ))
        
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return row_id
    
    def batch_insert_rounds(self, rounds: List[dict]) -> int:
        """Batch insert round records."""
        if not rounds:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO rounds 
            (bookmaker, timestamp, final_score, total_players, left_players, 
             total_money, duration_seconds)
            VALUES 
            (:bookmaker, :timestamp, :final_score, :total_players, :left_players,
             :total_money, :duration_seconds)
        """, rounds)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def batch_insert_thresholds(self, thresholds: List[dict]) -> int:
        """Batch insert threshold records."""
        if not thresholds:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO threshold_scores 
            (bookmaker, timestamp, threshold, current_players, current_money)
            VALUES 
            (:bookmaker, :timestamp, :threshold, :current_players, :current_money)
        """, thresholds)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count


class RGBTrainingDatabase(DatabaseModel):
    """
    RGB training data database.
    
    Tables:
    - phase_rgb: RGB samples from phase region
    - button_rgb: RGB samples from button region
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS phase_rgb (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        r_avg REAL NOT NULL,
        g_avg REAL NOT NULL,
        b_avg REAL NOT NULL,
        r_std REAL,
        g_std REAL,
        b_std REAL,
        label TEXT,
        
        CONSTRAINT chk_rgb_range CHECK (
            r_avg >= 0 AND r_avg <= 255 AND
            g_avg >= 0 AND g_avg <= 255 AND
            b_avg >= 0 AND b_avg <= 255
        )
    );
    
    CREATE INDEX IF NOT EXISTS idx_phase_bookmaker 
    ON phase_rgb(bookmaker, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_phase_label 
    ON phase_rgb(label);
    
    -- Button RGB table
    CREATE TABLE IF NOT EXISTS button_rgb (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        r_avg REAL NOT NULL,
        g_avg REAL NOT NULL,
        b_avg REAL NOT NULL,
        r_std REAL,
        g_std REAL,
        b_std REAL,
        label TEXT,
        
        CONSTRAINT chk_rgb_range CHECK (
            r_avg >= 0 AND r_avg <= 255 AND
            g_avg >= 0 AND g_avg <= 255 AND
            b_avg >= 0 AND b_avg <= 255
        )
    );
    
    CREATE INDEX IF NOT EXISTS idx_button_bookmaker 
    ON button_rgb(bookmaker, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_button_label 
    ON button_rgb(label);
    
    -- Sample statistics view
    CREATE VIEW IF NOT EXISTS rgb_statistics AS
    SELECT 
        'phase' as region_type,
        COUNT(*) as total_samples,
        COUNT(DISTINCT label) as unique_labels,
        AVG(r_avg) as avg_red,
        AVG(g_avg) as avg_green,
        AVG(b_avg) as avg_blue
    FROM phase_rgb
    UNION ALL
    SELECT 
        'button' as region_type,
        COUNT(*) as total_samples,
        COUNT(DISTINCT label) as unique_labels,
        AVG(r_avg) as avg_red,
        AVG(g_avg) as avg_green,
        AVG(b_avg) as avg_blue
    FROM button_rgb;
    """
    
    def __init__(self):
        super().__init__(config.paths.rgb_training_db, "RGBTraining")
    
    def initialize(self) -> None:
        """Create tables if they don't exist."""
        self.logger.info("Initializing RGB training database...")
        self.execute_script(self.SCHEMA)
        self.logger.info("RGB training database ready")
    
    def batch_insert_phase_rgb(self, samples: List[dict]) -> int:
        """Batch insert phase RGB samples."""
        if not samples:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO phase_rgb 
            (bookmaker, timestamp, r_avg, g_avg, b_avg, r_std, g_std, b_std, label)
            VALUES 
            (:bookmaker, :timestamp, :r_avg, :g_avg, :b_avg, 
             :r_std, :g_std, :b_std, :label)
        """, samples)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def batch_insert_button_rgb(self, samples: List[dict]) -> int:
        """Batch insert button RGB samples."""
        if not samples:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO button_rgb 
            (bookmaker, timestamp, r_avg, g_avg, b_avg, r_std, g_std, b_std, label)
            VALUES 
            (:bookmaker, :timestamp, :r_avg, :g_avg, :b_avg, 
             :r_std, :g_std, :b_std, :label)
        """, samples)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def update_labels(self, table: str, label_mapping: dict) -> int:
        """
        Update labels in bulk (after clustering).
        
        Args:
            table: 'phase_rgb' or 'button_rgb'
            label_mapping: {id: label}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = [(label, id_) for id_, label in label_mapping.items()]
        
        cursor.executemany(
            f"UPDATE {table} SET label = ? WHERE id = ?",
            updates
        )
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count


class BettingHistoryDatabase(DatabaseModel):
    """
    Betting history database.
    
    Tables:
    - bets: All placed bets with results
    - sessions: Betting sessions (start/stop times)
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        session_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        bet_amount REAL NOT NULL,
        auto_stop REAL,
        final_score REAL,
        money_before REAL,
        money_after REAL,
        profit REAL,
        status TEXT,
        
        CONSTRAINT chk_bet_amount CHECK (bet_amount > 0),
        CONSTRAINT chk_auto_stop CHECK (auto_stop IS NULL OR auto_stop > 1.0),
        CONSTRAINT chk_status CHECK (status IN ('WIN', 'LOSS', 'PENDING', 'ERROR'))
    );
    
    CREATE INDEX IF NOT EXISTS idx_bets_bookmaker 
    ON bets(bookmaker, timestamp DESC);
    
    CREATE INDEX IF NOT EXISTS idx_bets_session 
    ON bets(session_id);
    
    CREATE INDEX IF NOT EXISTS idx_bets_status 
    ON bets(status);
    
    -- Sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker TEXT NOT NULL,
        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        end_time DATETIME,
        starting_balance REAL,
        ending_balance REAL,
        total_bets INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        total_losses INTEGER DEFAULT 0,
        net_profit REAL DEFAULT 0,
        strategy TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_sessions_bookmaker 
    ON sessions(bookmaker, start_time DESC);
    
    -- Betting statistics view
    CREATE VIEW IF NOT EXISTS betting_statistics AS
    SELECT 
        bookmaker,
        COUNT(*) as total_bets,
        SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status = 'LOSS' THEN 1 ELSE 0 END) as losses,
        ROUND(100.0 * SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
        SUM(profit) as total_profit,
        AVG(profit) as avg_profit,
        AVG(bet_amount) as avg_bet_amount,
        MAX(profit) as max_win,
        MIN(profit) as max_loss
    FROM bets
    WHERE status IN ('WIN', 'LOSS')
    GROUP BY bookmaker;
    """
    
    def __init__(self):
        super().__init__(config.paths.betting_history_db, "BettingHistory")
    
    def initialize(self) -> None:
        """Create tables if they don't exist."""
        self.logger.info("Initializing betting history database...")
        self.execute_script(self.SCHEMA)
        self.logger.info("Betting history database ready")
    
    def create_session(
        self,
        bookmaker: str,
        starting_balance: float,
        strategy: str
    ) -> int:
        """Create a new betting session."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions 
            (bookmaker, start_time, starting_balance, strategy)
            VALUES (?, ?, ?, ?)
        """, (bookmaker, datetime.now().isoformat(), starting_balance, strategy))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def close_session(
        self,
        session_id: int,
        ending_balance: float
    ) -> None:
        """Close a betting session."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Calculate statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(profit) as net_profit
            FROM bets
            WHERE session_id = ?
        """, (session_id,))
        
        stats = cursor.fetchone()
        
        # Update session
        cursor.execute("""
            UPDATE sessions 
            SET end_time = ?,
                ending_balance = ?,
                total_bets = ?,
                total_wins = ?,
                total_losses = ?,
                net_profit = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            ending_balance,
            stats[0],
            stats[1],
            stats[2],
            stats[3],
            session_id
        ))
        
        conn.commit()
        conn.close()
    
    def batch_insert_bets(self, bets: List[dict]) -> int:
        """Batch insert bet records."""
        if not bets:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO bets 
            (bookmaker, session_id, timestamp, bet_amount, auto_stop, 
             final_score, money_before, money_after, profit, status)
            VALUES 
            (:bookmaker, :session_id, :timestamp, :bet_amount, :auto_stop,
             :final_score, :money_before, :money_after, :profit, :status)
        """, bets)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count


def initialize_all_databases():
    """Initialize all three databases."""
    print("\n" + "="*60)
    print("INITIALIZING ALL DATABASES")
    print("="*60)
    
    # Main game data
    print("\n1. Main Game Data Database...")
    main_db = MainGameDatabase()
    main_db.initialize()
    print(f"   ✅ {main_db.db_path}")
    
    # RGB training data
    print("\n2. RGB Training Data Database...")
    rgb_db = RGBTrainingDatabase()
    rgb_db.initialize()
    print(f"   ✅ {rgb_db.db_path}")
    
    # Betting history
    print("\n3. Betting History Database...")
    betting_db = BettingHistoryDatabase()
    betting_db.initialize()
    print(f"   ✅ {betting_db.db_path}")
    
    print("\n" + "="*60)
    print("✅ ALL DATABASES INITIALIZED")
    print("="*60)


if __name__ == "__main__":
    initialize_all_databases()