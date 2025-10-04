# bookmaker_process.py

from core.screen_reader import ScreenReader
from core.gui_controller import BettingRequest
from regions.score import Score
from regions.my_money import MyMoney
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.game_phase import GamePhaseDetector
from config import GamePhase
from logger import AviatorLogger

import multiprocessing as mp
from multiprocessing import Process, Queue
from multiprocessing.synchronize import Event as MPEvent
import time
import queue
from typing import Dict, Any, List, Tuple


class BookmakerProcess(Process):
    """Multiprocessing worker for individual bookmaker."""
    
    def __init__(
        self,
        bookmaker_name: str,
        auto_stop: float,
        target_money: float,
        betting_queue: Queue,
        db_queue: Queue,
        shutdown_event: MPEvent,
        play_amount_coords: Tuple[int, int],
        play_button_coords: Tuple[int, int],
        bet_sequence: List[int],
        score_region: Dict[str, int],
        my_money_region: Dict[str, int],
        other_count_region: Dict[str, int],
        other_money_region: Dict[str, int],
        phase_region: Dict[str, int]
    ):
        super().__init__(name=f"{bookmaker_name}-Process")
        
        self.bookmaker_name = bookmaker_name
        self.target_money = target_money
        self.bet_sequence = bet_sequence
        self.auto_stop = auto_stop
        
        self.betting_queue = betting_queue
        self.db_queue = db_queue
        self.shutdown_event = shutdown_event
        
        self.play_amount_coords = play_amount_coords
        self.play_button_coords = play_button_coords
        
        self.score_region = score_region
        self.my_money_region = my_money_region
        self.other_count_region = other_count_region
        self.other_money_region = other_money_region
        self.phase_region = phase_region
        
        self.score = None
        self.my_money = None
        self.phase_detector = None
        self.current_bet_index = 0
        self.current_money = 0.0
        self.round_snapshots = []
        self.rounds_played = 0
        self.logger = None
        
        # STATE MACHINE for betting control
        self.current_phase = None
        self.previous_phase = None
        self.bet_placed_for_current_round = False
        self.round_ended_data = None
    
    def run(self) -> None:
        """Main process loop."""
        self.logger = AviatorLogger.get_logger(f"Bookmaker-{self.bookmaker_name}")
        self.logger.info(f"Process started (PID: {mp.current_process().pid})")
        
        try:
            self._initialize_regions()
            
            while not self.shutdown_event.is_set():
                if self.current_money >= self.target_money:
                    self.logger.info(f"Target reached! Current: {self.current_money}, Target: {self.target_money}")
                    break
                
                try:
                    self._state_machine_loop()
                except Exception as e:
                    self.logger.error(f"State machine error: {e}")
                    time.sleep(0.5)
                
                time.sleep(0.05)
                
        except Exception as e:
            self.logger.critical(f"Critical error: {e}", exc_info=True)
        finally:
            self._cleanup()
            self.logger.info("Process finished")
    
    def _state_machine_loop(self) -> None:
        """State machine for round-based betting control."""
        if not self.phase_detector:
            return
        
        # Get current phase
        self.previous_phase = self.current_phase
        self.current_phase = self.phase_detector.get_phase()
        
        if not self.current_phase:
            return
        
        # STATE 1: ENDED - Round just ended
        if self.current_phase == GamePhase.ENDED and self.previous_phase != GamePhase.ENDED:
            self.logger.info("Phase: ENDED - Round finished, collecting data...")
            self._handle_round_end()
        
        # STATE 2: LOADING - Between rounds
        elif self.current_phase == GamePhase.LOADING:
            if self.previous_phase == GamePhase.ENDED and not self.bet_placed_for_current_round:
                self.logger.info("Phase: LOADING - Placing bet for next round...")
                self._place_bet_once()
        
        # STATE 3: BETTING - New round starting
        elif self.current_phase == GamePhase.BETTING:
            if self.previous_phase in [GamePhase.LOADING, GamePhase.ENDED]:
                self.logger.info("Phase: BETTING - New round started")
                self.bet_placed_for_current_round = False  # Reset for next round
                self.round_snapshots.clear()
        
        # STATE 4-6: SCORE phases - Collect snapshots
        elif self.current_phase in [GamePhase.SCORE_LOW, GamePhase.SCORE_MID, GamePhase.SCORE_HIGH]:
            self._collect_snapshot()
    
    def _handle_round_end(self) -> None:
        """Handle round end - collect data and send to DB."""
        try:
            score_data = self.score.read_text()
            
            if not score_data or 'result' not in score_data:
                self.logger.warning("No valid round end data")
                return
            
            result = score_data.get('result')
            final_score = score_data.get('score')
            self.current_money = score_data.get('my_money', self.current_money)
            
            self.rounds_played += 1
            
            self.logger.info(
                f"Round {self.rounds_played} - "
                f"{'WIN' if result else 'LOSS'}, Score: {final_score:.2f}, Money: {self.current_money:.2f}"
            )
            
            # Save to database
            db_entry = self._create_database_entry(score_data)
            try:
                self.db_queue.put((self.bookmaker_name, db_entry), timeout=1.0)
            except queue.Full:
                self.logger.warning("DB queue full, data may be lost")
            
            # Update bet index based on result
            if result:
                self.current_bet_index = 0  # Reset on win
            else:
                self.current_bet_index = (self.current_bet_index + 1) % len(self.bet_sequence)
            
        except Exception as e:
            self.logger.error(f"Error handling round end: {e}")
    
    def _place_bet_once(self) -> None:
        """Place bet ONCE for the next round."""
        if self.bet_placed_for_current_round:
            return
        
        bet_amount = self.bet_sequence[self.current_bet_index]
        request_id = f"{self.bookmaker_name}_{time.time()}"
        
        betting_request = BettingRequest(
            bookmaker_name=self.bookmaker_name,
            bet_amount=bet_amount,
            play_amount_coords=self.play_amount_coords,
            play_button_coords=self.play_button_coords,
            request_id=request_id,
            timestamp=time.time()
        )
        
        try:
            self.betting_queue.put(betting_request, timeout=1.0)
            self.bet_placed_for_current_round = True
            self.logger.info(f"Bet placed: {bet_amount} RSD (index: {self.current_bet_index})")
        except queue.Full:
            self.logger.warning("Betting queue full")
    
    def _collect_snapshot(self) -> None:
        """Collect snapshot during active round."""
        try:
            score_data = self.score.read_text()
            
            if not score_data or 'current_score' not in score_data:
                return
            
            snapshot = {
                'current_score': score_data.get('current_score'),
                'current_players': score_data.get('current_players'),
                'current_players_win': score_data.get('current_players_win'),
                'timestamp': time.time()
            }
            
            if (not self.round_snapshots or 
                self.round_snapshots[-1]['current_score'] != snapshot['current_score']):
                self.round_snapshots.append(snapshot)
                
        except Exception as e:
            self.logger.debug(f"Snapshot collection error: {e}")
    
    def _initialize_regions(self) -> None:
        """Initialize region readers in child process with retry logic."""
        self.logger.info("Initializing regions...")
        
        try:
            score_reader = ScreenReader(self.score_region)
            my_money_reader = ScreenReader(self.my_money_region)
            other_count_reader = ScreenReader(self.other_count_region)
            other_money_reader = ScreenReader(self.other_money_region)
            phase_reader = ScreenReader(self.phase_region)
            
            my_money = MyMoney(my_money_reader)
            other_count = OtherCount(other_count_reader)
            other_money = OtherMoney(other_money_reader)
            self.phase_detector = GamePhaseDetector(phase_reader)
            
            self.score = Score(
                screen_reader=score_reader,
                my_money=my_money,
                other_count=other_count,
                other_money=other_money,
                phase_detector=self.phase_detector,
                auto_stop=self.auto_stop
            )
            
            self.my_money = my_money
            
            balance_read = False
            for attempt in range(3):
                try:
                    balance = my_money.read_text()
                    if balance is not None and balance > 0:
                        self.current_money = balance
                        self.target_money += balance
                        balance_read = True
                        break
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} to read balance failed: {e}")
                
                time.sleep(0.5)
            
            if not balance_read:
                self.current_money = 0.0
                self.logger.warning("Could not read initial balance, starting at 0")
            
            self.logger.info(f"Initialized successfully, balance: {self.current_money}")
            
        except Exception as e:
            self.logger.critical(f"Region initialization failed: {e}", exc_info=True)
            raise
    
    def _create_database_entry(self, score_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create database entry from round data."""
        try:
            main_data = {
                'bookmaker': self.bookmaker_name,
                'score': score_data.get('score'),
                'total_win': score_data.get('total_win'),
                'total_players': score_data.get('total_players')
            }
            
            earnings_data = {
                'bet_amount': float(self.bet_sequence[self.current_bet_index]),
                'auto_stop': self.auto_stop,
                'balance': float(self.current_money)
            }
            
            return {
                'main': main_data,
                'snapshots': self.round_snapshots.copy(),
                'earnings': earnings_data
            }
            
        except Exception as e:
            self.logger.error(f"Error creating DB entry: {e}", exc_info=True)
            return {
                'main': {
                    'bookmaker': self.bookmaker_name,
                    'score': 0.0,
                    'total_win': 0.0,
                    'total_players': 0
                },
                'snapshots': [],
                'earnings': {
                    'bet_amount': float(self.bet_sequence[self.current_bet_index]),
                    'auto_stop': self.auto_stop,
                    'balance': float(self.current_money)
                }
            }
    
    def _cleanup(self) -> None:
        """Cleanup resources."""
        self.round_snapshots.clear()
        
        if self.score:
            try:
                if hasattr(self.score, 'screen_reader'):
                    self.score.screen_reader.close()
                if hasattr(self.score, 'phase_detector'):
                    self.score.phase_detector.close()
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")