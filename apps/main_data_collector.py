# apps/main_data_collector.py
# VERSION: 1.1 - Updated for new coordinate system
# PROGRAM: Main game data collection
# Collects: score, total_players, left_players, total_money, threshold data

import sys
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from multiprocessing import Process, Queue, Event
from multiprocessing.synchronize import Event as EventType
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.screen_reader import ScreenReader
from core.coord_manager import CoordsManager
from regions.score import Score
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.game_phase import GamePhaseDetector
from regions.my_money import MyMoney
from logger import init_logging, AviatorLogger


class MainDataCollector:
    """
    Main data collector application.
    Updated for new coordinate system with positions + bookmakers.
    """
    
    DATABASE_NAME = "main_game_data.db"
    SCORE_THRESHOLDS = [1.5, 2.0, 3.0, 5.0, 10.0]
    
    def __init__(self):
        init_logging()
        self.logger = AviatorLogger.get_logger("MainDataCollector")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.coords_manager = CoordsManager()
        self.shutdown_event = Event()
        self.processes = []
    
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
        
        # Indexes
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
    
    def select_bookmakers_interactive(self, num_bookmakers: int) -> List[Tuple[str, str, Dict]]:
        """
        Interactive selection of bookmakers and positions.
        
        Returns:
            List of tuples: (bookmaker_name, position_code, coordinates)
        """
        available_bookmakers = self.coords_manager.get_available_bookmakers()
        available_positions = self.coords_manager.get_available_positions()
        
        if not available_bookmakers:
            print("\n❌ No bookmakers configured!")
            print("   Run: python utils/region_editor.py")
            return []
        
        if not available_positions:
            print("\n❌ No positions configured!")
            print("   Add positions to bookmaker_coords.json")
            return []
        
        print(f"\n📊 Available bookmakers: {', '.join(available_bookmakers)}")
        print(f"📐 Available positions: {', '.join(available_positions)}")
        
        selected = []
        
        for i in range(1, num_bookmakers + 1):
            print(f"\n--- Bookmaker #{i} ---")
            
            # Select bookmaker
            while True:
                bookmaker = input(f"Choose bookmaker: ").strip()
                if bookmaker in available_bookmakers:
                    break
                print(f"❌ Invalid! Choose from: {', '.join(available_bookmakers)}")
            
            # Select position
            while True:
                position = input(f"Choose position for {bookmaker} (e.g., TL, TC, TR, BL, BC, BR): ").strip().upper()
                if position in available_positions:
                    break
                print(f"❌ Invalid! Choose from: {', '.join(available_positions)}")
            
            # Calculate coordinates
            coords = self.coords_manager.calculate_coords(bookmaker, position)
            if coords:
                selected.append((bookmaker, position, coords))
                print(f"✅ {bookmaker} @ {position}")
            else:
                print(f"❌ Failed to calculate coordinates for {bookmaker} @ {position}")
        
        return selected
    
    def verify_regions(self, bookmakers_config: List[Tuple[str, str, Dict]]) -> bool:
        """
        Verify regions with screenshots.
        
        Args:
            bookmakers_config: List of (bookmaker, position, coords)
        
        Returns:
            True if user confirms
        """
        print("\n📸 Creating verification screenshots...")
        
        from utils.region_visualizer import RegionVisualizer
        
        for bookmaker, position, coords in bookmakers_config:
            try:
                visualizer = RegionVisualizer(f"{bookmaker}_{position}", coords, position)
                filepath = visualizer.save_visualization()
                visualizer.cleanup()
                print(f"   ✅ {filepath}")
            except Exception as e:
                print(f"   ❌ Failed for {bookmaker}: {e}")
        
        print(f"\n📁 Screenshots saved in: tests/screenshots/")
        print("   Review them to verify region positions")
        
        confirm = input("\nDo regions look correct? (yes/no): ").strip().lower()
        return confirm in ['yes', 'y']
    
    def start_processes(self, bookmakers_config: List[Tuple[str, str, Dict]]):
        """Start collector processes."""
        print(f"\n🚀 Starting {len(bookmakers_config)} processes...")
        
        for bookmaker, position, coords in bookmakers_config:
            process = CollectorProcess(
                bookmaker_name=f"{bookmaker}_{position}",
                coords=coords,
                db_path=self.db_path,
                shutdown_event=self.shutdown_event
            )
            process.start()
            self.processes.append(process)
            print(f"   ✅ Started: {bookmaker} @ {position}")
    
    def wait_for_processes(self):
        """Wait for all processes to complete."""
        try:
            for process in self.processes:
                process.join()
        except KeyboardInterrupt:
            print("\n\n⚠️  Shutdown requested...")
            self.shutdown_event.set()
            
            # Wait for processes to finish
            for process in self.processes:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("🎰 MAIN DATA COLLECTOR v1.1")
        print("="*60)
        print("\nCollects:")
        print("  • Final score, players, money at round end")
        print("  • Score snapshots at thresholds (1.5x, 2x, 3x, 5x, 10x)")
        print("="*60)
        
        # Setup database
        self.setup_database()
        
        # Get number of bookmakers
        while True:
            try:
                num = int(input("\nHow many bookmakers to track? (1-6): "))
                if 1 <= num <= 6:
                    break
                print("❌ Please enter 1-6")
            except ValueError:
                print("❌ Invalid input")
        
        # Setup bookmakers
        bookmakers_config = self.select_bookmakers_interactive(num)
        
        if not bookmakers_config:
            print("\n❌ No bookmakers configured!")
            return
        
        # Verify regions
        if not self.verify_regions(bookmakers_config):
            print("\n❌ User cancelled. Fix regions and try again.")
            return
        
        # Start processes
        self.start_processes(bookmakers_config)
        
        # Wait
        print("\n📊 Collecting data... (Ctrl+C to stop)")
        self.wait_for_processes()
        
        print("\n✅ Data collection stopped")


