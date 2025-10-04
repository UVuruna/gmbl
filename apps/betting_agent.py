# betting_agent.py
# Lightweight betting agent - samo prati GamePhase, Score, MyMoney i betuje

from main.screen_reader import ScreenReader
from main.gui_controller import GUIController, BettingRequest
from main.coord_manager import CoordsManager
from regions.game_phase import GamePhaseDetector
from regions.score import Score
from regions.region_MyMoney import MyMoney
from config import GamePhase, BookmakerConfig, AppConstants
from root.logger import init_logging, AviatorLogger

import multiprocessing as mp
from multiprocessing import Manager, Process, Queue
import time
import signal
import sys


class BettingWorker(Process):
    """Lightweight worker - samo prati fazu i betuje"""
    
    def __init__(
        self,
        bookmaker_name: str,
        betting_queue: Queue,
        shutdown_event,
        play_amount_coords: tuple,
        play_button_coords: tuple,
        bet_sequence: list,
        auto_stop: float,
        phase_region: dict,
        score_region: dict,
        my_money_region: dict
    ):
        super().__init__(name=f"Bet-{bookmaker_name}")
        
        self.bookmaker_name = bookmaker_name
        self.betting_queue = betting_queue
        self.shutdown_event = shutdown_event
        
        self.play_amount_coords = play_amount_coords
        self.play_button_coords = play_button_coords
        self.bet_sequence = bet_sequence
        self.auto_stop = auto_stop
        
        self.phase_region = phase_region
        self.score_region = score_region
        self.my_money_region = my_money_region
        
        self.current_bet_index = 0
        self.bet_placed_for_round = False
        self.current_phase = None
        self.previous_phase = None
        
        self.logger = None
        self.phase_detector = None
        self.score_reader = None
        self.money_reader = None
    
    def run(self):
        init_logging()
        self.logger = AviatorLogger.get_logger(f"BetAgent-{self.bookmaker_name}")
        self.logger.info(f"Betting agent started for {self.bookmaker_name}")
        
        # Initialize readers
        self.phase_detector = GamePhaseDetector(self.phase_region)
        self.score_reader = Score(
            self.score_region,
            self.my_money_region,
            self.auto_stop
        )
        self.money_reader = MyMoney(self.my_money_region)
        
        try:
            while not self.shutdown_event.is_set():
                self._betting_cycle()
                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Agent error: {e}", exc_info=True)
        finally:
            self.logger.info(f"Betting agent stopped for {self.bookmaker_name}")
    
    def _betting_cycle(self):
        """Main betting cycle"""
        # Read phase
        self.previous_phase = self.current_phase
        self.current_phase = self.phase_detector.detect_phase()
        
        # Phase transition detection
        if self.current_phase != self.previous_phase:
            self.logger.info(f"Phase: {self.previous_phase} → {self.current_phase}")
            
            # WAITING → COUNTDOWN: place bet
            if self.current_phase == GamePhase.WAITING:
                self.bet_placed_for_round = False
            
            if self.current_phase == GamePhase.COUNTDOWN and not self.bet_placed_for_round:
                self._place_bet()
            
            # CRASHED → RESULT: check outcome
            if self.current_phase == GamePhase.CRASHED:
                self._check_outcome()
    
    def _place_bet(self):
        """Place bet for next round"""
        bet_amount = self.bet_sequence[self.current_bet_index]
        
        request = BettingRequest(
            bookmaker_name=self.bookmaker_name,
            bet_amount=bet_amount,
            play_amount_coords=self.play_amount_coords,
            play_button_coords=self.play_button_coords,
            request_id=f"{self.bookmaker_name}_{time.time()}",
            timestamp=time.time()
        )
        
        try:
            self.betting_queue.put(request, timeout=1.0)
            self.bet_placed_for_round = True
            self.logger.info(f"Bet placed: {bet_amount} RSD (index: {self.current_bet_index})")
        except:
            self.logger.warning("Betting queue full")
    
    def _check_outcome(self):
        """Check round outcome"""
        try:
            score_data = self.score_reader.read_text()
            money_data = self.money_reader.read_text()
            
            if score_data and 'result' in score_data:
                result = score_data['result']
                final_score = score_data['score']
                current_money = money_data.get('money', 0) if money_data else 0
                
                if result:
                    self.logger.info(f"WIN! Score: {final_score:.2f}x, Money: {current_money:.2f}")
                    self.current_bet_index = 0  # Reset on win
                else:
                    self.logger.info(f"LOSS. Score: {final_score:.2f}x, Money: {current_money:.2f}")
                    self.current_bet_index = (self.current_bet_index + 1) % len(self.bet_sequence)
        except Exception as e:
            self.logger.error(f"Error checking outcome: {e}")


