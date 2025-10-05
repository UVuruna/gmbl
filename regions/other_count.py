# regions/other_count.py
# VERSION: 5.0
# CHANGES: Advanced OCR integration

from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger
from typing import Optional, Tuple


class OtherCount(Region):
    """
    Player count reader with advanced OCR.
    VERSION: 5.0
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("OtherCount")
        
        # Set OCR type for tiny player count text
        self.screen_reader.ocr_type = 'player_count'
    
    def read_text(self) -> Optional[Tuple[int, int]]:
        """Read player count using advanced OCR."""
        try:
            result = self.screen_reader.read_with_advanced_ocr('player_count')
            
            if result is not None:
                current, total = result
                self.logger.debug(f"Player count: {current}/{total}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading player count: {e}")
            return None
    
    def get_current_count(self) -> Optional[int]:
        """Get current player count."""
        result = self.read_text()
        return result[0] if result else None
    
    def get_total_count(self) -> Optional[int]:
        """Get total player count."""
        result = self.read_text()
        return result[1] if result else None