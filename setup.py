# setup.py
# VERSION: 1.0
# System setup and verification script

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from config import config, BOOKMAKERS_INFO, LAYOUT_PRESETS
from database.models import initialize_all_databases
from core.coord_manager import CoordsManager


class SystemSetup:
    """System setup and verification."""
    
    def __init__(self):
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.success: List[str] = []
    
    def check_python_version(self) -> bool:
        """Check Python version."""
        print("\n🐍 Checking Python version...")
        
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            msg = f"   ✅ Python {version.major}.{version.minor}.{version.micro}"
            print(msg)
            self.success.append(msg)
            return True
        else:
            msg = f"   ❌ Python 3.8+ required (found {version.major}.{version.minor})"
            print(msg)
            self.issues.append(msg)
            return False
    
    def check_dependencies(self) -> bool:
        """Check required dependencies."""
        print("\n📦 Checking dependencies...")
        
        required = [
            'numpy',
            'pandas',
            'PIL',
            'pytesseract',
            'sklearn',
            'mss',
            'cv2',
            'pyautogui'
        ]
        
        all_ok = True
        
        for module in required:
            try:
                __import__(module)
                print(f"   ✅ {module}")
                self.success.append(f"{module} installed")
            except ImportError:
                print(f"   ❌ {module} NOT INSTALLED")
                self.issues.append(f"{module} missing")
                all_ok = False
        
        if not all_ok:
            print("\n   Run: pip install -r requirements.txt")
        
        return all_ok
    
    def check_tesseract(self) -> bool:
        """Check Tesseract installation."""
        print("\n🔍 Checking Tesseract OCR...")
        
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = config.ocr.tesseract_path
            
            # Try to get version
            version = pytesseract.get_tesseract_version()
            msg = f"   ✅ Tesseract {version}"
            print(msg)
            self.success.append(msg)
            return True
        except Exception as e:
            msg = f"   ❌ Tesseract not found or not configured"
            print(msg)
            print(f"   Error: {e}")
            self.issues.append("Tesseract not installed")
            
            print("\n   Install from:")
            print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   Linux: sudo apt-get install tesseract-ocr")
            print(f"   Then set path in config.py: {config.ocr.tesseract_path}")
            
            return False
    
    def check_directories(self) -> bool:
        """Check/create necessary directories."""
        print("\n📁 Checking directories...")
        
        config.initialize()
        
        directories = [
            config.paths.data_dir,
            config.paths.logs_dir,
            config.paths.database_dir,
            config.paths.models_dir,
            config.paths.coords_dir,
            config.paths.screenshots_dir
        ]
        
        all_ok = True
        for directory in directories:
            if directory.exists():
                print(f"   ✅ {directory.relative_to(config.paths.project_root)}")
            else:
                print(f"   ⚠️  Creating: {directory.relative_to(config.paths.project_root)}")
                directory.mkdir(parents=True, exist_ok=True)
                self.warnings.append(f"Created {directory}")
        
        return all_ok
    
    def check_coordinates(self) -> bool:
        """Check coordinate configuration."""
        print("\n🎯 Checking coordinates...")
        
        if not config.paths.bookmaker_coords.exists():
            print(f"   ⚠️  Coordinates file not found")
            print(f"   Creating template: {config.paths.bookmaker_coords}")
            
            # Create empty template
            import json
            template = {
                "layouts": {},
                "bookmakers": {}
            }
            with open(config.paths.bookmaker_coords, 'w') as f:
                json.dump(template, f, indent=2)
            
            self.warnings.append("Created empty coordinates file")
            print("   ⚠️  You need to configure coordinates!")
            print("   Run: python utils/region_editor.py")
            return False
        
        # Check contents
        manager = CoordsManager()
        layouts = manager.get_available_layouts()
        bookmakers = manager.get_available_bookmakers()
        
        if not layouts:
            print("   ⚠️  No layouts configured")
            self.warnings.append("No layouts in coordinates")
            return False
        
        if not bookmakers:
            print("   ⚠️  No bookmakers configured")
            self.warnings.append("No bookmakers in coordinates")
            return False
        
        print(f"   ✅ {len(layouts)} layout(s): {', '.join(layouts)}")
        print(f"   ✅ {len(bookmakers)} bookmaker(s): {', '.join(bookmakers)}")
        self.success.append(f"Coordinates: {len(layouts)} layouts, {len(bookmakers)} bookmakers")
        
        return True
    
    def check_databases(self) -> bool:
        """Check/initialize databases."""
        print("\n💾 Checking databases...")
        
        try:
            initialize_all_databases()
            self.success.append("All databases initialized")
            return True
        except Exception as e:
            print(f"   ❌ Database initialization failed: {e}")
            self.issues.append("Database initialization failed")
            return False
    
    def check_javascript_css(self) -> bool:
        """Check JavaScript/CSS file."""
        print("\n📝 Checking JavaScript/CSS configuration...")
        
        if not config.paths.javascript_css.exists():
            print(f"   ⚠️  javascript.txt not found")
            self.warnings.append("javascript.txt missing")
            print("   This file contains CSS to optimize bookmaker sites")
            return False
        
        print(f"   ✅ {config.paths.javascript_css}")
        self.success.append("javascript.txt found")
        return True
    
    def display_summary(self):
        """Display setup summary."""
        print("\n" + "="*60)
        print("SETUP SUMMARY")
        print("="*60)
        
        if self.success:
            print(f"\n✅ Success ({len(self.success)}):")
            for msg in self.success[:5]:  # Show first 5
                print(f"   • {msg}")
            if len(self.success) > 5:
                print(f"   ... and {len(self.success) - 5} more")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"   • {msg}")
        
        if self.issues:
            print(f"\n❌ Issues ({len(self.issues)}):")
            for msg in self.issues:
                print(f"   • {msg}")
        
        print("\n" + "="*60)
        
        if not self.issues:
            print("✅ SYSTEM READY!")
            print("\nNext steps:")
            print("  1. Configure coordinates (if not done):")
            print("     python utils/region_editor.py")
            print("  2. Inject CSS into bookmaker sites (use javascript.txt)")
            print("  3. Run programs:")
            print("     python apps/main_data_collector.py")
            print("     python apps/rgb_collector.py")
            print("     python apps/betting_agent.py")
        else:
            print("❌ SETUP INCOMPLETE")
            print("\nFix issues above before proceeding.")
        
        print("="*60)
    
    def run(self):
        """Run complete setup check."""
        print("="*60)
        print("AVIATOR SYSTEM SETUP v5.0")
        print("="*60)
        
        checks = [
            self.check_python_version,
            self.check_dependencies,
            self.check_tesseract,
            self.check_directories,
            self.check_coordinates,
            self.check_databases,
            self.check_javascript_css
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"\n❌ Check failed: {e}")
                self.issues.append(f"Check failed: {e}")
        
        self.display_summary()
        
        return len(self.issues) == 0


