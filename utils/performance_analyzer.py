# performance_analyzer.py
# VERSION: 3.0
# CHANGES: Database performance analysis and comparison tool

"""
Performance Analyzer for Aviator Data Collector

Analyzes database performance and collection statistics:
- Records per hour/day
- Data collection efficiency  
- Bookmaker distribution
- Timeline analysis
- Comparison with expected throughput
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import argparse


class PerformanceAnalyzer:
    """Analyze data collection performance from database."""
    
    def __init__(self, db_path: str = 'aviator.db'):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✅ Connected to: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def get_basic_stats(self) -> Dict:
        """Get basic database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM rounds")
        stats['total_records'] = cursor.fetchone()[0]
        
        # Unique bookmakers
        cursor.execute("SELECT COUNT(DISTINCT bookmaker) FROM rounds")
        stats['unique_bookmakers'] = cursor.fetchone()[0]
        
        # Bookmaker distribution
        cursor.execute("""
            SELECT bookmaker, COUNT(*) as count
            FROM rounds
            GROUP BY bookmaker
            ORDER BY count DESC
        """)
        stats['bookmaker_distribution'] = cursor.fetchall()
        
        # Time range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM rounds")
        min_time, max_time = cursor.fetchone()
        
        if min_time and max_time:
            stats['first_record'] = datetime.fromtimestamp(min_time)
            stats['last_record'] = datetime.fromtimestamp(max_time)
            stats['duration_hours'] = (max_time - min_time) / 3600
        
        # Database size
        cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
        stats['db_size_bytes'] = cursor.fetchone()[0]
        stats['db_size_mb'] = stats['db_size_bytes'] / (1024**2)
        
        return stats
    
    def analyze_timeline(self, hours: int = 24) -> pd.DataFrame:
        """Analyze records per hour."""
        cursor = self.conn.cursor()
        
        # Get records with timestamps
        cursor.execute("""
            SELECT 
                datetime(timestamp, 'unixepoch', 'localtime') as dt,
                bookmaker,
                score
            FROM rounds
            ORDER BY timestamp DESC
            LIMIT ?
        """, (hours * 3600 * 10,))  # Estimate 10 records per second max
        
        df = pd.DataFrame(cursor.fetchall(), columns=['datetime', 'bookmaker', 'score'])
        
        if df.empty:
            return df
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.floor('H')
        
        # Count per hour
        hourly = df.groupby(['hour', 'bookmaker']).size().reset_index(name='count')
        
        return hourly
    
    def calculate_throughput(self) -> Dict:
        """Calculate actual throughput."""
        stats = self.get_basic_stats()
        
        if stats['total_records'] == 0:
            return {'error': 'No records in database'}
        
        duration_hours = stats.get('duration_hours', 0)
        
        if duration_hours == 0:
            return {'error': 'Cannot calculate throughput (no time range)'}
        
        throughput = {
            'total_records': stats['total_records'],
            'duration_hours': duration_hours,
            'records_per_hour': stats['total_records'] / duration_hours,
            'records_per_second': stats['total_records'] / (duration_hours * 3600),
            'num_bookmakers': stats['unique_bookmakers']
        }
        
        # Expected throughput (assuming 0.2s interval)
        expected_per_sec = stats['unique_bookmakers'] / 0.2
        expected_per_hour = expected_per_sec * 3600
        
        throughput['expected_per_second'] = expected_per_sec
        throughput['expected_per_hour'] = expected_per_hour
        throughput['efficiency'] = (throughput['records_per_second'] / expected_per_sec) * 100
        
        return throughput
    
    def analyze_score_distribution(self) -> Dict:
        """Analyze game score distribution."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(score) as avg_score,
                MIN(score) as min_score,
                MAX(score) as max_score,
                COUNT(CASE WHEN score >= 2.0 THEN 1 END) as high_scores,
                COUNT(CASE WHEN score < 2.0 THEN 1 END) as low_scores
            FROM rounds
        """)
        
        result = cursor.fetchone()
        
        return {
            'avg_score': result[0],
            'min_score': result[1],
            'max_score': result[2],
            'high_scores': result[3],  # >= 2.0x
            'low_scores': result[4],   # < 2.0x
            'high_percentage': (result[3] / (result[3] + result[4]) * 100) if result[3] else 0
        }
    
    def compare_with_expectations(self, num_bookmakers: int, interval: float = 0.2) -> Dict:
        """Compare actual performance with expectations."""
        throughput = self.calculate_throughput()
        
        if 'error' in throughput:
            return throughput
        
        expected_per_sec = num_bookmakers / interval
        expected_per_hour = expected_per_sec * 3600
        
        actual_per_sec = throughput['records_per_second']
        actual_per_hour = throughput['records_per_hour']
        
        comparison = {
            'expected': {
                'per_second': expected_per_sec,
                'per_hour': expected_per_hour,
                'per_day': expected_per_hour * 24
            },
            'actual': {
                'per_second': actual_per_sec,
                'per_hour': actual_per_hour,
                'per_day': actual_per_hour * 24
            },
            'efficiency': {
                'percentage': (actual_per_sec / expected_per_sec * 100),
                'lost_records_per_hour': expected_per_hour - actual_per_hour,
                'lost_records_per_day': (expected_per_hour - actual_per_hour) * 24
            }
        }
        
        return comparison
    
    def print_report(self, detailed: bool = False):
        """Print comprehensive performance report."""
        print("\n" + "="*70)
        print("AVIATOR DATA COLLECTION - PERFORMANCE REPORT".center(70))
        print("="*70)
        
        # Basic stats
        stats = self.get_basic_stats()
        
        print(f"\n📊 BASIC STATISTICS")
        print(f"   Total records:        {stats['total_records']:,}")
        print(f"   Database size:        {stats['db_size_mb']:.2f} MB")
        print(f"   Unique bookmakers:    {stats['unique_bookmakers']}")
        
        if 'first_record' in stats:
            print(f"   First record:         {stats['first_record'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Last record:          {stats['last_record'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Duration:             {stats['duration_hours']:.2f} hours")
        
        # Bookmaker distribution
        print(f"\n📈 BOOKMAKER DISTRIBUTION")
        for bookmaker, count in stats['bookmaker_distribution']:
            percentage = (count / stats['total_records'] * 100) if stats['total_records'] > 0 else 0
            print(f"   {bookmaker:20s} {count:8,} ({percentage:5.1f}%)")
        
        # Throughput
        throughput = self.calculate_throughput()
        
        if 'error' not in throughput:
            print(f"\n⚡ THROUGHPUT")
            print(f"   Records/second:       {throughput['records_per_second']:.2f}")
            print(f"   Records/hour:         {throughput['records_per_hour']:,.0f}")
            print(f"   Records/day:          {throughput['records_per_hour'] * 24:,.0f}")
            print(f"\n   Expected/second:      {throughput['expected_per_second']:.2f}")
            print(f"   Expected/hour:        {throughput['expected_per_hour']:,.0f}")
            print(f"   Efficiency:           {throughput['efficiency']:.1f}%")
            
            # Efficiency indicator
            if throughput['efficiency'] >= 95:
                status = "🟢 EXCELLENT"
            elif throughput['efficiency'] >= 80:
                status = "🟡 GOOD"
            elif throughput['efficiency'] >= 60:
                status = "🟠 MODERATE"
            else:
                status = "🔴 POOR"
            
            print(f"   Status:               {status}")
        
        # Score distribution
        scores = self.analyze_score_distribution()
        
        if scores['avg_score']:
            print(f"\n🎲 SCORE ANALYSIS")
            print(f"   Average score:        {scores['avg_score']:.2f}x")
            print(f"   Min score:            {scores['min_score']:.2f}x")
            print(f"   Max score:            {scores['max_score']:.2f}x")
            print(f"   High scores (≥2.0x):  {scores['high_scores']:,} ({scores['high_percentage']:.1f}%)")
            print(f"   Low scores (<2.0x):   {scores['low_scores']:,} ({100-scores['high_percentage']:.1f}%)")
        
        # Detailed timeline
        if detailed and stats['total_records'] > 0:
            print(f"\n📅 HOURLY BREAKDOWN (Last 24 hours)")
            timeline = self.analyze_timeline(hours=24)
            
            if not timeline.empty:
                pivot = timeline.pivot_table(
                    index='hour',
                    columns='bookmaker',
                    values='count',
                    fill_value=0
                )
                
                print(pivot.to_string())
        
        # Comparison with expectations
        if stats['unique_bookmakers'] > 0:
            comparison = self.compare_with_expectations(stats['unique_bookmakers'])
            
            if 'error' not in comparison:
                print(f"\n🎯 PERFORMANCE COMPARISON")
                print(f"   Expected throughput:  {comparison['expected']['per_hour']:,.0f} records/hour")
                print(f"   Actual throughput:    {comparison['actual']['per_hour']:,.0f} records/hour")
                print(f"   Efficiency:           {comparison['efficiency']['percentage']:.1f}%")
                
                if comparison['efficiency']['lost_records_per_hour'] > 0:
                    print(f"   ⚠️  Lost data:         {comparison['efficiency']['lost_records_per_hour']:,.0f} records/hour")
                    print(f"   ⚠️  Lost data:         {comparison['efficiency']['lost_records_per_day']:,.0f} records/day")
        
        print("\n" + "="*70 + "\n")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze Aviator data collection performance')
    parser.add_argument('--db', default='aviator.db', help='Database path')
    parser.add_argument('--detailed', action='store_true', help='Show detailed timeline')
    
    args = parser.parse_args()
    
    analyzer = PerformanceAnalyzer(args.db)
    
    if analyzer.connect():
        analyzer.print_report(detailed=args.detailed)
        analyzer.close()
    else:
        print("❌ Failed to analyze database")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
