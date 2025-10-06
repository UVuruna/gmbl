# utils/region_visualizer.py
# VERSION: 1.0.3
# PURPOSE: Visualize screen regions - saves image instead of showing window
# CHANGES: Fixed OpenCV GUI issue - saves annotated screenshot instead

import numpy as np
import mss
from PIL import Image, ImageDraw, ImageFont
import time
import sys
from typing import Dict, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.coord_manager import CoordsManager
from logger import init_logging, AviatorLogger


class RegionVisualizer:
    """
    Visualize saved screen regions with overlay rectangles.
    Saves annotated screenshot since OpenCV GUI doesn't work.
    """
    
    # Colors for different region types (RGB format for PIL)
    COLORS = {
        'score_region': (0, 255, 0),        # Green
        'my_money_region': (0, 0, 255),     # Blue
        'other_count_region': (255, 165, 0), # Orange
        'other_money_region': (255, 255, 0), # Yellow
        'phase_region': (255, 0, 255),      # Magenta
        'play_amount_coords': (255, 255, 255), # White
        'play_button_coords': (128, 128, 128), # Gray
    }
    
    LABELS = {
        'score_region': 'SCORE',
        'my_money_region': 'MY MONEY',
        'other_count_region': 'PLAYER COUNT',
        'other_money_region': 'OTHER MONEY',
        'phase_region': 'PHASE',
        'play_amount_coords': 'BET AMOUNT',
        'play_button_coords': 'PLAY BUTTON',
    }
    
    def __init__(self, config_name: str, position: str):
        """Initialize visualizer."""
        init_logging()
        self.logger = AviatorLogger.get_logger("RegionVisualizer")
        
        self.config_name = config_name
        self.position = position
        
        # Load coordinates
        self.coords_manager = CoordsManager()
        self.coords = self.coords_manager.load_coordinates(config_name, position)
        
        if not self.coords:
            raise ValueError(f"No coordinates found for {config_name}/{position}")
        
        self.logger.info(f"Loaded coordinates: {config_name}/{position}")
        
        # Screen capture
        self.sct = mss.mss()
    
    def capture_screen(self) -> Tuple[Image.Image, Dict]:
        """Capture screen region containing all coordinates."""
        # Get bounding box
        all_coords = []
        
        for key, value in self.coords.items():
            if isinstance(value, dict) and 'left' in value:
                all_coords.append((value['left'], value['top']))
                all_coords.append((value['left'] + value['width'], 
                                  value['top'] + value['height']))
            elif isinstance(value, list) and len(value) == 2:
                all_coords.append(tuple(value))
        
        if not all_coords:
            raise ValueError("No valid coordinates found")
        
        # Calculate bounding box
        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        
        left = max(0, min(xs) - 50)
        top = max(0, min(ys) - 50)
        right = max(xs) + 50
        bottom = max(ys) + 50
        
        # Capture region
        region = {
            'left': left,
            'top': top,
            'width': right - left,
            'height': bottom - top
        }
        
        sct_img = self.sct.grab(region)
        img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        
        return img, region
    
    def draw_regions(self, img: Image.Image, capture_region: Dict) -> Image.Image:
        """Draw all regions on image with labels."""
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        offset_x = capture_region['left']
        offset_y = capture_region['top']
        
        # Draw each region
        for key, value in self.coords.items():
            color = self.COLORS.get(key, (255, 255, 255))
            label = self.LABELS.get(key, key)
            
            if isinstance(value, dict) and 'left' in value:
                # Rectangle region
                left = value['left'] - offset_x
                top = value['top'] - offset_y
                right = left + value['width']
                bottom = top + value['height']
                
                # Draw rectangle with transparency
                draw.rectangle(
                    [(left, top), (right, bottom)],
                    outline=color,
                    width=3
                )
                
                # Draw semi-transparent fill
                overlay_color = color + (30,)  # Add alpha
                draw.rectangle(
                    [(left, top), (right, bottom)],
                    fill=overlay_color
                )
                
                # Draw label background
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                draw.rectangle(
                    [(left, top - text_height - 6), (left + text_width + 6, top)],
                    fill=color
                )
                
                # Draw label text
                draw.text(
                    (left + 3, top - text_height - 3),
                    label,
                    fill=(0, 0, 0),
                    font=font
                )
                
                # Draw center crosshair
                center_x = left + value['width'] // 2
                center_y = top + value['height'] // 2
                cross_size = 15
                
                draw.line(
                    [(center_x - cross_size, center_y), (center_x + cross_size, center_y)],
                    fill=color,
                    width=2
                )
                draw.line(
                    [(center_x, center_y - cross_size), (center_x, center_y + cross_size)],
                    fill=color,
                    width=2
                )
                
                # Draw coordinates text
                coord_text = f"({value['left']}, {value['top']}) {value['width']}x{value['height']}"
                draw.text(
                    (left + 3, bottom + 3),
                    coord_text,
                    fill=color,
                    font=font_small
                )
                
            elif isinstance(value, list) and len(value) == 2:
                # Point coordinate
                x = value[0] - offset_x
                y = value[1] - offset_y
                
                # Draw circle
                radius = 10
                draw.ellipse(
                    [(x - radius, y - radius), (x + radius, y + radius)],
                    outline=color,
                    width=3
                )
                
                # Draw crosshair
                cross_size = 20
                draw.line(
                    [(x - cross_size, y), (x + cross_size, y)],
                    fill=color,
                    width=2
                )
                draw.line(
                    [(x, y - cross_size), (x, y + cross_size)],
                    fill=color,
                    width=2
                )
                
                # Draw label
                draw.text(
                    (x + 15, y - 15),
                    label,
                    fill=color,
                    font=font
                )
                
                # Draw coordinates
                coord_text = f"({value[0]}, {value[1]})"
                draw.text(
                    (x + 15, y + 5),
                    coord_text,
                    fill=color,
                    font=font_small
                )
        
        return img
    
    def add_legend(self, img: Image.Image) -> Image.Image:
        """Add legend panel to image."""
        # Create new image with space for legend
        legend_height = 200
        new_img = Image.new('RGB', (img.width, img.height + legend_height), (40, 40, 40))
        new_img.paste(img, (0, legend_height))
        
        draw = ImageDraw.Draw(new_img)
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 20)
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()
        
        # Title
        draw.text(
            (10, 10),
            f"Region Visualizer - {self.config_name}/{self.position}",
            fill=(255, 255, 255),
            font=title_font
        )
        
        # Instructions
        instructions = [
            "This screenshot shows all configured screen regions for OCR.",
            "Each region is marked with:",
            "  - Colored rectangle outline",
            "  - Label at the top",
            "  - Center crosshair",
            "  - Coordinates and dimensions"
        ]
        
        y = 40
        for instruction in instructions:
            draw.text((10, y), instruction, fill=(200, 200, 200), font=font)
            y += 20
        
        # Region legend
        y = 140
        draw.text((10, y), "Regions:", fill=(255, 255, 255), font=font)
        y += 25
        
        x = 10
        for key, color in self.COLORS.items():
            if key in self.coords:
                label = self.LABELS.get(key, key)
                
                # Draw color box
                draw.rectangle([(x, y), (x + 15, y + 15)], fill=color)
                
                # Draw label
                draw.text((x + 20, y), label, fill=(200, 200, 200), font=font)
                
                x += 180
                if x > img.width - 180:
                    x = 10
                    y += 25
        
        return new_img
    
    def save_visualization(self) -> str:
        """Capture screen, draw regions, and save."""
        self.logger.info("Capturing screen and drawing regions...")
        
        # Capture screen
        img, capture_region = self.capture_screen()
        
        # Draw regions
        img = self.draw_regions(img, capture_region)
        
        # Add legend
        img = self.add_legend(img)
        
        # Save
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"region_viz_{self.config_name}_{self.position}_{timestamp}.png"
        
        output_dir = Path("tests/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / filename
        img.save(filepath, 'PNG')
        
        self.logger.info(f"Screenshot saved: {filepath}")
        
        return str(filepath)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.sct:
            self.sct.close()


def main():
    """Main entry point."""
    print("="*60)
    print("REGION VISUALIZER v1.0.3")
    print("="*60)
    print("\nNOTE: This version saves an annotated screenshot")
    print("      instead of showing an interactive window.")
    print()
    
    # Get configuration
    coords_manager = CoordsManager()
    coords_manager.display_saved_configs()
    
    config_name = input("\nConfiguration name (e.g., '6'): ").strip()
    if not config_name:
        print("No configuration specified!")
        return
    
    # Get available positions
    positions = coords_manager.get_available_positions(config_name)
    if not positions:
        print(f"No positions found for configuration: {config_name}")
        print("\nTIP: Configuration name is the TOP-LEVEL key in JSON.")
        print("For your JSON, use: '6'")
        print("Then choose position: TL, TC, TR, BL, or BC")
        return
    
    print(f"\nAvailable positions: {', '.join(positions)}")
    position = input("Position (e.g., 'TL'): ").strip()
    
    if position not in positions:
        print(f"Invalid position: {position}")
        return
    
    # Create visualization
    try:
        visualizer = RegionVisualizer(config_name, position)
        filepath = visualizer.save_visualization()
        visualizer.cleanup()
        
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"Screenshot saved to: {filepath}")
        print("\nOpen this file to see all configured regions")
        print("with labels, coordinates, and dimensions.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()