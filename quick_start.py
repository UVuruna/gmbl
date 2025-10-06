# quick_start.py
# VERSION: 1.0
# Quick start helper for new users

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config, BOOKMAKERS_INFO


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "="*60)
    print(text.center(60))
    print("="*60)


def print_menu(title: str, options: list):
    """Print menu with options."""
    print(f"\n{title}")
    print("-" * len(title))
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")


def run_command(command: list, description: str):
    """Run subprocess command with description."""
    print(f"\n🚀 {description}...")
    print(f"   Command: {' '.join(command)}")
    print()
    
    try:
        subprocess.run(command, check=True)
        print(f"\n✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️  {description} interrupted")
        return False


def quick_test():
    """Quick system test."""
    print_header("QUICK SYSTEM TEST")
    
    print("\nThis will run a quick test of the system:")
    print("  1. Check Python version")
    print("  2. Check dependencies")
    print("  3. Check Tesseract")
    print("  4. Initialize databases")
    print("  5. Check coordinates")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        return
    
    run_command([sys.executable, 'setup.py'], "System check")


def setup_coordinates():
    """Setup coordinates interactively."""
    print_header("COORDINATE SETUP")
    
    print("\nChoose setup method:")
    print("  1. Create new coordinates (Region Editor)")
    print("  2. Migrate old coordinates (if you have old format)")
    print("  3. View current coordinates")
    print("  4. Back")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1':
        print("\n📝 Opening Region Editor...")
        print("   Use this to create coordinates for each bookmaker")
        run_command([sys.executable, 'utils/region_editor.py'], "Region Editor")
    
    elif choice == '2':
        print("\n🔄 Opening Migration Tool...")
        print("   This will convert old coordinate format to new")
        run_command([sys.executable, 'utils/coordinate_migrator.py'], "Coordinate Migration")
    
    elif choice == '3':
        print("\n📊 Current Coordinates:")
        from core.coord_manager import CoordsManager
        manager = CoordsManager()
        manager.display_info()
    
    else:
        return


def test_region_visualization():
    """Test region visualization."""
    print_header("REGION VISUALIZATION TEST")
    
    print("\nThis will capture screenshots of configured regions")
    print("to verify they are correctly positioned.")
    
    from core.coord_manager import CoordsManager
    manager = CoordsManager()
    
    layouts = manager.get_available_layouts()
    bookmakers = manager.get_available_bookmakers()
    
    if not layouts or not bookmakers:
        print("\n❌ No coordinates configured!")
        print("   Setup coordinates first (Option 2 from main menu)")
        return
    
    print(f"\nAvailable layouts: {', '.join(layouts)}")
    print(f"Available bookmakers: {', '.join(bookmakers)}")
    
    layout = input("\nLayout name: ").strip()
    bookmaker = input("Bookmaker name: ").strip()
    
    positions = manager.get_available_positions(layout)
    if not positions:
        print(f"\n❌ Layout '{layout}' not found")
        return
    
    print(f"\nAvailable positions: {', '.join(positions)}")
    position = input("Position: ").strip()
    
    # Calculate and visualize
    coords = manager.calculate_coords(bookmaker, layout, position)
    if not coords:
        print(f"\n❌ Could not calculate coordinates")
        return
    
    print("\n📸 Creating visualization...")
    from utils.region_visualizer import RegionVisualizer
    
    visualizer = RegionVisualizer(bookmaker, coords, position)
    filepath = visualizer.save_visualization()
    visualizer.cleanup()
    
    print(f"\n✅ Screenshot saved: {filepath}")
    print("   Open this file to verify region positions")


def css_injection_guide():
    """Show CSS injection guide."""
    print_header("CSS INJECTION GUIDE")
    
    print("\n⚠️  IMPORTANT: Before running any programs, inject CSS!")
    print("\nWhy? CSS removes unnecessary UI elements from bookmaker sites")
    print("to ensure accurate region detection.")
    
    print("\nSteps:")
    print("  1. Open bookmaker site in browser")
    print("  2. Open browser console (F12)")
    print("  3. Copy CSS from javascript.txt for that bookmaker")
    print("  4. Paste in console and press Enter")
    print("  5. Refresh if needed")
    
    if config.paths.javascript_css.exists():
        print(f"\n📝 CSS file location: {config.paths.javascript_css}")
        
        show = input("\nShow CSS for a bookmaker? (yes/no): ").strip().lower()
        if show in ['yes', 'y']:
            print(f"\nAvailable bookmakers:")
            for i, name in enumerate(BOOKMAKERS_INFO.keys(), 1):
                print(f"  {i}. {name}")
            
            choice = input("\nChoice: ").strip()
            try:
                idx = int(choice) - 1
                bookmaker = list(BOOKMAKERS_INFO.keys())[idx]
                
                print(f"\n--- CSS for {bookmaker} ---")
                with open(config.paths.javascript_css, 'r') as f:
                    content = f.read()
                    # Find section for this bookmaker
                    if bookmaker.upper() in content:
                        start = content.find(bookmaker.upper())
                        end = content.find("\n\n", start)
                        print(content[start:end])
                    else:
                        print("Not found in javascript.txt")
                
            except (ValueError, IndexError):
                print("Invalid choice")
    else:
        print("\n❌ javascript.txt not found!")


def run_program():
    """Run one of the main programs."""
    print_header("RUN PROGRAM")
    
    programs = [
        ("Main Data Collector", "apps/main_data_collector.py", 
         "Collects game statistics"),
        ("RGB Collector", "apps/rgb_collector.py", 
         "Collects RGB data for ML training"),
        ("Betting Agent", "apps/betting_agent.py", 
         "Automated betting (⚠️  REAL MONEY!)"),
    ]
    
    print("\nAvailable programs:")
    for i, (name, path, desc) in enumerate(programs, 1):
        print(f"  {i}. {name}")
        print(f"     {desc}")
    
    print("  4. Back")
    
    choice = input("\nChoice (1-4): ").strip()
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(programs):
            name, path, desc = programs[idx]
            
            print(f"\n⚠️  Before running {name}:")
            print("  ✅ CSS injected into bookmaker sites?")
            print("  ✅ Coordinates configured?")
            print("  ✅ Windows positioned correctly?")
            
            if "Betting" in name:
                print("\n⚠️⚠️⚠️  WARNING: BETTING AGENT USES REAL MONEY!")
                print("  ✅ Tested in demo mode?")
                print("  ✅ Ready to risk real money?")
            
            confirm = input("\nAll checks passed? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                run_command([sys.executable, path], name)
        
    except ValueError:
        print("Invalid choice")


def main_menu():
    """Main menu loop."""
    while True:
        print_header("🎰 AVIATOR QUICK START v5.0")
        
        options = [
            "Quick System Test (recommended for first time)",
            "Setup Coordinates (create or migrate)",
            "Test Region Visualization (verify positioning)",
            "CSS Injection Guide (important!)",
            "Run Program (collector or betting)",
            "View Documentation",
            "Exit"
        ]
        
        print_menu("Main Menu", options)
        
        choice = input("\nChoice (1-7): ").strip()
        
        if choice == '1':
            quick_test()
        
        elif choice == '2':
            setup_coordinates()
        
        elif choice == '3':
            test_region_visualization()
        
        elif choice == '4':
            css_injection_guide()
        
        elif choice == '5':
            run_program()
        
        elif choice == '6':
            print("\n📖 Documentation:")
            print("  • README.md - Full documentation")
            print("  • javascript.txt - CSS for bookmakers")
            print("  • config.py - System configuration")
            print("\nOnline: https://github.com/yourusername/aviator")
        
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("\n❌ Invalid choice")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
