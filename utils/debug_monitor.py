# debug_monitor.py
# Real-time OCR debug monitor - loguje šta vidi na svim regionima

from main.screen_reader import ScreenReader
from main.coord_manager import CoordsManager
from regions.game_phase import GamePhaseDetector
from regions.score import Score
from regions.region_MyMoney import MyMoney
from regions.other_count import OtherCount
from regions.other_money import OtherMoney
from config import GamePhase, AppConstants
from root.logger import init_logging, AviatorLogger

import time
import signal
import sys


class DebugMonitor:
    """Real-time OCR debug monitor"""
    
    def __init__(self, bookmaker_name: str, regions: dict, interval: float = 0.5):
        self.bookmaker_name = bookmaker_name
        self.regions = regions
        self.interval = interval
        self.running = False
        
        self.logger = AviatorLogger.get_logger(f"Debug-{bookmaker_name}")
        
        # Initialize readers
        self.phase_detector = GamePhaseDetector(regions['phase_region'])
        self.score_reader = Score(
            regions['score_region'],
            regions['my_money_region'],
            2.0  # dummy auto_stop
        )
        self.my_money_reader = MyMoney(regions['my_money_region'])
        self.other_count_reader = OtherCount(regions['other_count_region'])
        self.other_money_reader = OtherMoney(regions['other_money_region'])
    
    def start(self):
        """Start monitoring"""
        self.running = True
        self.logger.info(f"Debug monitor started for {self.bookmaker_name}")
        self.logger.info(f"Reading interval: {self.interval}s")
        
        try:
            while self.running:
                self._read_and_log()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.logger.info("Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}", exc_info=True)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
    
    def _read_and_log(self):
        """Read all regions and log"""
        try:
            # Phase
            phase = self.phase_detector.detect_phase()
            phase_name = GamePhase(phase).name if phase != GamePhase.UNKNOWN else "UNKNOWN"
            
            # Score
            score_data = self.score_reader.read_text()
            score_str = f"{score_data.get('score', 0):.2f}x" if score_data else "N/A"
            
            # My Money
            money_data = self.my_money_reader.read_text()
            money_str = f"{money_data.get('money', 0):.2f}" if money_data else "N/A"
            
            # Other Count
            count_data = self.other_count_reader.read_text()
            count_str = f"{count_data.get('currently_playing', 0)}/{count_data.get('total_players', 0)}" if count_data else "N/A"
            
            # Other Money
            other_money_data = self.other_money_reader.read_text()
            other_money_str = f"{other_money_data.get('total_money', 0):.2f}" if other_money_data else "N/A"
            
            # Log everything
            self.logger.info(
                f"Phase: {phase_name:10s} | "
                f"Score: {score_str:8s} | "
                f"MyMoney: {money_str:10s} | "
                f"Players: {count_str:10s} | "
                f"TotalBets: {other_money_str:10s}"
            )
            
        except Exception as e:
            self.logger.error(f"Read error: {e}")


def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("\nStopping debug monitor...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    init_logging()
    logger = AviatorLogger.get_logger("Main")
    
    logger.info("=" * 60)
    logger.info("DEBUG MONITOR - Real-time OCR Debug")
    logger.info("=" * 60)
    
    try:
        coords_manager = CoordsManager()
        
        # Load configuration
        config_name = input("Configuration name: ").strip()
        position = input("Position (e.g., Left, Center, Right): ").strip()
        interval = float(input("Read interval in seconds (default 0.5): ").strip() or "0.5")
        
        # Load coordinates
        regions = coords_manager.load_coordinates(config_name, position)
        
        # Start monitor
        monitor = DebugMonitor(position, regions, interval)
        
        logger.info(f"Starting monitor for {position}")
        logger.info("Press Ctrl+C to stop")
        
        monitor.start()
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
