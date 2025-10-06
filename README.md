# 🎰 Aviator Data Collection & Betting System v5.0

## 📋 Overview

Professional multi-bookmaker system for Aviator game with three independent applications:

1. **Main Data Collector** - Game statistics collection
2. **RGB Collector** - ML training data collection  
3. **Betting Agent** - Automated bet placement

### Key Features
- **New coordinate system** with layout-based positioning
- **Independent programs** - Run separately or together
- **Automatic region verification** on startup
- **Parallel processing** - 1-6 bookmakers simultaneously
- **Batch database operations** - High performance
- **Transaction-safe betting** - One bet at a time
- **Comprehensive logging** - Separate logs per program

---

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Linux: sudo apt-get install tesseract-ocr
```

### 2. Configuration

#### Coordinate System (NEW in v5.0)

The system uses a **layout-based coordinate system**:

**Structure:** `data/coordinates/bookmaker_coords.json`

```json
{
  "layouts": {
    "layout_name": {
      "width": 1280,
      "height": 720,
      "positions": {
        "TL": {"left": 0, "top": 0},
        "TR": {"left": 1280, "top": 0}
      }
    }
  },
  "bookmakers": {
    "BalkanBet": {
      "score_region": {"left": 215, "top": 280, "width": 800, "height": 215},
      ...
    }
  }
}
```

**How it works:**
1. **Layouts** define grid arrangements (window size + positions)
2. **Bookmakers** define base coordinates (relative to 0,0)
3. **Final coordinates** = base coordinates + position offset

**Example:**
- Layout "3_monitors_grid" has position "TC" at (1280, 0)
- BalkanBet score_region starts at (215, 280)
- Final position: (215+1280, 280+0) = (1495, 280)

#### JavaScript/CSS Setup

Use `javascript.txt` to inject CSS into each bookmaker site to optimize layout:

```javascript
// Example for Mozzart
.navigation-wrapper { display: none }
.game-header { display: none }
.casino-game-fullscreen { height: 100%; width: 100%; padding: 0 }
```

Load this CSS in browser console before running programs.

---

## 📁 Project Structure

```
Aviator/
├── apps/
│   ├── base_app.py              # Base template with region verification
│   ├── main_data_collector.py   # Program 1: Game statistics
│   ├── rgb_collector.py         # Program 2: RGB training data
│   └── betting_agent.py         # Program 3: Automated betting
│
├── core/
│   ├── coord_manager.py         # New coordinate system (v5.0)
│   ├── screen_reader.py         # OCR functionality
│   ├── gui_controller.py        # Mouse/keyboard control
│   └── ...
│
├── utils/
│   ├── region_visualizer.py     # Automatic verification (v2.0)
│   └── region_editor.py         # Interactive coordinate setup
│
├── data/
│   ├── coordinates/
│   │   └── bookmaker_coords.json
│   ├── databases/
│   │   ├── main_game_data.db
│   │   ├── rgb_training_data.db
│   │   └── betting_history.db
│   └── models/
│
└── logs/
    ├── main_data_collector.log
    ├── rgb_collector.log
    └── betting_agent.log
```

---

## 🎮 Programs

### Program 1: Main Data Collector

**Purpose:** Collect game statistics for analysis

**Collects:**
- End of round: `score`, `total_players`, `left_players`, `total_money`
- During round: Score at thresholds (1.5x, 2x, 3x, 5x, 10x)

**Database:** `main_game_data.db`

**Usage:**
```bash
python apps/main_data_collector.py
```

**Features:**
- ✅ Automatic region verification on startup
- ✅ Monitors phase changes (WAITING → FLYING → WAITING)
- ✅ Batch database inserts (50 rows at a time)
- ✅ Supports 1-6 bookmakers in parallel
- ✅ Individual log file

---

### Program 2: RGB Collector

**Purpose:** Collect RGB data for ML model training

**Collects:**
- `phase_region`: Average RGB + std dev (for phase detection)
- `play_button_coords`: Average RGB + std dev (for bet state: red/orange/green)

**Database:** `rgb_training_data.db`

**Usage:**
```bash
python apps/rgb_collector.py
```

**Features:**
- ✅ Samples every 500ms
- ✅ Calculates RGB statistics (mean + std)
- ✅ Unlabeled data (label later with clustering)
- ✅ Batch database inserts (100 rows at a time)
- ✅ Individual log file

**Later use:**
```python
# Train K-means clustering on collected data
from ai.model_trainer import train_phase_model
train_phase_model("data/databases/rgb_training_data.db")
```

---

### Program 3: Betting Agent

**Purpose:** Automated bet placement with configurable strategy

**Monitors:**
- `my_money` - Account balance
- `score` - Current multiplier
- `phase` - Game state

**Controls:**
- `bet_amount_coords` - Bet amount field
- `play_button_coords` - Place bet button
- `auto_play_coords` - Auto cash-out field

**Database:** `betting_history.db`

**Usage:**
```bash
python apps/betting_agent.py
```

**Features:**
- ✅ Transaction-safe betting (lock mechanism)
- ✅ Configurable strategy (fixed bet, Martingale, etc.)
- ✅ Auto cash-out support
- ✅ Full bet history logging
- ✅ Real-time profit tracking
- ✅ Individual log file

**⚠️ WARNING:** Uses real money! Test thoroughly in demo mode first.

---

## 🔧 Setup & Configuration

### Step 1: Configure Coordinates

Option A: **Use existing bookmaker coordinates**

If coordinates are already in `bookmaker_coords.json`:

```bash
# Just run any program - it will show available options
python apps/main_data_collector.py
```

Option B: **Create new coordinates**

```bash
# Use interactive region editor
python utils/region_editor.py
```

### Step 2: Verify Regions

**All programs automatically verify regions on startup!**

The system will:
1. Generate screenshots with region overlays
2. Save to `tests/screenshots/`
3. Ask for confirmation before proceeding

### Step 3: Inject CSS (Important!)

Before running programs:

1. Open each bookmaker site in browser
2. Open browser console (F12)
3. Copy CSS from `javascript.txt` for that bookmaker
4. Paste in console and press Enter
5. This removes unnecessary UI elements

### Step 4: Run Programs

Run programs independently in separate terminals:

```bash
# Terminal 1: Collect game data
python apps/main_data_collector.py

