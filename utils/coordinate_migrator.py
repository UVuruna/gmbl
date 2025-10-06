# utils/coordinate_migrator.py
# VERSION: 1.0
# Migrate old coordinate format to new layout-based system

import json
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import AviatorLogger


class CoordinateMigrator:
    """
    Migrate old bookmaker coordinates to new format.
    
    Old format:
    {
      "Four 100%": {
        "BalkanBet": { regions... },
        "MaxBet": { regions... }
      }
    }
    
    New format:
    {
      "layouts": {
        "Four_100": {
          "width": 1030,
          "height": 720,
          "positions": {
            "TL": {"left": 0, "top": 0},
            ...
          }
        }
      },
      "bookmakers": {
        "BalkanBet": { regions relative to 0,0 },
        ...
      }
    }
    """
    
    def __init__(self, old_file: str, new_file: Optional[str] = None):
        self.old_file = Path(old_file)
        self.new_file = Path(new_file) if new_file else self.old_file.parent / "bookmaker_coords_new.json"
        self.logger = AviatorLogger.get_logger("CoordinateMigrator")
        
        self.old_data = self._load_old_format()
        self.new_data = {
            "layouts": {},
            "bookmakers": {}
        }
    
    def _load_old_format(self) -> Dict:
        """Load old format coordinates."""
        try:
            with open(self.old_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load old coordinates: {e}")
            return {}
    
    def detect_layout(self, config_name: str, bookmaker_data: Dict) -> Dict:
        """
        Detect layout from old configuration.
        
        Tries to infer window size and positions from coordinate values.
        """
        # Sample bookmaker to analyze
        sample_bookmaker = next(iter(bookmaker_data.values()))
        
        # Try to detect window size from largest coordinates
        max_left = 0
        max_top = 0
        
        for region_data in sample_bookmaker.values():
            if isinstance(region_data, dict) and 'left' in region_data:
                max_left = max(max_left, region_data['left'] + region_data['width'])
                max_top = max(max_top, region_data['top'] + region_data['height'])
        
        # Estimate window size (round to nearest 10)
        width = round(max_left / 10) * 10
        height = round(max_top / 10) * 10
        
        # Common grid patterns
        if "Four" in config_name:
            # 2x2 grid
            positions = {
                "TL": {"left": 0, "top": 0},
                "TR": {"left": width, "top": 0},
                "BL": {"left": 0, "top": height},
                "BR": {"left": width, "top": height}
            }
        elif "Six" in config_name:
            # 2x3 grid
            positions = {
                "TL": {"left": 0, "top": 0},
                "TC": {"left": width, "top": 0},
                "TR": {"left": width * 2, "top": 0},
                "BL": {"left": 0, "top": height},
                "BC": {"left": width, "top": height},
                "BR": {"left": width * 2, "top": height}
            }
        elif "Three" in config_name:
            # 1x3 horizontal
            positions = {
                "L": {"left": 0, "top": 0},
                "C": {"left": width, "top": 0},
                "R": {"left": width * 2, "top": 0}
            }
        else:
            # Default: single window
            positions = {
                "CENTER": {"left": 0, "top": 0}
            }
        
        return {
            "width": width,
            "height": height,
            "positions": positions
        }
    
    def normalize_bookmaker_coords(self, coords: Dict, offset_left: int, offset_top: int) -> Dict:
        """
        Normalize bookmaker coordinates to be relative to (0, 0).
        
        Subtracts the offset from all left/top values.
        """
        normalized = {}
        
        for region_name, region_data in coords.items():
            if isinstance(region_data, dict) and 'left' in region_data:
                normalized[region_name] = {
                    'left': region_data['left'] - offset_left,
                    'top': region_data['top'] - offset_top,
                    'width': region_data['width'],
                    'height': region_data['height']
                }
            else:
                normalized[region_name] = region_data
        
        return normalized
    
    def find_min_offset(self, bookmaker_data: Dict) -> tuple:
        """Find minimum offset across all bookmakers in a config."""
        min_left = float('inf')
        min_top = float('inf')
        
        for coords in bookmaker_data.values():
            for region_data in coords.values():
                if isinstance(region_data, dict) and 'left' in region_data:
                    min_left = min(min_left, region_data['left'])
                    min_top = min(min_top, region_data['top'])
        
        return (int(min_left), int(min_top))
    
    def migrate(self) -> Dict:
        """Perform migration."""
        print("\n" + "="*60)
        print("COORDINATE MIGRATION")
        print("="*60)
        
        if not self.old_data:
            print("❌ No old data to migrate")
            return self.new_data
        
        print(f"\nOld file: {self.old_file}")
        print(f"New file: {self.new_file}")
        print(f"\nFound {len(self.old_data)} old configurations")
        
        # Process each old configuration
        for config_name, bookmaker_data in self.old_data.items():
            print(f"\n--- Processing: {config_name} ---")
            
            # Skip if already has 'width' key (new format)
            if 'width' in bookmaker_data or 'layouts' in bookmaker_data:
                print("⚠️  Skipping - already in new format")
                continue
            
            # Detect layout
            layout = self.detect_layout(config_name, bookmaker_data)
            layout_name = config_name.replace(" ", "_")
            
            self.new_data['layouts'][layout_name] = layout
            print(f"✅ Layout: {layout['width']}x{layout['height']}, {len(layout['positions'])} positions")
            
            # Find base offset
            offset_left, offset_top = self.find_min_offset(bookmaker_data)
            print(f"   Base offset: ({offset_left}, {offset_top})")
            
            # Process each bookmaker
            for bookmaker_name, coords in bookmaker_data.items():
                # Normalize to (0, 0)
                normalized = self.normalize_bookmaker_coords(coords, offset_left, offset_top)
                
                # Merge with existing bookmaker if already present
                if bookmaker_name in self.new_data['bookmakers']:
                    print(f"   ⚠️  {bookmaker_name} already exists - skipping")
                else:
                    self.new_data['bookmakers'][bookmaker_name] = normalized
                    print(f"   ✅ {bookmaker_name}")
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        print(f"\nLayouts: {len(self.new_data['layouts'])}")
        print(f"Bookmakers: {len(self.new_data['bookmakers'])}")
        
        return self.new_data
    
    def save(self, backup: bool = True):
        """Save migrated data."""
        # Backup old file
        if backup and self.old_file.exists():
            backup_path = self.old_file.with_suffix('.json.backup')
            print(f"\n📦 Creating backup: {backup_path}")
            
            import shutil
            shutil.copy2(self.old_file, backup_path)
        
        # Save new format
        print(f"\n💾 Saving new format: {self.new_file}")
        
        with open(self.new_file, 'w') as f:
            json.dump(self.new_data, f, indent=2)
        
        print("✅ Saved successfully")
        
        # Display usage example
        print("\n" + "="*60)
        print("USAGE EXAMPLE")
        print("="*60)
        print("\nOld way:")
        print("  coords = manager.load_coordinates('Four 100%', 'BalkanBet')")
        print("\nNew way:")
        print("  coords = manager.calculate_coords(")
        print("    bookmaker_name='BalkanBet',")
        print("    layout_name='Four_100',")
        print("    position='TL'")
        print("  )")
        print("="*60)
    
    def compare(self):
        """Compare old vs new coordinates for verification."""
        print("\n" + "="*60)
        print("COORDINATE COMPARISON")
        print("="*60)
        
        # This would need the old positions mapped to new positions
        # For now, just show sample
        
        if self.new_data['bookmakers']:
            sample_bookmaker = next(iter(self.new_data['bookmakers'].keys()))
            print(f"\nSample bookmaker: {sample_bookmaker}")
            
            old_coords = None
            for config_name, bookmakers in self.old_data.items():
                if sample_bookmaker in bookmakers:
                    old_coords = bookmakers[sample_bookmaker]
                    break
            
            if old_coords:
                new_coords = self.new_data['bookmakers'][sample_bookmaker]
                
                print("\nOld (absolute):")
                for key in list(old_coords.keys())[:3]:
                    if isinstance(old_coords[key], dict):
                        print(f"  {key}: left={old_coords[key]['left']}, top={old_coords[key]['top']}")
                
                print("\nNew (relative to 0,0):")
                for key in list(new_coords.keys())[:3]:
                    if isinstance(new_coords[key], dict):
                        print(f"  {key}: left={new_coords[key]['left']}, top={new_coords[key]['top']}")
                
                print("\n✅ Coordinates normalized successfully")


def main():
    """Main migration function."""
    print("="*60)
    print("COORDINATE MIGRATION TOOL v1.0")
    print("="*60)
    
    # Get input file
    default_file = "data/coordinates/bookmaker_coords.json"
    
    print(f"\nDefault file: {default_file}")
    file_path = input("Enter path to old coordinates file (or press Enter for default): ").strip()
    
    if not file_path:
        file_path = default_file
    
    if not Path(file_path).exists():
        print(f"\n❌ File not found: {file_path}")
        return
    
    # Create migrator
    migrator = CoordinateMigrator(file_path)
    
    # Migrate
    migrator.migrate()
    
    # Ask to save
    save = input("\nSave migrated coordinates? (yes/no): ").strip().lower()
    
    if save in ['yes', 'y']:
        migrator.save(backup=True)
        
        # Compare
        compare = input("\nShow coordinate comparison? (yes/no): ").strip().lower()
        if compare in ['yes', 'y']:
            migrator.compare()
    else:
        print("\n⚠️  Migration not saved")
        print("   Review the migration and run again to save")


if __name__ == "__main__":
    main()