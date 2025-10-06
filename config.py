# config.py
# VERSION: 5.0 - Reworked for new system
# Centralized configuration for all modules

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Dict, List


# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()


class GamePhase(IntEnum):
    """Game phase enumeration."""
    UNKNOWN = 0
    WAITING = 1
    FLYING = 2
    CRASHED = 3


class BetState(IntEnum):
    """Bet button state enumeration."""
    UNKNOWN = 0
    INACTIVE = 1    # Red - Cannot bet
    READY = 2       # Orange - Can place bet
    ACTIVE = 3      # Green - Bet placed


@dataclass
class PathConfig:
    """Path configuration for all data directories."""
    
    # Root directories
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / 'data'
    logs_dir: Path = PROJECT_ROOT / 'logs'
    tests_dir: Path = PROJECT_ROOT / 'tests'
    
    # Data subdirectories
    database_dir: Path = data_dir / 'databases'
    models_dir: Path = data_dir / 'models'
    coords_dir: Path = data_dir / 'coordinates'
    screenshots_dir: Path = tests_dir / 'screenshots'
    
    # Specific files
    bookmaker_coords: Path = coords_dir / 'bookmaker_coords.json'
    javascript_css: Path = project_root / 'javascript.txt'
    
    # Database files
    main_game_db: Path = database_dir / 'main_game_data.db'
    rgb_training_db: Path = database_dir / 'rgb_training_data.db'
    betting_history_db: Path = database_dir / 'betting_history.db'
    
    # ML models
    phase_model: Path = models_dir / 'game_phase_kmeans.pkl'
    button_model: Path = models_dir / 'bet_button_kmeans.pkl'
    
    def ensure_directories(self):
        """Create all necessary directories."""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.tests_dir,
            self.database_dir,
            self.models_dir,
            self.coords_dir,
            self.screenshots_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class OCRConfig:
    """OCR configuration."""
    
    # Tesseract path (adjust for your system)
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows
    # tesseract_path: str = "/usr/bin/tesseract"  # Linux
    
    # OCR parameters
    config_score: str = '--psm 7 -c tessedit_char_whitelist=0123456789.x'
    config_money: str = '--psm 7 -c tessedit_char_whitelist=0123456789.,'
    config_count: str = '--psm 7 -c tessedit_char_whitelist=0123456789/'
    
    # Preprocessing
    scale_factor: int = 2
    threshold_value: int = 127
    use_adaptive_threshold: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    # Performance settings
    batch_size: int = 50
    batch_timeout: float = 1.0
    max_queue_size: int = 10000
    
    # SQLite optimizations
    journal_mode: str = 'WAL'
    synchronous: str = 'NORMAL'
    cache_size: int = -64000  # 64MB
    temp_store: str = 'MEMORY'
    
    # Checkpoint settings
    checkpoint_interval: int = 1000
    checkpoint_threshold: int = 1000
    
    @property
    def pragma_statements(self) -> List[str]:
        """Get pragma statements for SQLite optimization."""
        return [
            f"PRAGMA journal_mode = {self.journal_mode}",
            f"PRAGMA synchronous = {self.synchronous}",
            f"PRAGMA cache_size = {self.cache_size}",
            f"PRAGMA temp_store = {self.temp_store}",
            "PRAGMA locking_mode = EXCLUSIVE",
            "PRAGMA mmap_size = 268435456"  # 256MB
        ]


@dataclass
class CollectionConfig:
    """Data collection configuration."""
    
    # Collection intervals
    default_interval: float = 0.2  # 200ms
    rgb_interval: float = 0.5      # 500ms for RGB sampling
    betting_interval: float = 0.5  # 500ms for betting checks
    
    # Score thresholds for data collection
    score_thresholds: List[float] = None
    
    def __post_init__(self):
        if self.score_thresholds is None:
            self.score_thresholds = [1.5, 2.0, 3.0, 5.0, 10.0]
    
    # Multiprocessing
    max_workers: int = 6
    process_timeout: int = 5


@dataclass
class BettingConfig:
    """Betting configuration."""
    
    # Safety limits
    min_bet_amount: float = 10.0
    max_bet_amount: float = 10000.0
    min_auto_stop: float = 1.1
    max_auto_stop: float = 100.0
    
    # Timing
    click_delay: float = 0.1
    action_delay: float = 0.2
    round_end_wait: float = 2.0
    
    # Transaction safety
    use_bet_lock: bool = True
    lock_timeout: float = 30.0


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    # Log file settings
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # Format
    format: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Levels (for different modules)
    default_level: str = "INFO"
    ocr_level: str = "WARNING"
    database_level: str = "INFO"


