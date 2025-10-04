# 📊 DATA COLLECTOR - Complete Guide

## 🎯 Overview

**`data_collector.py`** je jednostavan alat za prikupljanje podataka sa ekrana Aviator igre **bez ikakvog betting-a**. Fokusiran je isključivo na:

1. **OCR validaciju** - Provera tačnosti čitanja brojeva sa ekrana
2. **ML training data** - Prikupljanje RGB vrednosti za treniranje modela
3. **Phase detection testing** - Testiranje preciznosti GamePhase predikcije
4. **Debugging** - Analiza problema u real-time

---

## 🏗️ Arhitektura

### Dva Database-a:

#### 1. **`data.db`** - OCR Readings
Čuva sve očitane vrednosti sa ekrana:

| Kolona | Tip | Opis |
|--------|-----|------|
| `timestamp` | TEXT | Vreme očitavanja |
| `bookmaker` | TEXT | Ime bookmaker-a (BalkanBet, Mozzart, Soccer) |
| `score` | REAL | Očitani score (1.05, 2.35, itd.) |
| `game_phase` | TEXT | Detektovana faza (BETTING, SCORE_MID, ENDED, itd.) |
| `game_phase_value` | INTEGER | Numerička vrednost faze (0-5) |
| `my_money` | REAL | Stanje novca |
| `current_players` | INTEGER | Trenutno igra igrača |
| `total_players` | INTEGER | Ukupno igrača |
| `others_money` | REAL | Ukupni dobitak drugih igrača |

#### 2. **`game_phase.db`** - RGB Values
Čuva sirove RGB vrednosti za ML:

| Kolona | Tip | Opis |
|--------|-----|------|
| `timestamp` | TEXT | Vreme uzorka |
| `bookmaker` | TEXT | Ime bookmaker-a |
| `r` | REAL | Red channel (0-255) |
| `g` | REAL | Green channel (0-255) |
| `b` | REAL | Blue channel (0-255) |
| `predicted_phase` | TEXT | Predviđena faza modelom |
| `predicted_phase_value` | INTEGER | Numerička vrednost predviđene faze |

---

## 🚀 Korišćenje

### 1. **Pokretanje Data Collector-a**

```bash
python data_collector.py
```

### 2. **Interaktivni Setup**

Aplikacija će tražiti:

1. **Ime konfiguracije** (npr. `3_bookmakers_console`)
   - Mora postojati iz `main.py` setup-a
   
2. **Pozicija bookmaker-a:**
   - 1 = Left (BalkanBet)
   - 2 = Center (Mozzart)
   - 3 = Right (Soccer)

3. **Interval prikupljanja** (default: 0.2s)
   - 0.1s = 10 readings/second (brzo)
   - 0.2s = 5 readings/second (balans)
   - 0.5s = 2 readings/second (sporo, štedi resurse)

### 3. **Primer Session**

```
DATA COLLECTION SETUP
============================================================

Enter configuration name (e.g., '3_bookmakers_console'): 
Configuration: 3_bookmakers_console

Available positions:
1. Left
2. Center
3. Right

Select position (1-3): 2

✓ Loaded coordinates for Mozzart (Center)

Enter collection interval in seconds (default: 0.2): 
Interval: 0.2

============================================================
STARTING DATA COLLECTION
============================================================
Bookmaker: Mozzart
Interval: 0.2s (5 readings/second)
Databases: data.db, game_phase.db
Press Ctrl+C to stop
============================================================

[INFO] Starting data collection for Mozzart
[INFO] Collection interval: 0.2s
[INFO] ✓ data.db setup complete
[INFO] ✓ game_phase.db setup complete
[INFO] Progress: 50 readings, Success: 94.0%, Phase: SCORE_MID
[INFO] Progress: 100 readings, Success: 96.0%, Phase: BETTING
...
```

### 4. **Zaustavljanje**

Pritisni **`Ctrl+C`** za graceful shutdown:

```
CTRL+C DETECTED - Stopping data collection...
============================================================
DATA COLLECTION SUMMARY
============================================================
Total readings: 523
Successful: 502
Failed: 21
Success rate: 96.0%
✓ data.db closed
✓ game_phase.db closed
============================================================
```

---

## 📈 Analiza Podataka

### Korišćenje SQL Query-ja

Koristimo `data_analysis.sql` fajl sa prepared queries:

```bash
# Otvori data.db
sqlite3 data.db

# Učitaj queries iz fajla
.read data_analysis.sql
```

### Osnovne Analize

#### 1. **Total Readings**
```sql
SELECT COUNT(*) as total_readings FROM readings;
```

#### 2. **Phase Distribution**
```sql
SELECT 
    game_phase,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM readings), 2) as pct
FROM readings
WHERE game_phase IS NOT NULL
GROUP BY game_phase;
```