class CollectorProcess(Process):
    """Worker process for one bookmaker."""
    
    BATCH_SIZE = 50
    COLLECTION_INTERVAL = 0.2
    
    def __init__(
        self, 
        bookmaker_name: str,
        coords: Dict,
        db_path: Path,
        shutdown_event: EventType
    ):
        super().__init__(name=f"Collector-{bookmaker_name}")
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.db_path = db_path
        self.shutdown_event = shutdown_event
        
        # Data queues
        self.rounds_queue = []
        self.thresholds_queue = []
    
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
        logger.info("Starting collection")
        
        last_phase = None
        threshold_tracker = {t: False for t in MainDataCollector.SCORE_THRESHOLDS}
        
        while not self.shutdown_event.is_set():
            try:
                # Detect phase
                phase_result = self.phase_detector.read_text()
                current_phase = phase_result.get('phase') if phase_result else None
                
                # WAITING → FLYING transition - reset thresholds
                if last_phase == 'WAITING' and current_phase == 'FLYING':
                    threshold_tracker = {t: False for t in MainDataCollector.SCORE_THRESHOLDS}
                    logger.info("New round started")
                
                # During FLYING - track thresholds
                if current_phase == 'FLYING':
                    score_text = self.score_reader.read_once()
                    try:
                        score = float(score_text.replace('x', '').replace(',', '.').strip())
                        
                        # Check thresholds
                        for threshold in MainDataCollector.SCORE_THRESHOLDS:
                            if score >= threshold and not threshold_tracker[threshold]:
                                player_count = self.other_count.get_current_count()
                                total_money = self.other_money.read_text()
                                
                                self.thresholds_queue.append({
                                    'bookmaker': self.bookmaker_name,
                                    'timestamp': datetime.now().isoformat(),
                                    'threshold': threshold,
                                    'current_players': player_count,
                                    'current_money': total_money
                                })
                                threshold_tracker[threshold] = True
                                logger.debug(f"Threshold {threshold}x reached")
                    except:
                        pass
                
                # FLYING → ENDED transition - save round
                if last_phase == 'FLYING' and current_phase == 'ENDED':
                    score_text = self.score_reader.read_once()
                    try:
                        final_score = float(score_text.replace('x', '').replace(',', '.').strip())
                        total_players = self.other_count.get_total_count()
                        left_players = self.other_count.get_current_count()
                        total_money = self.other_money.read_text()
                        
                        self.rounds_queue.append({
                            'bookmaker': self.bookmaker_name,
                            'timestamp': datetime.now().isoformat(),
                            'final_score': final_score,
                            'total_players': total_players,
                            'left_players': left_players,
                            'total_money': total_money
                        })
                        
                        logger.info(f"Round ended: {final_score}x, {total_players} players")
                    except Exception as e:
                        logger.error(f"Error saving round: {e}")
                
                last_phase = current_phase
                
                # Batch insert check
                if len(self.rounds_queue) >= self.BATCH_SIZE:
                    self.batch_insert_rounds()
                if len(self.thresholds_queue) >= self.BATCH_SIZE:
                    self.batch_insert_thresholds()
                
                time.sleep(self.COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Collection error: {e}", exc_info=True)
                time.sleep(1)
        
        # Final batch inserts
        self.batch_insert_rounds()
        self.batch_insert_thresholds()
        logger.info("Collection stopped")
    
    def batch_insert_rounds(self):
        """Batch insert round data."""
        if not self.rounds_queue:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO rounds 
            (bookmaker, timestamp, final_score, total_players, left_players, total_money)
            VALUES (:bookmaker, :timestamp, :final_score, :total_players, :left_players, :total_money)
        ''', self.rounds_queue)
        
        conn.commit()
        conn.close()
        
        self.rounds_queue.clear()
    
    def batch_insert_thresholds(self):
        """Batch insert threshold data."""
        if not self.thresholds_queue:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT INTO threshold_scores 
            (bookmaker, timestamp, threshold, current_players, current_money)
            VALUES (:bookmaker, :timestamp, :threshold, :current_players, :current_money)
        ''', self.thresholds_queue)
        
        conn.commit()
        conn.close()
        
        self.thresholds_queue.clear()
    
    def run(self):
        """Process main loop."""
        try:
            self.setup_readers()
            self.collect_round_data()
        except Exception as e:
            logger = AviatorLogger.get_logger(f"Collector-{self.bookmaker_name}")
            logger.error(f"Process error: {e}", exc_info=True)


if __name__ == "__main__":
    app = MainDataCollector()
    app.run()