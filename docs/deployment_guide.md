# AVIATOR DATA COLLECTOR v3.0 - DEPLOYMENT GUIDE

## 📋 TABLE OF CONTENTS

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Initial Setup](#initial-setup)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## 🖥️ SYSTEM REQUIREMENTS

### Hardware
- **CPU:** Multi-core processor (4+ cores recommended)
- **RAM:** 4GB minimum, 8GB+ recommended
- **Storage:** 10GB+ free space (database grows ~100MB/day per bookmaker)
- **Display:** Multi-monitor setup recommended for 3+ bookmakers

### Software
- **OS:** Windows 10/11, Linux, or macOS
- **Python:** 3.8 or higher
- **Tesseract OCR:** 5.0 or higher

---

## 📥 INSTALLATION

### Step 1: Install Python

**Windows:**
```bash
# Download from python.org
# Make sure to check "Add Python to PATH"
python --version  # Should be 3.8+
```

**Linux:**
```bash
sudo apt update
sudo apt install python3 python3-pip
python3 --version
```

### Step 2: Install Tesseract OCR

**Windows:**
```bash
# Download installer from:
# https://github.com/UB-Mannheim/tesseract/wiki

# Default install path:
# C:\Program Files\Tesseract-OCR\tesseract.exe
```

**Linux:**
```bash
sudo apt install tesseract-ocr
tesseract --version
```

### Step 3: Clone or Download Project

```bash
# If using git
git clone <repository-url>
cd aviator

# Or extract zip file
unzip aviator-v3.0.zip
cd aviator
```

### Step 4: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or manually:
pip install numpy pandas scikit-learn pillow mss pytesseract joblib
```

---

## 🔧 INITIAL SETUP

### Step 1: Verify Installation

```bash
# Run diagnostic tool
python diagnostic.py
```

**Expected output:**
```
==========================================================
           AVIATOR SYSTEM DIAGNOSTIC v3.0
==========================================================

Testing: Python Version...
   Python 3.10.5
✅ Python Version - PASSED

Testing: Required Files...
   Found: logger.py
   Found: config.py
   ...
✅ Required Files - PASSED

Testing: Logger Fix...
✅ Logger fix applied (return statement present)
✅ Logger Fix - PASSED

...

==========================================================
                    DIAGNOSTIC REPORT
==========================================================

Test Results:
   Passed: 10/10

Status:
✅ System ready for production! 🚀
```

**If any tests fail, see [Troubleshooting](#troubleshooting)**

### Step 2: Update Tesseract Path (if needed)

Edit `config.py`:
```python
class AppConstants:
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows
    # tesseract_path = "/usr/bin/tesseract"  # Linux
```

### Step 3: Create Database

```bash
python database_setup.py
```

**Expected output:**
```
2025-10-04 15:30:45 | INFO     | DatabaseSetup        | Creating database tables...
2025-10-04 15:30:45 | INFO     | DatabaseSetup        | ✓ Table 'rounds' created successfully
2025-10-04 15:30:45 | INFO     | DatabaseSetup        | ✓ Table 'snapshots' created successfully
2025-10-04 15:30:45 | INFO     | DatabaseSetup        | ✓ Table 'earnings' created successfully
2025-10-04 15:30:45 | INFO     | DatabaseSetup        | Database setup completed!
```

### Step 4: Optimize Database

```bash
python database_optimizer.py
```

This will:
- Enable WAL mode
- Set optimal PRAGMA settings
- Create indexes
- Prepare database for high-performance inserts

---

## ⚙️ CONFIGURATION

### Step 1: Bookmaker Configuration

Edit `config.py` to adjust betting strategies:

```python
class BookmakerConfig:
    target_money: int = 35_000      # Stop when balance reaches this
    auto_stop: float = 2.35         # Auto cash-out multiplier
    bet_length: int = 10            # Betting sequence length
```

### Step 2: Performance Configuration

```python
class AppConstants:
    # Performance settings
    batch_size = 50              # Batch insert size (10-100)
    batch_timeout = 1.0          # Max batch wait (0.5-2.0s)
    max_queue_size = 10000       # Queue buffer size
    
    # Collection settings
    default_collection_interval = 0.2  # 200ms between reads
```

**Recommendations:**
- **1-2 bookmakers:** batch_size=20, timeout=2.0s
- **3-4 bookmakers:** batch_size=50, timeout=1.0s  
- **5-6 bookmakers:** batch_size=100, timeout=0.5s

### Step 3: Debug Mode

For testing, keep debug mode enabled:
```python
class AppConstants:
    debug = True  # Detailed logs
```

For production, disable:
```python
class AppConstants:
    debug = False  # Less verbose
```

---

## 🚀 FIRST RUN

### Quick Test (5 minutes)

```bash
# Run data collector
python data_collector.py

# When prompted:
# - Number of bookmakers: 1 (for testing)
# - Collection interval: 0.2
# - Follow on-screen instructions to set coordinates
```

**Setup process:**
1. Enter bookmaker name (e.g., "TestBookmaker")
2. Position windows and press ENTER
3. Take screenshot for each region:
   - Play amount field
   - Play button  
   - Score region
   - My money region
   - Other count region
   - Other money region
   - Phase region
4. Save coordinates (optional)

**Let it run for 5 minutes, then press Ctrl+C**

### Verify Test Results

```bash
# Check logs
tail -50 logs/main.log

# Check database
python performance_analyzer.py
```

**Expected results after 5 minutes:**
- Logs contain entries (not empty!)
- Database has records (check with analyzer)
- No critical errors in logs

---

## 📊 MONITORING

### Real-time Monitoring

**Option 1: Log file**
```bash
# Watch main log
tail -f logs/main.log

# Watch specific bookmaker
tail -f logs/balkanbet_*.log
```

**Option 2: Statistics**
Look for periodic stats in logs:
```
📊 Stats: 1,234 processed, 20.1 items/sec, avg batch: 48.3 items, queue: 156
```

### Performance Analysis

```bash
# Basic analysis
python performance_analyzer.py

# Detailed analysis
python performance_analyzer.py --detailed
```

**Expected output:**
```
======================================================================
        AVIATOR DATA COLLECTION - PERFORMANCE REPORT
======================================================================

📊 BASIC STATISTICS
   Total records:        72,458
   Database size:        14.35 MB
   Unique bookmakers:    4

⚡ THROUGHPUT
   Records/second:       20.1
   Records/hour:         72,360
   Efficiency:           99.8%
   Status:               🟢 EXCELLENT
```

### Key Metrics to Monitor

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Efficiency | >95% | 80-95% | <80% |
| Queue size | <1000 | 1000-5000 | >5000 |
| Items/sec | >18 (4 bookmakers) | 10-18 | <10 |
| Errors/hour | 0 | <10 | >10 |

---

## 🐛 TROUBLESHOOTING

### Issue 1: Logs are Empty

**Symptoms:**
- Log files exist but contain no data
- No "Logging initialized" message

**Solution:**
```bash
# Check logger.py has fix
grep "return root_logger" logger.py

# Should see line with return statement
# If not, update logger.py from v3.0
```

### Issue 2: Low Throughput (<10 items/sec)

**Symptoms:**
- Much fewer records than expected
- Efficiency <80%

**Possible causes:**
1. **Batch size too small**
   ```python
   # config.py
   batch_size = 50  # Increase to 100
   ```

2. **Database not optimized**
   ```bash
   python database_optimizer.py
   ```

3. **Disk I/O bottleneck**
   - Check disk space
   - Move database to faster drive (SSD)

### Issue 3: Queue Warnings

**Symptoms:**
```
⚠️  Queue size critical: 5,234 items (threshold: 5,000)
```

**Solutions:**
1. **Increase batch size**
   ```python
   batch_size = 100  # Process more at once
   ```

2. **Decrease batch timeout**
   ```python
   batch_timeout = 0.5  # Process more frequently
   ```

3. **Check database performance**
   ```bash
   python database_optimizer.py --benchmark
   ```

### Issue 4: Tesseract Errors

**Symptoms:**
```
Error: Tesseract not found
```

**Solutions:**
1. **Windows:** Reinstall Tesseract, check path
2. **Linux:** `sudo apt install tesseract-ocr`
3. **Update config.py** with correct path

### Issue 5: Screen Reading Errors

**Symptoms:**
- "Failed to extract score"
- "Text is empty after cleaning"

**Solutions:**
1. **Re-setup coordinates** (windows may have moved)
2. **Check window resolution** (should be consistent)
3. **Verify Tesseract language**: Use English (default)

---

## 🔧 MAINTENANCE

### Daily Tasks

**Check system status:**
```bash
# Quick check
python performance_analyzer.py

# Look for:
# - Efficiency >95%
# - No queue warnings
# - Consistent throughput
```

### Weekly Tasks

**1. Optimize database:**
```bash
python database_optimizer.py
```

**2. Check disk space:**
```bash
# Database grows ~100MB/day per bookmaker
# Ensure 10GB+ free space
```

**3. Review logs:**
```bash
# Check for errors
grep "ERROR" logs/*.log

# Check for warnings
grep "WARNING" logs/*.log
```

### Monthly Tasks

**1. Train prediction model:**
```bash
python prediction_analyzer.py
```

**2. Backup database:**
```bash
# Stop data collection first
cp aviator.db aviator_backup_$(date +%Y%m%d).db
```

**3. Clean old logs:**
```bash
# Keep only recent logs
find logs/ -name "*.log.*" -mtime +30 -delete
```

### Database Maintenance

**Backup strategy:**
```bash
# Daily backup (automatic via cron/Task Scheduler)
0 2 * * * cp /path/to/aviator.db /backups/aviator_$(date +%Y%m%d).db

# Keep 7 days of backups
find /backups -name "aviator_*.db" -mtime +7 -delete
```

**Restore from backup:**
```bash
# Stop data collection
# Copy backup
cp aviator_backup_20251004.db aviator.db
# Optimize
python database_optimizer.py
# Restart collection
```

---

## 🎯 PRODUCTION CHECKLIST

Before going to production:

- [ ] Ran `python diagnostic.py` - all tests passed
- [ ] Ran `python database_optimizer.py`
- [ ] Tested with 1 bookmaker for 30 minutes
- [ ] Verified logs are written correctly
- [ ] Verified database receives records
- [ ] Checked efficiency is >95%
- [ ] Set up bookmaker coordinates and saved config
- [ ] Configured betting strategies
- [ ] Set `debug = False` in config.py
- [ ] Set up automatic backups
- [ ] Documented monitor positions
- [ ] Created restore procedure document

---

## 📈 SCALING UP

### Adding More Bookmakers

```python
# Current: 4 bookmakers @ 0.2s = 20 items/sec

# Scaling to 6 bookmakers:
# Expected: 6 / 0.2 = 30 items/sec

# Update config.py:
batch_size = 60          # 6 bookmakers × 10
batch_timeout = 0.5      # Faster processing
max_queue_size = 15000   # Larger buffer
```

**Performance impact:**
- CPU: +50% usage per bookmaker
- RAM: +500MB per bookmaker
- Database: +100MB/day per bookmaker

### Performance Optimization Tips

1. **Use SSD for database** - 10x faster writes
2. **Multi-core CPU** - Better parallel processing
3. **16GB+ RAM** - Larger cache = faster
4. **Dedicated machine** - No other heavy tasks

---

## 🆘 SUPPORT

### Getting Help

1. **Check logs first:**
   ```bash
   tail -100 logs/main.log
   ```

2. **Run diagnostic:**
   ```bash
   python diagnostic.py
   ```

3. **Check performance:**
   ```bash
   python performance_analyzer.py
   ```

4. **Common issues:** See [Troubleshooting](#troubleshooting)

### Reporting Issues

Include:
- Output from `diagnostic.py`
- Last 100 lines from logs
- Performance analyzer output
- System specs (CPU, RAM, OS)
- Number of bookmakers

---

## 📚 USEFUL COMMANDS

```bash
# System check
python diagnostic.py

# Performance analysis
python performance_analyzer.py
python performance_analyzer.py --detailed

# Database optimization
python database_optimizer.py
python database_optimizer.py --benchmark

# Start data collection
python data_collector.py

# Train prediction model
python prediction_analyzer.py

# Database query
sqlite3 aviator.db "SELECT COUNT(*) FROM rounds;"
sqlite3 aviator.db "SELECT bookmaker, COUNT(*) FROM rounds GROUP BY bookmaker;"

# Check database size
du -h aviator.db

# Monitor logs real-time
tail -f logs/main.log | grep "Stats:"

# Check for errors
grep -r "ERROR" logs/

# Clean old log backups
find logs/ -name "*.log.*" -mtime +7 -delete
```

---

## ✅ SUCCESS CRITERIA

Your system is working correctly when:

- ✅ Logs contain regular entries
- ✅ Database receives ~20 items/sec (4 bookmakers @ 0.2s)
- ✅ Efficiency >95%
- ✅ Queue size <1000
- ✅ No errors in logs
- ✅ All bookmakers showing equal distribution
- ✅ Prediction model training succeeds

---

**SYSTEM STATUS: 🟢 READY FOR PRODUCTION**

Good luck! 🎰🚀
