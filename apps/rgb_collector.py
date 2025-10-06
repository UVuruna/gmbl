# apps/rgb_collector.py
# VERSION: 1.0
# PROGRAM 2: RGB data collection for ML training
# Collects: RGB values from phase_region and play_button_coords

import sys
import time
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from multiprocessing import Process, Queue
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.base_app import BaseAviatorApp, get_number_input
from core.screen_reader import ScreenReader
from logger import AviatorLogger


class RGBCollector(BaseAviatorApp):
    """
    RGB data collector for ML model training.
    
    Collects:
    - Average RGB from phase_region (for phase detection model)
    - Average RGB from play_button_coords (for bet state detection - 3 clusters)
    """
    
    DATABASE_NAME = "rgb_training_data.db"
    
    def __init__(self):
        super().__init__("RGBCollector")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def setup_database(self):
        """Create database tables."""
        self.logger.info("Setting up RGB database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Phase RGB data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phase_rgb (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                r_avg REAL,
                g_avg REAL,
                b_avg REAL,
                r_std REAL,
                g_std REAL,
                b_std REAL,
                label TEXT
            )
        ''')
        
        # Bet button RGB data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS button_rgb (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                r_avg REAL,
                g_avg REAL,
                b_avg REAL,
                r_std REAL,
                g_std REAL,
                b_std REAL,
                label TEXT
            )
        ''')
        
        # Indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_phase_bookmaker 
            ON phase_rgb(bookmaker, timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_button_bookmaker 
            ON button_rgb(bookmaker, timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"RGB Database ready: {self.db_path}")
    
    def create_process(
        self, 
        bookmaker: str,
        layout: str,
        position: str,
        coords: Dict,
        **kwargs
    ) -> Optional[Process]:
        """Create RGB collector process for bookmaker."""
        process = RGBCollectorProcess(
            bookmaker_name=bookmaker,
            coords=coords,
            db_path=self.db_path,
            shutdown_event=self.shutdown_event
        )
        return process
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("🎨 RGB COLLECTOR v1.0")
        print("="*60)
        print("\nCollects RGB values for ML training:")
        print("  • Phase region (for phase detection)")
        print("  • Play button region (for bet state: red/orange/green)")
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
        print("\n🎨 Collecting RGB data... (Ctrl+C to stop)")
        self.wait_for_processes()


class RGBCollectorProcess(Process):
    """Worker process for RGB collection."""
    
    BATCH_SIZE = 100
    COLLECTION_INTERVAL = 0.5  # 500ms between samples
    
    def __init__(
        self, 
        bookmaker_name: str,
        coords: Dict,
        db_path: Path,
        shutdown_event
    ):
        super().__init__(name=f"RGBCollector-{bookmaker_name}")
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.db_path = db_path
        self.shutdown_event = shutdown_event
        
        # Data queues
        self.phase_queue = Queue(maxsize=1000)
        self.button_queue = Queue(maxsize=1000)
    
    def setup_readers(self):
        """Setup screen readers."""
        self.phase_reader = ScreenReader(self.coords['phase_region'])
        self.button_reader = ScreenReader(self.coords['play_button_coords'])
    
    def calculate_rgb_stats(self, img_array: np.ndarray) -> Optional[Dict]:
        """
        Calculate RGB statistics from image array.
        
        Returns:
            Dict with avg and std for each channel
        """
        if img_array is None or img_array.size == 0:
            return None
        
        try:
            # Reshape to (pixels, channels)
            pixels = img_array.reshape(-1, 3)
            
            # Calculate statistics
            r_avg = float(np.mean(pixels[:, 0]))
            g_avg = float(np.mean(pixels[:, 1]))
            b_avg = float(np.mean(pixels[:, 2]))
            
            r_std = float(np.std(pixels[:, 0]))
            g_std = float(np.std(pixels[:, 1]))
            b_std = float(np.std(pixels[:, 2]))
            
            return {
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
        logger = AviatorLogger.get_logger(f"RGBCollector-{self.bookmaker_name}")
        logger.info("Starting RGB collection")
        
        sample_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Capture phase region
                phase_img = self.phase_reader.capture_region()
                if phase_img is not None:
                    phase_stats = self.calculate_rgb_stats(phase_img)
                    if phase_stats:
                        self.phase_queue.put({
                            'bookmaker': self.bookmaker_name,
                            'timestamp': datetime.now().isoformat(),
                            **phase_stats,
                            'label': None  # Will be labeled later
                        })
                
                # Capture button region
                button_img = self.button_reader.capture_region()
                if button_img is not None:
                    button_stats = self.calculate_rgb_stats(button_img)
                    if button_stats:
                        self.button_queue.put({
                            'bookmaker': self.bookmaker_name,
                            'timestamp': datetime.now().isoformat(),
                            **button_stats,
                            'label': None  # Will be labeled later
                        })
                
                sample_count += 1
                
                # Batch insert check
                if self.phase_queue.qsize() >= self.BATCH_SIZE:
                    self.batch_insert('phase')
                if self.button_queue.qsize() >= self.BATCH_SIZE:
                    self.batch_insert('button')
                
                # Progress log
                if sample_count % 100 == 0:
                    logger.info(
                        f"Collected {sample_count} samples "
                        f"(Phase: {self.phase_queue.qsize()}, "
                        f"Button: {self.button_queue.qsize()})"
                    )
                
                time.sleep(self.COLLECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Collection error: {e}", exc_info=True)
                time.sleep(1)
        
        # Final batch inserts
        self.batch_insert('phase')
        self.batch_insert('button')
        
        logger.info(f"Collection finished. Total samples: {sample_count}")
    
    def batch_insert(self, data_type: str):
        """
        Batch insert RGB data.
        
        Args:
            data_type: 'phase' or 'button'
        """
        queue = self.phase_queue if data_type == 'phase' else self.button_queue
        table = 'phase_rgb' if data_type == 'phase' else 'button_rgb'
        
        if queue.empty():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch = []
        while not queue.empty() and len(batch) < self.BATCH_SIZE:
            try:
                batch.append(queue.get_nowait())
            except:
                break
        
        if batch:
            cursor.executemany(f'''
                INSERT INTO {table}
                (bookmaker, timestamp, r_avg, g_avg, b_avg, r_std, g_std, b_std, label)
                VALUES 
                (:bookmaker, :timestamp, :r_avg, :g_avg, :b_avg, :r_std, :g_std, :b_std, :label)
            ''', batch)
            
            conn.commit()
        
        conn.close()
    
    def run(self):
        """Process main loop."""
        logger = AviatorLogger.get_logger(f"RGBCollector-{self.bookmaker_name}")
        logger.info(f"Starting RGB collector for {self.bookmaker_name}")
        
        try:
            self.setup_readers()
            self.collect_rgb_data()
        except Exception as e:
            logger.error(f"Process error: {e}", exc_info=True)
        finally:
            logger.info(f"RGB Collector stopped: {self.bookmaker_name}")


if __name__ == "__main__":
    app = RGBCollector()
    app.run()