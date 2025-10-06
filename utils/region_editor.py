# utils/region_editor.py
# VERSION: 2.0
# PURPOSE: Complete region editor - create, edit, save configurations
# FEATURES: Interactive adjustment, new configs, keyboard controls

import cv2
import numpy as np
import mss
from PIL import Image
import time
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import init_logging, AviatorLogger


class RegionEditor:
    """
    Interactive region editor with full keyboard controls.
    Create new configs, edit existing, fine-tune all regions.
    """
    
    # Colors for different region types (BGR format)
    COLORS = {
        'score_region': (0, 255, 0),            # Green
        'my_money_region': (255, 0, 0),         # Blue
        'other_count_region': (0, 128, 255),    # Orange
        'other_money_region': (0, 255, 255),    # Yellow
        'phase_region': (255, 0, 255),          # Magenta
        'play_amount_coords': (0, 0, 255),      # Red
        'play_button_coords': (255, 255, 0),    # Cyan
        'auto_play_coords': (255,0,128)         # Purple
    }
    
    LABELS = {
        'score_region': 'SCORE',
        'my_money_region': 'MY MONEY',
        'other_count_region': 'PLAYER COUNT',
        'other_money_region': 'OTHER MONEY',
        'phase_region': 'PHASE',
        'play_amount_coords': 'BET AMOUNT',
        'play_button_coords': 'PLAY BUTTON',
        'auto_play_coords': 'AUTO PLAY'
    }
    
    # Region types in order for selection
    REGION_KEYS = [
        'score_region',
        'my_money_region', 
        'other_count_region',
        'other_money_region',
        'phase_region',
        'play_amount_coords',
        'play_button_coords',
        'auto_play_coords'
    ]
    
    def __init__(self, config_name: str, position: str, coords_file: str = "data/coordinates/bookmaker_coords.json"):
        """Initialize region editor."""
        init_logging()
        self.logger = AviatorLogger.get_logger("RegionEditor")
        
        self.config_name = config_name
        self.position = position
        self.coords_file = Path(coords_file)
        
        # Ensure file and directory exist
        self.coords_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.coords_file.exists():
            with open(self.coords_file, 'w') as f:
                json.dump({}, f)
        
        # Load or create coordinates
        self.coords = self._load_or_create_coords()
        
        # Screen capture
        self.sct = mss.mss()
        self.capture_offset = (0, 0)  # For drawing offset
        
        # State
        self.selected_region = 0  # Index in REGION_KEYS
        self.show_help = True
        self.unsaved_changes = False
        self.step = 5
        
        # Window
        self.window_name = f"Region Editor - {config_name}/{position}"
        
        self.logger.info(f"Region editor initialized: {config_name}/{position}")
    
    def _load_or_create_coords(self) -> Dict:
        """Load existing or create new coordinates."""
        try:
            with open(self.coords_file, 'r') as f:
                data = json.load(f)
            
            if self.config_name in data and self.position in data[self.config_name]:
                self.logger.info(f"Loaded existing coordinates: {self.config_name}/{self.position}")
                return data[self.config_name][self.position]
            else:
                self.logger.info(f"Creating new configuration: {self.config_name}/{self.position}")
                return self._create_default_coords()
                
        except Exception as e:
            self.logger.error(f"Error loading coordinates: {e}")
            return self._create_default_coords()
    
    def _create_default_coords(self) -> Dict:
        """Create default coordinates (center of screen)."""
        # Get primary monitor size
        monitor = self.sct.monitors[1]
        center_x = monitor['width'] // 2
        center_y = monitor['height'] // 2
        
        return {
            'score_region': {
                'left': center_x - 400,
                'top': center_y - 200,
                'width': 700,
                'height': 140
            },
            'my_money_region': {
                'left': center_x + 200,
                'top': center_y - 300,
                'width': 100,
                'height': 25
            },
            'other_count_region': {
                'left': center_x - 500,
                'top': center_y - 100,
                'width': 150,
                'height': 20
            },
            'other_money_region': {
                'left': center_x - 300,
                'top': center_y - 150,
                'width': 120,
                'height': 25
            },
            'phase_region': {
                'left': center_x - 200,
                'top': center_y - 200,
                'width': 400,
                'height': 150
            },
            'play_amount_coords': [center_x - 100, center_y + 200],
            'play_button_coords': [center_x + 50, center_y + 200]
        }
    
    def capture_screen(self) -> np.ndarray:
        """Capture screen region containing all coordinates."""
        # Get bounding box from all coordinates
        all_coords = []
        
        for key, value in self.coords.items():
            if isinstance(value, dict) and 'left' in value:
                all_coords.append((value['left'], value['top']))
                all_coords.append((value['left'] + value['width'], 
                                  value['top'] + value['height']))
            elif isinstance(value, list) and len(value) == 2:
                all_coords.append(tuple(value))
        
        if not all_coords:
            # Fallback to primary monitor
            monitor = self.sct.monitors[1]
            self.capture_offset = (0, 0)
            sct_img = self.sct.grab(monitor)
        else:
            # Calculate bounding box with padding
            xs = [c[0] for c in all_coords]
            ys = [c[1] for c in all_coords]
            
            left = max(0, min(xs) - 100)
            top = max(0, min(ys) - 100)
            right = max(xs) + 100
            bottom = max(ys) + 100
            
            # Store offset for drawing
            self.capture_offset = (left, top)
            
            # Capture region
            region = {
                'left': left,
                'top': top,
                'width': right - left,
                'height': bottom - top
            }
            
            sct_img = self.sct.grab(region)
        
        img_rgb = np.array(Image.frombytes('RGB', sct_img.size, sct_img.rgb))
        img_bgr = img_rgb[:, :, ::-1].copy()
        
        return img_bgr
    
    def draw_regions(self, img: np.ndarray) -> np.ndarray:
        """Draw all regions on image."""
        overlay = img.copy()
        offset_x, offset_y = self.capture_offset
        
        for idx, key in enumerate(self.REGION_KEYS):
            if key not in self.coords:
                continue
            
            value = self.coords[key]
            color = self.COLORS.get(key, (255, 255, 255))
            label = self.LABELS.get(key, key)
            
            # Highlight selected region
            is_selected = (idx == self.selected_region)
            thickness = 1
            
            if isinstance(value, dict) and 'left' in value:
                # Rectangle region - adjust for capture offset
                left = value['left'] - offset_x
                top = value['top'] - offset_y
                width = value['width']
                height = value['height']
                
                # Draw rectangle
                cv2.rectangle(
                    overlay,
                    (left, top),
                    (left + width, top + height),
                    color,
                    thickness
                )
                
                # Draw selection indicator
                if is_selected:
                    cv2.rectangle(
                        overlay,
                        (left - 5, top - 5),
                        (left + width + 5, top + height + 5),
                        (255, 255, 0),  # Yellow border
                        2
                    )
                
                # Draw label background
                label_text = f"{idx+1}. {label}"
                if is_selected:
                    label_text += " [SELECTED]"
                
                (text_width, text_height), baseline = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                
                cv2.rectangle(
                    overlay,
                    (left, top - text_height - 10),
                    (left + text_width + 10, top),
                    color,
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    overlay,
                    label_text,
                    (left + 5, top - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    2
                )
                
                # Draw dimensions
                dim_text = f"{width}x{height}"
                cv2.putText(
                    overlay,
                    dim_text,
                    (left + 5, top + height + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
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
                    15,
                    2
                )
                
            elif isinstance(value, list) and len(value) == 2:
                # Point coordinate - adjust for capture offset
                x = value[0] - offset_x
                y = value[1] - offset_y
                
                # Draw circle
                radius = 12 if is_selected else 8
                cv2.circle(overlay, (x, y), radius, color, thickness)
                
                # Draw crosshair
                size = 25 if is_selected else 20
                cv2.drawMarker(
                    overlay,
                    (x, y),
                    color,
                    cv2.MARKER_CROSS,
                    size,
                    2
                )
                
                # Draw label
                label_text = f"{idx+1}. {label}"
                if is_selected:
                    label_text += " [SELECTED]"
                
                cv2.putText(
                    overlay,
                    label_text,
                    (x + 20, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )
                
                # Draw coordinates
                coord_text = f"({value[0]}, {value[1]})"
                cv2.putText(
                    overlay,
                    coord_text,
                    (x + 20, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1
                )
        
        # Blend
        alpha = 0.8
        result = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        return result
    
    def add_info_panel(self, img: np.ndarray) -> np.ndarray:
        """Add control panel."""
        panel_height = 250
        panel = np.zeros((panel_height, img.shape[1], 3), dtype=np.uint8)
        panel[:] = (30, 30, 30)
        
        # Title
        title = f"Region Editor - {self.config_name}/{self.position}"
        if self.unsaved_changes:
            title += " [UNSAVED]"
        
        cv2.putText(
            panel, title, (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
        
        # Keyboard controls
        controls = [
            f"SELECTION: 1-{len(self.REGION_KEYS)} keys | TAB: Next region",
            "MOVE: Arrow Keys (← → ↑ ↓) OR WASD (W=up A=left S=down D=right)",
            f"RESIZE: +/- Both | [] Width | <> Height | m/n Step ({self.step})",
            "ACTIONS: Enter: Save | R: Reset | H: Help | ESC/X: Exit",
            ""
        ]
        
        y = 55
        for i, control in enumerate(controls):
            color = (200, 200, 200) if i < 3 else (100, 255, 100)
            cv2.putText(
                panel, control, (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1
            )
            y += 30
        
        # Current selection info
        selected_key = self.REGION_KEYS[self.selected_region]
        selected_label = self.LABELS.get(selected_key, selected_key)
        selected_value = self.coords.get(selected_key)
        
        info_text = f"SELECTED: {selected_label}"
        cv2.putText(
            panel, info_text, (10, y + 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
        )
        
        if isinstance(selected_value, dict):
            detail = f"  Position: ({selected_value['left']}, {selected_value['top']})  Size: {selected_value['width']}x{selected_value['height']}"
        elif isinstance(selected_value, list):
            detail = f"  Position: ({selected_value[0]}, {selected_value[1]})"
        else:
            detail = "  [Not configured]"
        
        cv2.putText(
            panel, detail, (10, y + 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1
        )
        
        # Combine
        result = np.vstack([panel, img])
        return result
    
    def run(self):
        """Run interactive editor."""
        self.logger.info("Starting region editor")
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 800)
        
        # Enable window close button
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        
        try:
            while True:
                # Check if window was closed
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    if self.unsaved_changes:
                        print("\n⚠️  You have unsaved changes!")
                        response = input("Save before exiting? (y/n): ").strip().lower()
                        if response == 'y':
                            self.save_coords()
                    break
                
                # Capture and draw
                screen = self.capture_screen()
                result = self.draw_regions(screen)
                
                if self.show_help:
                    result = self.add_info_panel(result)
                
                # Show
                cv2.imshow(self.window_name, result)
                
                # Handle keyboard - USE waitKeyEx for arrow keys!
                key = cv2.waitKeyEx(50)
                
                if key != -1:  # Key was pressed
                    if not self._handle_keypress(key):
                        break
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        
        finally:
            cv2.destroyAllWindows()
            self.sct.close()
    
    def _handle_keypress(self, key: int) -> bool:
        """
        Handle keyboard input.
        Returns False to exit.
        """
        # ESC - Exit
        if key == 27:
            if self.unsaved_changes:
                print("\n⚠️  You have unsaved changes!")
                response = input("Save before exiting? (y/n): ").strip().lower()
                if response == 'y':
                    self.save_coords()
            return False
        
        # H - Toggle help
        elif key == ord('h') or key == ord('H'):
            self.show_help = not self.show_help
        
        # Ctrl+S - Save (key code for ENTER is 13)
        elif key == 13:
            self.save_coords()
        
        # R - Reset to defaults
        elif key == ord('r') or key == ord('R'):
            self.coords = self._create_default_coords()
            self.unsaved_changes = True
            self.logger.info("Reset to default coordinates")
            print("\n⚠️  Reset to default positions!")
        
        # 1-8 - Select region
        elif ord('1') <= key <= ord(f'{len(self.REGION_KEYS)}'):
            idx = key - ord('1')
            if idx < len(self.REGION_KEYS):
                self.selected_region = idx
                self.logger.info(f"Selected: {self.LABELS[self.REGION_KEYS[idx]]}")
        
        # TAB - Next region
        elif key == 9:
            self.selected_region = (self.selected_region + 1) % len(self.REGION_KEYS)
        
        # Arrow keys using waitKeyEx codes (Windows)
        elif key == 2424832:  # Left arrow
            self._move_region('left')
        elif key == 2555904:  # Right arrow
            self._move_region('right')
        elif key == 2490368:  # Up arrow
            self._move_region('up')
        elif key == 2621440:  # Down arrow
            self._move_region('down')
        
        # WASD alternative for movement (W=up, A=left, S=down, D=right)
        elif key == ord('w') or key == ord('W'):
            self._move_region('up')
        elif key == ord('a') or key == ord('A'):
            self._move_region('left')
        elif key == ord('s') or key == ord('S'):
            self._move_region('down')
        elif key == ord('d') or key == ord('D'):
            self._move_region('right')
        
        # +/= - Resize both width and height
        elif key == ord('+') or key == ord('='):
            self._resize_region('both', increase=True)
        elif key == ord('-') or key == ord('_'):
            self._resize_region('both', increase=False)
        
        # [ ] - Resize width only
        elif key == ord('['):
            self._resize_region('width', increase=False)
        elif key == ord(']'):
            self._resize_region('width', increase=True)
        
        # , . - Resize height only
        elif key == ord(',') or key == ord('<'):
            self._resize_region('height', increase=False)
        elif key == ord('.') or key == ord('>'):
            self._resize_region('height', increase=True)
            
        # m n - Increase Step Value
        elif key == ord('m') or key == ord('M'):
            self.step *= 5 if self.step < 125 else 1
        elif key == ord('n') or key == ord('N'):
            self.step //= 5 if self.step > 1 else 1
        
        return True
    
    def _move_region(self, direction: str):
        """Move selected region in given direction."""
        selected_key = self.REGION_KEYS[self.selected_region]
        value = self.coords[selected_key]
               
        if isinstance(value, dict):
            if direction == 'left':
                value['left'] -= self.step
            elif direction == 'right':
                value['left'] += self.step
            elif direction == 'up':
                value['top'] -= self.step
            elif direction == 'down':
                value['top'] += self.step
        
        elif isinstance(value, list):
            if direction == 'left':
                value[0] -= self.step
            elif direction == 'right':
                value[0] += self.step
            elif direction == 'up':
                value[1] -= self.step
            elif direction == 'down':
                value[1] += self.step
        
        self.unsaved_changes = True
    
    def _resize_region(self, dimension: str, increase: bool):
        """
        Resize selected region.
        
        Args:
            dimension: 'width', 'height', or 'both'
            increase: True to increase, False to decrease
        """
        selected_key = self.REGION_KEYS[self.selected_region]
        value = self.coords[selected_key]
        
        if not isinstance(value, dict):
            return  # Can't resize point coordinates
        
        direction = 1 if increase else -1
        
        if dimension == 'width':
            value['width'] = max(10, value['width'] + self.step * direction)
        elif dimension == 'height':
            value['height'] = max(10, value['height'] + self.step * direction)
        elif dimension == 'both':
            value['width'] = max(10, value['width'] + self.step * direction)
            value['height'] = max(10, value['height'] + self.step * direction)
        
        self.unsaved_changes = True
    
    def save_coords(self):
        """Save coordinates to JSON file."""
        try:
            # Load existing data
            with open(self.coords_file, 'r') as f:
                data = json.load(f)
            
            # Update
            if self.config_name not in data:
                data[self.config_name] = {}
            
            data[self.config_name][self.position] = self.coords
            
            # Save
            with open(self.coords_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.unsaved_changes = False
            self.logger.info(f"✅ Saved: {self.config_name}/{self.position}")
            print(f"\n✅ Coordinates saved to {self.coords_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving: {e}")
            print(f"\n❌ Error saving: {e}")


def list_configs(coords_file: Path):
    """List all saved configurations."""
    try:
        with open(coords_file, 'r') as f:
            data = json.load(f)
        
        if not data:
            print("\nNo saved configurations.")
            return
        
        print("\n" + "="*60)
        print("SAVED CONFIGURATIONS")
        print("="*60)
        
        for config_name, positions in data.items():
            print(f"\n📺 {config_name}")
            for position in positions.keys():
                print(f"   └─ {position}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"Error listing configs: {e}")


def main():
    """Main entry point."""
    print("="*60)
    print("REGION EDITOR v2.0 - Interactive Region Configuration")
    print("="*60)
    
    coords_file = Path("data/coordinates/bookmaker_coords.json")
    
    print("\n1. Edit existing configuration")
    print("2. Create new configuration")
    print("3. List all configurations")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == '3':
        list_configs(coords_file)
        return
    
    elif choice == '2':
        print("\n--- CREATE NEW CONFIGURATION ---")
        config_name = input("Configuration name (e.g., 'Four 100%', 'Six 80%'): ").strip()
        position = input("Bookmaker name (e.g., 'BalkanBet', 'Mozzart'): ").strip()
        
        if not config_name or not position:
            print("Invalid input!")
            return
        
    elif choice == '1':
        list_configs(coords_file)
        config_name = input("\nConfiguration name: ").strip()
        position = input("Bookmaker name: ").strip()
        
        if not config_name or not position:
            print("Invalid input!")
            return
    
    else:
        print("Invalid choice!")
        return
    
    # Run editor
    try:
        editor = RegionEditor(config_name, position)
        editor.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()