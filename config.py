# config.py
# VERSION: 3.1
# CHANGES: Updated paths for db/ folder structure

from dataclasses import dataclass
from enum import IntEnum
import os

@dataclass
class AppConstants:
    """Application-wide constants"""
    debug = True
    language = 'en'
    
    # Database paths - now in db/ folder
    database_dir = 'db'
    database = os.path.join(database_dir, 'aviator.db')
    
    # Models - in models/ folder
    models_dir = 'models'
    model_file = os.path.join(models_dir, 'game_phase_kmeans.pkl')
    prediction_model_file = os.path.join(models_dir, 'prediction_models.pkl')
    model_mapping_file = os.path.join(models_dir, 'model_mapping.json')
    
    # Tesseract
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # Logging
    log_dir = 'logs'
    log_max_bytes = 10 * 1024 * 1024
    log_backup_count = 5
    
    # Performance
    batch_size = 50
    batch_timeout = 1.0
    max_queue_size = 10000
    
    # Collection
    default_collection_interval = 0.2
    snapshot_frequency = 0.5
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        os.makedirs(cls.database_dir, exist_ok=True)
        os.makedirs(cls.models_dir, exist_ok=True)
        os.makedirs(cls.log_dir, exist_ok=True)


class BookmakerConfig:
    """Bookmaker configuration"""
    target_money: int = 35_000
    auto_stop: float = 2.35
    bet_length: int = 10
    
    bet_style: dict = {
        'cautious': [10, 25, 50, 95, 170, 305, 540, 950, 1660, 2900],
        'balanced': [15, 30, 65, 125, 220, 395, 700, 1235, 2160, 3770],
        'risky':    [15, 40, 75, 140, 255, 460, 810, 1425, 2490, 4350],
        'crazy':    [20, 50, 100, 190, 340, 610, 1080, 1900, 3320, 5800],
        'addict':   [30, 75, 150, 285, 510, 915, 1620, 2850, 4980, 8700],
        'all-in':   [40, 95, 190, 360, 645, 1160, 2050, 3610, 6310, 11000]
    }


class GamePhase(IntEnum):
    """Game phase enumeration (matches K-means cluster IDs)"""
    LOADING = 0
    WAITING = 1
    COUNTDOWN = 2
    PLAYING = 3
    CRASHED = 4
    RESULT = 5
    UNKNOWN = 6


class DatabaseConfig:
    """Database configuration"""
    connection_timeout = 10.0
    use_wal_mode = True
    journal_mode = 'WAL'
    synchronous = 'NORMAL'
    cache_size = -64000
    default_batch_size = 50
    default_batch_timeout = 1.0
    auto_vacuum = 'INCREMENTAL'
    page_size = 4096


class PerformanceConfig:
    """Performance monitoring"""
    stats_log_interval = 60.0
    queue_check_interval = 10.0
    queue_warning_threshold = 5000
    queue_critical_threshold = 8000
    expected_items_per_bookmaker_per_hour = 18000
    
    @staticmethod
    def calculate_expected_throughput(num_bookmakers: int, interval: float) -> float:
        return num_bookmakers / interval


# Create directories on import
AppConstants.ensure_directories()


if __name__ == "__main__":
    print("Config directories created:")
    print(f"  Database: {AppConstants.database_dir}")
    print(f"  Models:   {AppConstants.models_dir}")
    print(f"  Logs:     {AppConstants.log_dir}")