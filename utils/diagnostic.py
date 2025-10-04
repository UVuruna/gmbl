# utils/diagnostic.py
"""
System Diagnostic Tool
Version: 3.0
Comprehensive system checks for Aviator project
"""

import sys
import os
import time
import sqlite3
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import importlib
import tempfile

# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


class SystemDiagnostic:
    """Comprehensive system diagnostic tool"""
    
    def __init__(self):
        self.results = []
        self.warnings = []
        self.errors = []
        self.python_version = sys.version_info
        
    def run_all_checks(self, quick: bool = False) -> bool:
        """
        Run all diagnostic checks
        
        Args:
            quick: If True, skip time-consuming checks
            
        Returns:
            True if all critical checks pass
        """
        print_header("AVIATOR SYSTEM DIAGNOSTIC v3.0")
        
        # System information
        self.check_system_info()
        
        # Python version
        if not self.check_python_version():
            return False
        
        # Required modules
        if not self.check_required_modules():
            return False
        
        # Project structure
        if not self.check_project_structure():
            return False
        
        # Configuration
        if not self.check_configuration():
            return False
        
        # Logger fix
        if not self.check_logger_fix():
            return False
        
        # Database
        if not self.check_database():
            return False
        
        # OCR (Tesseract)
        if not self.check_tesseract():
            return False
        
        # Performance (if not quick mode)
        if not quick:
            self.check_performance()
        
        # Display summary
        self.display_summary()
        
        return len(self.errors) == 0
    
    def check_system_info(self) -> None:
        """Display system information"""
        print_header("SYSTEM INFORMATION")
        
        print_info(f"Platform:     {platform.system()} {platform.release()}")
        print_info(f"Architecture: {platform.machine()}")
        print_info(f"Processor:    {platform.processor()}")
        print_info(f"Python:       {sys.version}")
        print_info(f"Working Dir:  {os.getcwd()}")
        
        # Check available RAM
        try:
            import psutil
            memory = psutil.virtual_memory()
            print_info(f"RAM:          {memory.total / (1024**3):.1f} GB "
                      f"({memory.available / (1024**3):.1f} GB available)")
            
            if memory.available < 2 * (1024**3):  # Less than 2GB
                self.warnings.append("Low available memory")
                print_warning("Low available memory (< 2GB)")
        except ImportError:
            print_warning("psutil not installed - cannot check memory")
    
    def check_python_version(self) -> bool:
        """Check Python version"""
        print_header("PYTHON VERSION CHECK")
        
        required = (3, 8)
        current = self.python_version[:2]
        
        if current >= required:
            print_success(f"Python {current[0]}.{current[1]} meets requirements")
            return True
        else:
            print_error(f"Python {current[0]}.{current[1]} is too old (need 3.8+)")
            self.errors.append("Python version too old")
            return False
    
    def check_required_modules(self) -> bool:
        """Check if required modules are installed"""
        print_header("MODULE DEPENDENCIES")
        
        required_modules = [
            ('numpy', 'NumPy'),
            ('pandas', 'Pandas'),
            ('PIL', 'Pillow'),
            ('pytesseract', 'PyTesseract'),
            ('sklearn', 'Scikit-learn'),
            ('pyautogui', 'PyAutoGUI'),
            ('mss', 'MSS'),
            ('cv2', 'OpenCV'),
        ]
        
        all_present = True
        
        for module_name, display_name in required_modules:
            try:
                module = importlib.import_module(module_name)
                version = getattr(module, '__version__', 'unknown')
                print_success(f"{display_name:15} {version}")
            except ImportError:
                print_error(f"{display_name:15} NOT INSTALLED")
                self.errors.append(f"{display_name} not installed")
                all_present = False
        
        return all_present
    
    def check_project_structure(self) -> bool:
        """Check if project structure is correct"""
        print_header("PROJECT STRUCTURE")
        
        required_dirs = [
            'apps',
            'core',
            'database',
            'regions',
            'ai',
            'utils',
            'data',
            'data/databases',
            'data/models',
            'data/coordinates',
            'logs',
        ]
        
        required_files = [
            'config.py',
            'logger.py',
            'main.py',
            'requirements.txt'
        ]
        
        all_present = True
        
        # Check directories
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                print_success(f"Directory: {dir_name}/")
            else:
                print_warning(f"Directory missing: {dir_name}/")
                # Create missing directory
                dir_path.mkdir(parents=True, exist_ok=True)
                print_info(f"Created: {dir_name}/")
        
        # Check files
        for file_name in required_files:
            file_path = Path(file_name)
            if file_path.exists():
                print_success(f"File: {file_name}")
            else:
                print_error(f"File missing: {file_name}")
                self.errors.append(f"Missing file: {file_name}")
                all_present = False
        
        return all_present
    
    def check_configuration(self) -> bool:
        """Check configuration file"""
        print_header("CONFIGURATION CHECK")
        
        try:
            from config import app_config, bookmaker_config
            
            # Check critical settings
            checks = [
                ('Database path', app_config.main_database),
                ('Models directory', app_config.models_dir),
                ('Batch size', app_config.batch_size),
                ('Collection interval', app_config.default_collection_interval),
            ]
            
            for setting_name, value in checks:
                print_success(f"{setting_name:20} = {value}")
            
            # Check batch configuration
            if app_config.batch_size < 10:
                print_warning(f"Batch size ({app_config.batch_size}) is low - consider increasing")
                self.warnings.append("Low batch size")
            
            return True
            
        except Exception as e:
            print_error(f"Configuration error: {e}")
            self.errors.append("Configuration error")
            return False
    
    def check_logger_fix(self) -> bool:
        """Check if logger has v3.0 fix"""
        print_header("LOGGER FIX CHECK (v3.0)")
        
        try:
            # Check if logger returns object
            from logger import init_logging
            
            # Test initialization
            with tempfile.TemporaryDirectory() as tmpdir:
                logger = init_logging(log_dir=Path(tmpdir), console_output=False)
                
                if logger is None:
                    print_error("Logger init_logging() returns None - NOT FIXED!")
                    self.errors.append("Logger not fixed (v3.0)")
                    return False
                else:
                    print_success("Logger returns object correctly (v3.0 fix applied)")
                    
                    # Test logging
                    test_msg = "Diagnostic test message"
                    logger.info(test_msg)
                    
                    # Check log file
                    log_file = Path(tmpdir) / 'main.log'
                    if log_file.exists():
                        content = log_file.read_text()
                        if test_msg in content:
                            print_success("Logger writes to file correctly")
                        else:
                            print_warning("Logger initialized but not writing")
                            self.warnings.append("Logger write issue")
                    
                    return True
                    
        except Exception as e:
            print_error(f"Logger check failed: {e}")
            self.errors.append("Logger check failed")
            return False
    
    def check_database(self) -> bool:
        """Check database functionality"""
        print_header("DATABASE CHECK")
        
        try:
            # Test database creation and batch operations
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                test_db = f.name
            
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE test (
                    id INTEGER PRIMARY KEY,
                    value TEXT,
                    timestamp REAL
                )
            """)
            
            # Test batch insert
            start = time.time()
            data = [(f"test_{i}", time.time()) for i in range(100)]
            cursor.executemany(
                "INSERT INTO test (value, timestamp) VALUES (?, ?)",
                data
            )
            conn.commit()
            batch_time = time.time() - start
            
            # Check results
            cursor.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            
            conn.close()
            os.unlink(test_db)
            
            if count == 100:
                print_success(f"Database batch insert: 100 items in {batch_time*1000:.1f}ms")
                return True
            else:
                print_error(f"Database insert failed: expected 100, got {count}")
                self.errors.append("Database batch insert failed")
                return False
                
        except Exception as e:
            print_error(f"Database check failed: {e}")
            self.errors.append("Database error")
            return False
    
    def check_tesseract(self) -> bool:
        """Check Tesseract OCR installation"""
        print_header("TESSERACT OCR CHECK")
        
        try:
            import pytesseract
            from config import app_config
            
            # Set Tesseract path if configured
            if hasattr(app_config, 'tesseract_path'):
                pytesseract.pytesseract.tesseract_cmd = app_config.tesseract_path
            
            # Try to get version
            version = pytesseract.get_tesseract_version()
            print_success(f"Tesseract version: {version}")
            
            # Test OCR
            from PIL import Image
            import numpy as np
            
            # Create test image with text
            img = Image.new('RGB', (100, 30), color='white')
            test_text = pytesseract.image_to_string(img)
            
            print_success("Tesseract OCR functional")
            return True
            
        except Exception as e:
            print_error(f"Tesseract not found or not working: {e}")
            print_info("Install Tesseract: https://github.com/tesseract-ocr/tesseract")
            self.errors.append("Tesseract OCR not available")
            return False
    
    def check_performance(self) -> None:
        """Run performance benchmarks"""
        print_header("PERFORMANCE BENCHMARKS")
        
        try:
            # Database performance
            self._benchmark_database()
            
            # Queue performance
            self._benchmark_queue()
            
        except Exception as e:
            print_warning(f"Performance check failed: {e}")
            self.warnings.append("Performance check incomplete")
    
    def _benchmark_database(self) -> None:
        """Benchmark database performance"""
        print_info("Testing database performance...")
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            test_db = f.name
        
        try:
            conn = sqlite3.connect(test_db)
            cursor = conn.cursor()
            
            # Create table
            cursor.execute("""
                CREATE TABLE benchmark (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    value REAL
                )
            """)
            
            # Single inserts
            start = time.time()
            for i in range(100):
                cursor.execute(
                    "INSERT INTO benchmark (data, value) VALUES (?, ?)",
                    (f"data_{i}", i * 1.5)
                )
            conn.commit()
            single_time = time.time() - start
            
            # Batch insert
            cursor.execute("DELETE FROM benchmark")
            start = time.time()
            data = [(f"data_{i}", i * 1.5) for i in range(100)]
            cursor.executemany(
                "INSERT INTO benchmark (data, value) VALUES (?, ?)",
                data
            )
            conn.commit()
            batch_time = time.time() - start
            
            conn.close()
            os.unlink(test_db)
            
            speedup = single_time / batch_time if batch_time > 0 else 0
            
            print_info(f"Single inserts: {single_time*1000:.1f}ms")
            print_info(f"Batch insert:   {batch_time*1000:.1f}ms")
            print_info(f"Speedup:        {speedup:.1f}x")
            
            if speedup > 5:
                print_success("Database performance: EXCELLENT")
            elif speedup > 2:
                print_success("Database performance: GOOD")
            else:
                print_warning("Database performance: NEEDS OPTIMIZATION")
                self.warnings.append("Low database performance")
                
        except Exception as e:
            print_error(f"Database benchmark failed: {e}")
    
    def _benchmark_queue(self) -> None:
        """Benchmark queue performance"""
        import queue
        import threading
        
        print_info("Testing queue performance...")
        
        q = queue.Queue(maxsize=10000)
        items_to_process = 1000
        
        def producer():
            for i in range(items_to_process):
                q.put(f"item_{i}")
        
        def consumer():
            count = 0
            while count < items_to_process:
                try:
                    item = q.get(timeout=0.1)
                    count += 1
                    q.task_done()
                except queue.Empty:
                    break
        
        start = time.time()
        
        # Start threads
        prod = threading.Thread(target=producer)
        cons = threading.Thread(target=consumer)
        
        prod.start()
        cons.start()
        
        prod.join()
        cons.join()
        
        elapsed = time.time() - start
        throughput = items_to_process / elapsed if elapsed > 0 else 0
        
        print_info(f"Queue throughput: {throughput:.0f} items/sec")
        
        if throughput > 10000:
            print_success("Queue performance: EXCELLENT")
        elif throughput > 5000:
            print_success("Queue performance: GOOD")
        else:
            print_warning("Queue performance: NEEDS OPTIMIZATION")
            self.warnings.append("Low queue performance")
    
    def display_summary(self) -> None:
        """Display diagnostic summary"""
        print_header("DIAGNOSTIC SUMMARY")
        
        # Count results
        total_checks = len(self.results) + len(self.warnings) + len(self.errors)
        
        if self.errors:
            print(f"\n{Colors.RED}❌ CRITICAL ISSUES FOUND:{Colors.RESET}")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️  WARNINGS:{Colors.RESET}")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Overall status
        print(f"\n{Colors.BOLD}OVERALL STATUS:{Colors.RESET}")
        
        if self.errors:
            print_error("SYSTEM NOT READY - Fix critical issues")
        elif self.warnings:
            print_warning("SYSTEM READY - But check warnings")
        else:
            print_success("SYSTEM READY - All checks passed!")
        
        print(f"\nTotal checks: {total_checks}")
        print(f"Errors:       {len(self.errors)}")
        print(f"Warnings:     {len(self.warnings)}")


def run_diagnostics(quick: bool = False) -> bool:
    """
    Run system diagnostics
    
    Args:
        quick: If True, skip time-consuming checks
        
    Returns:
        True if all critical checks pass
    """
    diagnostic = SystemDiagnostic()
    return diagnostic.run_all_checks(quick=quick)


def main():
    """Main entry point for diagnostic tool"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Aviator System Diagnostic Tool')
    parser.add_argument('--quick', action='store_true', 
                       help='Skip time-consuming checks')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed output')
    
    args = parser.parse_args()
    
    # Run diagnostics
    success = run_diagnostics(quick=args.quick)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()