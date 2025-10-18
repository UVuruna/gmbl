# utils/pre_run_verification.py
# VERSION: 1.0
# PURPOSE: Complete system verification before first run
# Checks: database, coordinates, OCR, models, logging

import sys
import sqlite3
import json
import subprocess
import pickle
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import init_logging, AviatorLogger
from core.coord_manager import CoordsManager
from config import AppConstants


class SystemVerifier:
    """Comprehensive system verification."""
    
    def __init__(self):
        init_logging()
        self.logger = AviatorLogger.get_logger("SystemVerifier")
        
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        
        self.results = []
    
    def print_header(self, title: str):
        """Print section header."""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def check(self, name: str, passed: bool, message: str = "", warning: bool = False):
        """Record check result."""
        if passed:
            status = "✅"
            self.checks_passed += 1
        elif warning:
            status = "⚠️ "
            self.warnings += 1
        else:
            status = "❌"
            self.checks_failed += 1
        
        result = f"{status} {name}"
        if message:
            result += f": {message}"
        
        print(f"  {result}")
        self.results.append((name, passed, message))
        
        return passed
    
    def verify_python_version(self) -> bool:
        """Check Python version."""
        self.print_header("1. PYTHON VERSION")
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major >= 3 and version.minor >= 8:
            return self.check("Python Version", True, f"{version_str} (OK)")
        else:
            return self.check("Python Version", False, f"{version_str} (Need 3.8+)")
    
    def verify_dependencies(self) -> bool:
        """Check required Python packages."""
        self.print_header("2. PYTHON DEPENDENCIES")
        
        required = [
            'cv2',
            'numpy',
            'pytesseract',
            'mss',
            'PIL'
        ]
        
        all_ok = True
        for package in required:
            try:
                __import__(package)
                self.check(f"Package: {package}", True)
            except ImportError:
                self.check(f"Package: {package}", False, "NOT INSTALLED")
                all_ok = False
        
        return all_ok
    
    def verify_tesseract(self) -> bool:
        """Check Tesseract OCR installation."""
        self.print_header("3. TESSERACT OCR")
        
        try:
            result = subprocess.run(
                ['tesseract', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            version_line = result.stdout.split('\n')[0]
            return self.check("Tesseract", True, version_line)
            
        except FileNotFoundError:
            return self.check("Tesseract", False, "NOT FOUND - Install from https://github.com/UB-Mannheim/tesseract")
        except Exception as e:
            return self.check("Tesseract", False, str(e))
    
    def verify_database(self) -> bool:
        """Check database setup."""
        self.print_header("4. DATABASE")
        
        db_path = Path("data/databases/main_game_data.db")
        
        # Check if exists
        if not db_path.exists():
            self.check("Database File", False, f"{db_path} does not exist (will be auto-created)", warning=True)
            return True
        
        self.check("Database File", True, str(db_path))
        
        # Check tables
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check rounds table
            cursor.execute("SELECT COUNT(*) FROM rounds")
            rounds_count = cursor.fetchone()[0]
            self.check("Rounds Table", True, f"{rounds_count} rows")
            
            # Check threshold_scores table
            cursor.execute("SELECT COUNT(*) FROM threshold_scores")
            threshold_count = cursor.fetchone()[0]
            self.check("Threshold Table", True, f"{threshold_count} rows")
            
            conn.close()
            return True
            
        except sqlite3.Error as e:
            self.check("Database Schema", False, str(e))
            return False
    
    def verify_coordinates(self) -> bool:
        """Check coordinate system."""
        self.print_header("5. COORDINATE SYSTEM")
        
        coords_file = Path("data/coordinates/bookmaker_coords.json")
        
        if not coords_file.exists():
            return self.check("Coordinates File", False, f"{coords_file} NOT FOUND")
        
        self.check("Coordinates File", True, str(coords_file))
        
        try:
            manager = CoordsManager()
            
            # Check layouts
            layouts = manager.get_available_layouts()
            if layouts:
                self.check("Layouts", True, f"{len(layouts)} defined: {', '.join(layouts)}")
            else:
                self.check("Layouts", False, "No layouts defined", warning=True)
            
            # Check bookmakers
            bookmakers = manager.get_available_bookmakers()
            if bookmakers:
                self.check("Bookmakers", True, f"{len(bookmakers)} defined: {', '.join(bookmakers)}")
                
                # Verify each bookmaker has all required regions
                required_regions = [
                    'score_region',
                    'my_money_region',
                    'other_count_region',
                    'other_money_region',
                    'phase_region',
                    'play_amount_coords',
                    'play_button_coords',
                    'auto_play_coords'
                ]
                
                for bookmaker in bookmakers:
                    coords = manager.get_bookmaker_base_coords(bookmaker)
                    missing = [r for r in required_regions if r not in coords]
                    
                    if missing:
                        self.check(
                            f"  {bookmaker}",
                            False,
                            f"Missing: {', '.join(missing)}",
                            warning=True
                        )
                    else:
                        self.check(f"  {bookmaker}", True, "All regions defined")
                
                return True
            else:
                return self.check("Bookmakers", False, "No bookmakers defined")
        
        except Exception as e:
            return self.check("Coordinate System", False, str(e))
    
    def verify_models(self) -> bool:
        """Check ML models."""
        self.print_header("6. ML MODELS")
        
        model_path = Path(AppConstants.model_file)
        
        if not model_path.exists():
            return self.check(
                "K-means Model",
                False,
                f"{model_path} NOT FOUND (run apps/rgb_collector.py first)",
                warning=True
            )
        
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            # Check if it's a K-means model
            if hasattr(model, 'n_clusters'):
                return self.check(
                    "K-means Model",
                    True,
                    f"{model.n_clusters} clusters"
                )
            else:
                return self.check("K-means Model", False, "Invalid model format")
                
        except Exception as e:
            return self.check("K-means Model", False, str(e))
    
    def verify_logging(self) -> bool:
        """Check logging setup."""
        self.print_header("7. LOGGING")
        
        logs_dir = Path("logs")
        
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)
            self.check("Logs Directory", True, "Created")
        else:
            self.check("Logs Directory", True, str(logs_dir))
        
        # Check write permissions
        test_file = logs_dir / "test.log"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return self.check("Write Permissions", True)
        except Exception as e:
            return self.check("Write Permissions", False, str(e))
    
    def verify_javascript_css(self) -> bool:
        """Check JavaScript CSS file."""
        self.print_header("8. JAVASCRIPT/CSS")
        
        js_file = Path("javascript.txt")
        
        if not js_file.exists():
            return self.check(
                "javascript.txt",
                False,
                "NOT FOUND - CSS injection required for clean UI",
                warning=True
            )
        
        return self.check("javascript.txt", True, str(js_file))
    
    def verify_screen_capture(self) -> bool:
        """Test screen capture functionality."""
        self.print_header("9. SCREEN CAPTURE TEST")
        
        try:
            import mss
            
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                screenshot = sct.grab(monitor)
                
                width = screenshot.width
                height = screenshot.height
                
                return self.check(
                    "Screen Capture",
                    True,
                    f"{width}x{height} pixels"
                )
        
        except Exception as e:
            return self.check("Screen Capture", False, str(e))
    
    def print_summary(self):
        """Print final summary."""
        print("\n" + "="*70)
        print("  VERIFICATION SUMMARY")
        print("="*70)
        
        total_checks = self.checks_passed + self.checks_failed + self.warnings
        
        print(f"\n  Total Checks: {total_checks}")
        print(f"  ✅ Passed: {self.checks_passed}")
        print(f"  ⚠️  Warnings: {self.warnings}")
        print(f"  ❌ Failed: {self.checks_failed}")
        
        print("\n" + "="*70)
        
        if self.checks_failed == 0:
            print("  🎉 SYSTEM READY FOR OPERATION!")
            print("="*70)
            print("\nNext steps:")
            print("  1. Inject CSS (javascript.txt) into browser console")
            print("  2. Run: python apps/main_data_collector.py")
            print("  3. Monitor logs: tail -f logs/main_data_collector.log")
            return True
        else:
            print("  ⚠️  SYSTEM NOT READY - FIX ISSUES ABOVE")
            print("="*70)
            return False
    
    def run_all_checks(self) -> bool:
        """Run all verification checks."""
        print("\n" + "="*70)
        print("  AVIATOR DATA COLLECTOR - SYSTEM VERIFICATION")
        print("="*70)
        
        self.verify_python_version()
        self.verify_dependencies()
        self.verify_tesseract()
        self.verify_database()
        self.verify_coordinates()
        self.verify_models()
        self.verify_logging()
        self.verify_javascript_css()
        self.verify_screen_capture()
        
        return self.print_summary()


def main():
    """Main entry point."""
    verifier = SystemVerifier()
    success = verifier.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
