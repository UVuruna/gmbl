# core/coord_manager.py
# VERSION: 5.1 - Updated for new JSON format
# Supports: positions + bookmakers structure

import json
from pathlib import Path
from typing import Dict, Optional, List
from logger import AviatorLogger


class CoordsManager:
    """
    Coordinate manager for new JSON format.
    
    JSON Structure:
    {
      "positions": {
        "TL": {"left": 0, "top": 0},
        "TC": {"left": 853, "top": 0},
        ...
      },
      "bookmakers": {
        "BalkanBet": {
          "score_region": {...},
          ...
        }
      }
    }
    
    Final coordinates = bookmaker_base + position_offset
    """
    
    DEFAULT_FILE = "data/coordinates/bookmaker_coords.json"
    
    def __init__(self, coords_file: str = DEFAULT_FILE):
        self.coords_file = Path(coords_file)
        self.logger = AviatorLogger.get_logger("CoordsManager")
        self._ensure_file_exists()
        self.data = self._load_json()
    
    def _ensure_file_exists(self) -> None:
        """Create directory and empty JSON if doesn't exist."""
        self.coords_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.coords_file.exists():
            default_data = {"positions": {}, "bookmakers": {}}
            with open(self.coords_file, 'w') as f:
                json.dump(default_data, f, indent=2)
            self.logger.info(f"Created new coordinates file: {self.coords_file}")
    
    def _load_json(self) -> Dict:
        """Load JSON data."""
        try:
            with open(self.coords_file, 'r') as f:
                data = json.load(f)
            
            # Ensure structure
            if "positions" not in data:
                data["positions"] = {}
            if "bookmakers" not in data:
                data["bookmakers"] = {}
            
            return data
        except Exception as e:
            self.logger.error(f"Error loading coordinates: {e}")
            return {"positions": {}, "bookmakers": {}}
    
    def get_available_positions(self) -> List[str]:
        """Get list of available position codes (TL, TC, TR, BL, BC, BR)."""
        return list(self.data.get("positions", {}).keys())
    
    def get_available_bookmakers(self) -> List[str]:
        """Get list of configured bookmakers."""
        return list(self.data.get("bookmakers", {}).keys())
    
    def get_position_offset(self, position_code: str) -> Optional[Dict]:
        """
        Get offset for a position code.
        
        Args:
            position_code: Position code (e.g., 'TL', 'TC', 'TR')
        
        Returns:
            Dict with 'left' and 'top' offsets, or None if not found
        """
        return self.data.get("positions", {}).get(position_code)
    
    def get_bookmaker_base_coords(self, bookmaker_name: str) -> Optional[Dict]:
        """
        Get base coordinates for a bookmaker.
        
        Args:
            bookmaker_name: Name of bookmaker (e.g., 'BalkanBet')
        
        Returns:
            Dict with all regions, or None if not found
        """
        return self.data.get("bookmakers", {}).get(bookmaker_name)
    
    def calculate_coords(
        self, 
        bookmaker_name: str, 
        position_code: str
    ) -> Optional[Dict]:
        """
        Calculate final coordinates for a bookmaker at specific position.
        
        Formula: final_coords = base_coords + position_offset
        
        Args:
            bookmaker_name: Name of bookmaker (e.g., 'BalkanBet')
            position_code: Position code (e.g., 'TL', 'TC', 'TR')
        
        Returns:
            Dict with final coordinates for all regions, or None if error
        """
        try:
            # Get base coordinates
            base_coords = self.get_bookmaker_base_coords(bookmaker_name)
            if not base_coords:
                self.logger.error(f"Bookmaker not found: {bookmaker_name}")
                return None
            
            # Get position offset
            position_offset = self.get_position_offset(position_code)
            if not position_offset:
                self.logger.error(f"Position not found: {position_code}")
                return None
            
            # Calculate final coordinates
            offset_left = position_offset.get("left", 0)
            offset_top = position_offset.get("top", 0)
            
            final_coords = {}
            for region_name, region_data in base_coords.items():
                if isinstance(region_data, dict) and 'left' in region_data:
                    # Rectangle region
                    final_coords[region_name] = {
                        "left": region_data["left"] + offset_left,
                        "top": region_data["top"] + offset_top,
                        "width": region_data["width"],
                        "height": region_data["height"]
                    }
                else:
                    # Unknown format - keep as-is
                    final_coords[region_name] = region_data
            
            self.logger.info(
                f"Calculated coords: {bookmaker_name} @ {position_code} "
                f"(offset: +{offset_left}, +{offset_top})"
            )
            return final_coords
            
        except Exception as e:
            self.logger.error(f"Error calculating coordinates: {e}", exc_info=True)
            return None
    
    def save_bookmaker_coords(self, bookmaker_name: str, coords: Dict) -> bool:
        """
        Save base coordinates for a bookmaker.
        
        Args:
            bookmaker_name: Name of bookmaker
            coords: Base coordinates (all regions)
        
        Returns:
            True if successful
        """
        try:
            if "bookmakers" not in self.data:
                self.data["bookmakers"] = {}
            
            self.data["bookmakers"][bookmaker_name] = coords
            
            with open(self.coords_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            self.logger.info(f"Saved base coords for: {bookmaker_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving coordinates: {e}", exc_info=True)
            return False
    
    def save_positions(self, positions: Dict[str, Dict[str, int]]) -> bool:
        """
        Save position offsets.
        
        Args:
            positions: Dict of position codes with offsets
                      e.g., {"TL": {"left": 0, "top": 0}, "TC": {"left": 853, "top": 0}}
        
        Returns:
            True if successful
        """
        try:
            if "positions" not in self.data:
                self.data["positions"] = {}
            
            self.data["positions"].update(positions)
            
            with open(self.coords_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            self.logger.info(f"Saved positions: {list(positions.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving positions: {e}", exc_info=True)
            return False
    
    def display_info(self) -> None:
        """Display information about available configurations."""
        print("\n" + "="*60)
        print("COORDINATE SYSTEM INFO")
        print("="*60)
        
        # Positions
        positions = self.get_available_positions()
        print(f"\n📐 Available Positions ({len(positions)}):")
        for pos_code in positions:
            offset = self.get_position_offset(pos_code)
            print(f"  • {pos_code:3s} → Offset: (+{offset['left']}, +{offset['top']})")
        
        # Bookmakers
        bookmakers = self.get_available_bookmakers()
        print(f"\n🎰 Available Bookmakers ({len(bookmakers)}):")
        for bookmaker in bookmakers:
            coords = self.get_bookmaker_base_coords(bookmaker)
            regions = len([k for k in coords.keys() if 'region' in k or 'coords' in k])
            print(f"  • {bookmaker:15s} ({regions} regions configured)")
        
        print("\n" + "="*60)


# Legacy compatibility function
def load_coordinates(bookmaker_name: str, position_code: str) -> Optional[Dict]:
    """
    Legacy function for backward compatibility.
    
    Args:
        bookmaker_name: Name of bookmaker
        position_code: Position code
    
    Returns:
        Final coordinates or None
    """
    manager = CoordsManager()
    return manager.calculate_coords(bookmaker_name, position_code)


if __name__ == "__main__":
    """Test coordinate manager."""
    manager = CoordsManager()
    manager.display_info()
    
    # Test calculation
    if manager.get_available_bookmakers() and manager.get_available_positions():
        bookmaker = manager.get_available_bookmakers()[0]
        position = manager.get_available_positions()[0]
        
        print(f"\n🧪 Test: {bookmaker} @ {position}")
        coords = manager.calculate_coords(bookmaker, position)
        
        if coords:
            print("\nCalculated coordinates:")
            for region_name, region_data in list(coords.items())[:3]:
                print(f"  {region_name}: {region_data}")
        else:
            print("❌ Calculation failed!")