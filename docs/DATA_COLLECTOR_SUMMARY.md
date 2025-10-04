# 📊 DATA COLLECTION - Quick Start Guide

## 🎯 Svrha

**Data Collector** je odvojen sistem od `main.py` koji:
- ✅ **NE radi betove**
- ✅ **NE koristi multiprocessing**
- ✅ **SAMO čita podatke sa ekrana** i upisuje u bazu
- ✅ Služi za **validaciju OCR-a** i **treniranje ML modela**

---

## 📁 Novi Fajlovi

### 1. **`data_collector.py`** - Glavni program
Prikuplja podatke sa ekrana na svakih X sekundi i upisuje u baze.

### 2. **`analyze_data.py`** - Analiza helper
Brza analiza prikupljenih podataka sa izveštajima.

### 3. **`data_analysis.sql`** - SQL queries
Pripremljeni SQL queries za detaljnu analizu.

### 4. **`DATA_COLLECTOR_README.md`** - Potpuna dokumentacija
Kompletan guide sa svim detaljima.

---

## 🚀 Kako Koristiti (5 Koraka)

### **Korak 1: Pokreni Data Collector**
```bash
python data_collector.py
```

**Odgovori na pitanja:**
1. Ime konfiguracije: `3_bookmakers_console`
2. Pozicija: `2` (za Mozzart)
3. Interval: `0.2` (ili pritisni Enter za default)

### **Korak 2: Sačekaj da Prikupi Podatke**
Pusti da radi 10-30 minuta. Videćeš:
```
[INFO] Progress: 50 readings, Success: 94.0%, Phase: SCORE_MID
[INFO] Progress: 100 readings, Success: 96.0%, Phase: BETTING
```

### **Korak 3: Zaustavi sa Ctrl+C**
```
CTRL+C DETECTED - Stopping data collection...
Total readings: 523
Success rate: 96.0%
✓ data.db closed
✓ game_phase.db closed
```

### **Korak 4: Analiziraj Podatke**
```bash
# Pun izveštaj
python analyze_data.py report

# Ili samo specifične analize:
python analyze_data.py stats       # Osnovne statistike
python analyze_data.py quality     # Kvalitet podataka
python analyze_data.py accuracy    # Tačnost predikcije
python analyze_data.py rgb         # RGB klasteri
```

### **Korak 5: Export za ML (Opciono)**
```bash
# Izvezi RGB vrednosti u CSV
python analyze_data.py export rgb_training.csv
```

---

## 📊 Baze Podataka

### **`data.db`** - OCR Readings
```
Table: readings
├── timestamp       (TEXT)    - Vreme očitavanja
├── bookmaker       (TEXT)    - Ime bookmaker-a
├── score           (REAL)    - Očitani score
├── game_phase      (TEXT)    - Faza igre (BETTING, SCORE_MID...)
├── my_money        (REAL)    - Stanje novca
├── current_players (INTEGER) - Trenutno igrača
├── total_players   (INTEGER) - Ukupno igrača
└── others_money    (REAL)    - Ukupan dobitak drugih
```

### **`game_phase.db`** - RGB Values
```
Table: colors
├── timestamp             (TEXT)    - Vreme uzorka
├── bookmaker             (TEXT)    - Ime bookmaker-a
├── r, g, b               (REAL)    - RGB vrednosti (0-255)
├── predicted_phase       (TEXT)    - Predviđena faza
└── predicted_phase_value (INTEGER) - Numerička vrednost faze
```

---

## 🔍 Tipične Analize

### 1. **Koliko imam readings?**
```bash
sqlite3 data.db "SELECT COUNT(*) FROM readings;"
```

### 2. **Kakva je distribucija faza?**
```bash
python analyze_data.py stats
```
**Output:**
```
game_phase    count   pct
BETTING       120     23.0%
SCORE_MID     180     34.5%
ENDED         60      11.5%
```

### 3. **Da li model dobro predviđa faze?**
```bash
python analyze_data.py accuracy
```
**Output:**
```
game_phase    total  valid  invalid  accuracy_pct
SCORE_LOW     85     82     3        96.47%
SCORE_MID     180    165    15       91.67%  ⚠️
```

Ako je `accuracy < 90%` → **Problem sa modelom!**

### 4. **Kako izgledaju RGB vrednosti?**
```bash
python analyze_data.py rgb
```
**Output:**
```
phase         samples  avg_r  avg_g  avg_b  r_range
BETTING       1250     60.2   60.5   60.8   15.3
SCORE_MID     1450     150.3  126.8  178.2  48.7  ⚠️
```

