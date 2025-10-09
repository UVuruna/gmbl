# 📊 Analysis Tools - Documentation

Tri glavna alata za analizu prikupljenih podataka iz Aviator sistema.

---

## 🎯 Pregled Alata

| Alat | Prvobitni naziv | Funkcija |
|------|----------------|----------|
| **betting_stats_analyzer.py** | check_robin.py | Analiza betting statistike i profitabilnosti |
| **data_extractor.py** | extracted_to_list.py | Konverzija Excel → CSV i ekstrakcija podataka |
| **log_processor.py** | log_read_gpt.py | Parsiranje log.csv i interpolacija vremena |

---

## 📈 1. Betting Stats Analyzer

### Namena
Analizira CSV logove klađenja i prikazuje detaljnu statistiku performansi po bookmaker-ima.

### Šta radi?
- Učitava CSV logove za sve bookmaker-e (admiral, balkanbet, merkur, soccer)
- Simulira betting strategiju (Martingale ili fiksni ulozi)
- Računa profit/gubitak, potreban kapital, RSD/h zarade
- Prikazuje raspodelu dobitaka (nakon koliko gubitaka)

### Upotreba

```bash
python betting_stats_analyzer.py
```

### Konfiguracija

```python
config = BettingConfig(
    bet_order=[10, 20, 40, 70, 130, 250, 500, 950, 1750, 3200, 6000, 11000],
    auto_cashout=2.28,
    max_loss_streak=12
)
```

**Parametri:**
- `bet_order` - Redosled uloga u Martingale strategiji
- `auto_cashout` - Auto cash-out koeficijent
- `max_loss_streak` - Maksimalan broj uzastopnih gubitaka

### Input Format

CSV fajlovi u `documentation/logs/`:
```
admiral.csv
balkanbet.csv
merkur.csv
soccer.csv
```

**Struktura CSV:**
```csv
time,score,sec
01.01.2025 14:30:15,2.45,120
01.01.2025 14:30:35,1.15,140
01.01.2025 14:31:02,3.20,167
```

### Output Format

```
================================================================================
Analiziram: ADMIRAL
================================================================================
admiral        |    Total:      1,250    |    Max gubitak:    500 (7)    |    Veliki gubici:   2  | Vreme:  180.00 min
____________________________________________________________________________
520            |    Total:      1,250    |    Max gubitak:    500 (7)    |    Veliki gubici:   2  | Vreme:  180.00 min
____________________________________________________________________________
	*** STATS ADMIRAL:  total = 1,250 RSD      din/h: 416 RSD         Money needed: 2,500 RSD ***

********************************************************************************
	*** STATS ADMIRAL:  total = 1,250 RSD      din/h: 416 RSD         Money needed: 2,500 RSD ***
	*** STATS BALKANBET:  total = 890 RSD      din/h: 356 RSD         Money needed: 1,800 RSD ***
	*** STATS MERKUR:  total = 1,120 RSD      din/h: 448 RSD         Money needed: 2,200 RSD ***
	*** STATS SOCCER:  total = 950 RSD      din/h: 380 RSD         Money needed: 1,900 RSD ***
********************************************************************************

	ROUNDS = 2,145  |  TOTAL = 4,210 RSD  |  HOURS: 10.50h  |  din/h: 401 RSD  |  STYLE: max: 12, auto: 2.28

	RISK: 24,570 RSD - count: 8  |  WINS: (22 RSD : 2,584 RSD) - count: 1,987  |  Money needed: 8,400 RSD

All WINS:  1.= 1,450     | 2.= 342      | 3.= 125      | 4.= 48       | 5.= 15       | 6.= 5        | 7.= 2
All WINS:  1.= 73.0%     | 2.= 17.2%    | 3.= 6.3%     | 4.= 2.4%     | 5.= 0.8%     | 6.= 0.3%     | 7.= 0.1%

********************************************************************************
```

### Ključne Statistike

