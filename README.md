# 🎰 Aviator Data Collection System v4.0

## 📋 Overview

High-performance multi-bookmaker data collection system for AVIATOR game with parallel processing, batch database operations, and ML-based prediction capabilities.

### Key Features
- **Parallel Processing**: 3-6 bookmakers simultaneously
- **Batch Database Operations**: 10-50x performance improvement
- **Real-time OCR**: Screen reading with Tesseract
- **ML Predictions**: K-means clustering for game phase detection
- **Transaction-safe Betting**: Sequential bet placement
- **Performance Monitoring**: Real-time statistics and diagnostics

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/aviator.git
cd aviator

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Linux: sudo apt-get install tesseract-ocr
```

### 2. First Run

```bash
# Run system diagnostics
python utils/diagnostic.py

# If all checks pass, start the system
python main.py
```

### 3. Quick Test Mode

Select option 3 when prompted for "Quick test mode" to test with 1 bookmaker.

## 📁 Project Structure

```
Aviator/
├── 📄 Core Files
│   ├── main.py                 # Main entry point
│   ├── config.py               # Centralized configuration
│   ├── logger.py               # Logging system (v3.0 fixed)
│   └── requirements.txt        # Dependencies
│
├── 📁 apps/                    # Main applications
│   ├── data_collector.py       # Data collection
│   ├── betting_agent.py        # Betting system
│   └── prediction_trainer.py   # ML training
│
├── 📁 core/                    # Core business logic
│   ├── screen_reader.py        # OCR functionality
│   ├── coord_manager.py        # Coordinate management
│   ├── gui_controller.py       # Mouse/keyboard control
│   ├── bookmaker_process.py    # Worker processes
│   └── bookmaker_orchestrator.py # Process coordination
│
├── 📁 database/                # Database layer
│   ├── models.py               # Database schemas
│   ├── writer.py               # Write operations
│   ├── worker.py               # Batch queue worker
│   └── optimizer.py            # DB optimization
│
├── 📁 regions/                 # Screen region handlers
│   ├── base_region.py          # Base class
│   ├── game_phase.py           # Phase detection
│   ├── score.py                # Score reading
│   └── my_money.py             # Balance reading
│
├── 📁 utils/                   # Utility tools
│   ├── diagnostic.py           # System diagnostics
│   ├── performance_analyzer.py # Performance analysis
│   └── data_analyzer.py        # Data analysis
│
└── 📁 data/                    # Data storage
    ├── databases/              # SQLite databases
    ├── models/                 # Trained ML models
    └── coordinates/            # Saved configurations
```

## ⚙️ Configuration

### Edit `config.py`:

```python
# Database performance
batch_size = 50          # Items per batch (10-100)
batch_timeout = 1.0      # Max wait before batch (0.5-2.0s)

# Collection settings  
default_collection_interval = 0.2  # 200ms between reads

# Tesseract path
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Betting Strategies

Choose from 6 pre-configured strategies:
- **Cautious**: Low risk, slow growth
- **Balanced**: Moderate risk/reward
- **Risky**: High risk, faster growth
- **Crazy**: Very high risk
- **Addict**: Extreme risk
- **All-in**: Maximum risk

## 🔧 System Requirements

### Minimum:
- Python 3.8+
- 4GB RAM
- Dual-core CPU
- Windows 10/11 or Linux

### Recommended:
- Python 3.10+
- 8GB+ RAM  
- Quad-core+ CPU
- SSD for database
- 1920x1080 resolution

## 📊 Performance Metrics

### Expected Performance (4 bookmakers @ 0.2s):

| Metric | Value |
|--------|-------|
| Throughput | ~20 items/sec |
| Hourly volume | ~72,000 records |
| Daily volume | ~1.7M records |
| Database growth | ~400 MB/day |
| Efficiency | >95% |

## 🛠️ Maintenance

### Daily Tasks

```bash
# Check system health
python utils/performance_analyzer.py

# Monitor logs
tail -f logs/main.log
```

### Weekly Tasks

```bash
# Optimize database
python database/optimizer.py

# Train prediction model
python apps/prediction_trainer.py
```

### Backup Strategy

```bash
# Backup database
cp data/databases/aviator.db backups/aviator_$(date +%Y%m%d).db

# Backup models
cp -r data/models/ backups/models_$(date +%Y%m%d)/
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Empty Logs
```bash
# Check logger fix
grep "return root_logger" logger.py
# Should show line with return statement
```

#### 2. Low Throughput
```python
# Increase batch size in config.py
batch_size = 100
batch_timeout = 0.5
```

#### 3. Queue Warnings
```bash
# Check database performance
python database/optimizer.py --benchmark
```

#### 4. OCR Errors
```bash
# Verify Tesseract installation
tesseract --version

# Update path in config.py
tesseract_path = "your/path/to/tesseract"
```

## 📈 Data Analysis

### Quick Analysis

```bash
# Analyze collected data
python utils/data_analyzer.py

# Performance metrics
python utils/performance_analyzer.py --detailed

# Database statistics
sqlite3 data/databases/aviator.db "SELECT COUNT(*) FROM rounds;"
```

### Export Data

```sql
-- Export to CSV
.mode csv
.output data_export.csv
SELECT * FROM rounds WHERE bookmaker = 'BalkanBet';
.quit
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

Private project for educational and research purposes only.

## ⚠️ Disclaimer

This tool is for data collection and analysis purposes only. Use responsibly and in accordance with applicable terms of service.

## 🆘 Support

For issues or questions:
1. Check logs: `logs/main.log`
2. Run diagnostics: `python utils/diagnostic.py`
3. Review documentation in `docs/` folder

## 🎯 Version History

- **v4.0** (Current) - Complete reorganization, improved structure
- **v3.0** - Fixed logger, batch operations, ML predictions
- **v2.0** - Multiprocessing support
- **v1.0** - Initial release

---

**Made with ❤️ for data science and ML research**