# Terminal 2: Collect RGB training data
python apps/rgb_collector.py

# Terminal 3: Run betting agent
python apps/betting_agent.py
```

Or run all three simultaneously!

---

## 📊 Database Schemas

### main_game_data.db

**rounds table:**
```sql
id, bookmaker, timestamp, final_score, 
total_players, left_players, total_money
```

**threshold_scores table:**
```sql
id, bookmaker, timestamp, threshold, 
current_players, current_money
```

### rgb_training_data.db

**phase_rgb table:**
```sql
id, bookmaker, timestamp, 
r_avg, g_avg, b_avg, r_std, g_std, b_std, label
```

**button_rgb table:**
```sql
id, bookmaker, timestamp, 
r_avg, g_avg, b_avg, r_std, g_std, b_std, label
```

### betting_history.db

**bets table:**
```sql
id, bookmaker, timestamp, bet_amount, auto_stop,
final_score, money_before, money_after, profit, status
```

---

## 🎯 Best Practices

### Region Verification
- **Always check screenshots** before starting
- Adjust coordinates if regions don't align
- Re-run verification after any browser zoom changes

### Data Collection
- Run for extended periods (hours/days) for ML training
- Use **demo mode** for initial testing
- Monitor logs for errors

### Betting
- **Test in demo mode first!**
- Start with small bet amounts
- Monitor betting_history.db for performance analysis
- Use auto cash-out to limit losses

### Performance
- Each program uses **multiprocessing** for parallel bookmaker tracking
- Batch inserts optimize database performance
- Logs rotate automatically at 10MB

---

## 🔍 Troubleshooting

### Regions not aligning?
```bash
# Re-configure coordinates
python utils/region_editor.py

# Or adjust in JSON directly
nano data/coordinates/bookmaker_coords.json
```

### OCR not reading correctly?
- Check Tesseract installation
- Verify screen brightness/contrast
- Ensure browser zoom is 100%
- Inject CSS to remove overlapping UI

### Betting not working?
- Check that GUI automation is allowed
- Verify mouse coordinates are correct
- Check logs for error messages
- Ensure only one betting agent runs per bookmaker

### Database locked?
- Only one program should write to each database
- If stuck, restart programs
- Check for zombie processes

---

## 📈 Future Improvements

- [ ] Live dashboard for monitoring
- [ ] Advanced betting strategies
- [ ] ML prediction models integration
- [ ] Multi-monitor automatic setup
- [ ] Cloud database sync
- [ ] Telegram notifications

---

## ⚠️ Disclaimer

This software is for **educational and research purposes only**. 

- Use at your own risk
- Gambling involves real money and risk of loss
- Test thoroughly in demo mode
- Check local gambling regulations
- No warranty or guarantees provided

---

## 📝 Version History

**v5.0 (Current)**
- ✅ New layout-based coordinate system
- ✅ Three independent programs
- ✅ Automatic region verification
- ✅ Improved database schemas
- ✅ Enhanced logging
- ✅ Transaction-safe betting

**v4.0**
- Multi-bookmaker support
- Batch database operations
- ML models integration

**v3.0**
- Basic data collection
- OCR implementation

---

## 📧 Support

For issues, questions, or contributions:
- Check logs in `logs/` directory
- Review screenshots in `tests/screenshots/`
- Consult documentation above

---

**Happy collecting! 🎰📊**
