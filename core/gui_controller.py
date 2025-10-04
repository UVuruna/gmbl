# gui_controller.py
# VERSION: 2.1
# CHANGES: Added pause after bet execution, improved shutdown handling

import threading
import time
import queue
from typing import Optional, Tuple
from dataclasses import dataclass
import pyautogui
from logger import AviatorLogger


@dataclass
class BettingRequest:
    """Request for GUI betting action"""
    bookmaker_name: str
    bet_amount: int
    play_amount_coords: Tuple[int, int]
    play_button_coords: Tuple[int, int]
    request_id: str
    timestamp: float


class GUIController:
    """
    Centralized GUI controller - handles all mouse/keyboard.
    
    CRITICAL: Only one bet at a time, with proper pauses between actions.
    This prevents continuous mouse control and allows graceful shutdown.
    """
    
    PYAUTOGUI_SETTINGS = {
        'PAUSE': 0.1,
        'FAILSAFE': True,
        'MINIMUM_DURATION': 0.1
    }
    
    # CRITICAL: Pause after bet execution to release mouse control
    BET_COMPLETION_PAUSE = 2.0  # seconds
    
    def __init__(
        self,
        betting_queue
    ):
        self.betting_queue = betting_queue
        self.is_running = False
        self.controller_thread = None
        self.total_bets_placed = 0
        self.total_errors = 0
        self.logger = AviatorLogger.get_logger("GUIController")
        
        for setting, value in self.PYAUTOGUI_SETTINGS.items():
            setattr(pyautogui, setting, value)
    
    def start(self) -> None:
        if self.is_running:
            return
        
        self.is_running = True
        self.controller_thread = threading.Thread(
            target=self._controller_loop,
            name="GUIController",
            daemon=False
        )
        self.controller_thread.start()
        self.logger.info("GUI Controller started")
    
    def stop(self) -> None:
        if not self.is_running:
            return
        
        self.logger.info("Stopping GUI Controller...")
        self.is_running = False
        
        if self.controller_thread and self.controller_thread.is_alive():
            self.controller_thread.join(timeout=5.0)
        
        self.logger.info(f"GUI Controller stopped. Bets placed: {self.total_bets_placed}, Errors: {self.total_errors}")
    
    def _controller_loop(self) -> None:
        self.logger.info("GUI Controller loop started")
        
        while self.is_running:
            try:
                request = self._get_betting_request(timeout=0.1)
                if request:
                    self._process_betting_request(request)
                    
                    # CRITICAL FIX: Pause after each bet to release mouse control
                    # This allows:
                    # 1. User to regain mouse control
                    # 2. Graceful shutdown via Ctrl+C
                    # 3. System to process other events
                    if self.is_running:
                        time.sleep(self.BET_COMPLETION_PAUSE)
                        
            except Exception as e:
                self.logger.error(f"Loop error: {e}", exc_info=True)
                time.sleep(0.5)
        
        self.logger.info("GUI Controller loop finished")
    
    def _get_betting_request(self, timeout: float = 0.1) -> Optional[BettingRequest]:
        try:
            return self.betting_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _process_betting_request(self, request: BettingRequest) -> None:
        self.logger.info(f"Processing bet for {request.bookmaker_name}: {request.bet_amount}")
        
        try:
            success = self._execute_bet(
                request.bet_amount,
                request.play_amount_coords,
                request.play_button_coords
            )
            
            if success:
                self.total_bets_placed += 1
                self.logger.info(f"✓ Bet placed for {request.bookmaker_name}")
            else:
                self.total_errors += 1
                self.logger.error(f"✗ Failed to place bet for {request.bookmaker_name}")
                
        except Exception as e:
            self.total_errors += 1
            self.logger.error(f"Error placing bet for {request.bookmaker_name}: {e}", exc_info=True)
        
        try:
            self.betting_queue.task_done()
        except ValueError:
            pass  # Queue already empty
    
    def _execute_bet(self, amount: int, play_amount_coords: Tuple[int, int], 
                     play_button_coords: Tuple[int, int]) -> bool:
        """
        Execute a single bet action.
        
        This is a TRANSACTIONAL operation - either completes fully or fails.
        No other betting operations can occur while this executes.
        """
        try:
            # Click on amount field
            pyautogui.click(play_amount_coords)
            time.sleep(0.15)
            
            # Select all and type new amount
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            
            pyautogui.typewrite(str(amount), interval=0.05)
            time.sleep(0.2)
            
            # Click play button
            pyautogui.click(play_button_coords)
            time.sleep(0.1)
            
            self.logger.debug(f"Executed bet: amount={amount}, coords={play_amount_coords}, button={play_button_coords}")
            return True
            
        except pyautogui.FailSafeException:
            self.logger.warning("Fail-safe triggered - mouse moved to corner")
            return False
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return False