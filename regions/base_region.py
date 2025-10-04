# region.py

from main.screen_reader import ScreenReader

from abc import ABC, abstractmethod
import re


class Region(ABC):  # ABC = Abstract Base Class
    '''
        Abstract base class for different screen regions.
        Each region must implement the read_text method to extract relevant information.
    '''
    def __init__(
        self,
        screen_reader: ScreenReader
    ):
        self.screen_reader = screen_reader

    '''
        Abstract method to read text from the region.
        Must be implemented by subclasses.
    '''
    @abstractmethod
    def read_text(self):
        """Svaka klasa koja nasleđuje mora da implementira ovaj metod"""
        pass
    
    def _extract_number_from_text(self, text: str) -> float:
        """
        Extract current score from running game text.
        
        Removing spaces, 'x' and commas, then converting to float.
        
        Raises ValueError if extraction fails.
        """
        try:
            # Remove spaces, 'x', and commas
            cleaned_text = text.replace(' ', '').replace('x', '').replace(',', '')
            
            # Remove any remaining non-numeric characters except dot
            cleaned_text = re.sub(r'[^0-9.]', '', cleaned_text)
            
            if not cleaned_text:
                raise ValueError("Text is empty after cleaning")
            
            return float(cleaned_text)
        
        except ValueError as e:
            raise ValueError(f"Failed to extract current score from text: {e}")
