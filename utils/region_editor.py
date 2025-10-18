# utils/region_editor.py
# VERSION: 2.1 - FIXED DUAL MONITOR SUPPORT
# PURPOSE: Complete region editor with dual monitor option
# FEATURES: Interactive adjustment, keyboard controls, dual monitor support

import cv2
import numpy as np
import mss
from PIL import Image
import time
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import init_logging, AviatorLogger


class RegionEditor:
    """
    Interactive region editor with full keyboard controls.
    FIXED: Dual monitor support properly integrated!
    """
    
    SCREEN_WIDTH = 2560  # Width of left screen for dual monitor
    
    COLORS = {
        'score_region': (0, 255, 0),
        'my_money_region': (255, 0, 0),
        'other_count_region': (0, 128, 255),
        'other_money_region': (0, 255, 255),
        'phase_region': (255, 0, 255),
        'play_amount_coords': (0, 0, 255),
        'play_button_coords': (255, 255, 0),
        'auto_play_coords': (255, 0, 128)
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
    
    def __init__(
        self,
        bookmaker_name: str,
        double_monitor: bool = False,
        coords_file: str = "data/coordinates/bookmaker_coords.json"
    ):
        """
        Initialize region editor.
        
        Args:
            bookmaker_name: Name of bookmaker (e.g., 'BalkanBet')
            double_monitor: True if using 2 monitors (adds 2560 to left coords)
            coords_file: Path to coordinates JSON
        """
        init_logging()
        self.logger = AviatorLogger.get_logger("RegionEditor")
        
        self.bookmaker_name = bookmaker_name
        self.coords_file = Path(coords_file)
        
        # Dual monitor offset (0 if single monitor, 2560 if dual)
        self.screen_offset = self.SCREEN_WIDTH if double_monitor else 0
        
        self.logger.info(f"Region editor initialized: {bookmaker_name}, dual_monitor={double_monitor}, offset={self.screen_offset}")
        
        # Ensure file and directory exist
        self.coords_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.coords_file.exists():
            with open(self.coords_file, 'w') as f:
                json.dump({"positions": {}, "bookmakers": {}}, f, indent=2)
        
        # Load or create coordinates
        self.coords = self._load_or_create_coords()
        
        # Screen capture
        self.sct = mss.mss()
        self.capture_offset = (0, 0)
        
        # State
        self.selected_region = 0
        self.show_help = True
        self.unsaved_changes = False
        self.step = 5
        
        # Window
        self.window_name = f"Region Editor - {bookmaker_name}"
    
    def _load_or_create_coords(self) -> Dict:
        """Load existing or create new coordinates."""
        try:
            with open(self.coords_file, 'r') as f:
                data = json.load(f)
            
            # Check if bookmaker exists
            if "bookmakers" in data and self.bookmaker_name in data["bookmakers"]:
                self.logger.info(f"Loaded existing coordinates: {self.bookmaker_name}")
                return data["bookmakers"][self.bookmaker_name]
            else:
                self.logger.info(f"Creating new configuration: {self.bookmaker_name}")
                return self._create_default_coords()
                
        except Exception as e:
            self.logger.error(f"Error loading coordinates: {e}")
            return self._create_default_coords()
    
    def _create_default_coords(self) -> Dict:
        """Create default coordinates (center of screen WITH offset applied)."""
        # Get monitor size (use second monitor if dual setup)
        monitor_idx = 2 if self.screen_offset > 0 else 1
        monitor = self.sct.monitors[monitor_idx] if monitor_idx < len(self.sct.monitors) else self.sct.monitors[1]
        
        center_x = monitor['left'] + monitor['width'] // 2
        center_y = monitor['top'] + monitor['height'] // 2
        
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
            'play_amount_coords': {'left': center_x - 100, 'top': center_y + 200, 'width': 100, 'height': 30},
            'play_button_coords': {'left': center_x + 50, 'top': center_y + 200, 'width': 100, 'height': 30},
            'auto_play_coords': {'left': center_x + 200, 'top': center_y + 200, 'width': 100, 'height': 30}
        }
    
    def capture_screen(self) -> np.ndarray:
        """Capture screen region containing all coordinates."""
        all_coords = []
        
        for key, value in self.coords.items():
            if isinstance(value, dict) and 'left' in value:
                # Apply screen offset for capture
                left = value['left'] + self.screen_offset
                all_coords.append((left, value['top']))
                all_coords.append((left + value['width'], value['top'] + value['height']))
        
        if not all_coords:
            # Fallback to appropriate monitor
            monitor_idx = 2 if self.screen_offset > 0 else 1
            monitor = self.sct.monitors[monitor_idx] if monitor_idx < len(self.sct.monitors) else self.sct.monitors[1]
            self.capture_offset = (0, 0)
            sct_img = self.sct.grab(monitor)
        else:
            xs = [c[0] for c in all_coords]
            ys = [c[1] for c in all_coords]
            
            left = max(0, min(xs) - 100)
            top = max(0, min(ys) - 100)
            right = max(xs) + 100
            bottom = max(ys) + 100
            
            self.capture_offset = (left, top)
            
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
            is_selected = (idx == self.selected_region)
            thickness = 1
            
            if isinstance(value, dict) and 'left' in value:
                # Apply screen offset, then subtract capture offset
                left = (value['left'] + self.screen_offset) - offset_x
                top = value['top'] - offset_y
                width = value['width']
                height = value['height']
                
                # Draw rectangle
                cv2.rectangle(overlay, (left, top), (left + width, top + height), color, thickness)
                
                if is_selected:
                    cv2.rectangle(overlay, (left - 5, top - 5), (left + width + 5, top + height + 5), (255, 255, 0), 2)
                
                # Label
                label_text = f"{idx+1}. {label}"
                if is_selected:
                    label_text += " [SELECTED]"
                
                (text_width, text_height), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(overlay, (left, top - text_height - 10), (left + text_width + 10, top), color, -1)
                cv2.putText(overlay, label_text, (left + 5, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                
                # Dimensions
                dim_text = f"{width}x{height}"
                cv2.putText(overlay, dim_text, (left + 5, top + height + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Center crosshair
                center_x = left + width // 2
                center_y = top + height // 2
                cv2.drawMarker(overlay, (center_x, center_y), color, cv2.MARKER_CROSS, 15, 2)
        
        alpha = 0.8
        result = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        return result
    
    def add_info_panel(self, img: np.ndarray) -> np.ndarray:
        """Add control panel."""
        panel_height = 250
        panel = np.zeros((panel_height, img.shape[1], 3), dtype=np.uint8)
        panel[:] = (30, 30, 30)
        
        # Title
        title = f"Region Editor - {self.bookmaker_name}"
        if self.screen_offset > 0:
            title += " [DUAL MONITOR]"
        if self.unsaved_changes:
            title += " [UNSAVED]"
        
        cv2.putText(panel, title, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Controls
        controls = [
            f"SELECTION: 1-{len(self.REGION_KEYS)} keys | TAB: Next region",
            "MOVE: Arrow Keys (← → ↑ ↓) OR WASD (W=up A=left S=down D=right)",
            f"RESIZE: +/- Both | [] Width | <> Height | m/n Step ({self.step})",
            "ACTIONS: Enter: Save | R: Reset | H: Help | ESC/X: Exit"
        ]
        
        y = 55
        for i, control in enumerate(controls):
            color = (200, 200, 200) if i < 3 else (100, 255, 100)
            cv2.putText(panel, control, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            y += 30
        
        # Current selection
        selected_key = self.REGION_KEYS[self.selected_region]
        selected_label = self.LABELS.get(selected_key, selected_key)
        selected_value = self.coords.get(selected_key)
        
        info_text = f"SELECTED: {selected_label}"
        cv2.putText(panel, info_text, (10, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        if isinstance(selected_value, dict):
            detail = f"  Position: ({selected_value['left']}, {selected_value['top']})  Size: {selected_value['width']}x{selected_value['height']}"
        else:
            detail = "  [Not configured]"
        
        cv2.putText(panel, detail, (10, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        
        result = np.vstack([panel, img])
        return result
    
    def run(self):
        """Run interactive editor."""
        self.logger.info("Starting region editor")
        print(f"\n🎮 Editing regions for: {self.bookmaker_name}")
        print(f"📺 Monitor setup: {'DUAL (Right screen)' if self.screen_offset > 0 else 'SINGLE'}")
        print(f"💾 Coordinates saved as BASE (for TL position)")
        print("\n⌨️  Press 'H' to toggle help panel\n")
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 800)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        
        try:
            while True:
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    if self.unsaved_changes:
                        print("\n⚠️  You have unsaved changes!")
                        response = input("Save before exiting? (y/n): ").strip().lower()
                        if response == 'y':
                            self.save_coords()
                    break
                
                screen = self.capture_screen()
                result = self.draw_regions(screen)
                
                if self.show_help:
                    result = self.add_info_panel(result)
                
                cv2.imshow(self.window_name, result)
                key = cv2.waitKeyEx(50)
                
                if key != -1:
                    if not self._handle_keypress(key):
                        break
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            cv2.destroyAllWindows()
            self.sct.close()
    
    def _handle_keypress(self, key: int) -> bool:
        """Handle keyboard input."""
        if key == 27:  # ESC
            if self.unsaved_changes:
                print("\n⚠️  You have unsaved changes!")
                response = input("Save before exiting? (y/n): ").strip().lower()
                if response == 'y':
                    self.save_coords()
            return False
        
        elif key == ord('h') or key == ord('H'):
            self.show_help = not self.show_help
        
        elif key == 13:  # Enter
            self.save_coords()
        
        elif key == ord('r') or key == ord('R'):
            self.coords = self._create_default_coords()
            self.unsaved_changes = True
            print("\n🔄 Reset to default positions!")
        
        elif ord('1') <= key <= ord(f'{len(self.REGION_KEYS)}'):
            idx = key - ord('1')
            if idx < len(self.REGION_KEYS):
                self.selected_region = idx
        
        elif key == 9:  # TAB
            self.selected_region = (self.selected_region + 1) % len(self.REGION_KEYS)
        
        # Arrow keys
        elif key == 2424832:  # Left
            self._move_region('left')
        elif key == 2555904:  # Right
            self._move_region('right')
        elif key == 2490368:  # Up
            self._move_region('up')
        elif key == 2621440:  # Down
            self._move_region('down')
        
        # WASD
        elif key == ord('w') or key == ord('W'):
            self._move_region('up')
        elif key == ord('a') or key == ord('A'):
            self._move_region('left')
        elif key == ord('s') or key == ord('S'):
            self._move_region('down')
        elif key == ord('d') or key == ord('D'):
            self._move_region('right')
        
        # Resize
        elif key == ord('+') or key == ord('='):
            self._resize_region('both', increase=True)
        elif key == ord('-') or key == ord('_'):
            self._resize_region('both', increase=False)
        elif key == ord('['):
            self._resize_region('width', increase=False)
        elif key == ord(']'):
            self._resize_region('width', increase=True)
        elif key == ord(',') or key == ord('<'):
            self._resize_region('height', increase=False)
        elif key == ord('.') or key == ord('>'):
            self._resize_region('height', increase=True)
        
        # Step adjustment
        elif key == ord('m') or key == ord('M'):
            self.step = min(125, self.step * 5)
            print(f"Step size: {self.step}")
        elif key == ord('n') or key == ord('N'):
            self.step = max(1, self.step // 5)
            print(f"Step size: {self.step}")
        
        return True
    
    def _move_region(self, direction: str):
        """Move selected region."""
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
        
        self.unsaved_changes = True
    
    def _resize_region(self, dimension: str, increase: bool):
        """Resize selected region."""
        selected_key = self.REGION_KEYS[self.selected_region]
        value = self.coords[selected_key]
        
        if not isinstance(value, dict):
            return
        
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
            # Load existing
            with open(self.coords_file, 'r') as f:
                data = json.load(f)
            
            # Ensure structure
            if "bookmakers" not in data:
                data["bookmakers"] = {}
            if "positions" not in data:
                data["positions"] = {}
            
            # Save bookmaker coords
            data["bookmakers"][self.bookmaker_name] = self.coords
            
            # Write
            with open(self.coords_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.unsaved_changes = False
            self.logger.info(f"✅ Saved: {self.bookmaker_name}")
            
            print(f"\n✅ Coordinates saved!")
            print(f"   Bookmaker: {self.bookmaker_name}")
            print(f"   File: {self.coords_file}")
            print(f"   Regions: {len([k for k in self.coords.keys() if k in self.REGION_KEYS])}")
            
        except Exception as e:
            self.logger.error(f"Error saving: {e}")
            print(f"\n❌ Error saving: {e}")


def main():
    """Main entry point."""
    print("="*70)
    print("REGION EDITOR v2.1 - Keyboard-Based + Dual Monitor Support")
    print("="*70)
    
    # Get bookmaker name
    bookmaker_name = input("\nBookmaker name (e.g., BalkanBet, Mozzart): ").strip()
    if not bookmaker_name:
        print("❌ Bookmaker name required!")
        return
    
    # Ask about dual monitor
    dual_input = input("\nAre you using DUAL monitors (browser on RIGHT screen)? (y/n): ").strip().lower()
    double_monitor = (dual_input == 'y')
    
    if double_monitor:
        print(f"\n📺 DUAL MONITOR MODE")
        print(f"   - Will add {RegionEditor.SCREEN_WIDTH}px offset to coordinates")
        print(f"   - Coordinates saved as BASE (for TL position)")
    else:
        print(f"\n📺 SINGLE MONITOR MODE")
        print(f"   - Coordinates saved as-is (for TL position)")
    
    print("\n" + "="*70)
    print("IMPORTANT:")
    print("  • Browser should be FULLSCREEN (F11)")
    print("  • Coordinates are BASE coordinates (TopLeft position)")
    print("  • Layout system will calculate other positions automatically")
    print("="*70)
    
    input("\nPress Enter to start editing...")
    
    try:
        editor = RegionEditor(bookmaker_name, double_monitor)
        editor.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()