Ako je `r_range > 50` → **Klasteri se preklapaju!**

---

## ⚠️ Šta Ako Ima Problema?

### Problem: Previše NULL vrednosti
**Simptom:** `completeness_pct < 70%`

**Rešenje:**
1. Smanji brzinu → Povećaj interval na 0.3s ili 0.5s
2. Proveri koordinate u `bookmaker_coords.json`
3. Testiraj pojedinačne regione

### Problem: Loša accuracy (<85%)
**Simptom:** Mnogo INVALID phase-score kombinacija

**Rešenje:**
1. Model treba retreniranje
2. Export RGB data: `python analyze_data.py export`
3. Retrain K-means model sa novim podacima
4. Zameni `game_phase_kmeans.pkl`

### Problem: Svi NULL za game_phase
**Simptom:** `game_phase` kolona prazna

**Rešenje:**
1. Proveri da postoji `game_phase_kmeans.pkl`
2. Proveri RGB vrednosti sa: `python analyze_data.py rgb`
3. Ako su sve RGB vrednosti 0 ili 255 → Regija van ekrana!

---

## 🎓 Workflow Primer

### **Scenario: Treniranje Boljeg Modela**

#### Dan 1: Prikupljanje
```bash
# Jutro - 30min collection
python data_collector.py  # Select Mozzart

# Pauza

# Popodne - 30min collection  
python data_collector.py  # Select BalkanBet

# Veče - 30min collection
python data_collector.py  # Select Soccer
```

**Rezultat:** ~27,000 readings (3 x 30min x 300 readings/min)

#### Dan 2: Analiza
```bash
# Proveri kvalitet
python analyze_data.py report > report.txt

# Proveri accuracy
python analyze_data.py accuracy
```

**Ako accuracy > 90%** → Sve je OK!  
**Ako accuracy < 90%** → Nastavi na Dan 3

#### Dan 3: Retrain Model
```bash
# Export balanced RGB data
python analyze_data.py export rgb_balanced.csv

# Train new model (Python script)
python train_kmeans.py rgb_balanced.csv

# Backup old model
mv game_phase_kmeans.pkl game_phase_kmeans_old.pkl

# Use new model
mv game_phase_kmeans_v2.pkl game_phase_kmeans.pkl
```

#### Dan 4: Validacija
```bash
# Test new model
python data_collector.py  # 10min test

# Check accuracy
python analyze_data.py accuracy
```

**Ako accuracy > 95%** → ✅ Success!

---

## 📈 Tipične Metrike

### **Odlično:**
- ✅ Completeness: >90%
- ✅ Phase Accuracy: >95%
- ✅ RGB Range: <40
- ✅ Success Rate: >95%

### **Dobro:**
- ⚠️ Completeness: 80-90%
- ⚠️ Phase Accuracy: 85-95%
- ⚠️ RGB Range: 40-50
- ⚠️ Success Rate: 85-95%

### **Loše (zahteva popravke):**
- ❌ Completeness: <80%
- ❌ Phase Accuracy: <85%
- ❌ RGB Range: >50
- ❌ Success Rate: <85%

---

## 🛠️ SQL Quick Commands

```bash
# Otvori data.db
sqlite3 data.db

# Ukupno readings
SELECT COUNT(*) FROM readings;

# Poslednje reading
SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1;

# Phase distribucija
SELECT game_phase, COUNT(*) FROM readings GROUP BY game_phase;

# RGB samples
sqlite3 game_phase.db "SELECT COUNT(*) FROM colors;"

# Close
.quit
```

---

## 🎯 Summary

**Data Collector vs Main.py:**

| Feature | Data Collector | Main.py |
|---------|---------------|---------|
| **Betting** | ❌ No | ✅ Yes |
| **Multiprocessing** | ❌ No | ✅ Yes (3+ processes) |
| **Database** | `data.db`, `game_phase.db` | `aviator.db` |
| **Purpose** | Data collection & validation | Real betting simulation |
| **Speed** | 5-10 readings/sec | Varies by game |
| **Use Case** | ML training, debugging | Production data collection |

**Kada koristiti šta:**
- **Data Collector** → Kada testiraš OCR, treniraš model, debuguješ
- **Main.py** → Kada simuliraš betting i prikupljaš production data

---

## 📞 Help

Ako imaš problema, proveri:
1. `logs/aviator.log` - Detaljan log
2. `python analyze_data.py quality` - Kvalitet podataka
3. `DATA_COLLECTOR_README.md` - Puna dokumentacija

---

**Happy Data Collecting! 📊🎲**