**Expected Output:**
```
game_phase    count   pct
------------  ------  -----
BETTING       120     23.0
SCORE_LOW     85      16.3
SCORE_MID     180     34.5
SCORE_HIGH    45      8.6
ENDED         60      11.5
LOADING       33      6.3
```

#### 3. **Validate Phase-Score Accuracy**
Provera da li OCR score odgovara detektovanoj fazi:

```sql
SELECT 
    timestamp,
    score,
    game_phase,
    CASE 
        WHEN game_phase = 'SCORE_LOW' AND (score < 1.0 OR score >= 2.0) THEN 'INVALID'
        WHEN game_phase = 'SCORE_MID' AND (score < 2.0 OR score >= 10.0) THEN 'INVALID'
        WHEN game_phase = 'SCORE_HIGH' AND score < 10.0 THEN 'INVALID'
        ELSE 'VALID'
    END as validation
FROM readings
WHERE score IS NOT NULL AND game_phase IN ('SCORE_LOW', 'SCORE_MID', 'SCORE_HIGH')
HAVING validation = 'INVALID'
LIMIT 20;
```

**Ako ima INVALID redova** → Problem sa predikcijom faze!

#### 4. **RGB Cluster Analysis**
```bash
sqlite3 game_phase.db
```

```sql
SELECT 
    predicted_phase,
    COUNT(*) as samples,
    ROUND(AVG(r), 1) as avg_r,
    ROUND(AVG(g), 1) as avg_g,
    ROUND(AVG(b), 1) as avg_b
FROM colors
GROUP BY predicted_phase;
```

**Expected Output:**
```
predicted_phase  samples  avg_r   avg_g   avg_b
---------------  -------  ------  ------  ------
BETTING          1250     60.2    60.5    60.8
SCORE_LOW        980      128.4   153.2   172.1
ENDED            720      87.6    5.1     23.0
SCORE_MID        1450     150.3   126.8   178.2
SCORE_HIGH       520      159.7   112.4   159.3
LOADING          380      49.0    42.3    43.4
```

---

## 🔍 Debugging Uobičajenih Problema

### Problem 1: Prevelik Broj `NULL` Vrednosti

**Simptom:**
```sql
SELECT COUNT(*) - COUNT(score) as missing FROM readings;
-- Result: 300+ missing
```

**Mogući uzroci:**
1. OCR regija nije pravilno podešena
2. Tesseract ne prepoznaje font
3. Prevelika brzina očitavanja (interval < 0.1s)

**Rešenje:**
1. Povećaj interval na 0.3s
2. Proveri koordinate u `bookmaker_coords.json`
3. Testir aj OCR sa `screen_reader.py` pojedinačno

### Problem 2: Phase Detection Ne Radi

**Simptom:**
```sql
SELECT game_phase, COUNT(*) FROM readings GROUP BY game_phase;
-- Result: Sve NULL
```

**Mogući uzroci:**
1. Model `game_phase_kmeans.pkl` ne postoji
2. Phase region nije dobro podešen
3. Model nije dobro treniran

**Rešenje:**
1. Proveri da li postoji `game_phase_kmeans.pkl`
2. Proveri RGB vrednosti:
```sql
SELECT MIN(r), MAX(r), AVG(r) FROM colors;
-- Ako je sve 0 ili 255 → Regija van ekrana
```

### Problem 3: SCORE_MID se Meša sa BETTING

**Simptom:**
```sql
-- Veliki broj INVALID validacija
SELECT COUNT(*) FROM readings 
WHERE game_phase = 'SCORE_MID' AND score < 2.0;
-- Result: 150+
```

**Dijagnoza:**
```sql
-- Proveri RGB vrednosti za BETTING vs SCORE_MID
SELECT 
    predicted_phase,
    AVG(r) as r, AVG(g) as g, AVG(b) as b,
    (MAX(r) - MIN(r)) as r_range
FROM colors
WHERE predicted_phase IN ('BETTING', 'SCORE_MID')
GROUP BY predicted_phase;
```

**Ako se RGB ranges preklapaju** → Potreban bolji model ili dodatna validacija!

---

## 🛠️ Export Podataka za ML Training

### 1. **Export RGB Data (CSV)**

```bash
sqlite3 game_phase.db
```

```sql
.mode csv
.output rgb_training_data.csv
SELECT r, g, b, predicted_phase_value as label
FROM colors
WHERE predicted_phase_value IS NOT NULL
ORDER BY RANDOM();
.quit
```

Rezultat: `rgb_training_data.csv` sa kolonama `r,g,b,label`

### 2. **Balanced Dataset (Jednako Samples po Fazi)**

Ako imaš više SCORE_MID nego BETTING samples, treba balansirati:

