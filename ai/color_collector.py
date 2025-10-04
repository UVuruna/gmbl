# ai/color_collector.py
# Refactored from colors_insert.py

import numpy as np
import mss
import pyautogui
import sqlite3
import time
import threading
import queue
from logger import AviatorLogger


class ColorCollector:
    """Collect RGB colors from screen regions for training"""
    
    def __init__(self, db_path: str, delay: float, bookmakers: list):
        self.db_path = db_path
        self.delay_per_bookmaker = delay * len(bookmakers)
        self.bookmakers = bookmakers
        self.regions = {}
        self.logger = AviatorLogger.get_logger("ColorCollector")
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            bookmaker TEXT,
            r REAL,
            g REAL,
            b REAL
        )
        """)
        conn.commit()
        conn.close()
        self.logger.info(f"Database initialized: {self.db_path}")
    
    def setup_regions(self):
        """Interactive region setup"""
        for bookmaker in self.bookmakers:
            print(f"\n=== Setup region for {bookmaker} ===")
            print("Click TopLeft...")
            input("Press Enter to capture first point")
            x1, y1 = pyautogui.position()
            
            print("Click BottomRight...")
            input("Press Enter to capture second point")
            x2, y2 = pyautogui.position()
            
            self.regions[bookmaker] = {
                "top": min(y1, y2),
                "left": min(x1, x2),
                "width": abs(x2 - x1),
                "height": abs(y2 - y1)
            }
            self.logger.info(f"Region set for {bookmaker}: {self.regions[bookmaker]}")
    
    def _worker(self, bookmaker: str, bbox: dict, q: queue.Queue):
        """Worker thread for single bookmaker"""
        sct = mss.mss()
        while True:
            img = np.array(sct.grab(bbox))[:, :, :3]
            rgb = img.mean(axis=(0, 1))[::-1]
            r, g, b = map(float, rgb)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            q.put((timestamp, bookmaker, r, g, b))
            time.sleep(self.delay_per_bookmaker)
    
    def start_collection(self):
        """Start collection threads"""
        q = queue.Queue()
        threads = []
        
        for bookmaker, region in self.regions.items():
            t = threading.Thread(
                target=self._worker,
                args=(bookmaker, region, q),
                daemon=True
            )
            t.start()
            threads.append(t)
            self.logger.info(f"Started worker for {bookmaker}")
        
        # Batch insert every 10 seconds
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cur = conn.cursor()
        
        buffer = []
        start = time.time()
        total = 0
        
        self.logger.info("Collection started. Press Ctrl+C to stop.")
        
        try:
            while True:
                data = q.get()
                buffer.append(data)
                
                if time.time() - start >= 10:
                    start = time.time()
                    
                    cur.executemany(
                        "INSERT INTO colors (timestamp, bookmaker, r, g, b) VALUES (?, ?, ?, ?, ?)",
                        buffer
                    )
                    conn.commit()
                    
                    total += len(buffer)
                    self.logger.info(f"Inserted {len(buffer)} records. Total: {total:,}")
                    
                    # Show last 5
                    for item in buffer[-5:]:
                        ts, bk, r, g, b = item
                        self.logger.debug(f"{bk}: RGB({r:.0f}, {g:.0f}, {b:.0f})")
                    
                    buffer.clear()
        
        except KeyboardInterrupt:
            if buffer:
                cur.executemany(
                    "INSERT INTO colors (timestamp, bookmaker, r, g, b) VALUES (?, ?, ?, ?, ?)",
                    buffer
                )
                conn.commit()
                total += len(buffer)
            
            conn.close()
            self.logger.info(f"Collection stopped. Total records: {total:,}")


def main():
    from logger import init_logging
    
    init_logging()
    
    print("=" * 60)
    print("COLOR COLLECTOR - Training Data Collection")
    print("=" * 60)
    
    db_name = input("\nDatabase name (default 'game_phase'): ").strip() or "game_phase"
    db_path = f"db/{db_name}.db"
    
    delay = float(input("Collection interval in seconds (default 0.01): ").strip() or "0.01")
    
    bookmakers = []
    while True:
        bm = input("Bookmaker name (empty to finish): ").strip()
        if not bm:
            break
        bookmakers.append(bm)
    
    if not bookmakers:
        print("No bookmakers added!")
        return
    
    collector = ColorCollector(db_path, delay, bookmakers)
    collector.setup_regions()
    collector.start_collection()


if __name__ == "__main__":
    main()
