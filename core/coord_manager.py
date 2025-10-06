# core/coord_manager.py
# VERSION: 5.0 - New positioning system
# Supports layout-based coordinate positioning

import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from logger import AviatorLogger


class CoordsManager:
    """
    Coordinate manager with layout-based positioning.
    
    New structure:
    - layouts: Define grid layouts with width/height and positions
    - bookmakers: Base coordinates (relative to 0,0)
    - Auto-calculate final coordinates based on layout + position
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
            default_data = {"layouts": {}, "bookmakers": {}}
            with open(self.coords_file, 'w') as f:
                json.dump(default_data, f, indent=2)
            self.logger.info(f"Created new coordinates file: {self.coords_file}")
    
    def _load_json(self) -> Dict:
        """Load JSON data."""
        try:
            with open(self.coords_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading coordinates: {e}")
            return {"layouts": {}, "bookmakers": {}}
    
    def get_available_layouts(self) -> List[str]:
        """Get list of available layout configurations."""
        return list(self.data.get("layouts", {}).keys())
    
    def get_available_positions(self, layout_name: str) -> List[str]:
        """Get available positions for a layout."""
        layout = self.data.get("layouts", {}).get(layout_name, {})
        return list(layout.get("positions", {}).keys())
    
    def get_available_bookmakers(self) -> List[str]:
        """Get list of configured bookmakers."""
        return list(self.data.get("bookmakers", {}).keys())
    
    def get_layout_info(self, layout_name: str) -> Optional[Dict]:
        """Get layout information (width, height, positions)."""
        return self.data.get("layouts", {}).get(layout_name)
    
    def get_bookmaker_base_coords(self, bookmaker_name: str) -> Optional[Dict]:
        """Get base coordinates for a bookmaker (relative to 0,0)."""
        return self.data.get("bookmakers", {}).get(bookmaker_name)
    
    def calculate_coords(
        self, 
        bookmaker_name: str, 
        layout_name: str, 
        position: str
    ) -> Optional[Dict]:
        """
        Calculate final coordinates for a bookmaker at specific position.
        
        Args:
            bookmaker_name: Name of bookmaker (e.g., 'BalkanBet')
            layout_name: Layout configuration (e.g., '3_monitors_grid')
            position: Position in layout (e.g., 'TL', 'TC', 'TR')
        
        Returns:
            Dict with final coordinates or None if error
        """
        try:
            # Get base coordinates
            base_coords = self.get_bookmaker_base_coords(bookmaker_name)
            if not base_coords:
                self.logger.error(f"Bookmaker not found: {bookmaker_name}")
                return None
            
            # Get layout info
            layout = self.get_layout_info(layout_name)
            if not layout:
                self.logger.error(f"Layout not found: {layout_name}")
                return None
            
            # Get position offset
            position_offset = layout.get("positions", {}).get(position)
            if not position_offset:
                self.logger.error(f"Position not found: {position} in layout {layout_name}")
                return None
            
            # Calculate final coordinates
            offset_left = position_offset.get("left", 0)
            offset_top = position_offset.get("top", 0)
            
            final_coords = {}
            for region_name, region_data in base_coords.items():
                if isinstance(region_data, dict):
                    final_coords[region_name] = {
                        "left": region_data["left"] + offset_left,
                        "top": region_data["top"] + offset_top,
                        "width": region_data["width"],
                        "height": region_data["height"]
                    }
                else:
                    final_coords[region_name] = region_data
            
            self.logger.info(
                f"Calculated coords: {bookmaker_name} @ {layout_name}/{position}"
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
            coords: Base coordinates (relative to 0,0)
        
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
    
    def save_layout(
        self, 
        layout_name: str, 
        width: int, 
        height: int, 
        positions: Dict[str, Dict[str, int]]
    ) -> bool:
        """
        Save layout configuration.
        
        Args:
            layout_name: Name of layout
            width: Width of single window
            height: Height of single window
            positions: Dict of positions with offsets
        
        Returns:
            True if successful
        """
        try:
            if "layouts" not in self.data:
                self.data["layouts"] = {}
            
            self.data["layouts"][layout_name] = {
                "width": width,
                "height": height,
                "positions": positions
            }
            
            with open(self.coords_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            self.logger.info(f"Saved layout: {layout_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving layout: {e}", exc_info=True)
            return False
    
    def display_info(self) -> None:
        """Display information about available configurations."""
        print("\n" + "="*60)
        print("COORDINATE SYSTEM INFO")
        print("="*60)
        
        # Layouts
        layouts = self.get_available_layouts()
        print(f"\n📐 Available Layouts ({len(layouts)}):")
        for layout_name in layouts:
            layout = self.get_layout_info(layout_name)
            positions = list(layout.get("positions", {}).keys())
            print(f"  • {layout_name}")
            print(f"    Size: {layout['width']}x{layout['height']}")
            print(f"    Positions: {', '.join(positions)}")
        
        # Bookmakers
        bookmakers = self.get_available_bookmakers()
        print(f"\n🎰 Available Bookmakers ({len(bookmakers)}):")
        for bookmaker in bookmakers:
            print(f"  • {bookmaker}")
        
        print("\n" + "="*60)


# Backward compatibility function
def load_coordinates_legacy(config_name: str, position: str) -> Optional[Dict]:
    """Legacy function for backward compatibility."""
    manager = CoordsManager()
    # Try to interpret as layout_name/position
    return manager.calculate_coords(position, config_name, position)


if __name__ == "__main__":
    # Test/demo
    manager = CoordsManager()
    manager.display_info()
    
    # Example usage
    print("\n" + "="*60)
    print("EXAMPLE: Calculate coordinates")
    print("="*60)
    
    coords = manager.calculate_coords(
        bookmaker_name="BalkanBet",
        layout_name="3_monitors_grid",
        position="TL"
    )
    
    if coords:
        print("\n✅ Calculated coordinates for BalkanBet at TL:")
        for region, data in coords.items():
            print(f"  {region}: {data}")