# utils/video_region_editor.py
# VERSION: 2.2 - ZERO input() calls, SVE kroz GUI!
# Interaktivni editor - SVE se dešava u GUI window-u

import cv2
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class VideoRegionEditor:
    """
    Interaktivni tool za definisanje TEMP regiona.
    NEMA input() - sve preko keyboard u GUI!
    """
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        self.cap = None
        self.current_frame = None
        self.current_frame_number = 0
        self.total_frames = 0
        self.fps = 0
        
        self.regions = []
        self.drawing = False
        self.start_point = None
        self.current_rect = None
        
        # Rename mode
        self.rename_mode = False
        self.rename_buffer = ""
        
        # Confirm mode
        self.confirm_exit = False
        
        # Window
        self.window_name = "Video Region Editor"
        
        # Colors
        self.color_drawing = (0, 255, 0)
        self.color_finished = (255, 0, 255)
        self.color_text_bg = (0, 0, 0)
        self.color_text = (255, 255, 255)
        
    def open_video(self) -> bool:
        """Otvara video."""
        self.cap = cv2.VideoCapture(str(self.video_path))
        
        if not self.cap.isOpened():
            print(f"❌ Ne mogu otvoriti video: {self.video_path}")
            return False
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"✅ Video: {self.video_path.name}")
        print(f"   {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {self.fps:.1f}fps")
        print(f"   {self.total_frames} frames ({self.total_frames/self.fps/60:.1f} min)\n")
        
        return self.load_frame(0)
    
    def load_frame(self, frame_number: int) -> bool:
        """Učitava frame."""
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if not ret:
            return False
        
        self.current_frame = frame.copy()
        self.current_frame_number = frame_number
        return True
    
    def next_frame(self, step: int = 1):
        """Sledeći frame."""
        self.load_frame(self.current_frame_number + step)
    
    def prev_frame(self, step: int = 1):
        """Prethodni frame."""
        self.load_frame(self.current_frame_number - step)
    
    def jump_to_percent(self, percent: int):
        """Skoči na procenat."""
        frame_num = int(self.total_frames * percent / 100.0)
        self.load_frame(frame_num)
    
    def mouse_callback(self, event, x, y, flags, param):
        """Mouse handler."""
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing and self.start_point:
                self.current_rect = (self.start_point, (x, y))
                
        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing and self.start_point:
                x1, y1 = self.start_point
                x2, y2 = x, y
                
                x_min = min(x1, x2)
                y_min = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                if width > 10 and height > 10:
                    region_name = f"region_{len(self.regions) + 1}"
                    
                    self.regions.append({
                        'name': region_name,
                        'x': x_min,
                        'y': y_min,
                        'width': width,
                        'height': height,
                        'description': 'Temp region'
                    })
                    
                    print(f"✅ Region {len(self.regions)}: {region_name} ({x_min},{y_min}) {width}x{height}")
            
            # Reset
            self.drawing = False
            self.current_rect = None
            self.start_point = None
    
    def draw_overlay(self) -> None:
        """Crta sve na frame-u."""
        if self.current_frame is None:
            return
        
        display = self.current_frame.copy()
        
        # Regioni
        for i, region in enumerate(self.regions):
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            name = region['name']
            
            cv2.rectangle(display, (x, y), (x+w, y+h), self.color_finished, 2)
            
            label = f"{i+1}. {name}"
            cv2.rectangle(display, (x, y-25), (x+150, y), self.color_text_bg, -1)
            cv2.putText(display, label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_text, 2)
        
        # Trenutni rect
        if self.current_rect and self.drawing:
            pt1, pt2 = self.current_rect
            cv2.rectangle(display, pt1, pt2, self.color_drawing, 2)
        
        # Info panel
        h = display.shape[0]
        panel_h = 120
        panel = display[h-panel_h:h].copy()
        panel[:] = (30, 30, 30)
        
        time_sec = self.current_frame_number / self.fps
        info = [
            f"Frame: {self.current_frame_number}/{self.total_frames} ({time_sec:.1f}s)",
            f"Regiona: {len(self.regions)}",
            "",
            "ARROWS: Navigate | 1-9: % | R: Rename | Z: Delete | ENTER: Save | ESC: Exit"
        ]
        
        # Rename mode
        if self.rename_mode:
            info.append("")
            info.append(f"RENAME MODE: '{self.rename_buffer}_' (ENTER=save, ESC=cancel)")
        
        # Confirm exit
        if self.confirm_exit:
            info.append("")
            info.append("UNSAVED! Press Y to exit, N to cancel")
        
        y_pos = h - panel_h + 25
        for line in info:
            color = (255, 255, 0) if "RENAME" in line or "UNSAVED" in line else (200, 200, 200)
            cv2.putText(display, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y_pos += 20
        
        cv2.imshow(self.window_name, display)
    
    def handle_rename_key(self, key: int):
        """Hendluje tipkanje u rename modu."""
        if key == 13:  # ENTER
            if self.rename_buffer and self.regions:
                self.regions[-1]['name'] = self.rename_buffer
                print(f"✅ Renamed to: {self.rename_buffer}")
            self.rename_mode = False
            self.rename_buffer = ""
            
        elif key == 27:  # ESC
            self.rename_mode = False
            self.rename_buffer = ""
            print("❌ Rename cancelled")
            
        elif key == 8:  # Backspace
            self.rename_buffer = self.rename_buffer[:-1]
            
        elif 32 <= key <= 126:  # Printable chars
            self.rename_buffer += chr(key)
    
    def save_regions(self) -> Optional[Path]:
        """Snima regione."""
        if not self.regions:
            print("⚠️  Nema regiona!")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"data/coordinates/temp_video_regions_{timestamp}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {
            "type": "TEMPORARY_VIDEO_REGIONS",
            "note": "Temporary regioni za video ekstrakciju",
            "source_video": str(self.video_path.name),
            "video_resolution": f"{self.current_frame.shape[1]}x{self.current_frame.shape[0]}",
            "created": datetime.now().isoformat(),
            "regions": self.regions
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Saved: {output_path}")
        print(f"📊 {len(self.regions)} regiona\n")
        
        return output_path
    
    def run(self) -> Optional[Path]:
        """Main loop."""
        if not self.open_video():
            return None
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("="*60)
        print("VIDEO REGION EDITOR - Svi kontrole u GUI prozoru!")
        print("="*60)
        print("MOUSE:    Drag = crtaj region")
        print("ARROWS:   ◄► = 1 frame, ↑↓ = 10 frames")
        print("PAGE:     PgUp/Dn = 100 frames")
        print("NUMBERS:  1-9 = skoči na %")
        print("R:        Preimenuj poslednji (tipkaj ime u GUI)")
        print("Z:        Obriši poslednji")
        print("ENTER:    Snimi regione")
        print("ESC:      Izađi")
        print("="*60 + "\n")
        
        output_path = None
        
        while True:
            self.draw_overlay()
            
            key = cv2.waitKeyEx(10)
            if key == -1:
                continue
            
            key = key & 0xFFFFFFFF
            
            # Rename mode
            if self.rename_mode:
                self.handle_rename_key(key)
                continue
            
            # Confirm exit mode
            if self.confirm_exit:
                if key == ord('y') or key == ord('Y'):
                    print("👋 Exiting without save...")
                    break
                elif key == ord('n') or key == ord('N'):
                    self.confirm_exit = False
                continue
            
            # Normal mode
            if key == 27:  # ESC
                if self.regions:
                    self.confirm_exit = True
                else:
                    break
                    
            elif key == 13:  # ENTER
                output_path = self.save_regions()
                if output_path:
                    break
                    
            elif key == ord('r') or key == ord('R'):
                if self.regions:
                    self.rename_mode = True
                    self.rename_buffer = self.regions[-1]['name']
                    print("📝 Rename mode - tipkaj u GUI!")
                    
            elif key == ord('z') or key == ord('Z') or key == 8:
                if self.regions:
                    removed = self.regions.pop()
                    print(f"🗑️  Deleted: {removed['name']}")
                    
            # Arrows
            elif key == 2424832:  # Left
                self.prev_frame(1)
            elif key == 2555904:  # Right
                self.next_frame(1)
            elif key == 2490368:  # Up
                self.prev_frame(10)
            elif key == 2621440:  # Down
                self.next_frame(10)
                
            # Page
            elif key == 2162688:  # Page Up
                self.prev_frame(100)
            elif key == 2228224:  # Page Down
                self.next_frame(100)
                
            # Numbers 1-9
            elif ord('1') <= key <= ord('9'):
                percent = (key - ord('0')) * 10
                self.jump_to_percent(percent)
                print(f"⏩ {percent}%")
        
        # Cleanup
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        
        return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Video region editor - ZERO terminal input!")
    parser.add_argument("video_path", type=str, help="Video file")
    args = parser.parse_args()
    
    editor = VideoRegionEditor(args.video_path)
    output_path = editor.run()
    
    if output_path:
        print(f"✅ Config saved: {output_path}")
        print(f"Usage: python utils/video_screenshot_extractor.py <video> --regions-config {output_path}")
    else:
        print("❌ No config created")