def interactive_setup():
    """Interactive setup wizard."""
    print("\n" + "="*60)
    print("INTERACTIVE SETUP WIZARD")
    print("="*60)
    
    print("\nThis wizard will guide you through system setup.")
    print("Press Enter to continue or Ctrl+C to exit...")
    input()
    
    setup = SystemSetup()
    success = setup.run()
    
    if not success:
        print("\n⚠️  Some issues were found.")
        response = input("\nWould you like help fixing them? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            print("\n--- TROUBLESHOOTING GUIDE ---")
            
            if any('dependencies' in issue.lower() for issue in setup.issues):
                print("\n📦 Installing dependencies:")
                print("   pip install -r requirements.txt")
                install = input("\n   Install now? (yes/no): ").strip().lower()
                if install in ['yes', 'y']:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            
            if any('tesseract' in issue.lower() for issue in setup.issues):
                print("\n🔍 Tesseract OCR:")
                print("   Download and install Tesseract")
                print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
                print("   Linux: sudo apt-get install tesseract-ocr")
                print(f"\n   Then update path in config.py:")
                print(f"   tesseract_path = '{config.ocr.tesseract_path}'")
            
            if any('coordinates' in issue.lower() for issue in setup.issues):
                print("\n🎯 Coordinates:")
                print("   Run region editor to configure:")
                print("   python utils/region_editor.py")
                
                run_editor = input("\n   Run editor now? (yes/no): ").strip().lower()
                if run_editor in ['yes', 'y']:
                    subprocess.run([sys.executable, 'utils/region_editor.py'])
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Aviator System Setup')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Run interactive setup wizard')
    parser.add_argument('--quick', '-q', action='store_true',
                        help='Quick check only (no fixes)')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_setup()
    else:
        setup = SystemSetup()
        setup.run()
