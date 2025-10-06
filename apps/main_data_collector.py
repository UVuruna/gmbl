# apps/main_data_collector.py
# VERSION: 1.0
# PROGRAM 1: Main game data collection
# Collects: score, total_players, left_players, total_money, threshold data

import sys
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from multiprocessing import Process, Queue
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.base_app import BaseAviatorApp, get_number_input
from core.screen_reader import ScreenReader
from regions.score import Score
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.game_phase import GamePhaseDetector
from logger import AviatorLogger


class MainDataCollector(BaseAviatorApp):
    """
    Main data collector application.
    
    Collects:
    - End of round: score, total_players, left_players, total_money
    - During round: score at thresholds (1.5x, 2.0x, 3.0x, 5.0x, 10.0x)
    """
    
    DATABASE_NAME = "main_game_data.db"
    SCORE_THRESHOLDS = [1.5, 2.0, 3.0, 5.0, 10.0]
    
    def __init__(self):
        super().__init__("MainDataCollector")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def setup_database(self):
        """Create database tables."""
        self.logger.info("Setting up database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main rounds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                final_score REAL,
                total_players INTEGER,
                left_players INTEGER,
                total_money REAL
            )
        ''')
        
        # Threshold data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threshold_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                threshold REAL NOT NULL,
                current_players INTEGER,
                current_money REAL
            )
        ''')
        
        # Index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_rounds_bookmaker 
            ON rounds(bookmaker, timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_threshold_bookmaker 
            ON threshold_scores(bookmaker, timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Database ready: {self.db_path}")
    
    def create_process(
        self, 
        bookmaker: str,
        layout: str,
        position: str,
        coords: Dict,
        **kwargs
    ) -> Optional[Process]:
        """Create collector process for bookmaker."""
        process = CollectorProcess(
            bookmaker_name=bookmaker,
            coords=coords,
            db_path=self.db_path,
            shutdown_event=self.shutdown_event
        )
        return process
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("🎰 MAIN DATA COLLECTOR v1.0")
        print("="*60)
        print("\nCollects:")
        print("  • Final score, players, money at round end")
        print("  • Score snapshots at thresholds (1.5x, 2x, 3x, 5x, 10x)")
        print("="*60)
        
        # Setup database
        self.setup_database()
        
        # Get number of bookmakers
        num_bookmakers = get_number_input(
            "\nHow many bookmakers to track? (1-6): ", 1, 6
        )
        
        # Setup bookmakers
        bookmakers_config = self.setup_bookmakers_interactive(num_bookmakers)
        
        # Verify regions
        if not self.verify_regions(bookmakers_config):
            return
        
        # Start processes
        self.start_processes(bookmakers_config)
        
        # Wait
        print("\n📊 Collecting data... (Ctrl+C to stop)")
        self.wait_for_processes()


class CollectorProcess(Process):
    """Worker process for one bookmaker."""
    
    BATCH_SIZE = 50
    COLLECTION_INTERVAL = 0.2
    
    def __init__(
        self, 
        bookmaker_name: str,
        coords: Dict,
        db_path: Path,
        shutdown_event
    ):
        super().__init__(name=f"MainCollector-{bookmaker_name}")
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.db_path = db_path
        self.shutdown_event = shutdown_event
        
        # Data queues
        self.rounds_queue = Queue(maxsize=1000)
        self.thresholds_queue = Queue(maxsize=1000)
    
    def setup_readers(self):
        """Setup screen readers."""
        self.score_reader = ScreenReader(self.coords['score_region'])
        self.other_count_reader = ScreenReader(self.coords['other_count_region'])
        self.other_money_reader = ScreenReader(self.coords['other_money_region'])
        self.phase_reader = ScreenReader(self.coords['phase_region'])
        
        self.score = Score(self.score_reader)
        self.other_count = OtherCount(self.other_count_reader)
        self.other_money = OtherMoney(self.other_money_reader)
        self.phase_detector = GamePhaseDetector(self.phase_reader)
    
    def collect_round_data(self):
        """Main collection loop."""
        logger = AviatorLogger.get_logger(f"Collector-{self.bookmaker_name}")
        
        last_phase = None
        threshold_tracker = {t: False for t in MainDataCollector.SCORE_THRESHOLDS}
        
        while not self.shutdown_event.is_set():
            try:
                # Detect phase
                current_phase = self.phase_detector.get_phase()
                
                # Read data
                score_value = self.score.read_score()
                player_count = self.other_count.read_count()
                total_money = self.other_money.read_money()
                
                # Phase change: FLYING -> WAITING = round end
                if last_phase == 'FLYING' and current_phase == 'WAITING':
                    # Save round data
                    self.rounds_queue.put({
                        'bookmaker': self.bookmaker_name,
                        'timestamp': datetime.now().isoformat(),
                        'final_score': score_value,
                        'total_players': player_count,
                        'left_players': None,  # TODO: Implement if needed
                        'total_money': total_money
                    })
                    
                    # Reset threshold tracker
                    threshold_tracker = {t: False for t in MainDataCollector.SCORE_THRESHOLDS}
                    
                    logger.info(
                        f"Round ended: {score_value:.2f}x, "
                        f"Players: {player_count}, Money: {total_money:.2f}"
                    )
                
                # During FLYING: Check thresholds
                elif current_phase == 'FLYING' and score_value:
                    for threshold in MainDataCollector.SCORE_THRESHOLDS:
                        if not threshold_tracker[threshold] and score_value >= threshold:
                            self.thresholds_queue.put({
                                'bookmaker': self.bookmaker_name,
                                'timestamp': datetime.now().isoformat(),
                                'threshold': threshold,
                                'current_players': player_count,
                                'current_money': total_money
                            })
                            threshold_tracker[threshold] = True
                            logger.debug(f"Threshold {threshold}x reached")
                
                last_phase = current_phase
                
                # Batch insert check
                if self.rounds_queue.qsize() >= self.BATCH_SIZE:
                    self.batch_insert_rounds()
                if self.thresholds_queue.qsize() >= self.BATCH_SIZE:
                    self.batch_insert_thresholds()
                
                time.sleep(self.COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Collection error: {e}", exc_info=True)
                time.sleep(1)
        
        # Final batch inserts
        self.batch_insert_rounds()
        self.batch_insert_thresholds()
    
    def batch_insert_rounds(self):
        """Batch insert round data."""
        if self.rounds_queue.empty():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch = []
        while not self.rounds_queue.empty() and len(batch) < self.BATCH_SIZE:
            try:
                batch.append(self.rounds_queue.get_nowait())
            except:
                break
        
        if batch:
            cursor.executemany('''
                INSERT INTO rounds 
                (bookmaker, timestamp, final_score, total_players, left_players, total_money)
                VALUES (:bookmaker, :timestamp, :final_score, :total_players, :left_players, :total_money)
            ''', batch)
            
            conn.commit()
        
        conn.close()
    
    def batch_insert_thresholds(self):
        """Batch insert threshold data."""
        if self.thresholds_queue.empty():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch = []
        while not self.thresholds_queue.empty() and len(batch) < self.BATCH_SIZE:
            try:
                batch.append(self.thresholds_queue.get_nowait())
            except:
                break
        
        if batch:
            cursor.executemany('''
                INSERT INTO threshold_scores 
                (bookmaker, timestamp, threshold, current_players, current_money)
                VALUES (:bookmaker, :timestamp, :threshold, :current_players, :current_money)
            ''', batch)
            
            conn.commit()
        
        conn.close()
    
    def run(self):
        """Process main loop."""
        logger = AviatorLogger.get_logger(f"Collector-{self.bookmaker_name}")
        logger.info(f"Starting collector for {self.bookmaker_name}")
        
        try:
            self.setup_readers()
            self.collect_round_data()
        except Exception as e:
            logger.error(f"Process error: {e}", exc_info=True)
        finally:
            logger.info(f"Collector stopped: {self.bookmaker_name}")


if __name__ == "__main__":
    app = MainDataCollector()
    app.run()