- **Total** - Ukupan profit/gubitak
- **Max gubitak** - Najveći zaredom gubitak (iznos i broj rundi)
- **Veliki gubici** - Broj puta kada je dostignut max_loss_streak
- **din/h** - Profit po satu igranja
- **Money needed** - Potreban početni kapital (najniži balans)
- **RISK** - Maksimalan mogući gubitak u jednoj seriji
- **WINS raspodela** - Nakon koliko gubitaka dolazi dobitak

---

## 📁 2. Data Extractor

### Namena
Konvertuje Excel fajlove u CSV i ekstraktuje podatke iz text fajlova sa parsiranjem različitih formata brojeva.

### Šta radi?
- **Excel → CSV konverzija** (automatski traži .xlsx i pravi .csv)
- Parsira text fajlove sa rezultatima
- Podržava različite formate: `1.28`, `1,28`, `1:28`, `1.28x`, `1,000.23`
- Prilagođava redosled podataka na osnovu načina prikupljanja

### Upotreba

```bash
python data_extractor.py
```

**Interaktivni mod:**
```
Da li je od prvog screenshota (enter ako nije): [enter ili bilo šta]
Koliko ima screenshotova: 5
```

### Podržani Formati

```python
# Svi ovi formati se parsiraju u float:
"1.28"      → 1.28
"1,28"      → 1.28
"1:28"      → 1.28
"1.28x"     → 1.28
"1,000.23"  → 1000.23
"1.000,23"  → 1000.23
```

### Input Fajlovi

**Opcija 1:** Excel + Text
```
documentation/logs/extracted_numbers.xlsx  # Excel format
documentation/logs/extracted_numbers.txt   # Text format
```

**Opcija 2:** Samo Text
```
documentation/logs/extracted_numbers.txt
```

**Format Text fajla:**
```
1.28 1.45 2.03
1.89 1.12 3.45
2.11 1.77 1.98
```

### Output

```
================================================================================
DATA EXTRACTOR - Excel/CSV/Text Parser
================================================================================
Da li je od prvog screenshota (enter ako nije): 
Koliko ima screenshotova: 3
✓ Converted: extracted_numbers.xlsx → extracted_numbers.csv

BROJ PODATAKA: 9
********************************************************************************
1.28
1.45
2.03
1.89
1.12
3.45
2.11
1.77
1.98
********************************************************************************
```

### Redosled Podataka

**`first_to_last = True`** (screenshot od prvog ka poslednjem):
- Svaki chunk se obrće pojedinačno
- Korisno kada su screenshot-ovi hronološki, ali su podaci u svakom screenshot-u obrnuti

**`first_to_last = False`** (screenshot od poslednjeg ka prvom):
- Obrće se redosled chunk-ova
- Korisno kada su screenshot-ovi snimani unazad

---

## ⏱️ 3. Log Processor

### Namena
Parsira glavni `log.csv` i interpolira vremena između checkpoint-ova za sve bookmaker-e.

### Šta radi?
- Učitava `log.csv` sa svim bookmaker-ima
- Parsira Time i Score kolone za svaki market
- **Interpolira vremena** između checkpoint-ova (linearna interpolacija)
- Ekstrapolira vremena za redove nakon poslednjeg checkpoint-a
- Čuva poseban CSV za svaki bookmaker

### Upotreba

```bash
python log_processor.py
```

### Input Format

**`documentation/logs/log.csv`:**
```csv
Time Merkur,Merkur,Time BalkanBet,BalkanBet,Time Admiral,Admiral,Time Soccer,Soccer
01.01.2025 14:30:00,2.45,,,,,
,1.89,01.01.2025 14:30:15,3.12,,1.45,
,,,01.01.2025 14:30:30,2.78,,01.01.2025 14:30:20,1.98
```

**Struktura:**
- `Time {Market}` - Checkpoint vremena (kada je snimljen screenshot)
- `{Market}` - Score vrednost (koeficijent u igri)

### Output Format

