# region_Score.py

from config import AppConstants, GamePhase
from main.screen_reader import ScreenReader
from regions.base_region import Region
from regions.game_phase import GamePhaseDetector
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.region_MyMoney import MyMoney
from root.logger import AviatorLogger

from typing import Dict, Optional, Union


class Score(Region): 
    """
    This class reads the score from the game screen and interacts with other regions 
    to get additional information. It can return different types of information 
    based on the current state of the game.
    """
    
    STARTING_TEXT = ['official', 'partners']
    WINNING_TEXT = ['flew away!', 'odleteo!'] 
    THRESHOLDS = [1.25, 1.50, 1.75, 2.00, 2.25, 2.50, 3.00, 3.50, 4.00, 5.00] 
    
     
    def __init__(
        self, 
        screen_reader: ScreenReader,
        my_money: MyMoney,
        other_count: OtherCount,
        other_money: OtherMoney,
        phase_detector: GamePhaseDetector,
        auto_stop: float
    ): 
        super().__init__(screen_reader) 
        
        self.logger = AviatorLogger.get_logger("Score")
        self.temp_thresholds = None
        self.my_money = my_money
        self.other_count = other_count
        self.other_money = other_money
        self.phase_detector = phase_detector
        self.auto_stop = auto_stop
 
    def read_text(self) -> Optional[Dict]:
        """
        Main method that reads the score and returns different types of information 
        based on the game state.
        """
        try:
            # Detect phase
            phase = self.phase_detector.get_phase()
            
            if phase == GamePhase.ENDED:
                text = self._get_screen_text()
                return self._handle_finished_game(text)
            
            elif phase in [GamePhase.LOADING, GamePhase.BETTING]:
                return self._handle_game_starting()
            
            elif phase in [GamePhase.SCORE_LOW, GamePhase.SCORE_MID, GamePhase.SCORE_HIGH]:
                text = self._get_screen_text()
                return self._handle_running_game(text, phase)
            
            return None
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error reading text: {e}")
            return None
    
    def _validate_score_by_phase(self, score: float, phase: GamePhase) -> bool:
        """Validate OCR score against phase"""
        if phase == GamePhase.SCORE_LOW:
            return 1.0 <= score < 2.0
        elif phase == GamePhase.SCORE_MID:
            return 2.0 <= score < 10.0
        elif phase == GamePhase.SCORE_HIGH:
            return score >= 10.0
        return False
    
    def _get_screen_text(self) -> str:
        """Get and normalize text from screen reader."""
        text = self.screen_reader.read_once()
        return text.lower() if text else ""
    
    def _is_game_finished(self, text: str) -> bool:
        """Check if the game has finished."""
        return any(winning_text in text for winning_text in self.WINNING_TEXT)
    
    def _is_game_starting(self, text: str) -> bool:
        """Check if the game hasn't started yet."""
        return any(starting_text in text for starting_text in self.STARTING_TEXT)
    
    def _is_game_running(self, text: str) -> bool:
        """Check if the game is currently running (has content and is not empty)."""
        return bool(text.strip())
    
    
    def _handle_finished_game(self, text: str) -> Optional[Dict[str, Union[bool, float, int]]]:
        """Handle the case when game has finished."""
        try:
            
            score = self._extract_number_from_text(text)
            
            result = score > self.auto_stop
            money = self.my_money.read_text()
            total_players = self.other_count.get_total_count()
            total_win = self.other_money.read_text()
            
            self._log_debug_info_finished(score, money)
            
            return {
                'result': result, 
                'score': score, 
                'my_money': money,
                'total_players': total_players,
                'total_win': total_win
            }
            
        except (ValueError, AttributeError) as e:
            if AppConstants.debug:
                self.logger.error(f"Error handling finished game: {e}")
            return None
    
    def _handle_running_game(self, text: str, phase: GamePhase) -> Optional[Dict[str, Union[float, int]]]:
        """Handle the case when game is currently running."""
        try:
            current_score = self._extract_number_from_text(text)
            
            if not self._validate_score_by_phase(current_score, phase):
                if AppConstants.debug:
                    self.logger.warning(f"Score {current_score} does not match phase {phase.name}")
                return None

            return self._check_thresholds(current_score)
        
        except ValueError as e:
            if AppConstants.debug:
                self.logger.error(f"Error handling running game: {e}")
            return None
    
    def _handle_game_starting(self) -> None:
        """
        Handle the case when game hasn't started.
        Reset thresholds for the new round.
        After this, there are about 8 seconds until the next round starts.
        """
        self.temp_thresholds = self.THRESHOLDS.copy()
        if AppConstants.debug:
            self.logger.debug("Game starting - resetting thresholds")
        return None
    
    def _handle_game_loading(self) -> None:
        """
        Handle the case when round is starting (empty screen).
        
        In future, could implement time measuring mechanism here
        for loading times and their impact on results.
        """
        if AppConstants.debug:
            self.logger.debug("Round starting - waiting for game to begin")
        return None
    
    def _check_thresholds(self, current_score: float) -> Optional[Dict[str, Union[float, int]]]:
        """
        Check if current score has crossed any threshold and return threshold data.
        Only processes the first crossed threshold to maintain order.
        """
        if not self.temp_thresholds:
            return None
            
        for threshold in self.temp_thresholds[:]:
            if self._is_threshold_crossed(current_score, threshold):
                return self._get_threshold_data(threshold)
        
        return None
    
    def _is_threshold_crossed(self, current_score: float, threshold: float) -> bool:
        """Check if a specific threshold has been crossed."""
        return current_score >= threshold
    
    def _get_threshold_data(self, threshold: float) -> Optional[Dict[str, Union[float, int]]]:
        """Get data when a threshold is crossed."""
        try:
            self.temp_thresholds.remove(threshold)
            
            player_count = self.other_count.get_current_count()
            money = self.other_money.read_text()
            
            if not (player_count and money):
                raise ValueError("Can't get player count or money at threshold")
            
            self._log_debug_info_threshold(threshold, player_count, money)
            
            return {
                'current_score': threshold, 
                'current_players': player_count, 
                'current_players_win': money
            }
        except (ValueError, IndexError, AttributeError) as e:
            if AppConstants.debug:
                self.logger.error(f"Error getting threshold data: {e}")
            return None
    
    def _log_debug_info_threshold(self, threshold: float, player_count: int, money: float) -> None:
        """Log debug information for score in progress if AppConstants.debug is enabled."""
        if AppConstants.debug: 
            self.logger.debug(f"Prošao je threshold: {threshold} ; igrača: {player_count} ; zarada: {money}")
            
    def _log_debug_info_finished(self, score: float, money: float) -> None:
        """Log debug information for finished score if AppConstants.debug is enabled."""
        if AppConstants.debug: 
            self.logger.debug(f"Završena runda sa rezultatom: {score} ; novčano stanje: {money}")
    
    
    '''     Utility methods for testing and debugging     '''
    
    
    def reset_thresholds(self) -> None:
        """Manually reset thresholds - useful for testing or manual control."""
        self.temp_thresholds = self.THRESHOLDS.copy()
        if AppConstants.debug:
            self.logger.debug("Thresholds manually reset")
    
    def get_remaining_thresholds(self) -> Optional[list]:
        """Get list of remaining thresholds - useful for debugging."""
        return self.temp_thresholds.copy() if self.temp_thresholds else None