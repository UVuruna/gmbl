# utils/region_visualizer.py
# VERSION: 1.0
# PURPOSE: Visualize and fine-tune screen regions for OCR

import cv2
import numpy as np
import mss
from PIL import Image
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from core.coord_manager import CoordsManager
from logger import init_logging, AviatorLogger


class RegionVisualizer:
    """
    Visualize saved screen regions with overlay rectangles.
    Allows fine-tuning of region positions.
    """
    
    # Colors for different region types (BGR format)
    COLORS = {
        'score_region': (0, 255, 0),        # Green
        'my_money_region': (255, 0, 0),     # Blue
        'other_count_region': (0, 165, 255), # Orange
        'other_money_region': (0, 255, 255), # Yellow
        'phase_region': (255, 0, 255),      # Magenta
        'play_amount_coords': (255, 255, 255), # White (point)
        'play_button_coords': (128, 128, 128), # Gray (point)
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
        """
        Initialize visualizer.
        
        Args:
            config_name: Configuration name (e.g., '3_bookmakers_console')
            position: Position name (e.g., 'Left', 'Center', 'Right')
        """
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
        
        # Adjustments for fine-tuning
        self.adjustments = {}
        
        # Window name
        self.window_name = f"Region Visualizer - {config_name}/{position}"
    
    def capture_screen(self) -> np.ndarray:
        """Capture entire screen or specific monitor."""
        # Get screen dimensions from regions
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
        
        self.capture_region = region
        
        sct_img = self.sct.grab(region)
        img_rgb = np.array(Image.frombytes('RGB', sct_img.size, sct_img.rgb))
        img_bgr = img_rgb[:, :, ::-1].copy()
        
        return img_bgr
    
    def draw_regions(self, img: np.ndarray) -> np.ndarray:
        """
        Draw all regions on image with labels.
        
        Args:
            img: Input image
            
        Returns:
            Image with drawn regions
        """
        overlay = img.copy()
        
        # Calculate offset from capture region
        offset_x = self.capture_region['left']
        offset_y = self.capture_region['top']
        
        # Draw each region
        for key, value in self.coords.items():
            color = self.COLORS.get(key, (255, 255, 255))
            label = self.LABELS.get(key, key)
            
            # Apply adjustments if any
            adjustment = self.adjustments.get(key, (0, 0, 0, 0))
            
            if isinstance(value, dict) and 'left' in value:
                # Rectangle region
                left = value['left'] - offset_x + adjustment[0]
                top = value['top'] - offset_y + adjustment[1]
                width = value['width'] + adjustment[2]
                height = value['height'] + adjustment[3]
                
                # Draw rectangle
                cv2.rectangle(
                    overlay,
                    (left, top),
                    (left + width, top + height),
                    color,
                    2
                )
                
                # Draw label background
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(
                    overlay,
                    (left, top - label_size[1] - 8),
                    (left + label_size[0] + 4, top),
                    color,
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    overlay,
                    label,
                    (left + 2, top - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1
                )
                
                # Draw center crosshair
                center_x = left + width // 2
                center_y = top + height // 2
                cv2.drawMarker(
                    overlay,
                    (center_x, center_y),
                    color,
                    cv2.MARKER_CROSS,
                    10,
                    1
                )
                
            elif isinstance(value, list) and len(value) == 2:
                # Point coordinate
                x = value[0] - offset_x + adjustment[0]
                y = value[1] - offset_y + adjustment[1]
                
                # Draw circle
                cv2.circle(overlay, (x, y), 10, color, 2)
                
                # Draw crosshair
                cv2.drawMarker(
                    overlay,
                    (x, y),
                    color,
                    cv2.MARKER_CROSS,
                    20,
                    2
                )
                
                # Draw label
                cv2.putText(
                    overlay,
                    label,
                    (x + 15, y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1
                )
        
        # Blend overlay
        alpha = 0.7
        result = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        return result
    
    def add_info_panel(self, img: np.ndarray) -> np.ndarray:
        """Add information panel with instructions."""
        height = img.shape[0]
        
        # Create info panel
        panel_height = 150
        panel = np.zeros((panel_height, img.shape[1], 3), dtype=np.uint8)
        panel[:] = (40, 40, 40)
        
        # Title
        cv2.putText(
            panel,
            f"Region Visualizer - {self.config_name}/{self.position}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        # Instructions
        instructions = [
            "ESC: Exit | S: Save screenshot | R: Refresh | H: Toggle help",
            "Arrow Keys: Adjust selected region | +/-: Resize region",
            "1-7: Select region | SPACE: Reset adjustments"
        ]
        
        y_pos = 55
        for instruction in instructions:
            cv2.putText(
                panel,
                instruction,
                (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 200, 200),
                1
            )
            y_pos += 25
        
        # Region legend
        legend_x = 10
        legend_y = 125
        for key, color in self.COLORS.items():
            if key in self.coords:
                label = self.LABELS.get(key, key)
                
                # Draw color box
                cv2.rectangle(panel, (legend_x, legend_y - 10), 
                            (legend_x + 15, legend_y), color, -1)
                
                # Draw label
                cv2.putText(
                    panel,
                    label,
                    (legend_x + 20, legend_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    (200, 200, 200),
                    1
                )
                
                legend_x += 150
        
        # Combine
        result = np.vstack([panel, img])
        
        return result
    
    def run(self):
        """Run interactive visualizer."""
        self.logger.info("Starting region visualizer")
        self.logger.info("Press 'H' for help, 'ESC' to exit")
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        
        show_help = True
        selected_region = None
        
        try:
            while True:
                # Capture screen
                screen = self.capture_screen()
                
                # Draw regions
                result = self.draw_regions(screen)
                
                # Add info panel if help is shown
                if show_help:
                    result = self.add_info_panel(result)
                
                # Show
                cv2.imshow(self.window_name, result)
                
                # Handle keyboard
                key = cv2.waitKey(100) & 0xFF
                
                if key == 27:  # ESC
                    break
                
                elif key == ord('h') or key == ord('H'):
                    show_help = not show_help
                
                elif key == ord('s') or key == ord('S'):
                    self.save_screenshot(result)
                
                elif key == ord('r') or key == ord('R'):
                    # Refresh
                    pass
                
                elif key == ord(' '):
                    # Reset adjustments
                    self.adjustments.clear()
                    self.logger.info("Adjustments reset")
                
                # Region selection (1-7)
                elif ord('1') <= key <= ord('7'):
                    region_index = key - ord('1')
                    region_keys = list(self.coords.keys())
                    if region_index < len(region_keys):
                        selected_region = region_keys[region_index]
                        self.logger.info(f"Selected: {selected_region}")
                
                # Arrow keys for adjustment
                elif selected_region:
                    adjustment = list(self.adjustments.get(selected_region, [0, 0, 0, 0]))
                    
                    if key == 81:  # Left arrow
                        adjustment[0] -= 1
                    elif key == 83:  # Right arrow
                        adjustment[0] += 1
                    elif key == 82:  # Up arrow
                        adjustment[1] -= 1
                    elif key == 84:  # Down arrow
                        adjustment[1] += 1
                    elif key == ord('+') or key == ord('='):
                        # Increase size
                        adjustment[2] += 2
                        adjustment[3] += 2
                    elif key == ord('-') or key == ord('_'):
                        # Decrease size
                        adjustment[2] -= 2
                        adjustment[3] -= 2
                    
                    self.adjustments[selected_region] = tuple(adjustment)
                    
                    if any(adjustment):
                        self.logger.debug(f"{selected_region} adjustment: {adjustment}")
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        
        finally:
            cv2.destroyAllWindows()
            self.sct.close()
            
            # Save adjustments if any
            if self.adjustments:
                self.save_adjustments()
    
    def save_screenshot(self, img: np.ndarray):
        """Save screenshot with timestamp."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"region_viz_{self.config_name}_{self.position}_{timestamp}.png"
        
        output_dir = Path("tests/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), img)
        
        self.logger.info(f"Screenshot saved: {filepath}")
        print(f"\n✅ Screenshot saved: {filepath}\n")
    
    def save_adjustments(self):
        """Save adjustments to file."""
        if not self.adjustments:
            return
        
        output_dir = Path("tests/adjustments")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = output_dir / f"{self.config_name}_{self.position}_adjustments.txt"
        
        with open(filename, 'w') as f:
            f.write(f"Configuration: {self.config_name}\n")
            f.write(f"Position: {self.position}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            f.write("Adjustments (left, top, width, height):\n")
            f.write("-" * 50 + "\n")
            
            for region, adjustment in self.adjustments.items():
                f.write(f"{region}: {adjustment}\n")
        
        self.logger.info(f"Adjustments saved: {filename}")
        print(f"\n✅ Adjustments saved: {filename}\n")


def main():
    """Main entry point."""
    print("="*60)
    print("REGION VISUALIZER v1.0")
    print("="*60)
    
    # Get configuration
    coords_manager = CoordsManager()
    coords_manager.display_saved_configs()
    
    config_name = input("\nConfiguration name: ").strip()
    if not config_name:
        print("No configuration specified!")
        return
    
    # Get available positions
    positions = coords_manager.get_available_positions(config_name)
    if not positions:
        print(f"No positions found for configuration: {config_name}")
        return
    
    print(f"\nAvailable positions: {', '.join(positions)}")
    position = input("Position: ").strip()
    
    if position not in positions:
        print(f"Invalid position: {position}")
        return
    
    # Run visualizer
    try:
        visualizer = RegionVisualizer(config_name, position)
        visualizer.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()