**`documentation/logs/merkur.csv`:**
```csv
time,score,sec
01.01.2025 14:30:00,2.45,0
,1.89,15
```

**`documentation/logs/balkanbet.csv`:**
```csv
time,score,sec
01.01.2025 14:30:15,3.12,0
,2.78,15
```

### Logika Interpolacije

```
Checkpoint 1: 14:30:00 → sec = 0
Checkpoint 2: 14:30:30 → sec = 30

Redovi između (14:30:10): sec = 0 + (10/30) * 30 = 10
Redovi između (14:30:20): sec = 0 + (20/30) * 30 = 20

Tail (nakon poslednjeg checkpoint-a):
Koristi rate iz poslednjeg segmenta za ekstrapolaciju
```

### Output

```
================================================================================
LOG PROCESSOR - Time Interpolation & CSV Export
================================================================================

Učitavam: log.csv...
✓ Učitano 1250 redova

Parsiram podatke za sve market-e...
Računam vremena (interpolacija)...

Čuvam CSV fajlove:
✓ Saved: merkur.csv (320 rows)
✓ Saved: balkanbet.csv (315 rows)
✓ Saved: admiral.csv (298 rows)
✓ Saved: soccer.csv (317 rows)

================================================================================
✓ Procesiranje završeno!
================================================================================
```

---

## 🔄 Tipičan Workflow

```
1. Prikupiš podatke → log.csv (glavni log sa svim bookmaker-ima)
2. log_processor.py → Kreira admiral.csv, balkanbet.csv, merkur.csv, soccer.csv
3. betting_stats_analyzer.py → Analizira performanse betting strategije
4. (Opciono) data_extractor.py → Za ekstrakciju dodatnih podataka iz Excel/Text
```

---

## 📂 Folder Struktura

```
Aviator/
├── betting_stats_analyzer.py
├── data_extractor.py
├── log_processor.py
└── documentation/
    └── logs/
        ├── log.csv                    # Input: glavni log
        ├── admiral.csv                # Output: procesiran log
        ├── balkanbet.csv
        ├── merkur.csv
        ├── soccer.csv
        ├── extracted_numbers.xlsx     # Input: Excel sa podacima
        └── extracted_numbers.txt      # Input: Text sa podacima
```

---

## 🛠️ Refactoring Izmene

### Betting Stats Analyzer
- ✅ Uvedene dataclass-e za config i statistiku
- ✅ Razdvojena logika u klase (analizator, parser, printer)
- ✅ Poboljšana čitljivost output-a
- ✅ Type hints za sve funkcije

### Data Extractor
- ✅ **Dodato**: Automatska Excel → CSV konverzija
- ✅ Klase za parsiranje i ekstrakciju
- ✅ Bolje error handling
- ✅ Podržani svi decimalni formati

### Log Processor
- ✅ Razdvojena logika: TimeParser, ScoreParser, TimeInterpolator
- ✅ Klasa LogProcessor za orkestraciju
- ✅ Type hints i dokumentacija
- ✅ **Logika ostala ista** - samo čitljivost poboljšana

---

## 🎓 Best Practices

1. **Uvek prvo pokreni `log_processor.py`** da kreiraš CSV-ove po bookmaker-ima
2. **Proveri format ulaznih fajlova** pre pokretanja
3. **Excel → CSV konverzija** - Data Extractor automatski detektuje .xlsx i pravi .csv
4. **Backup podataka** pre analize
5. **Proveri konfiguracij betting parametara** u betting_stats_analyzer.py

---

## ⚠️ Važne Napomene

- Svi fajlovi moraju biti u `documentation/logs/` folderu
- CSV format: `time,score,sec` (sa header)
- Log Processor očekuje kolone: `Time {Market}` i `{Market}`
- Betting Stats Analyzer traži `.csv` fajlove sa imenima bookmaker-a (lowercase)

---

**Verzije:**
- betting_stats_analyzer.py v2.0
- data_extractor.py v2.0  
- log_processor.py v2.0

**Datum refaktoringa:** 2025-01-10
