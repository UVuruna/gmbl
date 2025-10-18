# utils/video_screenshot_extractor.py
# VERSION: 3.3
# HARDCODED ZA 10 FPS VIDEO LOGOVE
# 
# - Ekstrakcija po FREJMOVIMA za oštre slike
# - Intervali: 4, 16, 28, 40, 52 minuta (12 min razlika)
# - Zadnji screenshot: 30 frejmova (3 sek @ 10fps) pre kraja
# - AUTO-SPLIT: Deli master kolaže na delove ako height >= 6000px
# - NE SEČE chunk-ove na pola (Break + Screenshot + Spacing = 1 chunk)

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
    Ekstraktuje OŠTRE screenshot-ove iteriranjem po frejmovima.
    
    v3.3:
    - Ekstrakcija direktno iz frame-ova (bez video.set pozicioniranja)
    - Intervali: 4, 16, 28, 40, 52 minuta (12 min razlika)
    - Zadnji frame: 3 sekunde pre kraja (30 frejmova @ 10fps)
    - Screenshot-ovi obrnutim redom (najnoviji gore)
    - AUTO-SPLIT: Master kolaži se dele na delove ako prelaze 6000px
    """
    
    def __init__(self, regions_config_path: str = "data/coordinates/video_regions.json"):
        self.regions_config_path = Path(regions_config_path)
        self.regions = self._load_regions()
        self.master_data = {}
        
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
        """Parsira početno vreme iz imena video fajla."""
        filename = video_path.stem
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
    
    def extract_frame_by_number(self, cap: cv2.VideoCapture, frame_number: int) -> Optional[np.ndarray]:
        """
        Ekstraktuje tačan frame po broju.
        Direktno skače na frame bez interpolacije.
        """
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            return None
        
        return frame
    
    def extract_frames_at_intervals(
        self, 
        video_path: Path,
        include_final_frame: bool = False
    ) -> Tuple[List[np.ndarray], List[float], float]:
        """
        Ekstraktuje frame-ove na fiksnim intervalima: 4, 16, 28, 40, 52 min.
        Opciono dodaje zadnji frame 30 frejmova (3 sek @ 10fps) pre kraja.
        
        HARDCODED za 10 FPS video logove!
        
        Returns:
            (frames, time_points_minutes, fps)
        """
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Ne mogu otvoriti video: {video_path}")
        
        # VIDEO LOGOVI SU 10 FPS - HARDCODED
        FPS = 10.0
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / FPS
        duration_minutes = duration_seconds / 60
        
        print(f"⏱️  Trajanje: {duration_minutes:.2f} min ({total_frames} frejmova @ 10 fps)")
        
        # Fiksni intervali: 4, 16, 28, 40, 52 minuta (12 min razlika)
        time_points_minutes = [4.0, 16.0, 28.0, 40.0, 52.0]
        
        # Filtriraj samo one koji su u okviru trajanja videa
        valid_time_points = [t for t in time_points_minutes if t < duration_minutes]
        
        # Dodaj zadnji frame: 30 frejmova (3 sek) pre kraja
        if include_final_frame and total_frames > 30:
            final_frame_number = total_frames - 30
            final_time_minutes = final_frame_number / (FPS * 60)
            valid_time_points.append(final_time_minutes)
        
        print(f"📸 Screenshot-ovi na: {[f'{t:.1f}min' for t in valid_time_points]}")
        
        # Konvertuj minute u frame brojeve (10 FPS)
        frame_numbers = [round(t * 60 * FPS) for t in valid_time_points]
        
        # Ekstraktuj frame-ove
        frames = []
        actual_times = []
        
        for frame_num, time_min in zip(frame_numbers, valid_time_points):
            frame = self.extract_frame_by_number(cap, frame_num)
            
            if frame is not None:
                frames.append(frame)
                actual_times.append(time_min)
                
                is_final = (frame_num == frame_numbers[-1] and include_final_frame)
                marker = " [ZAVRŠNI - 30 frejmova pre kraja]" if is_final else ""
                print(f"  ✓ Frame {frame_num} ({time_min:.1f} min){marker}")
            else:
                print(f"  ✗ Frame {frame_num} ({time_min:.1f} min) - greška")
        
        cap.release()
        
        return frames, actual_times, FPS
    
    def extract_regions_from_frame(self, frame: np.ndarray) -> Dict[str, np.ndarray]:
        """Ekstraktuje sve regione iz frame-a."""
        regions_crops = {}
        
        for region in self.regions:
            x = region['x']
            y = region['y']
            w = region['width']
            h = region['height']
            name = region['name']
            
            # Kopiraj region - ovo sprečava mutne slike
            crop = frame[y:y+h, x:x+w].copy()
            regions_crops[name] = crop
        
        return regions_crops
    
    def _split_into_parts(
        self,
        region_images: List[np.ndarray],
        timestamps: List[datetime],
        max_height: int = 6000,
        break_height: int = 35,
        spacing: int = 30,
        header_height: int = 120
    ) -> List[Dict]:
        """
        Deli slike u delove (parts) tako da nijedan deo ne prelazi max_height.
        
        VAŽNO: NE sme da seče chunk na pola!
        Chunk = Break separator + Screenshot + Spacing
        
        Args:
            region_images: Lista screenshot-ova
            timestamps: Lista timestamp-ova
            max_height: Maksimalna visina jednog dela (px)
            break_height: Visina break separator-a
            spacing: Razmak između screenshot-ova
            header_height: Visina header-a
        
        Returns:
            Lista delova, svaki deo ima {'images': [...], 'timestamps': [...]}
        """
        if not region_images:
            return []
        
        # Konvertuj BGR -> RGB
        pil_images = [Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) 
                      for img in region_images]
        
        parts = []
        current_part_images = []
        current_part_timestamps = []
        current_height = header_height
        
        for img, ts in zip(pil_images, timestamps):
            # Visina jednog chunk-a
            chunk_height = break_height + img.height + spacing
            
            # Da li chunk staje u trenutni deo?
            if current_height + chunk_height > max_height and current_part_images:
                # Ne staje! Sačuvaj trenutni deo i počni novi
                parts.append({
                    'images': current_part_images,
                    'timestamps': current_part_timestamps,
                    'final_height': current_height
                })
                
                # Novi deo
                current_part_images = [img]
                current_part_timestamps = [ts]
                current_height = header_height + chunk_height
            else:
                # Staje! Dodaj u trenutni deo
                current_part_images.append(img)
                current_part_timestamps.append(ts)
                current_height += chunk_height
        
        # Dodaj poslednji deo
        if current_part_images:
            parts.append({
                'images': current_part_images,
                'timestamps': current_part_timestamps,
                'final_height': current_height
            })
        
        return parts
    
    def create_vertical_collage_with_timestamps(
        self,
        pil_images: List[Image.Image],
        timestamps: List[datetime],
        region_name: str,
        spacing: int = 30,
        bg_color: Tuple[int,int,int] = (40, 40, 40),
        break_height: int = 35
    ) -> Image.Image:
        """
        Kreira vertikalni kolaž OBRNUTIM redom (poslednji gore → prvi dole).
        
        Args:
            pil_images: Lista PIL slika (već konvertovanih iz BGR)
            timestamps: Lista timestamp-ova
            region_name: Ime regiona (može sadržati Part info)
        """
        if not pil_images:
            raise ValueError("Nema slika!")
        
        # OBRNI redosled
        pil_images = list(reversed(pil_images))
        timestamps = list(reversed(timestamps))
        
        # Dimensions
        max_img_width = max(img.width for img in pil_images)
        total_width = max_img_width + 40
        
        total_height = 100
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
            font_break = ImageFont.truetype("arialbd.ttf", 20)
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
            
            # Break tekst
            break_y = current_y + (break_height // 2) - 10
            
            if timestamp:
                break_text = f"Break - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                break_text = "Break"
            
            # Background za Break
            text_bbox = draw.textbbox((0, 0), break_text, font=font_break)
            text_width = text_bbox[2] - text_bbox[0]
            
            draw.rectangle(
                [x_offset - 5, current_y, x_offset + text_width + 10, current_y + break_height - 5],
                fill=(80, 80, 80),
                outline=(255, 255, 0),
                width=2
            )
            
            draw.text((x_offset + 5, break_y), break_text, fill=(255, 255, 0), font=font_break)
            
            current_y += break_height
            
            # Screenshot
            collage.paste(img, (x_offset, current_y))
            
            # Separator
            if i < len(pil_images) - 1:
                line_y = current_y + img.height + (spacing // 2)
                draw.line([(20, line_y), (total_width - 20, line_y)], 
                         fill=(80, 80, 80), width=1)
            
            current_y += img.height + spacing
        
        return collage
    
    def process_single_video(
        self,
        video_path: Path,
        output_dir: Path = None,
        include_final_frame: bool = False
    ) -> Dict[str, Path]:
        """Procesuje jedan video - hardcoded 10 FPS."""
        if output_dir is None:
            output_dir = Path("data/video_screenshots")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        start_time = self.parse_video_timestamp(video_path)
        
        print(f"\n🎥 {video_path.name}")
        if start_time:
            print(f"🕐 Početak: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ekstraktuj frame-ove (10 FPS hardcoded)
        frames, time_points, fps = self.extract_frames_at_intervals(
            video_path,
            include_final_frame=include_final_frame
        )
        
        if not frames:
            print("  ⚠️  Nema ekstraktovanih frame-ova!")
            return {}
        
        # Grupiši po regionima
        regions_over_time = {region['name']: [] for region in self.regions}
        timestamps_per_region = {region['name']: [] for region in self.regions}
        
        for frame, time_min in zip(frames, time_points):
            regions_crops = self.extract_regions_from_frame(frame)
            
            if start_time:
                screenshot_time = start_time + timedelta(minutes=time_min)
            else:
                screenshot_time = None
            
            for region_name, crop in regions_crops.items():
                regions_over_time[region_name].append(crop)
                timestamps_per_region[region_name].append(screenshot_time)
                
                # Čuvaj za master kolaž
                if region_name not in self.master_data:
                    self.master_data[region_name] = []
                self.master_data[region_name].append((crop, screenshot_time))
        
        # Kreiraj kolaže
        collage_paths = {}
        video_basename = video_path.stem
        
        for region_name, images in regions_over_time.items():
            if not images:
                continue
            
            timestamps = timestamps_per_region[region_name]
            
            # Konvertuj BGR -> RGB
            pil_images = [Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) 
                          for img in images]
            
            collage = self.create_vertical_collage_with_timestamps(
                pil_images,
                timestamps,
                region_name
            )
            
            output_filename = f"{video_basename}_{region_name}_collage.png"
            output_path = output_dir / output_filename
            collage.save(output_path, quality=100, optimize=False)
            
            collage_paths[region_name] = output_path
            print(f"  ✅ {output_filename} ({len(images)} screenshot-ova)")
        
        return collage_paths
    
    def create_master_collages(self, output_dir: Path = None, max_height: int = 6000):
        """
        Kreira MASTER kolaže za svaki region (svi videi).
        
        AUTO-SPLIT: Ako kolaž prelazi max_height, deli ga na delove.
        NE seče chunk-ove na pola!
        
        Args:
            output_dir: Folder za output
            max_height: Maksimalna visina jednog kolaža (px)
        """
        if output_dir is None:
            output_dir = Path("data/video_screenshots")
        
        if not self.master_data:
            print("⚠️  Nema podataka za master kolaže!")
            return []
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        master_paths = {}
        
        print(f"\n🎨 MASTER KOLAŽI (max height: {max_height}px):")
        
        for region_name, data_list in self.master_data.items():
            images = [img for img, _ in data_list]
            timestamps = [ts for _, ts in data_list]
            
            if not images:
                continue
            
            # Podeli na delove ako je potrebno
            parts = self._split_into_parts(
                images,
                timestamps,
                max_height=max_height
            )
            
            if len(parts) == 1:
                # JEDAN kolaž
                collage = self.create_vertical_collage_with_timestamps(
                    parts[0]['images'],
                    parts[0]['timestamps'],
                    f"{region_name} - MASTER"
                )
                
                output_filename = f"MASTER_{region_name}.png"
                output_path = output_dir / output_filename
                collage.save(output_path, quality=100, optimize=False)
                
                master_paths[region_name] = [output_path]
                print(f"  ✅ {output_filename} ({len(images)} screenshot-ova, {parts[0]['final_height']}px)")
            
            else:
                # VIŠE delova
                part_paths = []
                
                for part_idx, part in enumerate(parts, 1):
                    collage = self.create_vertical_collage_with_timestamps(
                        part['images'],
                        part['timestamps'],
                        f"{region_name} - MASTER (Part {part_idx}/{len(parts)})"
                    )
                    
                    output_filename = f"MASTER_{region_name}_{part_idx}.png"
                    output_path = output_dir / output_filename
                    collage.save(output_path, quality=100, optimize=False)
                    
                    part_paths.append(output_path)
                    print(f"  ✅ {output_filename} ({len(part['images'])} screenshot-ova, {part['final_height']}px)")
                
                master_paths[region_name] = part_paths
                print(f"  📊 {region_name}: {len(parts)} delova, {len(images)} total screenshot-ova")
        
        return master_paths
    
    def batch_process_videos(
        self,
        video_folder: Path,
        pattern: str = "*.mp4",
        include_final_frame: bool = False
    ):
        """Batch procesiranje - hardcoded 10 FPS."""
        video_files = sorted(video_folder.glob(pattern))
        
        if not video_files:
            print(f"❌ Nema video fajlova u: {video_folder}")
            return []
        
        print(f"\n{'='*70}")
        print(f"🎬 {len(video_files)} video fajlova (10 FPS)")
        print(f"📸 Intervali: 4, 16, 28, 40, 52 min (12 min razlika)")
        print(f"🎯 Završni frame: {'DA (30 frejmova pre kraja)' if include_final_frame else 'NE'}")
        print(f"✂️  Auto-split: Master kolaži > 6000px dele se na delove")
        print(f"{'='*70}")
        
        results = []
        
        for i, video_path in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}]", end=" ")
            
            is_last = (i == len(video_files))
            include_final = include_final_frame and is_last
            
            if include_final:
                print("🎯 POSLEDNJI - dodaje završni screenshot (30 frejmova pre kraja)!")
            
            try:
                collage_paths = self.process_single_video(
                    video_path,
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
        
        # MASTER KOLAŽI sa auto-split
        print(f"\n{'='*70}")
        master_paths = self.create_master_collages(max_height=6000)
        print(f"{'='*70}")
        
        # Summary
        successful = sum(1 for r in results if r['status'] == 'success')
        total_master_files = sum(len(paths) if isinstance(paths, list) else 1 
                                for paths in master_paths.values())
        
        print(f"\n✅ Uspešno: {successful}/{len(video_files)}")
        print(f"❌ Neuspešno: {len(video_files) - successful}/{len(video_files)}")
        print(f"🎨 Master kolaži: {len(master_paths)} regiona, {total_master_files} fajlova")
        
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Video screenshot extractor v3.3 - AUTO-SPLIT za velike kolaže"
    )
    
    parser.add_argument("video_folder", type=str, help="Folder sa video fajlovima")
    parser.add_argument("--pattern", type=str, default="*.mp4", help="Glob pattern")
    parser.add_argument("--regions-config", type=str, 
                       default="data/coordinates/video_regions.json",
                       help="TEMP JSON config")
    parser.add_argument("--single", action="store_true", help="Samo jedan video")
    parser.add_argument("--final-frame", action="store_true", 
                       help="Dodaj završni frame (30 frejmova pre kraja @ 10fps)")
    parser.add_argument("--max-height", type=int, default=6000,
                       help="Max visina master kolaža pre split-a (default: 6000px)")
    
    args = parser.parse_args()
    
    extractor = VideoScreenshotExtractor(regions_config_path=args.regions_config)
    
    if not extractor.regions:
        print("❌ Nema regiona! Koristi video_region_editor.py")
        exit(1)
    
    if args.single:
        video_path = Path(args.video_folder)
        if not video_path.is_file():
            print(f"❌ Fajl ne postoji: {video_path}")
            exit(1)
        
        extractor.process_single_video(
            video_path,
            include_final_frame=args.final_frame
        )
        
        extractor.create_master_collages(max_height=args.max_height)
    else:
        extractor.batch_process_videos(
            Path(args.video_folder),
            pattern=args.pattern,
            include_final_frame=args.final_frame
        )