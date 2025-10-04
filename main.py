# main.py
"""
Aviator Data Collection System - Main Entry Point
Version: 4.0
Multi-bookmaker parallel data collection with betting simulation
"""

import sys
import signal
import time
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import app_config, bookmaker_config
from logger import init_logging, AviatorLogger
from core.bookmaker_orchestrator import BookmakerOrchestrator
from core.coord_manager import CoordsManager
from database.worker import get_worker, stop_worker
from utils.diagnostic import run_diagnostics
from utils.performance_analyzer import PerformanceAnalyzer


class AviatorSystem:
    """Main system controller for Aviator data collection"""
    
    def __init__(self):
        """Initialize the Aviator system"""
        self.logger = None
        self.orchestrator = None
        self.db_worker = None
        self.coords_manager = None
        self.is_running = False
        self.start_time = None
        
    def initialize(self) -> bool:
        """
        Initialize all system components
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize logging
            init_logging(debug=app_config.debug)
            self.logger = AviatorLogger.get_logger("AviatorSystem")
            
            self.logger.info("="*70)
            self.logger.info("AVIATOR DATA COLLECTION SYSTEM v4.0")
            self.logger.info("="*70)
            
            # Run diagnostics
            self.logger.info("Running system diagnostics...")
            if not run_diagnostics(quick=True):
                self.logger.error("System diagnostics failed!")
                return False
            
            # Initialize coordinates manager
            self.coords_manager = CoordsManager()
            
            # Start database worker
            self.logger.info("Starting database worker...")
            self.db_worker = get_worker()
            
            # Initialize orchestrator
            self.logger.info("Initializing bookmaker orchestrator...")
            self.orchestrator = BookmakerOrchestrator()
            
            self.logger.info("System initialization complete")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.critical(f"Initialization failed: {e}", exc_info=True)
            else:
                print(f"CRITICAL: Initialization failed: {e}")
            return False
    
    def configure_bookmakers(self) -> bool:
        """
        Configure bookmakers for data collection
        
        Returns:
            True if at least one bookmaker configured
        """
        try:
            self.logger.info("\n" + "="*70)
            self.logger.info("BOOKMAKER CONFIGURATION")
            self.logger.info("="*70)
            
            # Get configuration choice
            print("\nConfiguration Options:")
            print("1. Use existing configuration")
            print("2. Create new configuration")
            print("3. Quick test mode (1 bookmaker)")
            
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "3":
                # Quick test mode
                return self._configure_test_mode()
            elif choice == "2":
                # New configuration
                return self._configure_new_bookmakers()
            else:
                # Existing configuration
                return self._load_existing_configuration()
                
        except Exception as e:
            self.logger.error(f"Configuration failed: {e}", exc_info=True)
            return False
    
    def _configure_test_mode(self) -> bool:
        """Configure single bookmaker for testing"""
        self.logger.info("Configuring test mode with 1 bookmaker...")
        
        # Setup test bookmaker
        test_config = {
            'name': 'TestBookmaker',
            'position': 'Center',
            'bet_style': 'balanced',
            'collection_interval': 0.2
        }
        
        # Setup coordinates
        print("\n📍 Setting up test bookmaker coordinates...")
        print("Please position the game window and follow instructions...")
        
        coords = self.coords_manager.setup_bookmaker_interactive(
            test_config['name'],
            test_config['position']
        )
        
        if coords:
            # Save configuration
            config_name = 'test_config'
            self.coords_manager.save_coordinates(config_name, 'Center', coords)
            
            # Add to orchestrator
            self.orchestrator.add_bookmaker(
                name=test_config['name'],
                coords=coords,
                bet_style=test_config['bet_style'],
                collection_interval=test_config['collection_interval']
            )
            
            self.logger.info("Test mode configured successfully")
            return True
        
        return False
    
    def _configure_new_bookmakers(self) -> bool:
        """Configure multiple bookmakers interactively"""
        config_name = input("\nEnter configuration name: ").strip()
        if not config_name:
            config_name = f"config_{int(time.time())}"
        
        num_bookmakers = int(input("Number of bookmakers (1-6): ").strip() or "3")
        num_bookmakers = max(1, min(6, num_bookmakers))
        
        configured = 0
        
        for i in range(num_bookmakers):
            print(f"\n{'='*60}")
            print(f"BOOKMAKER {i+1}/{num_bookmakers}")
            print(f"{'='*60}")
            
            # Get bookmaker details
            name = input(f"Bookmaker name: ").strip()
            if not name:
                name = f"Bookmaker_{i+1}"
            
            position = ['Left', 'Center', 'Right', 'TopLeft', 'TopCenter', 'TopRight'][i]
            
            # Choose betting style
            print("\nBetting styles:")
            print("1. Cautious (low risk)")
            print("2. Balanced (moderate)")
            print("3. Risky (high risk)")
            print("4. Crazy (very high)")
            print("5. Addict (extreme)")
            print("6. All-in (maximum)")
            
            style_choice = int(input("Select style (1-6): ").strip() or "2")
            styles = ['cautious', 'balanced', 'risky', 'crazy', 'addict', 'all-in']
            bet_style = styles[style_choice - 1] if 1 <= style_choice <= 6 else 'balanced'
            
            # Setup coordinates
            print(f"\n📍 Setting up coordinates for {name}...")
            coords = self.coords_manager.setup_bookmaker_interactive(name, position)
            
            if coords:
                # Save coordinates
                self.coords_manager.save_coordinates(config_name, position, coords)
                
                # Add to orchestrator
                self.orchestrator.add_bookmaker(
                    name=name,
                    coords=coords,
                    bet_style=bet_style,
                    collection_interval=app_config.default_collection_interval
                )
                
                configured += 1
                self.logger.info(f"Configured {name} ({position}) with {bet_style} strategy")
            else:
                self.logger.warning(f"Failed to configure {name}")
        
        self.logger.info(f"Configured {configured}/{num_bookmakers} bookmakers")
        return configured > 0
    
    def _load_existing_configuration(self) -> bool:
        """Load existing bookmaker configuration"""
        # List available configurations
        configs = self.coords_manager.list_configurations()
        
        if not configs:
            self.logger.warning("No existing configurations found")
            return False
        
        print("\nAvailable configurations:")
        for i, config in enumerate(configs, 1):
            print(f"{i}. {config}")
        
        choice = input("\nSelect configuration: ").strip()
        
        try:
            if choice.isdigit():
                config_name = configs[int(choice) - 1]
            else:
                config_name = choice
            
            # Load configuration
            bookmakers = self.coords_manager.load_configuration(config_name)
            
            if not bookmakers:
                self.logger.error(f"Configuration '{config_name}' is empty")
                return False
            
            # Add bookmakers to orchestrator
            for position, data in bookmakers.items():
                # Get betting style
                print(f"\nSelect betting style for {data.get('name', position)}:")
                print("1=Cautious, 2=Balanced, 3=Risky, 4=Crazy, 5=Addict, 6=All-in")
                style_choice = int(input("Choice (1-6): ").strip() or "2")
                
                styles = ['cautious', 'balanced', 'risky', 'crazy', 'addict', 'all-in']
                bet_style = styles[style_choice - 1] if 1 <= style_choice <= 6 else 'balanced'
                
                self.orchestrator.add_bookmaker(
                    name=data.get('name', position),
                    coords=data,
                    bet_style=bet_style,
                    collection_interval=app_config.default_collection_interval
                )
            
            self.logger.info(f"Loaded {len(bookmakers)} bookmakers from '{config_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def start(self) -> None:
        """Start the data collection system"""
        try:
            self.logger.info("\n" + "="*70)
            self.logger.info("STARTING DATA COLLECTION")
            self.logger.info("="*70)
            
            self.is_running = True
            self.start_time = time.time()
            
            # Start orchestrator
            self.orchestrator.start()
            
            self.logger.info(f"System running with {self.orchestrator.worker_count} bookmakers")
            self.logger.info("Press Ctrl+C to stop...")
            
            # Main monitoring loop
            self._run_monitoring_loop()
            
        except KeyboardInterrupt:
            self.logger.info("\nReceived shutdown signal...")
        except Exception as e:
            self.logger.critical(f"System error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _run_monitoring_loop(self) -> None:
        """Main monitoring loop"""
        last_stats_time = time.time()
        
        while self.is_running:
            try:
                # Sleep briefly
                time.sleep(1)
                
                # Log statistics periodically
                if time.time() - last_stats_time >= 30:
                    self._log_system_stats()
                    last_stats_time = time.time()
                
                # Check system health
                if not self.orchestrator.is_healthy():
                    self.logger.warning("System health check failed")
                
            except KeyboardInterrupt:
                break
    
    def _log_system_stats(self) -> None:
        """Log system statistics"""
        runtime = time.time() - self.start_time
        
        # Get database stats
        db_stats = self.db_worker.get_stats()
        
        # Get orchestrator stats
        orch_stats = self.orchestrator.get_stats()
        
        self.logger.info("="*60)
        self.logger.info("SYSTEM STATISTICS")
        self.logger.info("="*60)
        self.logger.info(f"Runtime:        {runtime/60:.1f} minutes")
        self.logger.info(f"Bookmakers:     {orch_stats['active_workers']}/{orch_stats['total_workers']}")
        self.logger.info(f"DB Processed:   {db_stats['total_processed']:,}")
        self.logger.info(f"DB Queue:       {db_stats['queue_size']:,}")
        self.logger.info(f"Throughput:     {db_stats['items_per_second']:.1f} items/sec")
        self.logger.info("="*60)
    
    def stop(self) -> None:
        """Stop the system gracefully"""
        self.logger.info("\n" + "="*70)
        self.logger.info("SHUTTING DOWN SYSTEM")
        self.logger.info("="*70)
        
        self.is_running = False
        
        # Stop orchestrator
        if self.orchestrator:
            self.logger.info("Stopping bookmaker orchestrator...")
            self.orchestrator.stop()
        
        # Stop database worker
        self.logger.info("Stopping database worker...")
        stop_worker()
        
        # Log final statistics
        if self.start_time:
            runtime = time.time() - self.start_time
            self.logger.info(f"Total runtime: {runtime/60:.1f} minutes")
        
        # Run performance analysis
        self.logger.info("Running final performance analysis...")
        analyzer = PerformanceAnalyzer()
        analyzer.analyze_session()
        
        self.logger.info("System shutdown complete")
        self.logger.info("="*70)


def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\n[SIGNAL] Shutdown requested...")
    sys.exit(0)


def main():
    """Main entry point"""
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    
    # Set multiprocessing start method
    mp.set_start_method('spawn', force=True)
    
    # Create and run system
    system = AviatorSystem()
    
    # Initialize
    if not system.initialize():
        print("Failed to initialize system!")
        sys.exit(1)
    
    # Configure bookmakers
    if not system.configure_bookmakers():
        print("No bookmakers configured!")
        sys.exit(1)
    
    # Start system
    system.start()
    
    # Exit cleanly
    sys.exit(0)


if __name__ == "__main__":
    main()