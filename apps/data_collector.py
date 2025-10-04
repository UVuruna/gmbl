# data_collector.py
# VERSION: 2.0 - Multi-bookmaker parallel collection
# Supports 3-6 bookmakers simultaneously with multiprocessing

from core.screen_reader import ScreenReader
from core.coord_manager import CoordsManager
from core.coord_getter import CoordGetter
from regions.score import Score
from regions.my_money import MyMoney
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.game_phase import GamePhaseDetector
from logger import init_logging, AviatorLogger
from config import AppConstants, GamePhase
from multiprocessing.synchronize import Event as MPEvent

import sqlite3
import time
import signal
import sys
from datetime import datetime
from typing import Dict, Optional, List
from multiprocessing import Process, Event


class DataCollector:
    
    def __init__(self, bookmaker_name: str, coords: Dict, collection_interval: float, shutdown_event: MPEvent):
        self.bookmaker_name = bookmaker_name
        self.collection_interval = collection_interval
        self.shutdown_event = shutdown_event
        self.is_running = False
        self.logger = AviatorLogger.get_logger(f"Collector-{bookmaker_name}")
        
        self.score_reader = ScreenReader(coords['score_region'])
        self.my_money_reader = ScreenReader(coords['my_money_region'])
        self.other_count_reader = ScreenReader(coords['other_count_region'])
        self.other_money_reader = ScreenReader(coords['other_money_region'])
        self.phase_reader = ScreenReader(coords['phase_region'])
        
        self.my_money = MyMoney(self.my_money_reader)
        self.other_count = OtherCount(self.other_count_reader)
        self.other_money = OtherMoney(self.other_money_reader)
        self.phase_detector = GamePhaseDetector(self.phase_reader)
        
        self.score = Score(
            screen_reader=self.score_reader,
            my_money=self.my_money,
            other_count=self.other_count,
            other_money=self.other_money,
            phase_detector=self.phase_detector,
            auto_stop=2.35
        )
        
        self.data_db = None
        self.phase_db = None
        self.total_readings = 0
        self.successful_readings = 0
    
    def setup_databases(self):
        self.data_db = sqlite3.connect('data.db', check_same_thread=False)
        cursor = self.data_db.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                bookmaker TEXT NOT NULL,
                score REAL,
                game_phase TEXT,
                game_phase_value INTEGER,
                my_money REAL,
                current_players INTEGER,
                total_players INTEGER,
                others_money REAL
            )
        """)
        self.data_db.commit()
        
        self.phase_db = sqlite3.connect('game_phase.db', check_same_thread=False)
        cursor = self.phase_db.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                bookmaker TEXT NOT NULL,
                r REAL NOT NULL,
                g REAL NOT NULL,
                b REAL NOT NULL,
                predicted_phase TEXT,
                predicted_phase_value INTEGER
            )
        """)
        self.phase_db.commit()
        self.logger.info("Databases setup complete")
    
    def collect_single_reading(self) -> Dict:
        reading = {
            'timestamp': datetime.now().isoformat(),
            'bookmaker': self.bookmaker_name,
            'score': None,
            'game_phase': None,
            'game_phase_value': None,
            'my_money': None,
            'current_players': None,
            'total_players': None,
            'others_money': None
        }
        
        try:
            phase_result = self.phase_detector.read_text()
            if phase_result:
                phase = GamePhase(phase_result['phase'])
                reading['game_phase'] = phase.name
                reading['game_phase_value'] = phase.value
            
            score_result = self.score.read_text()
            if score_result:
                reading['score'] = score_result.get('score')
            
            try:
                my_money = self.my_money.read_text()
                if my_money is not None:
                    reading['my_money'] = my_money
            except:
                pass
            
            try:
                current_count = self.other_count.get_current_count()
                total_count = self.other_count.get_total_count()
                if current_count is not None:
                    reading['current_players'] = current_count
                if total_count is not None:
                    reading['total_players'] = total_count
            except:
                pass
            
            try:
                others_money = self.other_money.read_text()
                if others_money is not None:
                    reading['others_money'] = others_money
            except:
                pass
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error collecting: {e}")
        
        return reading
    
    def collect_rgb_values(self) -> Optional[Dict]:
        try:
            rgb = self.phase_detector._get_mean_rgb()
            if rgb is None:
                return None
            
            phase_result = self.phase_detector.read_text()
            predicted_phase = None
            predicted_phase_value = None
            
            if phase_result:
                phase = GamePhase(phase_result['phase'])
                predicted_phase = phase.name
                predicted_phase_value = phase.value
            
            return {
                'timestamp': datetime.now().isoformat(),
                'bookmaker': self.bookmaker_name,
                'r': float(rgb[0][0]),
                'g': float(rgb[0][1]),
                'b': float(rgb[0][2]),
                'predicted_phase': predicted_phase,
                'predicted_phase_value': predicted_phase_value
            }
        except:
            return None
    
    def save_reading(self, reading: Dict):
        try:
            cursor = self.data_db.cursor()
            cursor.execute("""
                INSERT INTO readings (
                    timestamp, bookmaker, score, game_phase, game_phase_value,
                    my_money, current_players, total_players, others_money
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reading['timestamp'], reading['bookmaker'], reading['score'],
                reading['game_phase'], reading['game_phase_value'], reading['my_money'],
                reading['current_players'], reading['total_players'], reading['others_money']
            ))
            self.data_db.commit()
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error saving: {e}")
    
    def save_rgb(self, rgb_data: Dict):
        try:
            cursor = self.phase_db.cursor()
            cursor.execute("""
                INSERT INTO colors (
                    timestamp, bookmaker, r, g, b, 
                    predicted_phase, predicted_phase_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rgb_data['timestamp'], rgb_data['bookmaker'],
                rgb_data['r'], rgb_data['g'], rgb_data['b'],
                rgb_data['predicted_phase'], rgb_data['predicted_phase_value']
            ))
            self.phase_db.commit()
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error saving RGB: {e}")
    
    def run(self):
        self.logger.info(f"Starting collection - interval: {self.collection_interval}s")
        self.is_running = True
        
        try:
            while not self.shutdown_event.is_set():
                start_time = time.time()
                
                reading = self.collect_single_reading()
                self.save_reading(reading)
                
                rgb_data = self.collect_rgb_values()
                if rgb_data:
                    self.save_rgb(rgb_data)
                
                self.total_readings += 1
                if any(v is not None for k, v in reading.items() if k not in ['timestamp', 'bookmaker']):
                    self.successful_readings += 1
                
                if self.total_readings % 50 == 0:
                    success_rate = (self.successful_readings / self.total_readings) * 100
                    self.logger.info(
                        f"Progress: {self.total_readings}, "
                        f"Success: {success_rate:.1f}%, "
                        f"Phase: {reading.get('game_phase', 'N/A')}"
                    )
                
                elapsed = time.time() - start_time
                sleep_time = max(0, self.collection_interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        self.is_running = False
        
        self.logger.info(f"Stopped. Total: {self.total_readings}, Success: {self.successful_readings}")
        
        if self.data_db:
            self.data_db.close()
        if self.phase_db:
            self.phase_db.close()
        
        try:
            self.phase_detector.close()
        except:
            pass


class CollectorProcess(Process):
    def __init__(self, bookmaker_name: str, coords: Dict, interval: float, shutdown_event: MPEvent):
        super().__init__(name=f"Collector-{bookmaker_name}")
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.interval = interval
        self.shutdown_event = shutdown_event
    
    def run(self):
        collector = DataCollector(self.bookmaker_name, self.coords, self.interval, self.shutdown_event)
        collector.setup_databases()
        collector.run()


# Global variables
processes = []
shutdown_event = None


def signal_handler(signum, frame):
    print("\n\nCtrl+C detected - stopping all collectors...")
    if shutdown_event:
        shutdown_event.set()
    
    for proc in processes:
        proc.join(timeout=5)
        if proc.is_alive():
            proc.terminate()
    
    print("All collectors stopped")
    sys.exit(0)


def get_number_of_bookmakers() -> int:
    while True:
        try:
            num = input("\nHow many bookmakers to track? (3-6): ").strip()
            num = int(num)
            if 3 <= num <= 6:
                return num
            print("Please enter a number between 3 and 6")
        except ValueError:
            print("Invalid input. Enter a number.")


def setup_bookmaker_interactive(bookmaker_num: int, coords_manager: CoordsManager, monitors:int) -> Dict:
    BOOKMAKERS = ['BalkanBet', 'Soccer', 'Admiral', 'MaxBet', 'Mozzart','Meridian']
    POSITIONS = ['TL','TC','TR','BL','BC','BR']
    print(f"\n{'='*60}")
    print(f"BOOKMAKER {bookmaker_num} SETUP")
    print(f"{'='*60}")
    
    # Bookmaker name
    name = input(f"\nBookmaker {bookmaker_num} name (default: {BOOKMAKERS[bookmaker_num-1]}): ").strip() or BOOKMAKERS[bookmaker_num-1]
    if not name:
        name = f"Bookmaker{bookmaker_num}"
    
    # Try to load existing coordinates
    print(f"\nDo you have saved coordinates for {name}?")
    print("1. Yes - load from file")
    print("2. No - setup with mouse clicks")
    
    choice = input("Choice (1-2): ").strip()
    
    if choice == "1":
        config_name = input("Configuration name (default: '5_equal'): ").strip() or "5_equal"
        position = input(f"Position name (default: {POSITIONS[bookmaker_num-1]}): ").strip() or POSITIONS[bookmaker_num-1]
        
        try:
            coords = coords_manager.load_coordinates(config_name, position)
            if monitors == 1:
                for region in coords.values():
                    if isinstance(region,dict):
                        region['left'] -= 3840
            if coords is None:
                print("✗ Coordinates not found. Setup with mouse clicks:")
                choice = "2"
            else:
                print(f"✓ Loaded coordinates for {name}")
                return {'name': name, **coords}
        except Exception as e:
            print(f"✗ Failed to load: {e}")
            print("Setup with mouse clicks:")
            choice = "2"
    
    if choice == "2":
        coords = {}
        
        print(f"\n[1/5] SCORE REGION for {name}")
        print("Click TOP-LEFT corner, then BOTTOM-RIGHT corner of score display")
        score_getter = CoordGetter(name, "Score Region", "region")
        coords['score_region'] = score_getter.get_region()
        print(f"✓ Score region: {coords['score_region']}")
        
        print(f"\n[2/5] MY MONEY REGION for {name}")
        print("Click TOP-LEFT corner, then BOTTOM-RIGHT corner of your balance")
        money_getter = CoordGetter(name, "My Money Region", "region")
        coords['my_money_region'] = money_getter.get_region()
        print(f"✓ My money region: {coords['my_money_region']}")
        
        print(f"\n[3/5] OTHER COUNT REGION for {name}")
        print("Click TOP-LEFT corner, then BOTTOM-RIGHT corner of player count")
        count_getter = CoordGetter(name, "Other Count Region", "region")
        coords['other_count_region'] = count_getter.get_region()
        print(f"✓ Other count region: {coords['other_count_region']}")
        
        print(f"\n[4/5] OTHER MONEY REGION for {name}")
        print("Click TOP-LEFT corner, then BOTTOM-RIGHT corner of total winnings")
        other_money_getter = CoordGetter(name, "Other Money Region", "region")
        coords['other_money_region'] = other_money_getter.get_region()
        print(f"✓ Other money region: {coords['other_money_region']}")
        
        print(f"\n[5/5] PHASE REGION for {name}")
        print("Click TOP-LEFT corner, then BOTTOM-RIGHT corner for phase detection")
        phase_getter = CoordGetter(name, "Phase Region", "region")
        coords['phase_region'] = phase_getter.get_region()
        print(f"✓ Phase region: {coords['phase_region']}")
        
        # Ask to save
        save_coords = input(f"\nSave these coordinates? (y/n): ").strip().lower()
        if save_coords == 'y':
            config_name = input("Configuration name (e.g., 5_bookmakers_setup): ").strip()
            position = input(f"Position name for {name} (e.g., Position_{bookmaker_num}): ").strip()
            coords_manager.save_coordinates(config_name, position, coords)
            print(f"✓ Coordinates saved: {config_name} / {position}")
        
        return {'name': name, **coords}


def main():
    global processes, shutdown_event
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    init_logging()
    logger = AviatorLogger.get_logger("Main")
    
    logger.info("=" * 60)
    logger.info("AVIATOR DATA COLLECTION - MULTI-BOOKMAKER MODE")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Get number of bookmakers
        num_bookmakers = get_number_of_bookmakers()
        
        # Get collection interval
        interval_input = input("\nCollection interval in seconds (default: 0.2): ").strip()
        interval = float(interval_input) if interval_input else 0.2
        
        # Setup each bookmaker
        coords_manager = CoordsManager()
        bookmaker_configs = []
        
        monitor = int(input("\nNubmer of monitors (default: 1): ").strip()) or 1
        for i in range(1, num_bookmakers + 1):
            config = setup_bookmaker_interactive(i, coords_manager, monitor)
            bookmaker_configs.append(config)
        
        # Summary
        print(f"\n{'='*60}")
        print("SETUP COMPLETE")
        print(f"{'='*60}")
        print(f"Bookmakers: {num_bookmakers}")
        for i, config in enumerate(bookmaker_configs, 1):
            print(f"  {i}. {config['name']}")
        print(f"Interval: {interval}s")
        print(f"Press Ctrl+C to stop all collectors")
        print(f"{'='*60}\n")
        
        input("Press Enter to start collection...")
        
        # Create shutdown event
        from multiprocessing import Manager
        manager = Manager()
        shutdown_event = manager.Event()
        
        # Start processes
        for config in bookmaker_configs:
            proc = CollectorProcess(
                bookmaker_name=config['name'],
                coords=config,
                interval=interval,
                shutdown_event=shutdown_event
            )
            proc.start()
            processes.append(proc)
            logger.info(f"Started collector: {config['name']}")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            # Check if all processes are still alive
            if not any(p.is_alive() for p in processes):
                break
        
    except Exception as e:
        logger.critical(f"Error: {e}", exc_info=True)
        if shutdown_event:
            shutdown_event.set()
        for proc in processes:
            proc.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()