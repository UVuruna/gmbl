# utils/batch_video_processor.py
# VERSION: 2.3
# FIXED: Kompatibilnost sa video_screenshot_extractor.py v3.3
# - Uklonjeni interval_minutes parametri (sada hardcoded u ekstraktoru)
# - Intervali: 4, 16, 28, 40, 52 min (12 min razlika)
# - Dodato: --rename opcija za markiranje obrađenih videa
# - Dodato: --max-height za kontrolu auto-split master kolaža

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
    - AUTO-RENAME obrađenih fajlova (opciono)
    - AUTO-SPLIT master kolaža > max_height (opciono)
    
    v2.3: HARDCODED INTERVALI (4, 16, 28, 40, 52 min) u ekstraktoru
          + --rename opcija za markiranje obrađenih videa
          + --max-height za kontrolu auto-split master kolaža
    """
    
    def __init__(self, video_folder: Path, 
                 regions_config: str = "data/coordinates/video_regions.json",
                 include_final_frame: bool = True,
                 rename_suffix: Optional[str] = None,
                 max_collage_height: int = 6000):
        self.video_folder = Path(video_folder)
        self.regions_config = regions_config
        self.include_final_frame = include_final_frame
        self.rename_suffix = rename_suffix
        self.max_collage_height = max_collage_height
        self.extractor = VideoScreenshotExtractor(regions_config_path=regions_config)
        
        # Tracking
        self.start_time = None
        self.results = []
        self.renamed_files = []
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
    
    def _rename_video(self, video_path: Path, suffix: str) -> Optional[Path]:
        """
        Preimenovava video fajl dodavanjem suffixa pre ekstenzije.
        
        Args:
            video_path: Originalni video fajl
            suffix: Suffix za dodavanje (npr. "DONE")
        
        Returns:
            Path do preimenovanog fajla ili None ako nije uspelo
        
        Primer:
            2025-10-15 05-14-53.mp4 -> 2025-10-15 05-14-53-DONE.mp4
        """
        if not suffix:
            return None
        
        # Proveri da li već ima suffix
        stem = video_path.stem
        if stem.endswith(f"-{suffix}"):
            self._log(f"  ⚠️  Već preimenovan: {video_path.name}", also_print=False)
            return video_path
        
        # Kreiraj novo ime
        new_name = f"{stem}-{suffix}{video_path.suffix}"
        new_path = video_path.parent / new_name
        
        # Proveri da li novi fajl već postoji
        if new_path.exists():
            self._log(f"  ⚠️  Fajl već postoji: {new_name}", also_print=False)
            return None
        
        try:
            video_path.rename(new_path)
            self._log(f"  ✅ Preimenovan: {video_path.name} -> {new_name}")
            return new_path
        except Exception as e:
            self._log(f"  ❌ Greška pri preimenovanju: {e}")
            return None
    
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
        # HARDCODED: 5 screenshot-ova po videu (4, 16, 28, 40, 52 min) + 1 završni za poslednji
        screenshots_per_video = 5
        if self.include_final_frame:
            screenshots_per_video += (1 / num_videos)  # Samo poslednji dobija završni
        
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
        print("🎬 BATCH VIDEO PROCESSING v2.2")
        print("="*70)
        print(f"📂 Folder:        {self.video_folder}")
        print(f"🎥 Video fajlova: {len(video_files)}")
        
        if start_index or end_index:
            print(f"📊 Opseg:         [{start_index or 1} - {end_index or '?'}] (po abecedi)")
        
        print(f"⏱️  Intervali:     4, 16, 28, 40, 52 min (12 min razlika) @ 10 FPS")
        print(f"🎯 Završni frame: {'DA (SAMO za poslednji u batch-u)' if self.include_final_frame else 'NE'}")
        print(f"📋 Break separatori: DA (iznad svakog screenshot-a)")
        print(f"✂️  Master split:  {self.max_collage_height}px (auto-deli ako prelazi)")
        print(f"🔍 Pattern:       {pattern}")
        print(f"⏳ Procenjeno:    ~{self.estimate_time(len(video_files))}")
        print(f"📊 Output:        data/video_screenshots/")
        if self.rename_suffix:
            print(f"🏷️  Preimenovanje: Dodaj '-{self.rename_suffix}' nakon obrade")
        print("="*70)
        
        # Prikaži prvi i poslednji fajl
        print(f"\n📄 Prvi fajl:  {video_files[0].name}")
        print(f"📄 Zadnji fajl: {video_files[-1].name}\n")
        
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
        self._log(f"⏱️  Intervali: 4, 16, 28, 40, 52 min (HARDCODED @ 10 FPS)")
        self._log(f"{'='*70}")
        
        # Procesuj svaki video
        for i, video_path in enumerate(video_files, 1):
            video_start = time.time()
            
            # Globalni indeks (ako je opseg definisan)
            global_idx = start_index + i - 1 if start_index else i
            
            # ZAVRŠNI SCREENSHOT SAMO ZA POSLEDNJI FAJL U BATCH-U
            is_last_video = (i == len(video_files))
            include_final_for_this_video = self.include_final_frame and is_last_video
            
            self._log(f"\n[{i}/{len(video_files)}] (#{global_idx}) 🎥 {video_path.name}")
            print(f"\n{'─'*70}")
            print(f"[{i}/{len(video_files)}] (#{global_idx}) Processing: {video_path.name}")
            if include_final_for_this_video:
                print(f"🎯 POSLEDNJI U BATCH-U - dodaje se završni screenshot (30 frejmova pre kraja)!")
            print(f"{'─'*70}")
            
            try:
                # FIXED: Više ne prosleđujemo interval_minutes!
                collage_paths = self.extractor.process_single_video(
                    video_path,
                    include_final_frame=include_final_for_this_video
                )
                
                video_time = time.time() - video_start
                
                result = {
                    'video': video_path.name,
                    'global_index': global_idx,
                    'status': 'success',
                    'collages': len(collage_paths),
                    'time_seconds': video_time,
                    'renamed': False
                }
                
                self.results.append(result)
                self._log(f"  ✅ Uspešno za {video_time:.1f}s - {len(collage_paths)} kolaža (OBRNUTO + Break separatori)")
                
                # Preimenovanje nakon uspešne obrade
                if self.rename_suffix:
                    renamed_path = self._rename_video(video_path, self.rename_suffix)
                    if renamed_path:
                        result['renamed'] = True
                        result['new_name'] = renamed_path.name
                        self.renamed_files.append({
                            'original': video_path.name,
                            'renamed': renamed_path.name
                        })
                
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
        self._log(f"🎨 Kreiranje MASTER kolaža (max {self.max_collage_height}px)...")
        print(f"\n{'='*70}")
        print(f"🎨 Kreiranje MASTER kolaža za sve regione (max {self.max_collage_height}px)...")
        print(f"{'='*70}")
        
        master_paths = self.extractor.create_master_collages(max_height=self.max_collage_height)
        
        if master_paths:
            total_files = sum(len(paths) if isinstance(paths, list) else 1 
                            for paths in master_paths.values())
            self._log(f"✅ Kreirano {len(master_paths)} regiona, {total_files} fajlova")
            print(f"\n✅ Kreirano {len(master_paths)} regiona:")
            for region_name, paths in master_paths.items():
                if isinstance(paths, list):
                    print(f"   • {region_name}: {len(paths)} delova")
                    for path in paths:
                        print(f"      - {path.name}")
                else:
                    print(f"   • {paths.name}")
        
        # Final summary
        self._generate_summary(len(master_paths) if master_paths else 0)
        
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
        
        renamed_count = len(self.renamed_files)
        
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        print(f"✅ Uspešno:        {successful}/{len(self.results)} video fajlova")
        print(f"❌ Neuspešno:      {failed}/{len(self.results)} video fajlova")
        print(f"🖼️  Video kolaža:    {total_collages} (OBRNUTI + Break separatori)")
        print(f"🎨 MASTER kolaža:  {master_collages_count} (svi screenshot-ovi + Break)")
        print(f"⏱️  Ukupno vreme:    {total_time/60:.1f} minuta")
        print(f"⚡ Avg po video:    {total_time/len(self.results):.1f} sekundi")
        print(f"📸 Intervali:      4, 16, 28, 40, 52 min (HARDCODED @ 10 FPS)")
        if self.rename_suffix:
            print(f"🏷️  Preimenovano:    {renamed_count}/{successful} fajlova (suffix: '-{self.rename_suffix}')")
        print("="*70)
        
        if failed > 0:
            print("\n❌ NEUSPELI FAJLOVI:")
            for r in self.results:
                if r['status'] == 'failed':
                    idx = r.get('global_index', '?')
                    print(f"  [#{idx}] {r['video']}: {r.get('error', 'Unknown')}")
        
        if self.rename_suffix and self.renamed_files:
            print(f"\n🏷️  PREIMENOVANI FAJLOVI:")
            for item in self.renamed_files[:10]:  # Prikaži prvih 10
                print(f"  ✓ {item['original']} -> {item['renamed']}")
            if len(self.renamed_files) > 10:
                print(f"  ... i još {len(self.renamed_files)-10} fajlova")
        
        print(f"\n📂 Output folder: data/video_screenshots/")
        print(f"📝 Log fajl:      {self.log_path}")
        print()
        
        # Snimi u log
        self._log(f"\n{'='*70}")
        self._log(f"📊 SUMMARY: {successful} success, {failed} failed, "
                 f"{total_time/60:.1f}min, {master_collages_count} MASTER kolaža")
        if self.rename_suffix:
            self._log(f"🏷️  Preimenovano: {renamed_count} fajlova sa '-{self.rename_suffix}'")
        self._log(f"{'='*70}\n")


# ============================================================================
# CLI USAGE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch processing v2.2 - HARDCODED intervali (4, 16, 28, 40, 52 min @ 10 FPS)",
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
  
  # Procesuj i preimenuj obrađene fajlove sa sufixom "-DONE"
  python batch_video_processor.py V:/log/ --rename DONE
  # 2025-10-15 05-14-53.mp4 -> 2025-10-15 05-14-53-DONE.mp4

NAPOMENA:
  Intervali su HARDCODED: 4, 16, 28, 40, 52 min (12 min razlika) @ 10 FPS
  --interval opcija je uklonjena jer se više ne koristi!
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
        help="NE dodavaj završni screenshot (30 frejmova pre kraja) za poslednji fajl u batch-u"
    )
    
    parser.add_argument(
        "--rename",
        type=str,
        default=None,
        metavar="SUFFIX",
        help="Preimenuj uspešno obrađene fajlove dodavanjem suffixa (npr. DONE, OK, PROCESSED)"
    )
    
    parser.add_argument(
        "--max-height",
        type=int,
        default=6000,
        metavar="PIXELS",
        help="Maksimalna visina master kolaža pre auto-split (default: 6000px)"
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
        regions_config=args.regions_config,
        include_final_frame=not args.no_final_frame,
        rename_suffix=args.rename,
        max_collage_height=args.max_height
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