```sql
.output rgb_balanced.csv
WITH min_count AS (
    SELECT MIN(cnt) as min_samples
    FROM (
        SELECT COUNT(*) as cnt
        FROM colors
        GROUP BY predicted_phase_value
    )
)
SELECT r, g, b, predicted_phase_value as label
FROM (
    SELECT 
        r, g, b, predicted_phase_value,
        ROW_NUMBER() OVER (PARTITION BY predicted_phase_value ORDER BY RANDOM()) as rn
    FROM colors
)
WHERE rn <= (SELECT min_samples FROM min_count);
.quit
```

### 3. **Python Script za Re-training**

```python
import pandas as pd
import pickle
from sklearn.cluster import KMeans

# Load data
df = pd.read_csv('rgb_training_data.csv')
X = df[['r', 'g', 'b']].values

# Train new model
kmeans = KMeans(n_clusters=6, random_state=42, n_init=100)
kmeans.fit(X)

# Save model
with open('game_phase_kmeans_v2.pkl', 'wb') as f:
    pickle.dump(kmeans, f)

print("Model saved as game_phase_kmeans_v2.pkl")
```

---

## 📊 Real-Time Monitoring

Dok collector radi, možeš pratiti podatke u real-time:

### Terminal 1: Running Collector
```bash
python data_collector.py
```

### Terminal 2: Live Monitoring
```bash
watch -n 2 "sqlite3 data.db 'SELECT COUNT(*) as total, 
    SUM(CASE WHEN score IS NOT NULL THEN 1 ELSE 0 END) as with_score,
    MAX(timestamp) as last_reading FROM readings'"
```

Ili sa Python skriptom:

```python
# monitor.py
import sqlite3
import time

while True:
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            game_phase,
            MAX(timestamp) as last
        FROM readings
        WHERE timestamp > datetime('now', '-10 seconds')
        GROUP BY game_phase
    """)
    
    print("\n" + "="*50)
    for row in cursor.fetchall():
        print(f"{row[1]}: {row[0]} readings")
    
    conn.close()
    time.sleep(2)
```

---

## 🎯 Best Practices

### 1. **Collection Intervals**
- **0.1s** - Maksimalna brzina, veliki CPU usage, može propusti readings
- **0.2s** - Optimalno za većinu slučajeva, balans brzine i preciznosti
- **0.5s** - Štedi resurse, dovoljno za training data

### 2. **Session Duration**
- **5-10 minuta** - Dovoljno za basic testing (~1500-3000 readings)
- **30-60 minuta** - Za kvalitetne training data (~9000-18000 readings)
- **2-3 sata** - Za production-level dataset

### 3. **Multiple Sessions**
Pokreni za svaki bookmaker odvojeno:
```bash
# Session 1 - BalkanBet
python data_collector.py  # Select position 1

# Session 2 - Mozzart
python data_collector.py  # Select position 2

# Session 3 - Soccer
python data_collector.py  # Select position 3
```

Svaka sesija dodaje podatke u **iste** baze, dakle konačno imaš combined dataset!

---

## 🐛 Troubleshooting

### Error: "Configuration not found"
**Rešenje:** Pokreni `main.py` prvo da kreiraš koordinate

### Error: "Table already exists"
**Rešenje:** Normalno je, tabele se prave samo prvi put

### Error: "Cannot read screen"
**Rešenje:** Proveri da li je Aviator igra vidljiva na ekranu

### Previše INVALID readings
**Rešenje:** 
1. Smanji interval na 0.3s
2. Proveri da li su koordinate OK
3. Možda model treba retrenirati

---

## 📁 Output Files

Nakon prikupljanja imaš:

```
your_project/
├── data.db              # OCR readings database
├── game_phase.db        # RGB values database
└── logs/
    └── aviator.log      # Detailed logs
```

**Database Sizes** (estimate):
- **data.db:** ~100KB za 1000 readings
- **game_phase.db:** ~50KB za 1000 samples
- Za 1 sat na 0.2s interval → ~18K readings → ~2MB total

---

## 🎓 Next Steps

Nakon prikupljanja podataka:

1. **Validiraj tačnost:**
   ```sql
   -- Proveri INVALID phase-score kombinacije
   .read data_analysis.sql
   -- Run query #5
   ```

2. **Analiziraj RGB distribuciju:**
   ```sql
   -- Proveri da li su klasteri jasni
   .read data_analysis.sql
   -- Run query #13
   ```

3. **Export za ML:**
   - Ako je sve OK → Export balanced dataset
   - Retrain model sa novim podacima
   - Replace `game_phase_kmeans.pkl`

4. **Test novi model:**
   - Pokreni collector ponovo
   - Uporedi INVALID count pre/posle

---

**Autor:** Aviator ML Team  
**Verzija:** 1.0  
**Datum:** 2025-10-04