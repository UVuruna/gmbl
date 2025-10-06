# config.py
"""
Aviator Project Configuration
Version: 4.0
Centralized configuration for all modules
"""

from dataclasses import dataclass
from enum import IntEnum
import os
from typing import Dict, List
from pathlib import Path


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()


@dataclass
class AppConstants:
    """Application-wide constants and paths"""
    
    # Debug mode
    debug: bool = True
    language: str = 'en'
    
    # Directory structure
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / 'data'
    logs_dir: Path = PROJECT_ROOT / 'logs'
    
    # Database paths
    database_dir: Path = data_dir / 'databases'
    main_database: Path = database_dir / 'aviator.db'
    
    # Model paths
    models_dir: Path = data_dir / 'models'
    game_phase_model: Path = models_dir / 'game_phase_kmeans.pkl'
    bet_button_model: Path = models_dir / 'bet_button_kmeans.pkl'
    prediction_models: Path = models_dir / 'prediction_models.pkl'
    model_mapping: Path = models_dir / 'model_mapping.json'
    
    # Coordinates paths
    coords_dir: Path = data_dir / 'coordinates'
    bookmaker_coords: Path = coords_dir / 'bookmaker_coords.json'
    
    # Tesseract OCR
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows
    # tesseract_path: str = "/usr/bin/tesseract"  # Linux
    
    # Logging configuration
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Database performance settings
    batch_size: int = 50  # Items per batch insert
    batch_timeout: float = 1.0  # Maximum wait before forcing batch
    max_queue_size: int = 10000  # Maximum queue size
    db_checkpoint_interval: int = 1000  # WAL checkpoint interval
    
    # Data collection settings
    default_collection_interval: float = 0.2  # 200ms between reads
    snapshot_frequency: float = 0.5  # Snapshot every 500ms
    max_workers: int = 6  # Maximum parallel bookmaker processes
    
    # OCR settings
    ocr_timeout: float = 5.0  # Maximum OCR processing time
    ocr_retry_count: int = 3  # Number of retries on OCR failure
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create all necessary directories if they don't exist"""
        dirs_to_create = [
            cls.data_dir,
            cls.database_dir,
            cls.models_dir,
            cls.coords_dir,
            cls.logs_dir
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_database_path(cls, name: str = None) -> Path:
        """Get path for a specific database"""
        if name:
            return cls.database_dir / f"{name}.db"
        return cls.main_database
    
    @classmethod
    def get_model_path(cls, name: str) -> Path:
        """Get path for a specific model"""
        return cls.models_dir / name
    
    @classmethod
    def get_log_path(cls, name: str) -> Path:
        """Get path for a specific log file"""
        return cls.logs_dir / name


@dataclass
class BookmakerConfig:
    """Bookmaker-specific configuration"""
    
    # Financial targets
    target_money: int = 35_000  # Stop when balance reaches this
    auto_stop: float = 2.35  # Auto cash-out multiplier
    initial_balance: int = 10_000  # Starting balance
    
    # Betting configuration
    bet_length: int = 10  # Length of betting sequence
    max_concurrent_bets: int = 2  # Max bets per bookmaker
    bet_cooldown: float = 1.0  # Seconds between bets
    
    # Betting strategies (Martingale variations)
    bet_styles: Dict[str, List[int]] = None
    
    def __post_init__(self):
        """Initialize betting styles after dataclass creation"""
        if self.bet_styles is None:
            self.bet_styles = {
                'cautious': [10, 25, 50, 95, 170, 305, 540, 950, 1660, 2900],
                'balanced': [15, 30, 65, 125, 220, 395, 700, 1235, 2160, 3770],
                'risky':    [15, 40, 75, 140, 255, 460, 810, 1425, 2490, 4350],
                'crazy':    [20, 50, 100, 190, 340, 610, 1080, 1900, 3320, 5800],
                'addict':   [30, 75, 150, 285, 510, 915, 1620, 2850, 4980, 8700],
                'all-in':   [40, 95, 190, 360, 645, 1160, 2050, 3610, 6310, 11000],
                'uv':       [20, 40, 80, 150, 300, 600, 1200, 2100, 3700, 6600]
            }
    
    def get_bet_sequence(self, style: str = 'balanced') -> List[int]:
        """Get betting sequence for a specific style"""
        sequence = self.bet_styles.get(style, self.bet_styles['balanced'])
        return sequence[:self.bet_length]
    
    def calculate_max_loss(self, style: str = 'balanced') -> int:
        """Calculate maximum possible loss for a betting style"""
        sequence = self.get_bet_sequence(style)
        return sum(sequence)


class GamePhase(IntEnum):
    """Game phase enumeration (matches K-means cluster IDs)"""
    LOADING = 0      # Gray loading screen
    WAITING = 1      # Waiting for next round
    COUNTDOWN = 2    # Countdown before round starts
    PLAYING = 3      # Plane is flying
    CRASHED = 4      # Round ended
    RESULT = 5       # Showing results
    UNKNOWN = 99     # Cannot determine phase
    
    @classmethod
    def from_rgb(cls, r: float, g: float, b: float) -> 'GamePhase':
        """Determine phase from RGB values (requires trained model)"""
        # This would use the K-means model in practice
        # Simplified logic here for illustration
        brightness = (r + g + b) / 3
        
        if brightness < 50:
            return cls.LOADING
        elif brightness > 200:
            return cls.WAITING
        else:
            return cls.UNKNOWN
    
    @property
    def can_bet(self) -> bool:
        """Check if betting is allowed in this phase"""
        return self in [GamePhase.WAITING, GamePhase.COUNTDOWN]
    
    @property
    def is_active(self) -> bool:
        """Check if game is actively playing"""
        return self == GamePhase.PLAYING


@dataclass
class RegionConfig:
    """Configuration for screen regions"""
    
    # Default region sizes (can be overridden per bookmaker)
    default_widths = {
        'score': 150,
        'my_money': 200,
        'other_count': 100,
        'other_money': 200,
        'phase': 50
    }
    
    default_heights = {
        'score': 40,
        'my_money': 30,
        'other_count': 30,
        'other_money': 30,
        'phase': 50
    }
    
    # OCR preprocessing settings
    ocr_scale_factor: float = 2.0  # Scale image before OCR
    ocr_threshold: int = 127  # Binary threshold
    ocr_invert: bool = False  # Invert colors
    
    # Tesseract OCR config
    tesseract_config: str = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
    
    @classmethod
    def get_region_size(cls, region_type: str) -> tuple:
        """Get default width and height for a region type"""
        width = cls.default_widths.get(region_type, 100)
        height = cls.default_heights.get(region_type, 30)
        return (width, height)


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration"""
    
    # Thresholds for performance monitoring
    efficiency_threshold_excellent: float = 0.95  # >95% is excellent
    efficiency_threshold_good: float = 0.85  # 85-95% is good
    efficiency_threshold_warning: float = 0.75  # 75-85% needs attention
    
    # Queue monitoring
    queue_warning_size: int = 5000  # Warn if queue > 5000
    queue_critical_size: int = 8000  # Critical if queue > 8000
    
    # Timing thresholds
    max_ocr_time: float = 0.5  # Maximum acceptable OCR time
    max_db_write_time: float = 0.1  # Maximum DB write time
    max_batch_process_time: float = 1.0  # Maximum batch processing time
    
    # Stats reporting
    stats_report_interval: int = 30  # Report stats every 30 seconds
    detailed_logging_interval: int = 300  # Detailed stats every 5 minutes


# Create singleton instances
app_config = AppConstants()
bookmaker_config = BookmakerConfig()
region_config = RegionConfig()
performance_config = PerformanceConfig()

# Ensure all directories exist on import
app_config.ensure_directories()

# Export commonly used items
__all__ = [
    'AppConstants',
    'BookmakerConfig',
    'GamePhase',
    'RegionConfig',
    'PerformanceConfig',
    'app_config',
    'bookmaker_config',
    'region_config',
    'performance_config'
]