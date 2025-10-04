# diagnostic.py
# VERSION: 3.0
# CHANGES: Complete system diagnostic and validation tool

"""
System Diagnostic Tool for Aviator Data Collector v3.0

This script checks:
1. Logger functionality
2. Database performance
3. Configuration validity
4. File integrity
5. Performance benchmarks

Run before starting data collection to ensure everything works!
"""

import os
import sys
import sqlite3
import time
from pathlib import Path
from datetime import datetime
import subprocess

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def print_success(text):
    """Print success message."""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    """Print error message."""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    """Print info message."""
    print(f"   {text}")


class SystemDiagnostic:
    """Complete system diagnostic."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed_tests = 0
        self.total_tests = 0
    
    def test(self, name, func):
        """Run a test and track results."""
        self.total_tests += 1
        print(f"\n{YELLOW}Testing: {name}...{RESET}")
        try:
            result = func()
            if result:
                self.passed_tests += 1
                print_success(f"{name} - PASSED")
                return True
            else:
                print_error(f"{name} - FAILED")
                return False
        except Exception as e:
            print_error(f"{name} - ERROR: {e}")
            self.errors.append(f"{name}: {e}")
            return False
    
    def check_python_version(self):
        """Check Python version."""
        version = sys.version_info
        print_info(f"Python {version.major}.{version.minor}.{version.micro}")
        
        if version.major == 3 and version.minor >= 8:
            print_success("Python version OK (3.8+)")
            return True
        else:
            print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
            return False
    
    def check_required_files(self):
        """Check all required files exist."""
        required_files = [
            'logger.py',
            'config.py',
            'main.py',
            'data_collector.py',
            'database/database_worker.py',
            'database/database_writer.py',
            'main/bookmaker_orchestrator.py',
            'main/bookmaker_process.py',
        ]
        
        missing = []
        for file in required_files:
            if not os.path.exists(file):
                missing.append(file)
                print_error(f"Missing: {file}")
            else:
                print_info(f"Found: {file}")
        
        if missing:
            self.errors.append(f"Missing files: {', '.join(missing)}")
            return False
        
        print_success("All required files present")
        return True
    
    def check_logger_fix(self):
        """Check if logger.py has the return statement fix."""
        try:
            with open('logger.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'return root_logger' in content:
                print_success("Logger fix applied (return statement present)")
                return True
            else:
                print_error("Logger NOT fixed - missing 'return root_logger'")
                self.errors.append("Logger missing return statement")
                return False
                
        except Exception as e:
            print_error(f"Cannot read logger.py: {e}")
            return False
    
    def check_batch_configuration(self):
        """Check if batch configuration is correct."""
        try:
            # Import config
            sys.path.insert(0, '.')
            from config import AppConstants
            
            batch_size = getattr(AppConstants, 'batch_size', None)
            batch_timeout = getattr(AppConstants, 'batch_timeout', None)
            
            if batch_size is None:
                print_error("batch_size not found in config")
                return False
            
            if batch_timeout is None:
                print_error("batch_timeout not found in config")
                return False
            
            print_info(f"batch_size: {batch_size}")
            print_info(f"batch_timeout: {batch_timeout}s")
            
            if batch_size >= 10:
                print_success(f"Batch configuration OK (size={batch_size})")
                return True
            else:
                print_warning(f"Batch size low ({batch_size}), recommend 50+")
                self.warnings.append("Low batch size")
                return True
                
        except Exception as e:
            print_error(f"Cannot check config: {e}")
            return False
    
    def check_tesseract(self):
        """Check if Tesseract OCR is installed."""
        try:
            from config import AppConstants
            tesseract_path = AppConstants.tesseract_path
            
            if os.path.exists(tesseract_path):
                print_success(f"Tesseract found at: {tesseract_path}")
                
                # Try to run tesseract
                try:
                    result = subprocess.run(
                        [tesseract_path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    version = result.stdout.split('\n')[0]
                    print_info(f"Version: {version}")
                    return True
                except:
                    print_warning("Tesseract found but cannot execute")
                    self.warnings.append("Tesseract execution failed")
                    return True
            else:
                print_error(f"Tesseract not found at: {tesseract_path}")
                print_info("Install from: https://github.com/UB-Mannheim/tesseract/wiki")
                self.errors.append("Tesseract not installed")
                return False
                
        except Exception as e:
            print_error(f"Cannot check Tesseract: {e}")
            return False
    
    def check_dependencies(self):
        """Check required Python packages."""
        required = [
            'numpy',
            'pandas',
            'sklearn',
            'PIL',
            'mss',
            'pytesseract',
            'joblib'
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
                print_info(f"✓ {package}")
            except ImportError:
                print_error(f"✗ {package}")
                missing.append(package)
        
        if missing:
            print_error(f"Missing packages: {', '.join(missing)}")
            print_info("Install with: pip install " + " ".join(missing))
            self.errors.append(f"Missing dependencies: {', '.join(missing)}")
            return False
        
        print_success("All dependencies installed")
        return True
    
    def check_database(self):
        """Check database structure and integrity."""
        try:
            from config import AppConstants
            db_path = AppConstants.database
            
            if not os.path.exists(db_path):
                print_warning(f"Database not found: {db_path}")
                print_info("Run 'python database_setup.py' to create it")
                self.warnings.append("Database not created yet")
                return True
            
            # Check database integrity
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check integrity
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()[0]
            
            if result == 'ok':
                print_success("Database integrity OK")
            else:
                print_error(f"Database integrity failed: {result}")
                conn.close()
                return False
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['rounds', 'snapshots', 'earnings']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print_error(f"Missing tables: {', '.join(missing_tables)}")
                conn.close()
                return False
            
            print_info(f"Tables: {', '.join(tables)}")
            
            # Check record count
            cursor.execute("SELECT COUNT(*) FROM rounds;")
            count = cursor.fetchone()[0]
            print_info(f"Records: {count:,}")
            
            # Check WAL mode
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            print_info(f"Journal mode: {mode}")
            
            if mode.upper() != 'WAL':
                print_warning("Not using WAL mode (recommend enabling)")
                self.warnings.append("Not using WAL mode")
            
            conn.close()
            print_success("Database structure OK")
            return True
            
        except Exception as e:
            print_error(f"Database check failed: {e}")
            return False
    
    def benchmark_database(self):
        """Benchmark database write performance."""
        try:
            from config import AppConstants
            import tempfile
            
            print_info("Running database benchmark...")
            
            # Create temporary database
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                temp_db = f.name
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE test (
                    id INTEGER PRIMARY KEY,
                    value TEXT,
                    timestamp REAL
                )
            """)
            
            # Test 1: Single inserts
            start = time.time()
            for i in range(100):
                cursor.execute(
                    "INSERT INTO test (value, timestamp) VALUES (?, ?)",
                    (f"test_{i}", time.time())
                )
                conn.commit()
            single_time = time.time() - start
            
            # Test 2: Batch inserts
            cursor.execute("DELETE FROM test")
            start = time.time()
            data = [(f"test_{i}", time.time()) for i in range(100)]
            cursor.executemany(
                "INSERT INTO test (value, timestamp) VALUES (?, ?)",
                data
            )
            conn.commit()
            batch_time = time.time() - start
            
            conn.close()
            os.unlink(temp_db)
            
            speedup = single_time / batch_time if batch_time > 0 else 0
            
            print_info(f"Single inserts (100 items): {single_time*1000:.1f}ms")
            print_info(f"Batch insert (100 items): {batch_time*1000:.1f}ms")
            print_info(f"Speedup: {speedup:.1f}x")
            
            if speedup > 5:
                print_success(f"Database performance excellent ({speedup:.1f}x faster with batching)")
                return True
            elif speedup > 2:
                print_warning(f"Database performance moderate ({speedup:.1f}x)")
                return True
            else:
                print_warning("Database performance low")
                self.warnings.append("Low database performance")
                return True
                
        except Exception as e:
            print_error(f"Benchmark failed: {e}")
            return False
    
    def check_logging_system(self):
        """Test logging system."""
        try:
            print_info("Testing logging system...")
            
            # Import logger
            from root.logger import init_logging, AviatorLogger
            
            # Initialize
            logger_obj = init_logging()
            
            if logger_obj is None:
                print_error("init_logging() returned None - NOT FIXED!")
                self.errors.append("Logger returns None")
                return False
            
            print_success("init_logging() returns logger object")
            
            # Try to create log
            test_logger = AviatorLogger.get_logger("DiagnosticTest")
            test_logger.info("Diagnostic test message")
            
            # Check if log file exists
            from config import AppConstants
            log_dir = AppConstants.log_dir
            
            if os.path.exists(log_dir):
                log_files = os.listdir(log_dir)
                if log_files:
                    print_info(f"Found {len(log_files)} log file(s)")
                    print_success("Logging system working")
                    return True
                else:
                    print_warning("Log directory empty")
                    return True
            else:
                print_warning("Log directory not created yet")
                return True
                
        except Exception as e:
            print_error(f"Logging test failed: {e}")
            return False
    
    def estimate_performance(self):
        """Estimate expected performance."""
        try:
            print_info("Performance estimation for 4 bookmakers @ 0.2s interval:")
            
            items_per_sec = 4 / 0.2
            items_per_hour = items_per_sec * 3600
            items_per_day = items_per_hour * 24
            
            print_info(f"Items per second: {items_per_sec:.1f}")
            print_info(f"Items per hour: {items_per_hour:,.0f}")
            print_info(f"Items per day: {items_per_day:,.0f}")
            
            # Database size estimation
            bytes_per_record = 200  # Rough estimate
            db_size_per_day = items_per_day * bytes_per_record / (1024**2)
            
            print_info(f"Est. database growth: {db_size_per_day:.1f} MB/day")
            
            print_success("Performance estimation complete")
            return True
            
        except Exception as e:
            print_error(f"Estimation failed: {e}")
            return False
    
    def generate_report(self):
        """Generate final diagnostic report."""
        print_header("DIAGNOSTIC REPORT")
        
        print(f"\n{BLUE}Test Results:{RESET}")
        print(f"   Passed: {self.passed_tests}/{self.total_tests}")
        
        if self.errors:
            print(f"\n{RED}Errors ({len(self.errors)}):{RESET}")
            for error in self.errors:
                print(f"   {RED}•{RESET} {error}")
        
        if self.warnings:
            print(f"\n{YELLOW}Warnings ({len(self.warnings)}):{RESET}")
            for warning in self.warnings:
                print(f"   {YELLOW}•{RESET} {warning}")
        
        print(f"\n{BLUE}Status:{RESET}")
        if not self.errors:
            print_success("System ready for production! 🚀")
            return True
        else:
            print_error("Fix errors before running data collection")
            return False


def main():
    """Run full system diagnostic."""
    print_header("AVIATOR SYSTEM DIAGNOSTIC v3.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    diag = SystemDiagnostic()
    
    # Run all tests
    diag.test("Python Version", diag.check_python_version)
    diag.test("Required Files", diag.check_required_files)
    diag.test("Logger Fix", diag.check_logger_fix)
    diag.test("Batch Configuration", diag.check_batch_configuration)
    diag.test("Tesseract OCR", diag.check_tesseract)
    diag.test("Dependencies", diag.check_dependencies)
    diag.test("Database", diag.check_database)
    diag.test("Database Performance", diag.benchmark_database)
    diag.test("Logging System", diag.check_logging_system)
    diag.test("Performance Estimation", diag.estimate_performance)
    
    # Generate report
    success = diag.generate_report()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
