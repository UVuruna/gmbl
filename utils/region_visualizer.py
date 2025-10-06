# utils/region_visualizer.py
# VERSION: 2.0 - Works with new coordinate system
# Takes bookmaker name and calculated coordinates directly

import mss
import time
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Dict, Tuple, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import init_logging, AviatorLogger


class RegionVisualizer:
    """
    Visualize screen regions for verification.
    
    New system: Takes bookmaker name and pre-calculated coordinates.
    """
    
    # Colors for different regions (RGB)
    COLORS = {
        'score_region': (0, 255, 0),            # Green
        'my_money_region': (255, 0, 0),         # Blue  
        'other_count_region': (255, 128, 0),    # Orange
        'other_money_region': (255, 255, 0),    # Yellow
        'phase_region': (255, 0, 255),          # Magenta
        'bet_amount_coords': (0, 0, 255),       # Red
        'play_button_coords': (0, 255, 255),    # Cyan
        'auto_play_coords': (128, 0, 255)       # Purple
    }
    
    LABELS = {
        'score_region': 'SCORE',
        'my_money_region': 'MY MONEY',
        'other_count_region': 'PLAYER COUNT',
        'other_money_region': 'OTHER MONEY',
        'phase_region': 'PHASE',
        'bet_amount_coords': 'BET AMOUNT',
        'play_button_coords': 'PLAY BUTTON',
        'auto_play_coords': 'AUTO PLAY'
    }
    
    def __init__(
        self, 
        bookmaker_name: str, 
        coords: Dict,
        position: str = "unknown"
    ):
        """
        Initialize visualizer.
        
        Args:
            bookmaker_name: Name of bookmaker
            coords: Calculated coordinates (final positions)
            position: Position name for filename (e.g., 'TL', 'TC')
        """
        init_logging()
        self.logger = AviatorLogger.get_logger("RegionVisualizer")
        
        self.bookmaker_name = bookmaker_name
        self.coords = coords
        self.position = position
        
        # Screen capture
        self.sct = mss.mss()
        
        self.logger.info(f"Visualizer created for {bookmaker_name} @ {position}")
    
    def _get_capture_region(self) -> Dict[str, int]:
        """Calculate capture region that includes all coordinates."""
        if not self.coords:
            return {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # Find bounds
        min_left = float('inf')
        min_top = float('inf')
        max_right = 0
        max_bottom = 0
        
        for region_data in self.coords.values():
            if isinstance(region_data, dict) and 'left' in region_data:
                left = region_data['left']
                top = region_data['top']
                width = region_data['width']
                height = region_data['height']
                
                min_left = min(min_left, left)
                min_top = min(min_top, top)
                max_right = max(max_right, left + width)
                max_bottom = max(max_bottom, top + height)
        
        # Add padding
        padding = 50
        return {
            "left": int(max(0, min_left - padding)),
            "top": int(max(0, min_top - padding)),
            "width": int(max_right - min_left + 2 * padding),
            "height": int(max_bottom - min_top + 2 * padding)
        }
    
    def capture_screen(self) -> Tuple[Image.Image, Dict]:
        """Capture screen region."""
        capture_region = self._get_capture_region()
        
        # Capture
        sct_img = self.sct.grab(capture_region)
        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
        
        return img, capture_region
    
    def draw_regions(
        self, 
        img: Image.Image, 
        capture_offset: Dict
    ) -> Image.Image:
        """Draw regions on image."""
        draw = ImageDraw.Draw(img)
        
        # Try to load font
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_large = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            font_large = font
        
        offset_left = capture_offset['left']
        offset_top = capture_offset['top']
        
        # Draw each region
        for key, region_data in self.coords.items():
            if not isinstance(region_data, dict) or 'left' not in region_data:
                continue
            
            # Calculate relative position
            left = region_data['left'] - offset_left
            top = region_data['top'] - offset_top
            width = region_data['width']
            height = region_data['height']
            
            # Get color
            color = self.COLORS.get(key, (255, 255, 255))
            
            # Draw rectangle
            draw.rectangle(
                [(left, top), (left + width, top + height)],
                outline=color,
                width=3
            )
            
            # Draw center crosshair
            center_x = left + width // 2
            center_y = top + height // 2
            crosshair_size = 10
            
            draw.line(
                [(center_x - crosshair_size, center_y), 
                 (center_x + crosshair_size, center_y)],
                fill=color,
                width=2
            )
            draw.line(
                [(center_x, center_y - crosshair_size), 
                 (center_x, center_y + crosshair_size)],
                fill=color,
                width=2
            )
            
            # Draw label
            label = self.LABELS.get(key, key)
            label_text = f"{label}\n({width}x{height})"
            
            # Background for text
            text_bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            draw.rectangle(
                [(left, top - text_height - 4), 
                 (left + text_width + 8, top)],
                fill=(0, 0, 0)
            )
            
            draw.text(
                (left + 4, top - text_height - 2),
                label_text,
                fill=color,
                font=font
            )
        
        return img
    
    def add_header(self, img: Image.Image) -> Image.Image:
        """Add header with info."""
        # Create new image with header space
        header_height = 80
        new_img = Image.new('RGB', (img.width, img.height + header_height), (30, 30, 30))
        new_img.paste(img, (0, header_height))
        
        draw = ImageDraw.Draw(new_img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        # Title
        title = f"REGION VERIFICATION: {self.bookmaker_name} @ {self.position}"
        draw.text((10, 10), title, fill=(255, 255, 255), font=font)
        
        # Instructions
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 35), f"Captured: {timestamp}", fill=(200, 200, 200), font=font_small)
        draw.text((10, 55), "Check that all regions align correctly with screen elements", 
                  fill=(200, 200, 200), font=font_small)
        
        return new_img
    
    def save_visualization(self) -> str:
        """Capture, draw regions, and save."""
        self.logger.info(f"Creating visualization for {self.bookmaker_name}")
        
        # Capture
        img, capture_region = self.capture_screen()
        
        # Draw regions
        img = self.draw_regions(img, capture_region)
        
        # Add header
        img = self.add_header(img)
        
        # Save
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"region_check_{self.bookmaker_name}_{self.position}_{timestamp}.png"
        
        output_dir = Path("tests/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / filename
        img.save(filepath, 'PNG')
        
        self.logger.info(f"Visualization saved: {filepath}")
        return str(filepath)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.sct:
            self.sct.close()


# Example usage
if __name__ == "__main__":
    from core.coord_manager import CoordsManager
    
    print("="*60)
    print("REGION VISUALIZER v2.0")
    print("="*60)
    
    # Example: Visualize BalkanBet at TL position in 3_monitors_grid
    manager = CoordsManager()
    manager.display_info()
    
    print("\n--- Example Visualization ---")
    bookmaker = input("Bookmaker name: ").strip() or "BalkanBet"
    layout = input("Layout name: ").strip() or "3_monitors_grid"
    position = input("Position: ").strip() or "TL"
    
    coords = manager.calculate_coords(bookmaker, layout, position)
    
    if coords:
        visualizer = RegionVisualizer(bookmaker, coords, position)
        filepath = visualizer.save_visualization()
        visualizer.cleanup()
        
        print(f"\n✅ Screenshot saved: {filepath}")
    else:
        print("\n❌ Could not calculate coordinates")