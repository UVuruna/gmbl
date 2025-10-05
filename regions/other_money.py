# regions/other_money.py
# VERSION: 5.0
# CHANGES: Advanced OCR integration

from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger
from typing import Optional


class OtherMoney(Region):
    """
    Other money reader with advanced OCR.
    VERSION: 5.0
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("OtherMoney")
        
        # Set OCR type for medium money text
        self.screen_reader.ocr_type = 'money_medium'
    
    def read_text(self) -> Optional[float]:
        """Read total money using advanced OCR."""
        try:
            money = self.screen_reader.read_with_advanced_ocr('money_medium')
            
            if money is not None:
                self.logger.debug(f"Other money: {money:.2f}")
            
            return money
            
        except Exception as e:
            self.logger.error(f"Error reading other money: {e}")
            return None