class BettingAgentOrchestrator:
    """Orchestrator for betting agents"""
    
    def __init__(self):
        self.manager = Manager()
        self.betting_queue = self.manager.Queue(maxsize=100)
        self.shutdown_event = self.manager.Event()
        
        self.gui_controller = None
        self.workers = []
        self.logger = None
    
    def add_bookmaker(
        self,
        name: str,
        auto_stop: float,
        bet_sequence: list,
        play_amount_coords: tuple,
        play_button_coords: tuple,
        phase_region: dict,
        score_region: dict,
        my_money_region: dict
    ):
        """Add betting worker"""
        worker = BettingWorker(
            bookmaker_name=name,
            betting_queue=self.betting_queue,
            shutdown_event=self.shutdown_event,
            play_amount_coords=play_amount_coords,
            play_button_coords=play_button_coords,
            bet_sequence=bet_sequence,
            auto_stop=auto_stop,
            phase_region=phase_region,
            score_region=score_region,
            my_money_region=my_money_region
        )
        self.workers.append(worker)
        self.logger.info(f"Added betting worker: {name}")
    
    def start(self):
        """Start all workers"""
        init_logging()
        self.logger = AviatorLogger.get_logger("BettingOrchestrator")
        self.logger.info("Starting betting agent orchestrator")
        
        # Start GUI controller
        self.gui_controller = GUIController(self.betting_queue)
        self.gui_controller.start()
        self.logger.info("GUI controller started")
        
        # Start workers
        for worker in self.workers:
            worker.start()
            self.logger.info(f"Started: {worker.name}")
        
        self.logger.info(f"Betting agent running with {len(self.workers)} bookmakers")
    
    def stop(self):
        """Stop all workers"""
        self.logger.info("Stopping betting agent...")
        
        self.shutdown_event.set()
        
        if self.gui_controller:
            self.gui_controller.stop()
        
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=3.0)
                if worker.is_alive():
                    worker.terminate()
        
        self.manager.shutdown()
        self.logger.info("Betting agent stopped")


def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("\nShutting down betting agent...")
    if orchestrator:
        orchestrator.stop()
    sys.exit(0)


orchestrator = None

def main():
    global orchestrator
    
    signal.signal(signal.SIGINT, signal_handler)
    
    init_logging()
    logger = AviatorLogger.get_logger("Main")
    logger.info("=" * 60)
    logger.info("BETTING AGENT - LIGHTWEIGHT BETTING SYSTEM")
    logger.info("=" * 60)
    
    try:
        coords_manager = CoordsManager()
        
        # Load bookmaker configurations
        config_name = input("Configuration name (e.g., '3_bookmakers_console'): ").strip()
        bookmakers = ['Left', 'Center', 'Right']  # Positions
        
        orchestrator = BettingAgentOrchestrator()
        
        for position in bookmakers:
            try:
                coords = coords_manager.load_coordinates(config_name, position)
                
                # Choose betting style
                print(f"\nBetting style for {position}:")
                print("1=Cautious, 2=Balanced, 3=Risky, 4=Crazy, 5=Addict, 6=All-in")
                choice = int(input("Choose (1-6): ") or "2")
                
                styles = {
                    1: BookmakerConfig.bet_style['cautious'],
                    2: BookmakerConfig.bet_style['balanced'],
                    3: BookmakerConfig.bet_style['risky'],
                    4: BookmakerConfig.bet_style['crazy'],
                    5: BookmakerConfig.bet_style['addict'],
                    6: BookmakerConfig.bet_style['all-in']
                }
                bet_sequence = styles.get(choice, BookmakerConfig.bet_style['balanced'])
                
                orchestrator.add_bookmaker(
                    name=position,
                    auto_stop=BookmakerConfig.auto_stop,
                    bet_sequence=bet_sequence,
                    play_amount_coords=coords['play_amount_coords'],
                    play_button_coords=coords['play_button_coords'],
                    phase_region=coords['phase_region'],
                    score_region=coords['score_region'],
                    my_money_region=coords['my_money_region']
                )
            except Exception as e:
                logger.warning(f"Could not load {position}: {e}")
        
        if len(orchestrator.workers) == 0:
            logger.error("No bookmakers configured!")
            return
        
        orchestrator.start()
        
        # Keep alive
        while True:
            time.sleep(1)
    
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        if orchestrator:
            orchestrator.stop()


if __name__ == "__main__":
    main()
