# analyze_data.py
# VERSION: 1.0
# PURPOSE: Analyze collected data from data.db and game_phase.db

"""
Data Analysis Helper for Aviator Data Collector

Quick analysis of collected data with visualization and reports.
"""

import sqlite3
import pandas as pd
import sys
from datetime import datetime
from typing import Dict, List


class DataAnalyzer:
    """Analyze data from data collector databases."""
    
    def __init__(self, data_db='data.db', phase_db='game_phase.db'):
        self.data_db = data_db
        self.phase_db = phase_db
    
    def print_header(self, title: str):
        """Print formatted header."""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def print_table(self, df: pd.DataFrame, title: str = None):
        """Print dataframe as formatted table."""
        if title:
            print(f"\n{title}:")
        print(df.to_string(index=False))
    
    def get_basic_stats(self):
        """Get basic statistics from data.db."""
        self.print_header("BASIC STATISTICS - data.db")
        
        conn = sqlite3.connect(self.data_db)
        
        # Total readings
        query = """
            SELECT 
                COUNT(*) as total_readings,
                COUNT(DISTINCT bookmaker) as bookmakers,
                MIN(timestamp) as first_reading,
                MAX(timestamp) as last_reading,
                COUNT(score) as readings_with_score,
                COUNT(game_phase) as readings_with_phase
            FROM readings
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df, "Overview")
        
        # Calculate duration
        if df['first_reading'].iloc[0] and df['last_reading'].iloc[0]:
            first = datetime.fromisoformat(df['first_reading'].iloc[0])
            last = datetime.fromisoformat(df['last_reading'].iloc[0])
            duration = (last - first).total_seconds()
            print(f"\nCollection Duration: {duration/60:.1f} minutes ({duration:.0f} seconds)")
            print(f"Average Rate: {df['total_readings'].iloc[0] / duration:.2f} readings/second")
        
        conn.close()
    
    def get_phase_distribution(self):
        """Analyze game phase distribution."""
        self.print_header("GAME PHASE DISTRIBUTION")
        
        conn = sqlite3.connect(self.data_db)
        
        query = """
            SELECT 
                game_phase,
                game_phase_value,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM readings WHERE game_phase IS NOT NULL), 2) as percentage
            FROM readings
            WHERE game_phase IS NOT NULL
            GROUP BY game_phase, game_phase_value
            ORDER BY count DESC
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df)
        
        conn.close()
    
    def get_data_quality(self):
        """Check data quality - missing values."""
        self.print_header("DATA QUALITY REPORT")
        
        conn = sqlite3.connect(self.data_db)
        
        query = """
            SELECT 
                'score' as field,
                COUNT(*) as total,
                COUNT(score) as not_null,
                COUNT(*) - COUNT(score) as missing,
                ROUND((COUNT(score) * 100.0 / COUNT(*)), 2) as completeness_pct
            FROM readings
            UNION ALL
            SELECT 
                'game_phase',
                COUNT(*),
                COUNT(game_phase),
                COUNT(*) - COUNT(game_phase),
                ROUND((COUNT(game_phase) * 100.0 / COUNT(*)), 2)
            FROM readings
            UNION ALL
            SELECT 
                'my_money',
                COUNT(*),
                COUNT(my_money),
                COUNT(*) - COUNT(my_money),
                ROUND((COUNT(my_money) * 100.0 / COUNT(*)), 2)
            FROM readings
            UNION ALL
            SELECT 
                'current_players',
                COUNT(*),
                COUNT(current_players),
                COUNT(*) - COUNT(current_players),
                ROUND((COUNT(current_players) * 100.0 / COUNT(*)), 2)
            FROM readings
            UNION ALL
            SELECT 
                'total_players',
                COUNT(*),
                COUNT(total_players),
                COUNT(*) - COUNT(total_players),
                ROUND((COUNT(total_players) * 100.0 / COUNT(*)), 2)
            FROM readings
            UNION ALL
            SELECT 
                'others_money',
                COUNT(*),
                COUNT(others_money),
                COUNT(*) - COUNT(others_money),
                ROUND((COUNT(others_money) * 100.0 / COUNT(*)), 2)
            FROM readings
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df)
        
        # Warning for low completeness
        print("\nWARNINGS:")
        low_quality = df[df['completeness_pct'] < 80]
        if len(low_quality) > 0:
            for _, row in low_quality.iterrows():
                print(f"  ⚠ {row['field']}: Only {row['completeness_pct']}% complete!")
        else:
            print("  ✓ All fields have >80% completeness")
        
        conn.close()
    
    def check_phase_score_accuracy(self):
        """Check if OCR score matches predicted phase."""
        self.print_header("PHASE-SCORE ACCURACY CHECK")
        
        conn = sqlite3.connect(self.data_db)
        
        query = """
            SELECT 
                game_phase,
                COUNT(*) as total,
                SUM(CASE 
                    WHEN game_phase = 'SCORE_LOW' AND (score >= 1.0 AND score < 2.0) THEN 1
                    WHEN game_phase = 'SCORE_MID' AND (score >= 2.0 AND score < 10.0) THEN 1
                    WHEN game_phase = 'SCORE_HIGH' AND score >= 10.0 THEN 1
                    ELSE 0
                END) as valid,
                SUM(CASE 
                    WHEN game_phase = 'SCORE_LOW' AND (score < 1.0 OR score >= 2.0) THEN 1
                    WHEN game_phase = 'SCORE_MID' AND (score < 2.0 OR score >= 10.0) THEN 1
                    WHEN game_phase = 'SCORE_HIGH' AND score < 10.0 THEN 1
                    ELSE 0
                END) as invalid,
                ROUND(
                    SUM(CASE 
                        WHEN game_phase = 'SCORE_LOW' AND (score >= 1.0 AND score < 2.0) THEN 1
                        WHEN game_phase = 'SCORE_MID' AND (score >= 2.0 AND score < 10.0) THEN 1
                        WHEN game_phase = 'SCORE_HIGH' AND score >= 10.0 THEN 1
                        ELSE 0
                    END) * 100.0 / COUNT(*), 2
                ) as accuracy_pct
            FROM readings
            WHERE score IS NOT NULL AND game_phase IN ('SCORE_LOW', 'SCORE_MID', 'SCORE_HIGH')
            GROUP BY game_phase
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df)
        
        # Show some invalid examples
        if df['invalid'].sum() > 0:
            print("\nSample INVALID Readings:")
            query_invalid = """
                SELECT 
                    timestamp,
                    bookmaker,
                    score,
                    game_phase
                FROM readings
                WHERE score IS NOT NULL AND game_phase IN ('SCORE_LOW', 'SCORE_MID', 'SCORE_HIGH')
                AND (
                    (game_phase = 'SCORE_LOW' AND (score < 1.0 OR score >= 2.0)) OR
                    (game_phase = 'SCORE_MID' AND (score < 2.0 OR score >= 10.0)) OR
                    (game_phase = 'SCORE_HIGH' AND score < 10.0)
                )
                ORDER BY timestamp DESC
                LIMIT 10
            """
            df_invalid = pd.read_sql_query(query_invalid, conn)
            self.print_table(df_invalid)
        else:
            print("\n  ✓ No invalid phase-score combinations found!")
        
        conn.close()
    
    def get_rgb_analysis(self):
        """Analyze RGB cluster distribution."""
        self.print_header("RGB CLUSTER ANALYSIS - game_phase.db")
        
        conn = sqlite3.connect(self.phase_db)
        
        query = """
            SELECT 
                predicted_phase,
                predicted_phase_value,
                COUNT(*) as samples,
                ROUND(AVG(r), 2) as avg_r,
                ROUND(AVG(g), 2) as avg_g,
                ROUND(AVG(b), 2) as avg_b,
                ROUND(MIN(r), 2) as min_r,
                ROUND(MAX(r), 2) as max_r,
                ROUND(MAX(r) - MIN(r), 2) as r_range
            FROM colors
            WHERE predicted_phase IS NOT NULL
            GROUP BY predicted_phase, predicted_phase_value
            ORDER BY predicted_phase_value
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df)
        
        # Check for potential cluster overlap
        print("\nCluster Quality Assessment:")
        print(f"  Average R range: {df['r_range'].mean():.1f}")
        if df['r_range'].mean() > 50:
            print("  ⚠ Large RGB ranges detected - clusters may overlap!")
            print("  → Consider retraining model with more samples")
        else:
            print("  ✓ RGB ranges look good - clusters are well-defined")
        
        conn.close()
    
    def get_score_statistics(self):
        """Get score statistics by phase."""
        self.print_header("SCORE STATISTICS BY PHASE")
        
        conn = sqlite3.connect(self.data_db)
        
        query = """
            SELECT 
                game_phase,
                COUNT(score) as readings,
                ROUND(MIN(score), 2) as min_score,
                ROUND(MAX(score), 2) as max_score,
                ROUND(AVG(score), 2) as avg_score
            FROM readings
            WHERE score IS NOT NULL
            GROUP BY game_phase
            ORDER BY avg_score
        """
        
        df = pd.read_sql_query(query, conn)
        self.print_table(df)
        
        conn.close()
    
    def export_rgb_csv(self, filename='rgb_export.csv'):
        """Export RGB data for ML training."""
        self.print_header("EXPORTING RGB DATA")
        
        conn = sqlite3.connect(self.phase_db)
        
        query = """
            SELECT 
                r, g, b, predicted_phase_value as label
            FROM colors
            WHERE predicted_phase_value IS NOT NULL
            ORDER BY RANDOM()
        """
        
        df = pd.read_sql_query(query, conn)
        df.to_csv(filename, index=False)
        
        print(f"✓ Exported {len(df)} samples to '{filename}'")
        print(f"\nLabel distribution:")
        print(df['label'].value_counts().sort_index())
        
        conn.close()
    
    def generate_full_report(self):
        """Generate complete analysis report."""
        print("\n" + "="*70)
        print("  AVIATOR DATA COLLECTION - FULL ANALYSIS REPORT")
        print("  " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("="*70)
        
        try:
            self.get_basic_stats()
            self.get_data_quality()
            self.get_phase_distribution()
            self.check_phase_score_accuracy()
            self.get_score_statistics()
            self.get_rgb_analysis()
            
            print("\n" + "="*70)
            print("  REPORT COMPLETE")
            print("="*70 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error generating report: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analyze_data.py report          - Generate full report")
        print("  python analyze_data.py stats           - Basic statistics only")
        print("  python analyze_data.py quality         - Data quality check")
        print("  python analyze_data.py accuracy        - Phase-score accuracy")
        print("  python analyze_data.py rgb             - RGB cluster analysis")
        print("  python analyze_data.py export [file]   - Export RGB to CSV")
        sys.exit(1)
    
    analyzer = DataAnalyzer()
    command = sys.argv[1].lower()
    
    try:
        if command == 'report':
            analyzer.generate_full_report()
        elif command == 'stats':
            analyzer.get_basic_stats()
        elif command == 'quality':
            analyzer.get_data_quality()
        elif command == 'accuracy':
            analyzer.check_phase_score_accuracy()
        elif command == 'rgb':
            analyzer.get_rgb_analysis()
        elif command == 'export':
            filename = sys.argv[2] if len(sys.argv) > 2 else 'rgb_export.csv'
            analyzer.export_rgb_csv(filename)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n❌ Database not found: {e}")
        print("Make sure data_collector.py has been run first!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()