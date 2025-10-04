# coord_getter.py

from config import AppConstants
from logger import AviatorLogger

from pynput import mouse
from typing import Literal, Dict, Tuple, List, Optional


class CoordGetter:
    """
    Interactive coordinate and region selection tool.
    Supports multiple languages and different selection modes.
    """
    
    QUERY_TEXT = {
        'region': {
            'sr': 'Klikni na gornji levi ugao, pa na donji desni ugao elementa',
            'en': 'Click on the top-left corner, then on the bottom-right corner of the element'
        },
        'coordinate': {
            'sr': 'Klikni na lokaciju elementa',
            'en': 'Click on the location of the element'
        },
        'cancel': {
            'sr': 'Pritisnite ESC za otkazivanje',
            'en': 'Press ESC to cancel'
        }
    }
    
    def __init__(
        self, 
        bookmaker_name: str, 
        element_name: str, 
        element_type: Literal['region', 'coordinate']
    ):
        """
        Initialize coordinate getter.
        
        Args:
            bookmaker_name: Name of the bookmaker
            element_name: Name of the element to select
            element_type: Type of selection ('region' or 'coordinate')
        """
        self.bookmaker_name = bookmaker_name
        self.element_name = element_name
        self.element_type = element_type
        
        self._coords: List[Tuple[int, int]] = []
        self._listener: Optional[mouse.Listener] = None
        self._cancelled = False
        
        self.logger = AviatorLogger.get_logger("CoordGetter")
        self._messages = self._get_localized_messages()
    
    def _get_localized_messages(self) -> Dict[str, str]:
        """Get localized messages based on current language."""
        return {
            'prompt': self.QUERY_TEXT[self.element_type][AppConstants.language],
            'cancel': self.QUERY_TEXT['cancel'][AppConstants.language]
        }
    
    def get_region(self) -> Dict[str, int]:
        """
        Get region coordinates through user interaction.
        
        Returns:
            Dictionary with 'left', 'top', 'width', 'height' keys
            
        Raises:
            ValueError: If selection was cancelled or invalid
        """
        if self.element_type != 'region':
            raise ValueError("get_region() can only be used with element_type='region'")
        
        self._start_selection(required_clicks=2)
        
        if self._cancelled or len(self._coords) != 2:
            raise ValueError("Region selection was cancelled or incomplete")
        
        return self._calculate_region()
    
    def get_coordinate(self) -> Tuple[int, int]:
        """
        Get single coordinate through user interaction.
        
        Returns:
            Tuple of (x, y) coordinates
            
        Raises:
            ValueError: If selection was cancelled or invalid
        """
        if self.element_type != 'coordinate':
            raise ValueError("get_coordinate() can only be used with element_type='coordinate'")
        
        self._start_selection(required_clicks=1)
        
        if self._cancelled or len(self._coords) != 1:
            raise ValueError("Coordinate selection was cancelled or incomplete")
        
        return self._coords[0]
    
    def _start_selection(self, required_clicks: int) -> None:
        """Start coordinate selection process."""
        self._coords.clear()
        self._cancelled = False
        
        self._display_instructions()
        self._listen_for_clicks(required_clicks)
    
    def _display_instructions(self) -> None:
        """Display selection instructions to user."""
        print(f"\n{self._messages['prompt']}:")
        print(f"\t>>> {self.bookmaker_name} -- {self.element_name} <<<")
        print(f"{self._messages['cancel']}\n")
    
    def _listen_for_clicks(self, required_clicks: int) -> None:
        """Listen for mouse clicks until required number is reached."""
        def on_click(x: int, y: int, button, pressed: bool) -> bool:
            if not pressed:
                return True
            
            return self._handle_click(x, y, required_clicks)
        
        def on_key_press(key):
            try:
                if hasattr(key, 'name') and key.name == 'esc':
                    self._cancelled = True
                    return False
            except AttributeError:
                pass
            return True
        
        with mouse.Listener(on_click=on_click) as self._listener:
            self._listener.join()
    
    def _handle_click(self, x: int, y: int, required_clicks: int) -> bool:
        """
        Handle mouse click event.
        
        Returns:
            False to stop listener, True to continue
        """
        self._coords.append((x, y))
        click_number = len(self._coords)
        
        if AppConstants.debug:
            self.logger.debug(f"Click {click_number}: ({x}, {y})")
        
        if required_clicks == 2:
            if click_number == 1:
                print(f"✓ Prvi ugao: ({x}, {y}) - Kliknite na drugi ugao")
            elif click_number == 2:
                print(f"✓ Drugi ugao: ({x}, {y}) - Selekcija završena")
        else:
            print(f"✓ Koordinate: ({x}, {y}) - Selekcija završena")
        
        return click_number < required_clicks
    
    def _calculate_region(self) -> Dict[str, int]:
        """Calculate region from two corner coordinates."""
        if len(self._coords) != 2:
            raise ValueError("Exactly 2 coordinates required for region calculation")
        
        (x1, y1), (x2, y2) = self._coords
        
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        
        width = right - left
        height = bottom - top
        
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid region dimensions: {width}x{height}")
        
        region = {
            'left': left,
            'top': top,
            'width': width,
            'height': height
        }
        
        if AppConstants.debug:
            self.logger.debug(f"Calculated region: {region}")
        
        return region