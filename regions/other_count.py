# region_OtherCount.py

from config import AppConstants
from main.screen_reader import ScreenReader
from regions.base_region import Region
from root.logger import AviatorLogger

from typing import Tuple, Optional


class OtherCount(Region):
    """
    This class reads the count of other players from the game screen.
    Both current and total player counts are returned as a tuple of integers.
    """
    
    def __init__(self, screen_reader: ScreenReader):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("OtherCount")
        
    def read_text(self) -> Optional[Tuple[int, int]]:
        """
        Reads the count of other players and returns it as a tuple (current, total).
        
        Returns:
            Optional[Tuple[int, int]]: (current_players, total_players), None if error occurs
        """
        try:
            text = self._get_raw_text()
            if not text:
                if AppConstants.debug:
                    self.logger.warning("Empty text received from OtherCount screen reader")
                return (0, 0)
                
            current_count, total_count = self._parse_player_counts(text)
            self._log_debug_info(current_count, total_count)
            return (current_count, total_count)
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error reading player count: {e}")
            return None
    
    def _get_raw_text(self) -> str:
        """Get raw text from screen reader."""
        text = self.screen_reader.read_once()
        return text if text is not None else ""
    
    def _parse_player_counts(self, text: str) -> Tuple[int, int]:
        """
        Parse player counts from text format "current/total" or similar formats.
        
        Args:
            text: Raw text containing player count information
            
        Returns:
            Tuple[int, int]: (current_players, total_players)
            
        Raises:
            ValueError: If text format is invalid or cannot be parsed
        """
        try:
            cleaned_text = text.strip()
            if not cleaned_text:
                raise ValueError("Empty text after stripping")
            
            parts = cleaned_text.split(' ')
            if not parts:
                raise ValueError("No parts found after splitting by space")
                
            count_part = parts[0]
            
            if '/' not in count_part:
                raise ValueError(f"Expected '/' separator in count part '{count_part}'")
                
            count_components = count_part.split('/')
            if len(count_components) != 2:
                raise ValueError(f"Expected exactly 2 components separated by '/', got {count_part}")
            
            current_str, total_str = count_components
            current_count = int(current_str.strip())
            total_count = int(total_str.strip())
            
            if current_count < 0 or total_count < 0:
                raise ValueError(f"Player counts cannot be negative: current={current_count}, total={total_count}")
                
            if current_count > total_count:
                if AppConstants.debug:
                    self.logger.warning(f"Current players ({current_count}) > Total players ({total_count})")
            
            return current_count, total_count
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to parse player counts from '{text}': {e}")
    
    def _log_debug_info(self, current_count: int, total_count: int) -> None:
        """Log debug information if AppConstants.debug is enabled."""
        if AppConstants.debug:
            self.logger.debug(f"Trenutno igra: {current_count}, Ukupno igrača: {total_count}")
    
    
    '''     Utility methods to get individual counts     '''
    
    
    def get_current_count(self) -> Optional[int]:
        """
        Get only the current player count.
        
        Returns:
            Optional[int]: Current player count, None if error occurs
        """
        result = self.read_text()
        return result[0] if result else None
    
    def get_total_count(self) -> Optional[int]:
        """
        Get only the total player count.
        
        Returns:
            Optional[int]: Total player count, None if error occurs
        """
        result = self.read_text()
        return result[1] if result else None