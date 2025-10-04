# main.py
# VERSION: 2.1
# CHANGES: Fixed signal handler for graceful shutdown, improved Ctrl+C handling

"""
Aviator Game Data Collection Application
Collects game data from demo mode for AI pattern analysis
Supports multiple parallel bookmakers (up to 6)

SHUTDOWN: Press Ctrl+C to gracefully stop all processes
"""

from main.bookmaker_orchestrator import BookmakerOrchestrator
from main.coord_getter import CoordGetter
from main.coord_manager import CoordsManager
from database.setup import setup_database
from config import AppConstants, BookmakerConfig
from root.logger import init_logging, AviatorLogger

import signal
import sys
import time
from typing import List, Dict


# Global orchestrator for signal handler access
orchestrator = None


def signal_handler(signum, frame):
    """
    Handle Ctrl+C (SIGINT) gracefully.
    
    CRITICAL: This allows user to stop application with Ctrl+C
    instead of requiring Alt+F4 or Task Manager.
    """
    logger = AviatorLogger.get_logger("Main")
    logger.info("\n" + "="*60)
    logger.info("CTRL+C DETECTED - Initiating graceful shutdown...")
    logger.info("="*60)
    
    global orchestrator
    if orchestrator:
        orchestrator.stop()
    
    logger.info("Application stopped successfully")
    sys.exit(0)


def setup_bookmaker_coordinates(bookmaker_name: str, position: str) -> Dict:
    """Interactive setup for bookmaker screen regions and coordinates."""
    logger = AviatorLogger.get_logger("Setup")
    
    print(f"\n{'='*60}")
    print(f"Setting up: {bookmaker_name} ({position} position)")
    print(f"{'='*60}\n")
    
    config = {}
    
    try:
        print("\n[1/7] Setting up SCORE region...")
        print("Click top-left corner, then bottom-right corner of the score display")
        score_getter = CoordGetter(bookmaker_name, "Score Region", "region")
        config['score_region'] = score_getter.get_region()
        logger.info(f"Score region set: {config['score_region']}")
        
        print("\n[2/7] Setting up MY MONEY region...")
        print("Click top-left corner, then bottom-right corner of your balance display")
        my_money_getter = CoordGetter(bookmaker_name, "My Money Region", "region")
        config['my_money_region'] = my_money_getter.get_region()
        logger.info(f"My money region set: {config['my_money_region']}")
        
        print("\n[3/7] Setting up OTHER COUNT region...")
        print("Click top-left corner, then bottom-right corner of the player count display")
        other_count_getter = CoordGetter(bookmaker_name, "Other Count Region", "region")
        config['other_count_region'] = other_count_getter.get_region()
        logger.info(f"Other count region set: {config['other_count_region']}")
        
        print("\n[4/7] Setting up OTHER MONEY region...")
        print("Click top-left corner, then bottom-right corner of total players' winnings")
        other_money_getter = CoordGetter(bookmaker_name, "Other Money Region", "region")
        config['other_money_region'] = other_money_getter.get_region()
        logger.info(f"Other money region set: {config['other_money_region']}")
        
        print("\n[5/7] Setting up PHASE DETECTION region...")
        print("Click top-left corner, then bottom-right corner for phase color detection")
        print("(Can be same as score region, or a specific area that changes color)")
        phase_getter = CoordGetter(bookmaker_name, "Phase Region", "region")
        config['phase_region'] = phase_getter.get_region()
        logger.info(f"Phase region set: {config['phase_region']}")
        
        print("\n[6/7] Setting up BET AMOUNT input field...")
        print("Click on the bet amount input field")
        amount_getter = CoordGetter(bookmaker_name, "Bet Amount Field", "coordinate")
        config['play_amount_coords'] = amount_getter.get_coordinate()
        logger.info(f"Bet amount coords set: {config['play_amount_coords']}")
        
        print("\n[7/7] Setting up PLAY BUTTON...")
        print("Click on the PLAY/BET button")
        button_getter = CoordGetter(bookmaker_name, "Play Button", "coordinate")
        config['play_button_coords'] = button_getter.get_coordinate()
        logger.info(f"Play button coords set: {config['play_button_coords']}")
        
        print(f"\n{'='*60}")
        print(f"✓ Setup complete for {bookmaker_name} ({position})!")
        print(f"{'='*60}\n")
        
        return config
        
    except Exception as e:
        logger.error(f"Setup error: {e}", exc_info=True)
        raise


