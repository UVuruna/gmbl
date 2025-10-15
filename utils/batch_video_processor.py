# utils/batch_video_processor.py
# VERSION: 2.0
# Automatski batch processing sa opsegom fajlova (od-do) + završni frame

import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.video_screenshot_extractor import VideoScreenshotExtractor


class BatchVideoProcessor:
    """
    Wrapper za batch processing sa naprednim features:
    - Progress tracking
    - Error handling
    - Summary report
    - Resume capability
    - OPSEG fajlova (od-do po abecednom redu)
    """
    
    def __init__(self, video_folder: Path, 
                 interval_minutes: int = 16,
                 regions_config: str = "data/coordinates/video_regions.json",
                 include_final_frame: bool = True):
        self.video_folder = Path(video_folder)
        self.interval_minutes = interval_minutes
        self.regions_config = regions_config
        self.include_final_frame = include_final_frame
        self.extractor = VideoScreenshotExtractor(regions_config_path=regions_config)
        
        # Tracking
        self.start_time = None
        self.results = []
        self.log_path = Path("data/video_screenshots/processing_log.txt")
        
    def _log(self, message: str, also_print: bool = True):
        """Log poruke u fajl i opciono na ekran."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Snima u log fajl
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        if also_print:
            print(message)
    
    def get_video_files(self, pattern: str = "*.mp4", 
                        start_index: Optional[int] = None,
                        end_index: Optional[int] = None) -> List[Path]:
        """
        Pronalazi video fajlove sa opcionalnim opsegom.
        Ako default pattern ne nađe ništa, automatski traži sve video formate.
        """
        all_videos = sorted(self.video_folder.glob(pattern))
        
        # Ako je default i nije našlo ništa, traži sve video formate
        if not all_videos and pattern == "*.mp4":
            print(f"⚠️  Nema .mp4 fajlova, tražim sve video formate...")
            patterns = ["*.avi", "*.mkv", "*.mov", "*.wmv", "*.flv", "*.webm", "*.mp4"]
            for p in patterns:
                videos = list(self.video_folder.glob(p))
                if videos:
                    all_videos.extend(videos)
                    print(f"   ✓ Našao {len(videos)} {p} fajlova")
            all_videos = sorted(all_videos)
        
        # Ako nema opsega, vrati sve
        if start_index is None and end_index is None:
            return all_videos
        
        # Konvertuj u 0-based index
        start = (start_index - 1) if start_index else 0
        end = end_index if end_index else len(all_videos)
        
        # Validacija
        if start < 0 or start >= len(all_videos):
            print(f"⚠️  Start index {start_index} van opsega! Ima {len(all_videos)} fajlova.")
            start = 0
        
        if end > len(all_videos):
            print(f"⚠️  End index {end_index} van opsega! Ima {len(all_videos)} fajlova.")
            end = len(all_videos)
        
        return all_videos[start:end]
    
    def show_video_list(self, pattern: str = "*.mp4"):
        """Prikazuje sve video fajlove sa indeksima."""
        
        # Ako je default pattern i ništa ne nađe, probaj sve video formate
        if pattern == "*.mp4":
            all_videos = sorted(self.video_folder.glob(pattern))
            
            if not all_videos:
                print(f"⚠️  Nema .mp4 fajlova, tražim sve video formate...")
                patterns = ["*.mp4", "*.avi", "*.mkv", "*.mov", "*.wmv", "*.flv", "*.webm"]
                for p in patterns:
                    videos = list(self.video_folder.glob(p))
                    if videos:
                        all_videos.extend(videos)
                all_videos = sorted(all_videos)
        else:
            all_videos = sorted(self.video_folder.glob(pattern))
        
        print(f"\n{'='*70}")
        print(f"📂 DOSTUPNI VIDEO FAJLOVI u {self.video_folder}")
        print(f"{'='*70}")
        
        if not all_videos:
            # Debug info
            print(f"❌ Nema fajlova sa pattern: {pattern}")
            print(f"\n🔍 Debug info:")
            print(f"   Folder: {self.video_folder}")
            print(f"   Folder exists: {self.video_folder.exists()}")
            print(f"   Is directory: {self.video_folder.is_dir()}")
            
            # Prikaži SVE fajlove u folderu
            if self.video_folder.exists() and self.video_folder.is_dir():
                all_files = list(self.video_folder.iterdir())
                print(f"   Ukupno fajlova/foldera: {len(all_files)}")
                
                if all_files:
                    print(f"\n📄 Svi fajlovi u folderu:")
                    for f in all_files[:20]:  # Prikaži prvih 20
                        ftype = "DIR" if f.is_dir() else f.suffix
                        print(f"      {ftype:8s} {f.name}")
                    if len(all_files) > 20:
                        print(f"      ... i još {len(all_files)-20} fajlova")
            return
        
        for i, video in enumerate(all_videos, 1):
            size_mb = video.stat().st_size / (1024*1024) if video.exists() else 0
            print(f"  [{i:3d}] {video.name:50s} ({size_mb:.1f} MB)")
        
        print(f"{'='*70}")
        print(f"Ukupno: {len(all_videos)} video fajlova")
        print(f"{'='*70}\n")
    
    def estimate_time(self, num_videos: int, avg_duration_min: float = 60) -> str:
        """Procenjuje vreme procesovanja."""
        # Prosečno 2-3 sekunde po screenshot-u
        screenshots_per_video = avg_duration_min // self.interval_minutes + 1  # +1 za završni
        total_screenshots = num_videos * screenshots_per_video
        estimated_seconds = total_screenshots * 2.5
        
        hours = int(estimated_seconds // 3600)
        minutes = int((estimated_seconds % 3600) // 60)
        
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    
    def process_with_progress(self, pattern: str = "*.mp4",
                             start_index: Optional[int] = None,
                             end_index: Optional[int] = None) -> Dict:
        """
        Procesuje video fajlove sa progress tracking-om.
        
        Args:
            pattern: Glob pattern
            start_index: Prvi fajl (1-based, po abecedi)
            end_index: Poslednji fajl (1-based, po abecedi, inclusive)
        """
        video_files = self.get_video_files(pattern, start_index, end_index)
        
        if not video_files:
            self._log(f"❌ Nema video fajlova u opsegu!")
            return {'status': 'failed', 'reason': 'no_videos'}
        
        # Header
        print("\n" + "="*70)
        print("🎬 BATCH VIDEO PROCESSING v2.0")
        print("="*70)
        print(f"📂 Folder:        {self.video_folder}")
        print(f"📹 Video fajlova: {len(video_files)}")
        
        if start_index or end_index:
            print(f"📊 Opseg:         [{start_index or 1} - {end_index or '?'}] (po abecedi)")
        
        print(f"⏱️  Interval:      {self.interval_minutes} minuta")
        print(f"🎯 Završni frame: {'DA (SAMO za poslednji u batch-u)' if self.include_final_frame else 'NE'}")
        print(f"📝 Break separatori: DA (iznad svakog screenshot-a)")
        print(f"🔍 Pattern:       {pattern}")
        print(f"⏳ Procenjeno:    ~{self.estimate_time(len(video_files))}")
        print(f"📊 Output:        data/video_screenshots/")
        print("="*70)
        
        # Prikaži prvi i poslednji fajl
        print(f"\n📝 Prvi fajl:  {video_files[0].name}")
        print(f"📝 Zadnji fajl: {video_files[-1].name}\n")
        
        # Potvrda
        response = input("🚀 Nastavi sa obradom? [Y/n]: ").strip().lower()
        if response and response != 'y':
            print("❌ Otkazano")
            return {'status': 'cancelled'}
        
        self.start_time = time.time()
        self._log(f"\n{'='*70}")
        self._log(f"🚀 START: Batch processing {len(video_files)} video fajlova")
        if start_index or end_index:
            self._log(f"📊 Opseg: [{start_index or 1} - {end_index or len(video_files)}]")
        self._log(f"{'='*70}")
        
        # Procesuj svaki video
        for i, video_path in enumerate(video_files, 1):
            video_start = time.time()
            
            # Globalni indeks (ako je opseg definisan)
            global_idx = start_index + i - 1 if start_index else i
            
            # ZAVRŠNI SCREENSHOT SAMO ZA POSLEDNJI FAJL U BATCH-U
            is_last_video = (i == len(video_files))
            include_final_for_this_video = self.include_final_frame and is_last_video
            
            self._log(f"\n[{i}/{len(video_files)}] (#{global_idx}) 📹 {video_path.name}")
            print(f"\n{'─'*70}")
            print(f"[{i}/{len(video_files)}] (#{global_idx}) Processing: {video_path.name}")
            if include_final_for_this_video:
                print(f"🎯 POSLEDNJI U BATCH-U - dodaje se završni screenshot!")
            print(f"{'─'*70}")
            
            try:
                collage_paths = self.extractor.process_single_video(
                    video_path,
                    interval_minutes=self.interval_minutes,
                    include_final_frame=include_final_for_this_video
                )
                
                video_time = time.time() - video_start
                
                result = {
                    'video': video_path.name,
                    'global_index': global_idx,
                    'status': 'success',
                    'collages': len(collage_paths),
                    'time_seconds': video_time
                }
                
                self.results.append(result)
                self._log(f"  ✅ Uspešno za {video_time:.1f}s - {len(collage_paths)} kolaža (OBRNUTO + Break separatori)")
                
            except Exception as e:
                video_time = time.time() - video_start
                
                result = {
                    'video': video_path.name,
                    'global_index': global_idx,
                    'status': 'failed',
                    'error': str(e),
                    'time_seconds': video_time
                }
                
                self.results.append(result)
                self._log(f"  ❌ Greška: {e}")
            
            # Progress update
            elapsed = time.time() - self.start_time
            avg_time = elapsed / i
            remaining = (len(video_files) - i) * avg_time
            
            print(f"\n⏱️  Progres: {i}/{len(video_files)} | "
                  f"Prošlo: {elapsed/60:.1f}min | "
                  f"Preostalo: ~{remaining/60:.1f}min")
        
        # MASTER KOLAŽI nakon svih videa
        self._log(f"\n{'='*70}")
        self._log("🎨 Kreiranje MASTER kolaža...")
        print(f"\n{'='*70}")
        print("🎨 Kreiranje MASTER kolaža za sve regione...")
        print(f"{'='*70}")
        
        master_paths = self.extractor.create_master_collages()
        
        if master_paths:
            self._log(f"✅ Kreirano {len(master_paths)} MASTER kolaža")
            print(f"\n✅ Kreirano {len(master_paths)} MASTER kolaža:")
            for region_name, path in master_paths.items():
                print(f"   • {path.name}")
        
        # Final summary
        self._generate_summary(len(master_paths))
        
        return {
            'status': 'completed',
            'results': self.results,
            'total_time': time.time() - self.start_time
        }
    
    def _generate_summary(self, master_collages_count: int = 0):
        """Generiše finalni izveštaj."""
        total_time = time.time() - self.start_time
        successful = sum(1 for r in self.results if r['status'] == 'success')
        failed = len(self.results) - successful
        
        total_collages = sum(r.get('collages', 0) for r in self.results 
                            if r['status'] == 'success')
        
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        print(f"✅ Uspešno:        {successful}/{len(self.results)} video fajlova")
        print(f"❌ Neuspešno:      {failed}/{len(self.results)} video fajlova")
        print(f"🖼️  Video kolaža:    {total_collages} (OBRNUTI + Break separatori)")
        print(f"🎨 MASTER kolaža:  {master_collages_count} (svi screenshot-ovi + Break)")
        print(f"⏱️  Ukupno vreme:    {total_time/60:.1f} minuta")
        print(f"⚡ Avg po video:    {total_time/len(self.results):.1f} sekundi")
        print("="*70)
        
        if failed > 0:
            print("\n❌ NEUSPELI FAJLOVI:")
            for r in self.results:
                if r['status'] == 'failed':
                    idx = r.get('global_index', '?')
                    print(f"  [#{idx}] {r['video']}: {r.get('error', 'Unknown')}")
        
        print(f"\n📂 Output folder: data/video_screenshots/")
        print(f"📝 Log fajl:      {self.log_path}")
        print()
        
        # Snimi u log
        self._log(f"\n{'='*70}")
        self._log(f"📊 SUMMARY: {successful} success, {failed} failed, "
                 f"{total_time/60:.1f}min, {master_collages_count} MASTER kolaža")
        self._log(f"{'='*70}\n")


# ============================================================================
# CLI USAGE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch processing sa OPSEGOM fajlova (od-do) + završni frame",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PRIMERI:
  # Prikaži sve video fajlove (auto-detect formata)
  python batch_video_processor.py V:/log/ --list
  
  # Procesuj samo .avi fajlove
  python batch_video_processor.py V:/log/ --pattern "*.avi"
  
  # Procesuj fajlove od 1. do 20. (samo #20 dobija završni screenshot)
  python batch_video_processor.py V:/log/ --from 1 --to 20
  
  # Procesuj fajlove od 50. do kraja (poslednji dobija završni screenshot)
  python batch_video_processor.py V:/log/ --from 50
        """
    )
    
    parser.add_argument(
        "video_folder",
        type=str,
        help="Folder sa video fajlovima"
    )
    
    parser.add_argument(
        "--from",
        dest="from_index",
        type=int,
        default=None,
        help="Prvi fajl (1-based index, po abecedi)"
    )
    
    parser.add_argument(
        "--to",
        dest="to_index",
        type=int,
        default=None,
        help="Poslednji fajl (1-based index, inclusive)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=16,
        help="Interval između screenshot-ova u minutima (default: 16)"
    )
    
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.mp4",
        help="Glob pattern za video fajlove (default: *.mp4 ili auto-detect)"
    )
    
    parser.add_argument(
        "--regions-config",
        type=str,
        default="data/coordinates/video_regions.json",
        help="Putanja do TEMP JSON config fajla sa regionima"
    )
    
    parser.add_argument(
        "--no-final-frame",
        action="store_true",
        help="NE dodavaj završni screenshot (1sec pre kraja) za poslednji fajl u batch-u"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="Prikaži sve video fajlove sa indeksima i izađi"
    )
    
    args = parser.parse_args()
    
    # Pokreni batch processor
    processor = BatchVideoProcessor(
        video_folder=args.video_folder,
        interval_minutes=args.interval,
        regions_config=args.regions_config,
        include_final_frame=not args.no_final_frame
    )
    
    # Samo prikaz liste?
    if args.list:
        processor.show_video_list(pattern=args.pattern)
        exit(0)
    
    # Batch processing
    result = processor.process_with_progress(
        pattern=args.pattern,
        start_index=args.from_index,
        end_index=args.to_index
    )
    
    if result['status'] == 'completed':
        print("\n✅ Batch processing završen!")
    else:
        print(f"\n❌ Batch processing {result['status']}")