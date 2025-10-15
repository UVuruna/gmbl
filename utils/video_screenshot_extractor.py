# utils/video_screenshot_extractor.py
# VERSION: 3.0
# REVERSED ORDER + MASTER COLLAGES + TIMESTAMPS

import cv2
import json
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import re


class VideoScreenshotExtractor:
    """
    Ekstraktuje screenshot-ove sa OBRNUTIM redosledom i pravi master kolaže.
    
    v3.0:
    - Screenshot-ovi po video snimku OBRNUTI (poslednji gore → prvi dole)
    - Master kolaž za svaki region (svi screenshot-ovi svih videa)
    - Timestamp-ovi pored screenshot-ova
    - Automatski završni frame samo za poslednji video
    """
    
    def __init__(self, regions_config_path: str = "data/coordinates/video_regions.json"):
        self.regions_config_path = Path(regions_config_path)
        self.regions = self._load_regions()
        
        # Za master kolaže - čuvamo sve screenshot-ove kroz sve videe
        self.master_data = {}  # {region_name: [(image, timestamp), ...]}
        
    def _load_regions(self) -> List[Dict]:
        """Učitava regione."""
        if not self.regions_config_path.exists():
            print(f"⚠️  Config ne postoji: {self.regions_config_path}")
            return []
            
        with open(self.regions_config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get('type') == 'TEMPORARY_VIDEO_REGIONS':
            print(f"✅ Učitani TEMP regioni iz: {self.regions_config_path.name}")
        
        return data.get('regions', [])
    
    def parse_video_timestamp(self, video_path: Path) -> Optional[datetime]:
        """
        Parsira početno vreme iz imena video fajla.
        Format: "2025-10-07 11-20-04.avi" -> datetime(2025, 10, 7, 11, 20, 4)
        """
        filename = video_path.stem
        
        # Regex: YYYY-MM-DD HH-MM-SS
        pattern = r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2})-(\d{2})-(\d{2})'
        match = re.search(pattern, filename)
        
        if match:
            year, month, day, hour, minute, second = map(int, match.groups())
            try:
                return datetime(year, month, day, hour, minute, second)
            except ValueError:
                print(f"  ⚠️  Invalid datetime: {filename}")
                return None
        else:
            print(f"  ⚠️  Cannot parse datetime: {filename}")
            return None
    
    def extract_frame_at_time(self, video_path: Path, time_minutes: float) -> np.ndarray:
        """Ekstraktuje frame na određenom vremenu."""
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Ne mogu otvoriti video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_number = int(time_minutes * 60 * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"Ne mogu pročitati frame na {time_minutes:.1f} min")
        
        return frame
    
    def extract_final_frame(self, video_path: Path, seconds_before_end: float = 1.0) -> np.ndarray:
        """Ekstraktuje frame X sekundi pre kraja."""
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Ne mogu otvoriti video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frames_before_end = int(seconds_before_end * fps)
        final_frame_number = max(0, total_frames - frames_before_end)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, final_frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"Ne mogu pročitati završni frame")
        
        return frame
    
    def extract_regions_from_frame(self, frame: np.ndarray) -> Dict[str, np.ndarray]:
        """Ekstraktuje sve regione iz frame-a."""
        regions_crops = {}
        
        for region in self.regions:
            x = region['x']
            y = region['y']
            w = region['width']
            h = region['height']
            name = region['name']
            
            crop = frame[y:y+h, x:x+w].copy()
            regions_crops[name] = crop
        
        return regions_crops
    
    def create_vertical_collage_with_timestamps(
        self,
        region_images: List[np.ndarray],
        timestamps: List[datetime],
        region_name: str,
        spacing: int = 30,
        bg_color: Tuple[int,int,int] = (40, 40, 40),
        break_height: int = 35
    ) -> Image.Image:
        """
        Kreira vertikalni kolaž OBRNUTIM redom (poslednji gore → prvi dole).
        "Break - YYYY-MM-DD HH:MM:SS" u istoj liniji iznad screenshot-a.
        """
        if not region_images:
            raise ValueError("Nema slika!")
        
        # OBRNI redosled - poslednji gore, prvi dole
        region_images = list(reversed(region_images))
        timestamps = list(reversed(timestamps))
        
        # Konvertuj BGR → RGB
        pil_images = [Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) 
                      for img in region_images]
        
        # Dimensions
        max_img_width = max(img.width for img in pil_images)
        total_width = max_img_width + 40  # Padding
        
        # Visina: header + (break_height + screenshot + spacing) za svaki screenshot
        total_height = 100  # Header
        for img in pil_images:
            total_height += break_height + img.height + spacing
        
        # Kreiraj kolaž
        collage = Image.new('RGB', (total_width, total_height), 
                           (bg_color[2], bg_color[1], bg_color[0]))
        
        draw = ImageDraw.Draw(collage)
        
        # Font
        try:
            font_large = ImageFont.truetype("arial.ttf", 28)
            font_small = ImageFont.truetype("arial.ttf", 16)
            font_break = ImageFont.truetype("arialbd.ttf", 20)  # Manji bold za Break
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_break = ImageFont.load_default()
        
        # Header
        header = f"{region_name} (najnoviji → najstariji)"
        draw.text((20, 30), header, fill=(255, 255, 255), font=font_large)
        draw.text((20, 65), f"{len(pil_images)} screenshot-ova", 
                 fill=(180, 180, 180), font=font_small)
        
        # Lepi screenshot-ove
        current_y = 120
        
        for i, (img, timestamp) in enumerate(zip(pil_images, timestamps)):
            x_offset = 20
            
            # --- "Break - YYYY-MM-DD HH:MM:SS" U ISTOJ LINIJI ---
            break_y = current_y + (break_height // 2) - 10
            
            # Format: "Break - 2025-10-08 05:20:05"
            if timestamp:
                break_text = f"Break - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                break_text = "Break"
            
            # Background za Break+timestamp
            text_bbox = draw.textbbox((0, 0), break_text, font=font_break)
            text_width = text_bbox[2] - text_bbox[0]
            
            draw.rectangle(
                [x_offset - 5, current_y, x_offset + text_width + 10, current_y + break_height - 5],
                fill=(80, 80, 80),
                outline=(255, 255, 0),
                width=2
            )
            
            # "Break - timestamp" text
            draw.text((x_offset + 5, break_y), break_text, fill=(255, 255, 0), font=font_break)
            
            current_y += break_height
            
            # --- SCREENSHOT ---
            collage.paste(img, (x_offset, current_y))
            
            # Separator line (ako nije poslednji)
            if i < len(pil_images) - 1:
                line_y = current_y + img.height + (spacing // 2)
                draw.line([(20, line_y), (total_width - 20, line_y)], 
                         fill=(80, 80, 80), width=1)
            
            current_y += img.height + spacing
        
        return collage
    
    def process_single_video(
        self,
        video_path: Path,
        interval_minutes: int = 16,
        output_dir: Path = None,
        include_final_frame: bool = False
    ) -> Dict[str, Path]:
        """Procesuje jedan video - screenshot-ovi OBRNUTIM redom."""
        if output_dir is None:
            output_dir = Path("data/video_screenshots")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parsuj početno vreme iz imena
        start_time = self.parse_video_timestamp(video_path)
        
        # Video info
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_minutes = (frame_count / fps) / 60
        cap.release()
        
        print(f"\n📹 {video_path.name}")
        print(f"⏱️  Trajanje: {duration_minutes:.1f} min")
        if start_time:
            print(f"🕐 Početak: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Time points
        time_points = list(range(0, int(duration_minutes), interval_minutes))
        
        # Dodaj završni frame ako treba
        if include_final_frame:
            final_time_min = (frame_count / fps - 1.0) / 60.0
            if final_time_min > 0:
                time_points.append(final_time_min)
        
        print(f"📸 Ekstrakcija na: {[f'{t:.0f}min' for t in time_points]}")
        
        # Ekstraktuj
        regions_over_time = {region['name']: [] for region in self.regions}
        timestamps_per_region = {region['name']: [] for region in self.regions}
        
        for time_min in time_points:
            try:
                frame = self.extract_frame_at_time(video_path, time_min)
                regions_crops = self.extract_regions_from_frame(frame)
                
                # Timestamp za ovaj screenshot
                if start_time:
                    screenshot_time = start_time + timedelta(minutes=time_min)
                else:
                    screenshot_time = None
                
                for region_name, crop in regions_crops.items():
                    regions_over_time[region_name].append(crop)
                    timestamps_per_region[region_name].append(screenshot_time)
                    
                    # Sačuvaj za master kolaž
                    if region_name not in self.master_data:
                        self.master_data[region_name] = []
                    self.master_data[region_name].append((crop, screenshot_time))
                
                is_final = (time_min == time_points[-1] and include_final_frame)
                marker = " [ZAVRŠNI]" if is_final else ""
                print(f"  ✓ {time_min:.0f} min{marker}")
                
            except Exception as e:
                print(f"  ✗ {time_min:.0f} min - {e}")
        
        # Kreiraj kolaže za ovaj video (OBRNUTIM redom)
        collage_paths = {}
        video_basename = video_path.stem
        
        for region_name, images in regions_over_time.items():
            if not images:
                continue
            
            timestamps = timestamps_per_region[region_name]
            
            collage = self.create_vertical_collage_with_timestamps(
                images,
                timestamps,
                region_name
            )
            
            output_filename = f"{video_basename}_{region_name}_collage.png"
            output_path = output_dir / output_filename
            collage.save(output_path)
            
            collage_paths[region_name] = output_path
            print(f"  ✅ {output_filename} ({len(images)} screenshot-ova, OBRNUTO + Break)")
        
        return collage_paths
    
    def create_master_collages(self, output_dir: Path = None):
        """
        Kreira MASTER kolaže za svaki region.
        Sadrži SVE screenshot-ove iz SVIH videa (najnoviji → najstariji).
        """
        if output_dir is None:
            output_dir = Path("data/video_screenshots")
        
        if not self.master_data:
            print("⚠️  Nema podataka za master kolaže!")
            return {}
        
        print(f"\n{'='*70}")
        print("🎨 Kreiranje MASTER kolaža...")
        print(f"{'='*70}")
        
        master_paths = {}
        
        for region_name, data_list in self.master_data.items():
            if not data_list:
                continue
            
            # Razdvoji slike i timestamp-ove
            images = [img for img, _ in data_list]
            timestamps = [ts for _, ts in data_list]
            
            # Kreiraj master kolaž (već je obrnutim redom jer su videi dodavani hronološki)
            collage = self.create_vertical_collage_with_timestamps(
                images,
                timestamps,
                f"MASTER - {region_name}",
                spacing=40,  # Malo veći razmak za master
                break_height=40  # Malo veći Break za master
            )
            
            output_filename = f"MASTER_{region_name}_collage.png"
            output_path = output_dir / output_filename
            collage.save(output_path)
            
            master_paths[region_name] = output_path
            print(f"✅ {output_filename} ({len(images)} screenshot-ova iz svih videa + Break)")
        
        return master_paths
    
    def batch_process_videos(
        self,
        video_folder: Path,
        pattern: str = "*.mp4",
        interval_minutes: int = 16,
        include_final_frame: bool = True
    ) -> List[Dict]:
        """Procesuje sve videe i pravi master kolaže."""
        video_folder = Path(video_folder)
        video_files = sorted(video_folder.glob(pattern))
        
        # Auto-detect ako nema .mp4
        if not video_files and pattern == "*.mp4":
            print(f"⚠️  Nema .mp4, tražim sve formate...")
            for p in ["*.avi", "*.mkv", "*.mov", "*.wmv", "*.flv", "*.webm"]:
                videos = list(video_folder.glob(p))
                if videos:
                    video_files.extend(videos)
            video_files = sorted(video_files)
        
        if not video_files:
            print(f"❌ Nema video fajlova!")
            return []
        
        print(f"\n{'='*70}")
        print(f"🎬 {len(video_files)} video fajlova")
        print(f"⏱️  Interval: {interval_minutes} min")
        print(f"🎯 Završni frame: {'DA (samo poslednji)' if include_final_frame else 'NE'}")
        print(f"{'='*70}")
        
        results = []
        
        for i, video_path in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}]", end=" ")
            
            # Završni frame SAMO za poslednji video
            is_last = (i == len(video_files))
            include_final = include_final_frame and is_last
            
            if include_final:
                print("🎯 POSLEDNJI - dodaje završni screenshot!")
            
            try:
                collage_paths = self.process_single_video(
                    video_path,
                    interval_minutes=interval_minutes,
                    include_final_frame=include_final
                )
                
                results.append({
                    'video': video_path.name,
                    'status': 'success',
                    'collages': collage_paths
                })
                
            except Exception as e:
                print(f"  ❌ Greška: {e}")
                results.append({
                    'video': video_path.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # MASTER KOLAŽI na kraju
        print(f"\n{'='*70}")
        master_paths = self.create_master_collages()
        print(f"{'='*70}")
        
        # Summary
        successful = sum(1 for r in results if r['status'] == 'success')
        print(f"\n✅ Uspešno: {successful}/{len(video_files)}")
        print(f"❌ Neuspešno: {len(video_files) - successful}/{len(video_files)}")
        print(f"🎨 Master kolaži: {len(master_paths)}")
        
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Video screenshot extractor v3.0 - REVERSED + MASTER kolaži"
    )
    
    parser.add_argument("video_folder", type=str, help="Folder sa video fajlovima")
    parser.add_argument("--interval", type=int, default=16, help="Interval u minutima")
    parser.add_argument("--pattern", type=str, default="*.mp4", help="Glob pattern")
    parser.add_argument("--regions-config", type=str, 
                       default="data/coordinates/video_regions.json",
                       help="TEMP JSON config")
    parser.add_argument("--single", action="store_true", help="Samo jedan video")
    parser.add_argument("--no-final-frame", action="store_true", 
                       help="NE dodavaj završni frame")
    
    args = parser.parse_args()
    
    extractor = VideoScreenshotExtractor(regions_config_path=args.regions_config)
    
    if not extractor.regions:
        print("❌ Nema regiona! Koristi video_region_editor.py")
        exit(1)
    
    include_final = not args.no_final_frame
    
    if args.single:
        video_path = Path(args.video_folder)
        if not video_path.is_file():
            print(f"❌ Fajl ne postoji: {video_path}")
            exit(1)
        
        extractor.process_single_video(
            video_path,
            interval_minutes=args.interval,
            include_final_frame=include_final
        )
        
        # Master kolaž i za single
        extractor.create_master_collages()
    else:
        extractor.batch_process_videos(
            Path(args.video_folder),
            pattern=args.pattern,
            interval_minutes=args.interval,
            include_final_frame=include_final
        )