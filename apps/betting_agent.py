# apps/betting_agent.py
# VERSION: 2.0
# PROGRAM 3: Automated betting agent
# Places bets using configured strategy

import sys
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Lock as LockType
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.base_app import BaseAviatorApp, get_number_input
from core.screen_reader import ScreenReader
from core.gui_controller import GUIController
from regions.score import Score
from regions.my_money import MyMoney
from regions.game_phase import GamePhaseDetector
from logger import AviatorLogger


class BettingAgent(BaseAviatorApp):
    """
    Automated betting agent.
    
    Features:
    - Monitors: my_money, score, phase
    - Controls: bet_amount, play_button, auto_play
    - Transaction-safe: One bet at a time using locks
    - Logs all bets to database
    """
    
    DATABASE_NAME = "betting_history.db"
    
    def __init__(self):
        super().__init__("BettingAgent")
        self.db_path = Path("data/databases") / self.DATABASE_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Shared lock for bet transactions
        from multiprocessing import Manager
        manager = Manager()
        self.bet_lock: LockType = manager.Lock()  # Type hint added
    
    def setup_database(self):
        """Create database tables."""
        self.logger.info("Setting up betting database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Betting history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmaker TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                bet_amount REAL NOT NULL,
                auto_stop REAL,
                final_score REAL,
                money_before REAL,
                money_after REAL,
                profit REAL,
                status TEXT
            )
        ''')
        
        # Index
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bets_bookmaker 
            ON bets(bookmaker, timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Betting database ready: {self.db_path}")
    
    def get_betting_strategy(self) -> Dict:
        """Get betting strategy from user."""
        print("\n" + "="*60)
        print("BETTING STRATEGY CONFIGURATION")
        print("="*60)
        
        strategy = {}
        
        # Bet amount
        while True:
            try:
                bet_amount = float(input("\nBet amount: ").strip())
                if bet_amount > 0:
                    strategy['bet_amount'] = bet_amount
                    break
                print("Bet amount must be positive")
            except ValueError:
                print("Invalid input")
        
        # Auto stop
        use_auto_stop = input("\nUse auto stop? (yes/no): ").strip().lower()
        if use_auto_stop in ['yes', 'y']:
            while True:
                try:
                    auto_stop = float(input("Auto stop multiplier (e.g., 2.0): ").strip())
                    if auto_stop > 1.0:
                        strategy['auto_stop'] = auto_stop
                        break
                    print("Auto stop must be > 1.0")
                except ValueError:
                    print("Invalid input")
        else:
            strategy['auto_stop'] = None
        
        # Betting mode
        print("\nBetting mode:")
        print("  1. Every round")
        print("  2. Skip N rounds after loss")
        print("  3. Martingale (double after loss)")
        
        mode = input("Mode (1-3): ").strip()
        strategy['mode'] = mode
        
        if mode == '2':
            skip_rounds = int(input("Skip how many rounds after loss? ").strip())
            strategy['skip_rounds'] = skip_rounds
        
        return strategy
    
    def create_process(
        self, 
        bookmaker: str,
        layout: str,
        position: str,
        coords: Dict,
        **kwargs
    ) -> Optional[Process]:
        """Create betting process for bookmaker."""
        strategy = kwargs.get('strategy', {})
        
        process = BettingProcess(
            bookmaker_name=bookmaker,
            coords=coords,
            db_path=self.db_path,
            strategy=strategy,
            bet_lock=self.bet_lock,
            shutdown_event=self.shutdown_event
        )
        return process
    
    def run(self):
        """Main run method."""
        print("\n" + "="*60)
        print("🎮 BETTING AGENT v2.0")
        print("="*60)
        print("\nAutomated bet placement with:")
        print("  • Configurable strategy")
        print("  • Transaction-safe betting")
        print("  • Full history logging")
        print("="*60)
        
        # Setup database
        self.setup_database()
        
        # Get betting strategy
        strategy = self.get_betting_strategy()
        
        # Get number of bookmakers
        num_bookmakers = get_number_input(
            "\nHow many bookmakers to bet on? (1-6): ", 1, 6
        )
        
        # Setup bookmakers
        bookmakers_config = self.setup_bookmakers_interactive(num_bookmakers)
        
        # Verify regions
        if not self.verify_regions(bookmakers_config):
            return
        
        # Confirm before starting
        print("\n" + "="*60)
        print("⚠️  WARNING: Betting will start automatically!")
        print("="*60)
        print(f"Strategy: {strategy}")
        print(f"Bookmakers: {len(bookmakers_config)}")
        confirm = input("\nStart betting? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("Cancelled")
            return
        
        # Start processes
        self.start_processes(bookmakers_config, strategy=strategy)
        
        # Wait
        print("\n🎮 Betting active... (Ctrl+C to stop)")
        self.wait_for_processes()


class BettingProcess(Process):
    """Worker process for automated betting."""
    
    def __init__(
        self, 
        bookmaker_name: str,
        coords: Dict,
        db_path: Path,
        strategy: Dict,
        bet_lock: LockType,  # Fixed type hint
        shutdown_event
    ):
        super().__init__(name=f"BettingAgent-{bookmaker_name}")
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.db_path = db_path
        self.strategy = strategy
        self.bet_lock = bet_lock
        self.shutdown_event = shutdown_event
        
        self.bet_queue = Queue(maxsize=100)
    
    def setup_components(self):
        """Setup readers and controller."""
        # Screen readers
        self.score_reader = ScreenReader(self.coords['score_region'])
        self.my_money_reader = ScreenReader(self.coords['my_money_region'])
        self.phase_reader = ScreenReader(self.coords['phase_region'])
        
        self.score = Score(self.score_reader)
        self.my_money = MyMoney(self.my_money_reader)
        self.phase_detector = GamePhaseDetector(self.phase_reader)
        
        # GUI controller
        self.gui = GUIController()
    
    def place_bet(self, bet_amount: float, auto_stop: Optional[float]):
        """
        Place a bet (transaction-safe).
        
        Args:
            bet_amount: Amount to bet
            auto_stop: Auto stop multiplier (or None)
        """
        logger = AviatorLogger.get_logger(f"BettingAgent-{self.bookmaker_name}")
        
        # Acquire lock - only one bet at a time across all processes
        with self.bet_lock:
            try:
                money_before = self.my_money.read_money()
                
                # Click bet amount field
                bet_coords = self.coords['bet_amount_coords']
                center_x = bet_coords['left'] + bet_coords['width'] // 2
                center_y = bet_coords['top'] + bet_coords['height'] // 2
                
                self.gui.click(center_x, center_y)
                time.sleep(0.1)
                
                # Clear and enter amount
                self.gui.clear_field()
                self.gui.type_text(str(bet_amount))
                time.sleep(0.1)
                
                # Set auto stop if needed
                if auto_stop:
                    auto_coords = self.coords['auto_play_coords']
                    auto_x = auto_coords['left'] + auto_coords['width'] // 2
                    auto_y = auto_coords['top'] + auto_coords['height'] // 2
                    
                    self.gui.click(auto_x, auto_y)
                    time.sleep(0.1)
                    self.gui.clear_field()
                    self.gui.type_text(str(auto_stop))
                    time.sleep(0.1)
                
                # Click play button
                play_coords = self.coords['play_button_coords']
                play_x = play_coords['left'] + play_coords['width'] // 2
                play_y = play_coords['top'] + play_coords['height'] // 2
                
                self.gui.click(play_x, play_y)
                
                logger.info(f"Bet placed: {bet_amount} (auto stop: {auto_stop})")
                
                # Wait for round to finish
                time.sleep(2)
                while self.phase_detector.get_phase() == 'FLYING':
                    time.sleep(0.2)
                
                # Get final results
                time.sleep(1)
                final_score = self.score.read_score()
                money_after = self.my_money.read_money()
                
                profit = (money_after or 0) - (money_before or 0)
                status = 'WIN' if profit > 0 else 'LOSS'
                
                # Log bet
                self.bet_queue.put({
                    'bookmaker': self.bookmaker_name,
                    'timestamp': datetime.now().isoformat(),
                    'bet_amount': bet_amount,
                    'auto_stop': auto_stop,
                    'final_score': final_score,
                    'money_before': money_before,
                    'money_after': money_after,
                    'profit': profit,
                    'status': status
                })
                
                logger.info(
                    f"Result: {final_score:.2f}x, Profit: {profit:.2f} ({status})"
                )
                
            except Exception as e:
                logger.error(f"Bet placement error: {e}", exc_info=True)
    
    def betting_loop(self):
        """Main betting loop."""
        logger = AviatorLogger.get_logger(f"BettingAgent-{self.bookmaker_name}")
        logger.info("Starting betting agent")
        
        bet_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                # Wait for WAITING phase
                current_phase = self.phase_detector.get_phase()
                
                if current_phase == 'WAITING':
                    # Place bet
                    bet_amount = self.strategy.get('bet_amount', 100)
                    auto_stop = self.strategy.get('auto_stop')
                    
                    self.place_bet(bet_amount, auto_stop)
                    bet_count += 1
                    
                    # Batch insert
                    if self.bet_queue.qsize() >= 10:
                        self.batch_insert_bets()
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Betting loop error: {e}", exc_info=True)
                time.sleep(1)
        
        # Final batch insert
        self.batch_insert_bets()
        logger.info(f"Betting finished. Total bets: {bet_count}")
    
    def batch_insert_bets(self):
        """Batch insert bet history."""
        if self.bet_queue.empty():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        batch = []
        while not self.bet_queue.empty():
            try:
                batch.append(self.bet_queue.get_nowait())
            except:
                break
        
        if batch:
            cursor.executemany('''
                INSERT INTO bets 
                (bookmaker, timestamp, bet_amount, auto_stop, final_score, 
                 money_before, money_after, profit, status)
                VALUES 
                (:bookmaker, :timestamp, :bet_amount, :auto_stop, :final_score,
                 :money_before, :money_after, :profit, :status)
            ''', batch)
            
            conn.commit()
        
        conn.close()
    
    def run(self):
        """Process main loop."""
        logger = AviatorLogger.get_logger(f"BettingAgent-{self.bookmaker_name}")
        logger.info(f"Starting betting agent for {self.bookmaker_name}")
        
        try:
            self.setup_components()
            self.betting_loop()
        except Exception as e:
            logger.error(f"Process error: {e}", exc_info=True)
        finally:
            logger.info(f"Betting agent stopped: {self.bookmaker_name}")


if __name__ == "__main__":
    app = BettingAgent()
    app.run()