def choose_gambling_style(bookmaker_name: str) -> List[int]:
    """Let user choose a gambling style and return the corresponding bet sequence."""
    print(f"\n[OPTIONAL] Choose gambling style for {bookmaker_name}")
    print("\nGambling styles:")
    print("1. Cautious (low risk)")
    print("2. Balanced (moderate risk)")
    print("3. Risky (high risk)")
    print("4. Crazy (very high risk)")
    print("5. Addict (extreme risk)")
    print("6. All-in (maximum risk)")
    
    choice = input("\nEnter choice (1-6, default 1): ").strip()
    choice = int(choice) if choice.isdigit() and 1 <= int(choice) <= 6 else 1
    
    styles = {
        1: BookmakerConfig.bet_style['cautious'],
        2: BookmakerConfig.bet_style['balanced'],
        3: BookmakerConfig.bet_style['risky'],
        4: BookmakerConfig.bet_style['crazy'],
        5: BookmakerConfig.bet_style['addict'],
        6: BookmakerConfig.bet_style['all-in']
    }
    
    gambling_style = styles.get(choice, BookmakerConfig.bet_style['cautious'])
    
    try:
        bet_length = int(input(
            f"\n[OPTIONAL] Enter bet length for {bookmaker_name}"
            f"\n\tOptions: (5-10, default: {BookmakerConfig.bet_length}): "
        ).strip() or BookmakerConfig.bet_length)
    except ValueError:
        bet_length = BookmakerConfig.bet_length
    
    bet_length = max(5, min(bet_length, len(gambling_style)))
    return gambling_style[:bet_length]


def get_bookmaker_configs_interactive(coords_manager: CoordsManager) -> List[Dict]:
    """Interactive setup for 3 bookmakers with coordinate saving."""
    logger = AviatorLogger.get_logger("Main")
    
    bookmaker_positions = [
        ("Left", "BalkanBet"),
        ("Center", "Mozzart"),
        ("Right", "Soccer")
    ]
    
    print("\n" + "="*60)
    print("BOOKMAKER CONFIGURATION")
    print("="*60)
    print("\nOptions:")
    print("1. Use existing configuration")
    print("2. Create new configuration")
    
    choice = input("\nEnter choice (1-2): ").strip()
    
    if choice == "1":
        config_name = input("Enter configuration name (e.g., '3_bookmakers_console'): ").strip()
        if not config_name:
            config_name = "3_bookmakers_console"
        
        try:
            configs = []
            for position, name in bookmaker_positions:
                coords = coords_manager.load_coordinates(config_name, position)
                configs.append({
                    'name': name,
                    'bet_sequence': choose_gambling_style(name),
                    **coords
                })
                logger.info(f"Loaded bookmaker {len(configs)}: {name} ({position})")
            return configs
        except FileNotFoundError:
            print(f"\nConfiguration '{config_name}' not found. Creating new configuration...")
            choice = "2"
    
    if choice == "2":
        config_name = input("Enter new configuration name (e.g., '3_bookmakers_console'): ").strip()
        if not config_name:
            config_name = "3_bookmakers_console"
        
        logger.info(f"Starting interactive setup for {len(bookmaker_positions)} bookmakers")
        
        configs = []
        for idx, (position, name) in enumerate(bookmaker_positions, 1):
            print(f"\n{'='*60}")
            print(f"BOOKMAKER {idx}/{len(bookmaker_positions)}")
            print(f"{'='*60}")
            
            coords = setup_bookmaker_coordinates(name, position)
            coords_manager.save_coordinates(config_name, position, coords)
            
            configs.append({
                'name': name,
                'bet_sequence': choose_gambling_style(name),
                **coords
            })
            
            logger.info(f"Bookmaker {idx}/{len(bookmaker_positions)} configured: {name} ({position})")
        
        return configs
    
    raise ValueError("Invalid choice")


def main():
    """Main application entry point."""
    global orchestrator
    
    # CRITICAL: Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize logging
    logger = init_logging()
    
    logger.info("=" * 60)
    logger.info(f"Aviator Data Collection Started - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Debug mode: {AppConstants.debug}")
    logger.info("=" * 60)
    
    try:
        # Setup database
        logger.info("Setting up database...")
        setup_database()
        
        # Initialize coords manager
        coords_manager = CoordsManager()
        
        # Get bookmaker configurations
        bookmaker_configs = get_bookmaker_configs_interactive(coords_manager)
        
        # Create orchestrator
        orchestrator = BookmakerOrchestrator()
        
        # Add bookmakers to orchestrator
        for config in bookmaker_configs:
            orchestrator.add_bookmaker(
                name=config['name'],
                auto_stop=BookmakerConfig.auto_stop,
                target_money=BookmakerConfig.target_money,
                play_amount_coords=config['play_amount_coords'],
                play_button_coords=config['play_button_coords'],
                bet_sequence=config['bet_sequence'],
                score_region=config['score_region'],
                my_money_region=config['my_money_region'],
                other_count_region=config['other_count_region'],
                other_money_region=config['other_money_region'],
                phase_region=config['phase_region']
            )
            logger.info(f"Added bookmaker: {config['name']} (auto_stop={BookmakerConfig.auto_stop}, target={BookmakerConfig.target_money})")
        
        # Start data collection
        logger.info(f"Starting data collection with {len(bookmaker_configs)} parallel bookmakers...")
        logger.info("Press Ctrl+C to stop gracefully")
        orchestrator.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # This should not be reached due to signal handler, but just in case
            logger.info("KeyboardInterrupt caught in main loop")
            orchestrator.stop()
        
    except Exception as e:
        logger.critical(f"Critical application error: {e}", exc_info=True)
        if orchestrator:
            orchestrator.stop()
        sys.exit(1)
    
    finally:
        logger.info("Application stopped")
        logger.info(f"Check '{AppConstants.database}' for collected data")
        logger.info(f"Check 'logs/{AppConstants.log_file}' for detailed logs")


if __name__ == "__main__":
    main()