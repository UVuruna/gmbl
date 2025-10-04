# database_optimizer.py
# VERSION: 3.0
# CHANGES: Database optimization and maintenance tool

"""
Database Optimizer for Aviator Data Collector

Optimizes SQLite database for maximum performance:
- Enable WAL mode
- Optimize PRAGMA settings
- Create indexes
- Vacuum database
- Analyze statistics
- Check integrity
"""

import sqlite3
import os
import time
from typing import Dict, List
import argparse


class DatabaseOptimizer:
    """Optimize SQLite database for maximum performance."""
    
    def __init__(self, db_path: str = 'aviator.db'):
        self.db_path = db_path
        self.conn = None
        self.results = []
    
    def connect(self):
        """Connect to database."""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Database not found: {self.db_path}")
                return False
            
            self.conn = sqlite3.connect(self.db_path)
            print(f"✅ Connected to: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def get_current_settings(self) -> Dict:
        """Get current PRAGMA settings."""
        cursor = self.conn.cursor()
        
        settings = {}
        pragmas = [
            'journal_mode',
            'synchronous',
            'cache_size',
            'page_size',
            'temp_store',
            'locking_mode',
            'auto_vacuum'
        ]
        
        for pragma in pragmas:
            cursor.execute(f"PRAGMA {pragma}")
            settings[pragma] = cursor.fetchone()[0]
        
        return settings
    
    def print_settings(self, settings: Dict, label: str = "Settings"):
        """Print PRAGMA settings."""
        print(f"\n{label}:")
        for key, value in settings.items():
            print(f"   {key:20s} = {value}")
    
    def enable_wal_mode(self) -> bool:
        """Enable Write-Ahead Logging for better concurrency."""
        try:
            print("\n⚙️  Enabling WAL mode...")
            cursor = self.conn.cursor()
            
            # Check current mode
            cursor.execute("PRAGMA journal_mode")
            current_mode = cursor.fetchone()[0]
            
            if current_mode.upper() == 'WAL':
                print("   ✅ WAL mode already enabled")
                return True
            
            # Enable WAL
            cursor.execute("PRAGMA journal_mode=WAL")
            new_mode = cursor.fetchone()[0]
            
            if new_mode.upper() == 'WAL':
                print(f"   ✅ Changed from {current_mode} to WAL")
                self.results.append("Enabled WAL mode")
                return True
            else:
                print(f"   ❌ Failed to enable WAL (still {new_mode})")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def optimize_pragmas(self) -> bool:
        """Set optimal PRAGMA settings."""
        try:
            print("\n⚙️  Optimizing PRAGMA settings...")
            cursor = self.conn.cursor()
            
            optimizations = [
                ("synchronous", "NORMAL", "Balance between safety and speed"),
                ("cache_size", "-64000", "64MB cache for better performance"),
                ("temp_store", "MEMORY", "Use memory for temporary tables"),
                ("page_size", "4096", "Optimal page size for most systems"),
            ]
            
            for pragma, value, description in optimizations:
                try:
                    cursor.execute(f"PRAGMA {pragma} = {value}")
                    print(f"   ✅ {pragma:20s} → {value:10s} ({description})")
                    self.results.append(f"Set {pragma} to {value}")
                except Exception as e:
                    print(f"   ⚠️  {pragma:20s} → Failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """Create indexes for better query performance."""
        try:
            print("\n⚙️  Creating indexes...")
            cursor = self.conn.cursor()
            
            indexes = [
                ("idx_rounds_bookmaker", "rounds", "bookmaker"),
                ("idx_rounds_timestamp", "rounds", "timestamp"),
                ("idx_rounds_score", "rounds", "score"),
                ("idx_snapshots_round", "snapshots", "round_ID"),
                ("idx_earnings_round", "earnings", "round_ID"),
            ]
            
            for index_name, table, column in indexes:
                try:
                    # Check if index exists
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name=?
                    """, (index_name,))
                    
                    if cursor.fetchone():
                        print(f"   ✓ {index_name:30s} (already exists)")
                    else:
                        # Create index
                        cursor.execute(f"""
                            CREATE INDEX {index_name} 
                            ON {table} ({column})
                        """)
                        print(f"   ✅ {index_name:30s} created on {table}.{column}")
                        self.results.append(f"Created index {index_name}")
                        
                except Exception as e:
                    print(f"   ⚠️  {index_name:30s} → Failed: {e}")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def vacuum_database(self) -> bool:
        """Vacuum database to reclaim space and optimize."""
        try:
            print("\n⚙️  Vacuuming database...")
            
            # Get size before
            size_before = os.path.getsize(self.db_path)
            
            cursor = self.conn.cursor()
            start_time = time.time()
            
            cursor.execute("VACUUM")
            
            elapsed = time.time() - start_time
            size_after = os.path.getsize(self.db_path)
            
            saved = size_before - size_after
            saved_mb = saved / (1024**2)
            
            print(f"   ✅ Vacuum completed in {elapsed:.1f}s")
            print(f"   📦 Size before:  {size_before / (1024**2):.2f} MB")
            print(f"   📦 Size after:   {size_after / (1024**2):.2f} MB")
            if saved > 0:
                print(f"   💾 Space saved:  {saved_mb:.2f} MB")
                self.results.append(f"Reclaimed {saved_mb:.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def analyze_database(self) -> bool:
        """Analyze database statistics for query optimization."""
        try:
            print("\n⚙️  Analyzing database statistics...")
            cursor = self.conn.cursor()
            
            start_time = time.time()
            cursor.execute("ANALYZE")
            elapsed = time.time() - start_time
            
            print(f"   ✅ Analysis completed in {elapsed:.1f}s")
            self.results.append("Updated statistics")
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def check_integrity(self) -> bool:
        """Check database integrity."""
        try:
            print("\n⚙️  Checking database integrity...")
            cursor = self.conn.cursor()
            
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result == 'ok':
                print("   ✅ Database integrity OK")
                return True
            else:
                print(f"   ❌ Integrity check failed: {result}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def get_table_info(self) -> Dict:
        """Get information about tables."""
        cursor = self.conn.cursor()
        
        info = {}
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            info[table] = count
        
        return info
    
    def benchmark_queries(self) -> Dict:
        """Benchmark common queries."""
        try:
            print("\n⚙️  Benchmarking queries...")
            cursor = self.conn.cursor()
            
            benchmarks = {}
            
            queries = [
                ("Count all rounds", "SELECT COUNT(*) FROM rounds"),
                ("Recent rounds", "SELECT * FROM rounds ORDER BY timestamp DESC LIMIT 100"),
                ("Bookmaker filter", "SELECT * FROM rounds WHERE bookmaker = 'BalkanBet' LIMIT 100"),
                ("Join with earnings", "SELECT r.*, e.* FROM rounds r JOIN earnings e ON r.round_ID = e.round_ID LIMIT 100"),
            ]
            
            for name, query in queries:
                start = time.time()
                cursor.execute(query)
                cursor.fetchall()
                elapsed = (time.time() - start) * 1000  # ms
                
                benchmarks[name] = elapsed
                print(f"   {name:25s} {elapsed:6.1f}ms")
            
            return benchmarks
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {}
    
    def print_summary(self):
        """Print optimization summary."""
        print("\n" + "="*70)
        print("OPTIMIZATION SUMMARY".center(70))
        print("="*70)
        
        if self.results:
            print("\n✅ Optimizations applied:")
            for result in self.results:
                print(f"   • {result}")
        else:
            print("\n⚠️  No optimizations were needed")
        
        print("\n" + "="*70)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Optimize Aviator database')
    parser.add_argument('--db', default='aviator.db', help='Database path')
    parser.add_argument('--skip-vacuum', action='store_true', help='Skip VACUUM (faster)')
    parser.add_argument('--benchmark', action='store_true', help='Run query benchmarks')
    
    args = parser.parse_args()
    
    print("="*70)
    print("AVIATOR DATABASE OPTIMIZER v3.0".center(70))
    print("="*70)
    
    optimizer = DatabaseOptimizer(args.db)
    
    if not optimizer.connect():
        return 1
    
    # Show current settings
    current = optimizer.get_current_settings()
    optimizer.print_settings(current, "Current Settings")
    
    # Show table info
    tables = optimizer.get_table_info()
    print("\nDatabase Tables:")
    for table, count in tables.items():
        print(f"   {table:20s} {count:,} records")
    
    # Run optimizations
    optimizer.check_integrity()
    optimizer.enable_wal_mode()
    optimizer.optimize_pragmas()
    optimizer.create_indexes()
    
    if not args.skip_vacuum:
        optimizer.vacuum_database()
    else:
        print("\n⚠️  Skipping VACUUM (--skip-vacuum)")
    
    optimizer.analyze_database()
    
    # Show new settings
    new = optimizer.get_current_settings()
    optimizer.print_settings(new, "Optimized Settings")
    
    # Benchmark if requested
    if args.benchmark:
        optimizer.benchmark_queries()
    
    # Summary
    optimizer.print_summary()
    
    optimizer.close()
    
    print("\n✅ Optimization complete!")
    print("💡 Tip: Run this optimizer weekly for best performance\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
