# region_OtherMoney.py

from config import AppConstants
from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger

from typing import Optional


class OtherMoney(Region):
    """
    This class reads the total money earned from all players from that round.
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("OtherMoney")
    
    def read_text(self) -> Optional[float]:
        """
        Reads the total money from all players and returns it as a float.
        
        Returns:
            Optional[float]: Total money amount from all players, None if error occurs
        """
        try:
            text = self._get_raw_text()
            if not text:
                if AppConstants.debug:
                    self.logger.warning("Empty text received from OtherMoney screen reader")
                return 0.0
                
            total_money = self._extract_number_from_text(text)
            self._log_debug_info(total_money)
            
            return total_money
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error reading other money: {e}")
            return None
    
    def _get_raw_text(self) -> str:
        """Get raw text from screen reader."""
        text = self.screen_reader.read_once()
        return text if text is not None else ""
    
    
    def _log_debug_info(self, amount: float) -> None:
        """Log debug information if AppConstants.debug is enabled."""
        if AppConstants.debug:
            self.logger.debug(f"Ukupni novac od svih igrača: {amount}")