@dataclass
class VisualizationConfig:
    """Region visualization configuration."""
    
    # Colors (RGB format)
    colors: Dict[str, tuple] = None
    
    # Labels
    labels: Dict[str, str] = None
    
    # Screenshot settings
    screenshot_format: str = "PNG"
    screenshot_quality: int = 95
    add_timestamp: bool = True
    add_header: bool = True
    
    def __post_init__(self):
        if self.colors is None:
            self.colors = {
                'score_region': (0, 255, 0),
                'my_money_region': (255, 0, 0),
                'other_count_region': (255, 128, 0),
                'other_money_region': (255, 255, 0),
                'phase_region': (255, 0, 255),
                'bet_amount_coords': (0, 0, 255),
                'play_button_coords': (0, 255, 255),
                'auto_play_coords': (128, 0, 255)
            }
        
        if self.labels is None:
            self.labels = {
                'score_region': 'SCORE',
                'my_money_region': 'MY MONEY',
                'other_count_region': 'PLAYER COUNT',
                'other_money_region': 'OTHER MONEY',
                'phase_region': 'PHASE',
                'bet_amount_coords': 'BET AMOUNT',
                'play_button_coords': 'PLAY BUTTON',
                'auto_play_coords': 'AUTO PLAY'
            }


@dataclass
class AppConfig:
    """Main application configuration."""
    
    # Sub-configs
    paths: PathConfig = None
    ocr: OCRConfig = None
    database: DatabaseConfig = None
    collection: CollectionConfig = None
    betting: BettingConfig = None
    logging: LoggingConfig = None
    visualization: VisualizationConfig = None
    
    # Application settings
    debug: bool = False
    language: str = 'en'
    
    def __post_init__(self):
        if self.paths is None:
            self.paths = PathConfig()
        if self.ocr is None:
            self.ocr = OCRConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.collection is None:
            self.collection = CollectionConfig()
        if self.betting is None:
            self.betting = BettingConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()
    
    def initialize(self):
        """Initialize application (create directories, etc.)"""
        self.paths.ensure_directories()


# Global configuration instance
config = AppConfig()


# Bookmaker information
BOOKMAKERS_INFO = {
    'BalkanBet': {
        'url': 'https://balkanbet.rs',
        'css_server': 'BALKANBET',
        'color_profile': 'dark'
    },
    'MaxBet': {
        'url': 'https://maxbet.rs',
        'css_server': 'MAXBET',
        'color_profile': 'light'
    },
    'Mozzart': {
        'url': 'https://mozzartbet.rs',
        'css_server': 'MOZZART',
        'color_profile': 'dark'
    },
    'Soccer': {
        'url': 'https://soccerbet.rs',
        'css_server': 'SOCCER',
        'color_profile': 'light'
    },
    'Admiral': {
        'url': 'https://admiralbet.rs',
        'css_server': 'ADMIRAL',
        'color_profile': 'dark'
    },
    'Meridian': {
        'url': 'https://meridianbet.rs',
        'css_server': 'MERIDIAN',
        'color_profile': 'dark'
    },
    'Merkur': {
        'url': 'https://merkurxtip.rs',
        'css_server': 'MERKUR',
        'color_profile': 'light'
    }
}


# Layout presets
LAYOUT_PRESETS = {
    '3_monitors_grid': {
        'description': '3 monitors, 2x3 grid',
        'total_bookmakers': 6,
        'window_size': (1280, 720)
    },
    '4_windows_fullhd': {
        'description': '1 monitor, 4 windows',
        'total_bookmakers': 4,
        'window_size': (960, 540)
    },
    '6_windows_compact': {
        'description': '2 monitors, 6 compact windows',
        'total_bookmakers': 6,
        'window_size': (640, 360)
    }
}


def get_bookmaker_info(bookmaker_name: str) -> Dict:
    """Get information about a bookmaker."""
    return BOOKMAKERS_INFO.get(bookmaker_name, {})


def get_layout_preset(layout_name: str) -> Dict:
    """Get preset information for a layout."""
    return LAYOUT_PRESETS.get(layout_name, {})


if __name__ == "__main__":
    # Test configuration
    print("="*60)
    print("AVIATOR SYSTEM CONFIGURATION v5.0")
    print("="*60)
    
    config.initialize()
    
    print(f"\n📁 Project Root: {config.paths.project_root}")
    print(f"📊 Databases: {config.paths.database_dir}")
    print(f"📝 Logs: {config.paths.logs_dir}")
    print(f"🎯 Coordinates: {config.paths.bookmaker_coords}")
    
    print(f"\n⚙️  Collection Interval: {config.collection.default_interval}s")
    print(f"⚙️  Batch Size: {config.database.batch_size}")
    print(f"⚙️  Max Workers: {config.collection.max_workers}")
    
    print(f"\n🎰 Bookmakers: {len(BOOKMAKERS_INFO)}")
    for name in BOOKMAKERS_INFO.keys():
        print(f"   • {name}")
    
    print(f"\n📐 Layout Presets: {len(LAYOUT_PRESETS)}")
    for name, info in LAYOUT_PRESETS.items():
        print(f"   • {name}: {info['description']}")
    
    print("\n" + "="*60)
    print("✅ Configuration loaded successfully")
    print("="*60)