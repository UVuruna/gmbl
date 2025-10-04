# region_MyMoney.py

from config import AppConstants
from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger

from typing import Optional


class MyMoney(Region):
    """
    This class reads region showing our current money.
    Used for tracking our own money in the game and confirming WIN or LOSS.
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("MyMoney")
    
    def read_text(self) -> Optional[float]:
        """
        Reads the current money and returns it as a float.
        
        Returns:
            Optional[float]: Current money amount, None if error occurs
        """
        try:
            text = self._get_raw_text()
            if not text:
                if AppConstants.debug:
                    self.logger.warning("Empty text received from MyMoney screen reader")
                return None
                
            money_amount = self._extract_number_from_text(text)
            self._log_debug_info(money_amount)
            
            return money_amount
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error reading my money: {e}")
            return None
    
    def _get_raw_text(self) -> str:
        """Get raw text from screen reader."""
        text = self.screen_reader.read_once()
        return text if text is not None else ""
    
    def _log_debug_info(self, amount: float) -> None:
        """Log debug information if AppConstants.debug is enabled."""
        if AppConstants.debug:
            self.logger.debug(f"Trenutno stanje novca (Našeg): {amount}")