# apps/betting_agent.py
# VERSION: 1.1 - Basic update for new coordinate system
# PURPOSE: Automated bet placement (DEMO MODE ONLY!)
# WARNING: Uses real money! Test thoroughly first!

import sys
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from multiprocessing import Process, Event, Lock
from multiprocessing.synchronize import Event as EventType, Lock as LockType
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.coord_manager import CoordsManager
from core.screen_reader import ScreenReader
from core.gui_controller import GUIController
from regions.score import Score
from regions.my_money import MyMoney
from regions.game_phase import GamePhaseDetector
from logger import init_logging, AviatorLogger


class BettingAgent:
    """
    Automated betting agent.
    
    ⚠️  WARNING: This uses REAL MONEY!
    Only use in DEMO MODE for testing!
    """
    
    DATABASE_NAME = "betting_history.db"
    
    def __init__(self):
        init_logging()
        self.logger = AviatorLogger.get_logger("BettingAgent")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.coords_manager = CoordsManager()
        self.shutdown_event = Event()
        self.bet_lock = Lock()  # Transaction safety
        self.process = None
    
    def setup_database(self):
        """Create database tables."""
        self.logger.info("Setting up betting database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                bet_amount REAL,
                auto_stop REAL,
                final_score REAL,
                money_before REAL,
                money_after REAL,
                profit REAL,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bets_bookmaker 
            ON bets(bookmaker, timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Betting database ready: {self.db_path}")
    
    def configure_betting(self) -> Dict:
        """Interactive betting configuration."""
        print("\n" + "="*60)
        print("⚠️  BETTING CONFIGURATION")
        print("="*60)
        
        # Select bookmaker
        available_bookmakers = self.coords_manager.get_available_bookmakers()
        available_positions = self.coords_manager.get_available_positions()
        
        if not available_bookmakers or not available_positions:
            print("❌ No bookmakers or positions configured!")
            return None
        
        print(f"\n📊 Available bookmakers: {', '.join(available_bookmakers)}")
        
        while True:
            bookmaker = input("Choose bookmaker: ").strip()
            if bookmaker in available_bookmakers:
                break
            print("❌ Invalid bookmaker!")
        
        print(f"\n📐 Available positions: {', '.join(available_positions)}")
        
        while True:
            position = input(f"Choose position for {bookmaker}: ").strip().upper()
            if position in available_positions:
                break
            print("❌ Invalid position!")
        
        # Get coordinates
        coords = self.coords_manager.calculate_coords(bookmaker, position)
        if not coords:
            print("❌ Failed to calculate coordinates!")
            return None
        
        # Betting parameters
        print("\n" + "="*60)
        print("BETTING PARAMETERS")
        print("="*60)
        
        try:
            bet_amount = float(input("Bet amount (e.g., 100): "))
            auto_stop = float(input("Auto cash-out multiplier (e.g., 2.0): "))
        except ValueError:
            print("❌ Invalid input!")
            return None
        
        # Confirm
        print("\n" + "="*60)
        print("CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Bookmaker: {bookmaker}")
        print(f"Position: {position}")
        print(f"Bet amount: {bet_amount}")
        print(f"Auto cash-out: {auto_stop}x")
        print("="*60)
        
        confirm = input("\n⚠️  WARNING: This will use REAL money! Continue? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Cancelled by user")
            return None
        
        return {
            'bookmaker': bookmaker,
            'position': position,
            'coords': coords,
            'bet_amount': bet_amount,
            'auto_stop': auto_stop
        }
    
    def start_betting(self, config: Dict):
        """Start betting process."""
        print("\n🚀 Starting betting agent...")
        
        self.process = BettingProcess(
            config=config,
            db_path=self.db_path,
            bet_lock=self.bet_lock,
            shutdown_event=self.shutdown_event
        )
        self.process.start()
        
        print(f"   ✅ Started: {config['bookmaker']} @ {config['position']}")
        print("\n💰 Betting active... (Ctrl+C to stop)")
        
        try:
            self.process.join()
        except KeyboardInterrupt:
            print("\n\n⚠️  Shutdown requested...")
            self.shutdown_event.set()
            self.process.join(timeout=10)
            if self.process.is_alive():
                self.process.terminate()
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("💰 BETTING AGENT v1.1")
        print("="*60)
        print("\n⚠️  WARNING: This agent uses REAL MONEY!")
        print("   Only use in DEMO MODE for testing!")
        print("   Test thoroughly before using with real funds!")
        print("="*60)
        
        self.setup_database()
        
        config = self.configure_betting()
        if not config:
            return
        
        self.start_betting(config)
        
        print("\n✅ Betting agent stopped")


class BettingProcess(Process):
    """Worker process for betting."""
    
    def __init__(
        self,
        config: Dict,
        db_path: Path,
        bet_lock: LockType,
        shutdown_event: EventType
    ):
        super().__init__(name=f"BettingAgent-{config['bookmaker']}")
        self.config = config
        self.db_path = db_path
        self.bet_lock = bet_lock
        self.shutdown_event = shutdown_event
    
    def setup_components(self):
        """Setup screen readers and GUI controller."""
        coords = self.config['coords']
        
        self.score_reader = ScreenReader(coords['score_region'])
        self.money_reader = ScreenReader(coords['my_money_region'])
        self.phase_reader = ScreenReader(coords['phase_region'])
        
        self.score = Score(self.score_reader)
        self.my_money = MyMoney(self.money_reader)
        self.phase_detector = GamePhaseDetector(self.phase_reader)
        
        self.gui = GUIController()
    
    def place_bet(self) -> bool:
        """
        Place a bet (transaction-safe).
        
        Returns:
            True if bet placed successfully
        """
        with self.bet_lock:  # Ensure only one bet at a time
            try:
                # Get current money
                money_before = self.my_money.read_text()
                
                # Click bet amount field
                amount_coords = self.config['coords']['play_amount_coords']
                self.gui.click(amount_coords['left'] + 50, amount_coords['top'] + 15)
                time.sleep(0.1)
                
                # Clear and type amount
                self.gui.press_key('ctrl', 'a')
                self.gui.type_text(str(self.config['bet_amount']))
                time.sleep(0.1)
                
                # Set auto cash-out
                auto_coords = self.config['coords']['auto_play_coords']
                self.gui.click(auto_coords['left'] + 50, auto_coords['top'] + 15)
                time.sleep(0.1)
                self.gui.press_key('ctrl', 'a')
                self.gui.type_text(str(self.config['auto_stop']))
                time.sleep(0.1)
                
                # Click play button
                button_coords = self.config['coords']['play_button_coords']
                self.gui.click(button_coords['left'] + 140, button_coords['top'] + 50)
                
                return True
                
            except Exception as e:
                return False
    
    def betting_loop(self):
        """Main betting loop."""
        logger = AviatorLogger.get_logger(f"BettingAgent-{self.config['bookmaker']}")
        logger.info("Starting betting loop")
        
        while not self.shutdown_event.is_set():
            try:
                # Detect phase
                phase_result = self.phase_detector.read_text()
                current_phase = phase_result.get('phase') if phase_result else None
                
                # Wait for WAITING phase to place bet
                if current_phase == 'WAITING':
                    logger.info("Placing bet...")
                    success = self.place_bet()
                    
                    if success:
                        logger.info("Bet placed!")
                        # Wait for round to complete
                        time.sleep(25)  # Average round duration
                    else:
                        logger.error("Failed to place bet")
                        time.sleep(5)
                else:
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Betting error: {e}", exc_info=True)
                time.sleep(5)
        
        logger.info("Betting loop stopped")
    
    def run(self):
        """Process main loop."""
        try:
            self.setup_components()
            self.betting_loop()
        except Exception as e:
            logger = AviatorLogger.get_logger(f"BettingAgent-{self.config['bookmaker']}")
            logger.error(f"Process error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n⚠️  WARNING: BETTING AGENT - USE ONLY IN DEMO MODE!")
    print("   This software uses real money and involves risk.")
    print("   Test thoroughly before using with real funds.\n")
    
    confirm = input("Do you understand the risks? (yes/no): ").strip().lower()
    if confirm == 'yes':
        app = BettingAgent()
        app.run()
    else:
        print("❌ Exiting...")