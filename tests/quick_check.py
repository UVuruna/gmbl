# quick_check.py
# Quick database checker for data.db and game_phase.db

import sqlite3
import sys


def check_data_db():
    """Check data.db readings."""
    print("\n" + "="*70)
    print(" DATA.DB - READINGS")
    print("="*70)
    
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM readings")
        total = cursor.fetchone()[0]
        print(f"\nTOTAL READINGS: {total}")
        
        if total == 0:
            print("No data yet!")
            conn.close()
            return
        
        # Per bookmaker
        print("\nPER BOOKMAKER:")
        cursor.execute("""
            SELECT bookmaker, COUNT(*) as count 
            FROM readings 
            GROUP BY bookmaker 
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} readings")
        
        # Phase distribution
        print("\nPHASE DISTRIBUTION:")
        cursor.execute("""
            SELECT game_phase, COUNT(*) as count 
            FROM readings 
            WHERE game_phase IS NOT NULL
            GROUP BY game_phase 
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        # First 10
        print("\n" + "-"*70)
        print("FIRST 10 READINGS:")
        print("-"*70)
        cursor.execute("""
            SELECT id, timestamp, bookmaker, score, game_phase 
            FROM readings 
            ORDER BY id ASC 
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"#{row[0]}: {row[2]} | {row[4]} | Score: {row[3]} | {row[1]}")
        
        # Last 10
        print("\n" + "-"*70)
        print("LAST 10 READINGS:")
        print("-"*70)
        cursor.execute("""
            SELECT id, timestamp, bookmaker, score, game_phase 
            FROM readings 
            ORDER BY id DESC 
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"#{row[0]}: {row[2]} | {row[4]} | Score: {row[3]} | {row[1]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Error reading data.db: {e}")


def check_game_phase_db():
    """Check game_phase.db colors."""
    print("\n" + "="*70)
    print(" GAME_PHASE.DB - RGB SAMPLES")
    print("="*70)
    
    try:
        conn = sqlite3.connect('game_phase.db')
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM colors")
        total = cursor.fetchone()[0]
        print(f"\nTOTAL RGB SAMPLES: {total}")
        
        if total == 0:
            print("No RGB data yet!")
            conn.close()
            return
        
        # Per bookmaker
        print("\nPER BOOKMAKER:")
        cursor.execute("""
            SELECT bookmaker, COUNT(*) as count 
            FROM colors 
            GROUP BY bookmaker 
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} samples")
        
        # Per phase
        print("\nPER PREDICTED PHASE:")
        cursor.execute("""
            SELECT predicted_phase, COUNT(*) as count,
                   ROUND(AVG(r), 1) as avg_r,
                   ROUND(AVG(g), 1) as avg_g,
                   ROUND(AVG(b), 1) as avg_b
            FROM colors 
            WHERE predicted_phase IS NOT NULL
            GROUP BY predicted_phase 
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} samples | RGB avg: ({row[2]}, {row[3]}, {row[4]})")
        
        # Last 10
        print("\n" + "-"*70)
        print("LAST 10 RGB SAMPLES:")
        print("-"*70)
        cursor.execute("""
            SELECT id, bookmaker, 
                   ROUND(r, 1) as r, ROUND(g, 1) as g, ROUND(b, 1) as b,
                   predicted_phase
            FROM colors 
            ORDER BY id DESC 
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"#{row[0]}: {row[1]} | RGB: ({row[2]}, {row[3]}, {row[4]}) | {row[5]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Error reading game_phase.db: {e}")


def main():
    print("\n" + "="*70)
    print(" AVIATOR DATABASE QUICK CHECK")
    print("="*70)
    
    # Check both databases
    check_data_db()
    check_game_phase_db()
    
    print("\n" + "="*70)
    print(" CHECK COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()