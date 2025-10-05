# regions/my_money.py
# VERSION: 5.0
# CHANGES: Advanced OCR integration

from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger
from typing import Optional


class MyMoney(Region):
    """
    My money reader with advanced OCR.
    VERSION: 5.0
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("MyMoney")
        
        # Set OCR type for small money text
        self.screen_reader.ocr_type = 'money_small'
    
    def read_text(self) -> Optional[float]:
        """Read money using advanced OCR."""
        try:
            money = self.screen_reader.read_with_advanced_ocr('money_small')
            
            if money is not None:
                self.logger.debug(f"My money: {money:.2f}")
            
            return money
            
        except Exception as e:
            self.logger.error(f"Error reading my money: {e}")
            return None