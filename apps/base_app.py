# apps/base_app.py
# VERSION: 1.0
# Base template for all Aviator apps with region verification

import sys
import signal
from pathlib import Path
from typing import Dict, List, Optional
from multiprocessing import Process, Event
from abc import ABC, abstractmethod

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import init_logging, AviatorLogger
from core.coord_manager import CoordsManager
from utils.region_visualizer import RegionVisualizer


class BaseAviatorApp(ABC):
    """
    Base class for all Aviator applications.
    
    Features:
    - Automatic region verification on startup
    - Multi-bookmaker support with multiprocessing
    - Proper shutdown handling
    - Standardized logging
    """
    
    def __init__(self, app_name: str):
        """
        Initialize base app.
        
        Args:
            app_name: Name of the application (e.g., 'DataCollector')
        """
        self.app_name = app_name
        init_logging()
        self.logger = AviatorLogger.get_logger(app_name)
        self.coords_manager = CoordsManager()
        
        self.processes: List[Process] = []
        self.shutdown_event = Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"{app_name} initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info("Shutdown signal received")
        print(f"\n\n{'='*60}")
        print(f"🛑 Stopping {self.app_name}...")
        print(f"{'='*60}")
        self.shutdown()
        sys.exit(0)
    
    def verify_regions(
        self, 
        bookmakers_config: List[Dict[str, str]]
    ) -> bool:
        """
        Verify regions for all bookmakers before starting.
        
        Args:
            bookmakers_config: List of dicts with 'bookmaker', 'layout', 'position'
        
        Returns:
            True if user confirms regions are correct
        """
        print("\n" + "="*60)
        print("🔍 REGION VERIFICATION")
        print("="*60)
        print("\nGenerating region visualizations for all bookmakers...")
        print("Please check that all regions are correctly positioned.")
        
        screenshots = []
        
        for i, config in enumerate(bookmakers_config, 1):
            bookmaker = config['bookmaker']
            layout = config['layout']
            position = config['position']
            
            print(f"\n[{i}/{len(bookmakers_config)}] {bookmaker} @ {position}")
            
            try:
                # Get final coordinates
                coords = self.coords_manager.calculate_coords(
                    bookmaker, layout, position
                )
                
                if not coords:
                    self.logger.error(f"Could not load coords for {bookmaker}")
                    print(f"  ❌ Failed to load coordinates")
                    return False
                
                # Create visualizer
                visualizer = RegionVisualizer(
                    bookmaker_name=bookmaker,
                    coords=coords,
                    position=position
                )
                
                # Save screenshot
                filepath = visualizer.save_visualization()
                screenshots.append(filepath)
                visualizer.cleanup()
                
                print(f"  ✅ Screenshot saved: {filepath}")
                
            except Exception as e:
                self.logger.error(f"Visualization error: {e}", exc_info=True)
                print(f"  ❌ Error: {e}")
                return False
        
        # Ask for confirmation
        print("\n" + "="*60)
        print("📸 SCREENSHOTS SAVED:")
        for screenshot in screenshots:
            print(f"  • {screenshot}")
        
        print("\n" + "="*60)
        print("Please open the screenshots and verify regions are correct.")
        response = input("\nAre all regions correctly positioned? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            self.logger.info("Regions verified - proceeding with startup")
            return True
        else:
            self.logger.warning("Region verification failed - user cancelled")
            print("\n❌ Please adjust coordinates and try again.")
            return False
    
    def setup_bookmakers_interactive(
        self, 
        num_bookmakers: int
    ) -> List[Dict[str, str]]:
        """
        Interactive setup for bookmakers.
        
        Args:
            num_bookmakers: Number of bookmakers to configure
        
        Returns:
            List of bookmaker configurations
        """
        print("\n" + "="*60)
        print(f"BOOKMAKER SETUP ({num_bookmakers} bookmakers)")
        print("="*60)
        
        # Show available options
        self.coords_manager.display_info()
        
        bookmakers_config = []
        
        for i in range(1, num_bookmakers + 1):
            print(f"\n--- BOOKMAKER {i} ---")
            
            # Get bookmaker name
            available_bookmakers = self.coords_manager.get_available_bookmakers()
            print(f"Available: {', '.join(available_bookmakers)}")
            bookmaker = input(f"Bookmaker name: ").strip()
            
            # Get layout
            available_layouts = self.coords_manager.get_available_layouts()
            print(f"Available layouts: {', '.join(available_layouts)}")
            layout = input(f"Layout name: ").strip()
            
            # Get position
            available_positions = self.coords_manager.get_available_positions(layout)
            print(f"Available positions: {', '.join(available_positions)}")
            position = input(f"Position: ").strip()
            
            bookmakers_config.append({
                'bookmaker': bookmaker,
                'layout': layout,
                'position': position
            })
        
        return bookmakers_config
    
    def create_process(
        self, 
        bookmaker: str,
        layout: str,
        position: str,
        **kwargs
    ) -> Optional[Process]:
        """
        Create a process for a bookmaker.
        To be implemented by child classes.
        
        Args:
            bookmaker: Bookmaker name
            layout: Layout name
            position: Position in layout
            **kwargs: Additional arguments for specific app
        
        Returns:
            Process instance or None
        """
        raise NotImplementedError("Child class must implement create_process()")
    
    def start_processes(
        self, 
        bookmakers_config: List[Dict[str, str]],
        **kwargs
    ) -> None:
        """
        Start all bookmaker processes.
        
        Args:
            bookmakers_config: List of bookmaker configurations
            **kwargs: Additional arguments passed to create_process()
        """
        print("\n" + "="*60)
        print(f"🚀 STARTING {self.app_name}")
        print("="*60)
        
        for config in bookmakers_config:
            bookmaker = config['bookmaker']
            layout = config['layout']
            position = config['position']
            
            # Get final coordinates
            coords = self.coords_manager.calculate_coords(
                bookmaker, layout, position
            )
            
            if not coords:
                self.logger.error(f"Could not load coords for {bookmaker}")
                continue
            
            # Create process
            process = self.create_process(
                bookmaker=bookmaker,
                layout=layout,
                position=position,
                coords=coords,
                **kwargs
            )
            
            if process:
                process.start()
                self.processes.append(process)
                self.logger.info(f"Started process for {bookmaker}")
                print(f"  ✅ Started: {bookmaker}")
        
        print("\n" + "="*60)
        print(f"✅ All processes started ({len(self.processes)} bookmakers)")
        print("="*60)
    
    def wait_for_processes(self) -> None:
        """Wait for all processes to complete."""
        try:
            for process in self.processes:
                process.join()
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt - shutting down")
            self.shutdown()
    
    def shutdown(self) -> None:
        """Shutdown all processes gracefully."""
        self.logger.info("Initiating shutdown...")
        self.shutdown_event.set()
        
        # Wait for processes with timeout
        for process in self.processes:
            process.join(timeout=5)
            if process.is_alive():
                self.logger.warning(f"Force terminating: {process.name}")
                process.terminate()
        
        self.logger.info("Shutdown complete")
        print("\n✅ All processes stopped")
    
    @abstractmethod
    def run(self) -> None:
        """
        Main run method - to be implemented by child classes.
        """
        raise NotImplementedError("Child class must implement run()")


def get_number_input(prompt: str, min_val: int, max_val: int) -> int:
    """Helper function to get validated number input."""
    while True:
        try:
            value = int(input(prompt).strip())
            if min_val <= value <= max_val:
                return value
            print(f"Please enter a number between {min_val} and {max_val}")
        except ValueError:
            print("Invalid input. Please enter a number.")


if __name__ == "__main__":
    print("This is a base template class. Use specific app implementations.")