# Changelog

All notable changes to the Aviator Data Collection & Betting System.

## [5.0.0] - 2025-01-XX - MAJOR REWORK

### 🎯 Breaking Changes

- **NEW coordinate system**: Layout-based positioning instead of absolute coordinates
- **Separated programs**: Three independent applications instead of one monolithic app
- **New database structure**: Three separate databases with improved schemas
- **Simplified language**: Single-language support (removed bilingual code)

### ✨ New Features

#### Coordinate System v5.0
- Layout-based coordinate system with `width`, `height`, and `positions`
- Base coordinates for bookmakers (relative to 0,0)
- Automatic position calculation: `final = base + offset`
- `CoordsManager` v5.0 with `calculate_coords()` function
- Migration tool for old coordinates → new format

#### Independent Programs
1. **Main Data Collector** (`apps/main_data_collector.py`)
   - Collects game statistics (score, players, money)
   - Threshold-based snapshots (1.5x, 2x, 3x, 5x, 10x)
   - Database: `main_game_data.db`
   
2. **RGB Collector** (`apps/rgb_collector.py`)
   - Collects RGB samples for ML training
   - Phase region + button region
   - Database: `rgb_training_data.db`
   
3. **Betting Agent** (`apps/betting_agent.py`)
   - Automated bet placement
   - Transaction-safe with lock mechanism
   - Database: `betting_history.db`

#### Base Application Framework
- `BaseAviatorApp` template for all programs
- **Automatic region verification** on startup
- Region visualizer creates screenshots before running
- Standardized multiprocessing setup
- Proper shutdown handling

#### Database Improvements
- Three separate databases (no dependencies between them)
- Improved schemas with constraints and indexes
- Views for statistics
- Batch operations optimized
- `DatabaseModel` base class

#### New Utilities
- `region_visualizer.py` v2.0 - Works with new coordinate system
- `coordinate_migrator.py` - Migrate old → new format
- `setup.py` - Complete system verification
- `quick_start.py` - Interactive wizard for new users

#### Configuration
- `config.py` v5.0 - Restructured with dataclasses
- Centralized all configuration
- Separate configs for OCR, Database, Collection, Betting, Logging
- Path management with `PathConfig`
- Bookmaker and layout presets

### 🔧 Improvements

- **Performance**: Batch inserts optimized (50-100 rows at a time)
- **Logging**: Separate log files per program
- **Error Handling**: Better exception handling throughout
- **Documentation**: Complete rewrite of README and inline docs
- **Code Quality**: Type hints, docstrings, standardized formatting

### 📝 Changed Files

#### New Files
- `apps/base_app.py` - Base template for all apps
- `apps/main_data_collector.py` - Program 1
- `apps/rgb_collector.py` - Program 2
- `database/models.py` v5.0 - All database schemas
- `utils/coordinate_migrator.py` - Migration tool
- `setup.py` - System verification
- `quick_start.py` - Interactive wizard
- `CHANGELOG.md` - This file

#### Heavily Modified
- `core/coord_manager.py` - Complete rewrite for v5.0
- `config.py` - Restructured with dataclasses
- `utils/region_visualizer.py` - Adapted for new system
- `apps/betting_agent.py` - Rewritten using base template
- `README.md` - Complete rewrite

#### Updated
- `requirements.txt` - Version updates
- `.gitignore` - New patterns
- `data/coordinates/bookmaker_coords.json` - New structure

### 🗑️ Removed

- Bilingual support code (removed to simplify)
- Old monolithic `main.py` (replaced by 3 programs)
- Unused utility scripts
- Legacy database code
- Deprecated OCR methods

### 🐛 Bug Fixes

- Fixed coordinate calculation errors
- Fixed database locking issues (separate databases)
- Fixed multiprocessing shutdown (proper event handling)
- Fixed OCR preprocessing inconsistencies
- Fixed region visualization offset errors

### 📊 Database Schema Changes

#### main_game_data.db
```sql
-- rounds table
+ duration_seconds column
+ CHECK constraints
+ New indexes
+ Statistics view

-- threshold_scores table
+ Improved indexes
```

#### rgb_training_data.db (NEW)
```sql
-- phase_rgb table (new)
-- button_rgb table (new)
-- rgb_statistics view (new)
```

#### betting_history.db
```sql
-- bets table
+ session_id column
+ CHECK constraints
+ Status field

-- sessions table (new)
-- betting_statistics view (new)
```

### 🔄 Migration Guide

#### From v4.x to v5.0

1. **Backup everything!**
   ```bash
   cp -r data data.backup
   ```

2. **Update code**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   ```

3. **Migrate coordinates**
   ```bash
   python utils/coordinate_migrator.py
   ```

4. **Initialize new databases**
   ```bash
   python setup.py
   ```

5. **Update your scripts**
   - Old: `python main.py`
   - New: `python apps/main_data_collector.py`

6. **Test with region visualizer**
   ```bash
   python utils/region_visualizer.py
   ```

### ⚠️ Important Notes

- **Coordinates**: Old format coordinates must be migrated
- **Databases**: Not backward compatible - start fresh or migrate data
- **Programs**: Run independently (not all at once unless needed)
- **CSS Injection**: Still required before running (see javascript.txt)

---

## [4.0.0] - 2024-XX-XX

### Added
- Multi-bookmaker support (3-6 simultaneous)
- Batch database operations
- ML models for phase detection
- Improved logging system

### Changed
- Switched to multiprocessing
- Database optimization with WAL mode
- Enhanced screen reader

---

## [3.0.0] - 2024-XX-XX

### Added
- Basic data collection
- OCR with Tesseract
- Screen region detection
- SQLite database

### Changed
- Initial project structure

---

## [2.0.0] - 2024-XX-XX

### Added
- Proof of concept
- Manual coordinate setup

---

## [1.0.0] - 2024-XX-XX

### Added
- Initial prototype
- Basic screen capture

---

## Version Numbering

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes, major rework
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, minor improvements
