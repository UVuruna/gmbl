# regions/score.py
# VERSION: 5.0
# CHANGES: Integration with AdvancedOCRReader

from config import GamePhase
from core.screen_reader import ScreenReader
from regions.base_region import Region
from regions.game_phase import GamePhaseDetector
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from regions.my_money import MyMoney
from logger import AviatorLogger

from typing import Dict, Optional


class Score(Region):
    """
    Score reader with advanced OCR.
    VERSION: 5.0
    """
    
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
        self.my_money = my_money
        self.other_count = other_count
        self.other_money = other_money
        self.phase_detector = phase_detector
        self.auto_stop = auto_stop
        
        self.logger = AviatorLogger.get_logger("Score")
        
        # Set OCR type for score
        self.screen_reader.ocr_type = 'score'
    
    def read_text(self) -> Optional[Dict]:
        """Read score using advanced OCR."""
        try:
            phase = self.phase_detector.get_phase()
            
            if phase == GamePhase.ENDED:
                return self._handle_finished_game()
            
            elif phase in [GamePhase.LOADING, GamePhase.BETTING]:
                return self._handle_game_starting()
            
            elif phase in [GamePhase.SCORE_LOW, GamePhase.SCORE_MID, GamePhase.SCORE_HIGH]:
                return self._handle_running_game(phase)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading score: {e}")
            return None
    
    def _handle_finished_game(self) -> Optional[Dict]:
        """Handle finished game with advanced OCR."""
        try:
            # Use advanced OCR
            score = self.screen_reader.read_with_advanced_ocr('score')
            
            if score is None:
                self.logger.warning("Failed to read final score")
                return None
            
            # Validate score is in reasonable range for finished game
            if not (1.0 <= score <= 1000.0):
                self.logger.warning(f"Suspicious final score: {score}")
                return None
            
            result = score >= self.auto_stop
            money = self.my_money.read_text()
            total_players = self.other_count.get_total_count()
            total_win = self.other_money.read_text()
            
            self.logger.info(
                f"Game ended - Score: {score:.2f}x, "
                f"Result: {'WIN' if result else 'LOSS'}, "
                f"Money: {money}"
            )
            
            return {
                'result': result,
                'score': score,
                'my_money': money,
                'total_players': total_players,
                'total_win': total_win
            }
            
        except Exception as e:
            self.logger.error(f"Error handling finished game: {e}")
            return None
    
    def _handle_running_game(self, phase: GamePhase) -> Optional[Dict]:
        """Handle running game with advanced OCR."""
        try:
            score = self.screen_reader.read_with_advanced_ocr('score')
            
            if score is None:
                return None
            
            # Validate score matches phase
            if not self._validate_score_phase(score, phase):
                self.logger.warning(
                    f"Score {score:.2f} doesn't match phase {phase.name}"
                )
                return None
            
            # Check thresholds...
            # (rest of logic stays the same)
            
            return {
                'current_score': score,
                'phase': phase.name
            }
            
        except Exception as e:
            self.logger.error(f"Error handling running game: {e}")
            return None
    
    def _validate_score_phase(self, score: float, phase: GamePhase) -> bool:
        """Validate score matches expected phase."""
        if phase == GamePhase.SCORE_LOW:
            return 1.0 <= score < 2.0
        elif phase == GamePhase.SCORE_MID:
            return 2.0 <= score < 10.0
        elif phase == GamePhase.SCORE_HIGH:
            return score >= 10.0
        return False