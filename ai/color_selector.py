import sqlite3

def main(database_name: str):
    conn = sqlite3.connect(f"{database_name}.db")
    cur = conn.cursor()

    # --- Čitanje poslednjih 10 zapisa ---
    cur.execute("SELECT timestamp, r, g, b FROM colors ORDER BY id")
    rows = cur.fetchall()

    print("\tPrvih 50 zapisa:")
    for row in rows[:50]:  # obrnut redosled da ide od starijih ka novijima
        timestamp, r, g, b = row
        print(f"{timestamp} | R: {r:.0f}, G: {g:.0f}, B: {b:.0f}")
    print('...')
    print("\tPoslednjih 50 zapisa:")
    for row in rows[-50:]:  # obrnut redosled da ide od starijih ka novijima
        timestamp, r, g, b = row
        print(f"{timestamp} | R: {r:.0f}, G: {g:.0f}, B: {b:.0f}")
        
    print(f"\n{len(rows):,.0f} ukupno zapisa u bazi.")
    print('...')

    conn.close()
    
if __name__ == "__main__":
    database_name = input("Unesi ime baze (default 'game_phase'): ") or "game_phase"
    main(database_name)
