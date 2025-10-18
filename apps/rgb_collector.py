# apps/rgb_collector.py
# VERSION: 1.1 - Updated for new coordinate system
# PURPOSE: Collect RGB samples for ML training
# COLLECTS: phase_region → phase_rgb, play_button_coords → button_rgb

import sys
import time
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from multiprocessing import Process, Queue, Event
from multiprocessing.synchronize import Event as EventType
from datetime import datetime
import mss

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.coord_manager import CoordsManager
from logger import init_logging, AviatorLogger


class RGBCollector:
    """
    RGB data collector for ML training.
    Collects RGB statistics from phase_region and play_button_coords.
    """
    
    DATABASE_NAME = "rgb_training_data.db"
    COLLECTION_INTERVAL = 0.5  # 2 samples per second
    
    def __init__(self):
        init_logging()
        self.logger = AviatorLogger.get_logger("RGBCollector")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.coords_manager = CoordsManager()
        self.shutdown_event = Event()
        self.processes = []
    
    def setup_database(self):
        """Create database tables."""
        self.logger.info("Setting up RGB database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Phase RGB table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phase_rgb (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                r_avg REAL,
                g_avg REAL,
                b_avg REAL,
                r_std REAL,
                g_std REAL,
                b_std REAL
            )
        ''')
        
        # Button RGB table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS button_rgb (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                r_avg REAL,
                g_avg REAL,
                b_avg REAL,
                r_std REAL,
                g_std REAL,
                b_std REAL
            )
        ''')
        
        # Indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_phase_timestamp 
            ON phase_rgb(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_button_timestamp 
            ON button_rgb(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"RGB database ready: {self.db_path}")
    
    def select_bookmakers_interactive(self, num_bookmakers: int) -> List[Tuple[str, str, Dict]]:
        """Interactive selection of bookmakers and positions."""
        available_bookmakers = self.coords_manager.get_available_bookmakers()
        available_positions = self.coords_manager.get_available_positions()
        
        if not available_bookmakers:
            print("\n❌ No bookmakers configured!")
            return []
        
        if not available_positions:
            print("\n❌ No positions configured!")
            return []
        
        print(f"\n📊 Available bookmakers: {', '.join(available_bookmakers)}")
        print(f"📐 Available positions: {', '.join(available_positions)}")
        
        selected = []
        
        for i in range(1, num_bookmakers + 1):
            print(f"\n--- Bookmaker #{i} ---")
            
            while True:
                bookmaker = input(f"Choose bookmaker: ").strip()
                if bookmaker in available_bookmakers:
                    break
                print(f"❌ Invalid! Choose from: {', '.join(available_bookmakers)}")
            
            while True:
                position = input(f"Choose position for {bookmaker}: ").strip().upper()
                if position in available_positions:
                    break
                print(f"❌ Invalid! Choose from: {', '.join(available_positions)}")
            
            coords = self.coords_manager.calculate_coords(bookmaker, position)
            if coords:
                selected.append((bookmaker, position, coords))
                print(f"✅ {bookmaker} @ {position}")
            else:
                print(f"❌ Failed to calculate coordinates!")
        
        return selected
    
    def start_processes(self, bookmakers_config: List[Tuple[str, str, Dict]]):
        """Start RGB collector processes."""
        print(f"\n🚀 Starting {len(bookmakers_config)} RGB collectors...")
        
        for bookmaker, position, coords in bookmakers_config:
            process = RGBCollectorProcess(
                identifier=f"{bookmaker}_{position}",
                coords=coords,
                db_path=self.db_path,
                shutdown_event=self.shutdown_event
            )
            process.start()
            self.processes.append(process)
            print(f"   ✅ Started: {bookmaker} @ {position}")
    
    def wait_for_processes(self):
        """Wait for all processes."""
        try:
            for process in self.processes:
                process.join()
        except KeyboardInterrupt:
            print("\n\n⚠️  Shutdown requested...")
            self.shutdown_event.set()
            
            for process in self.processes:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("🎨 RGB COLLECTOR v1.1")
        print("="*60)
        print("\nCollects RGB statistics for ML training:")
        print("  • phase_region → phase_rgb table")
        print("  • play_button_coords → button_rgb table")
        print("="*60)
        
        self.setup_database()
        
        while True:
            try:
                num = int(input("\nHow many bookmakers to track? (1-6): "))
                if 1 <= num <= 6:
                    break
                print("❌ Please enter 1-6")
            except ValueError:
                print("❌ Invalid input")
        
        bookmakers_config = self.select_bookmakers_interactive(num)
        
        if not bookmakers_config:
            print("\n❌ No bookmakers configured!")
            return
        
        self.start_processes(bookmakers_config)
        
        print("\n🎨 Collecting RGB data... (Ctrl+C to stop)")
        self.wait_for_processes()
        
        print("\n✅ RGB collection stopped")


class RGBCollectorProcess(Process):
    """Worker process for RGB collection."""
    
    BATCH_SIZE = 100
    COLLECTION_INTERVAL = 0.5
    
    def __init__(
        self,
        identifier: str,
        coords: Dict,
        db_path: Path,
        shutdown_event: EventType
    ):
        super().__init__(name=f"RGBCollector-{identifier}")
        self.identifier = identifier
        self.coords = coords
        self.db_path = db_path
        self.shutdown_event = shutdown_event
        
        # Data queues
        self.phase_queue = []
        self.button_queue = []
    
    def calculate_rgb_stats(self, region: Dict) -> Optional[Dict]:
        """
        Calculate RGB statistics for a region.
        
        Args:
            region: Region dict with left, top, width, height
        
        Returns:
            Dict with r_avg, g_avg, b_avg, r_std, g_std, b_std or None
        """
        try:
            with mss.mss() as sct:
                screenshot = sct.grab(region)
                img = np.array(screenshot)[:, :, :3]  # Remove alpha, keep RGB
                
                # Calculate statistics
                r_avg = float(np.mean(img[:, :, 0]))
                g_avg = float(np.mean(img[:, :, 1]))
                b_avg = float(np.mean(img[:, :, 2]))
                
                r_std = float(np.std(img[:, :, 0]))
                g_std = float(np.std(img[:, :, 1]))
                b_std = float(np.std(img[:, :, 2]))
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'r_avg': r_avg,
                    'g_avg': g_avg,
                    'b_avg': b_avg,
                    'r_std': r_std,
                    'g_std': g_std,
                    'b_std': b_std
                }
        except Exception as e:
            return None
    
    def collect_rgb_data(self):
        """Main collection loop."""
        logger = AviatorLogger.get_logger(f"RGBCollector-{self.identifier}")
        logger.info("Starting RGB collection")
        
        # Get regions
        phase_region = self.coords.get('phase_region')
        button_region = self.coords.get('play_button_coords')
        
        if not phase_region or not button_region:
            logger.error("Missing required regions!")
            return
        
        sample_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Collect phase RGB
                phase_stats = self.calculate_rgb_stats(phase_region)
                if phase_stats:
                    self.phase_queue.append(phase_stats)
                
                # Collect button RGB
                button_stats = self.calculate_rgb_stats(button_region)
                if button_stats:
                    self.button_queue.append(button_stats)
                
                sample_count += 1
                
                if sample_count % 100 == 0:
                    logger.info(f"Collected {sample_count} samples")
                
                # Batch insert check
                if len(self.phase_queue) >= self.BATCH_SIZE:
                    self.batch_insert('phase')
                if len(self.button_queue) >= self.BATCH_SIZE:
                    self.batch_insert('button')
                
                time.sleep(self.COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Collection error: {e}", exc_info=True)
                time.sleep(1)
        
        # Final batch inserts
        self.batch_insert('phase')
        self.batch_insert('button')
        
        logger.info(f"RGB collection stopped. Total samples: {sample_count}")
    
    def batch_insert(self, data_type: str):
        """
        Batch insert RGB data.
        
        Args:
            data_type: 'phase' or 'button'
        """
        queue = self.phase_queue if data_type == 'phase' else self.button_queue
        table = 'phase_rgb' if data_type == 'phase' else 'button_rgb'
        
        if not queue:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executemany(f'''
            INSERT INTO {table}
            (timestamp, r_avg, g_avg, b_avg, r_std, g_std, b_std)
            VALUES (:timestamp, :r_avg, :g_avg, :b_avg, :r_std, :g_std, :b_std)
        ''', queue)
        
        conn.commit()
        conn.close()
        
        queue.clear()
    
    def run(self):
        """Process main loop."""
        try:
            self.collect_rgb_data()
        except Exception as e:
            logger = AviatorLogger.get_logger(f"RGBCollector-{self.identifier}")
            logger.error(f"Process error: {e}", exc_info=True)


if __name__ == "__main__":
    app = RGBCollector()
    app.run()