# coords_manager.py

"""
Coordinate management system for saving and loading bookmaker screen coordinates.
Organizes coordinates by screen setup (number of bookmakers) and position (Left/Center/Right).
"""

import json
import os
from typing import Dict, Optional, List
from logger import AviatorLogger


class CoordsManager:
    """Manages saving and loading of bookmaker coordinates to/from JSON file."""
    
    DEFAULT_FILE = "bookmaker_coords.json"
    POSITIONS = ["Left", "Center", "Right"]
    
    def __init__(self, coords_file: str = DEFAULT_FILE):
        self.coords_file = coords_file
        self.logger = AviatorLogger.get_logger("CoordsManager")
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Create empty JSON file if it doesn't exist."""
        if not os.path.exists(self.coords_file):
            with open(self.coords_file, 'w') as f:
                json.dump({}, f, indent=2)
            self.logger.info(f"Created new coordinates file: {self.coords_file}")
    
    def save_coordinates(
        self,
        screen_setup: str,
        position: str,
        coordinates: Dict
    ) -> bool:
        """
        Save coordinates for a specific screen setup and position.
        
        Args:
            screen_setup: e.g., "3_bookmakers_console"
            position: "Left", "Center", or "Right"
            coordinates: Dict with all region and coordinate data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load existing data
            data = self._load_json()
            
            # Create screen_setup key if doesn't exist
            if screen_setup not in data:
                data[screen_setup] = {}
            
            # Save coordinates for this position
            data[screen_setup][position] = coordinates
            
            # Write back to file
            with open(self.coords_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved coordinates: {screen_setup} / {position}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving coordinates: {e}", exc_info=True)
            return False
    
    def load_coordinates(
        self,
        screen_setup: str,
        position: str
    ) -> Optional[Dict]:
        """
        Load coordinates for a specific screen setup and position.
        
        Args:
            screen_setup: e.g., "3_bookmakers_console"
            position: "Left", "Center", or "Right"
            
        Returns:
            Dict with coordinates or None if not found
        """
        try:
            data = self._load_json()
            
            if screen_setup in data and position in data[screen_setup]:
                self.logger.info(f"Loaded coordinates: {screen_setup} / {position}")
                return data[screen_setup][position]
            else:
                self.logger.warning(f"Coordinates not found: {screen_setup} / {position}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading coordinates: {e}", exc_info=True)
            return None
    
    def get_available_setups(self) -> List[str]:
        """Get list of available screen setups."""
        try:
            data = self._load_json()
            return list(data.keys())
        except Exception as e:
            self.logger.error(f"Error getting setups: {e}")
            return []
    
    def get_available_positions(self, screen_setup: str) -> List[str]:
        """Get list of configured positions for a screen setup."""
        try:
            data = self._load_json()
            if screen_setup in data:
                return list(data[screen_setup].keys())
            return []
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def _load_json(self) -> Dict:
        """Load JSON data from file."""
        try:
            with open(self.coords_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON file, returning empty dict")
            return {}
        except Exception as e:
            self.logger.error(f"Error reading JSON: {e}")
            return {}
    
    def display_saved_configs(self) -> None:
        """Display all saved configurations."""
        data = self._load_json()
        
        if not data:
            print("\nNo saved configurations found.")
            return
        
        print("\n" + "="*60)
        print("SAVED COORDINATE CONFIGURATIONS")
        print("="*60)
        
        for setup, positions in data.items():
            print(f"\n📺 {setup}")
            for position in positions.keys():
                print(f"   └─ {position}")
        
        print("\n" + "="*60)