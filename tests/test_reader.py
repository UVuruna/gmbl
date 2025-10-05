# test_screen_reader.py

from core.screen_reader import ScreenReader
from core.coord_getter import CoordGetter
import time

def test_screen_reader():
    """Test OCR screen reading on Score region"""
    
    print("="*60)
    print("SCREEN READER TEST")
    print("="*60)
    
    # Get Score region interactively
    print("\nClick on Score region (top-left then bottom-right):")
    coord_getter = CoordGetter("Test", "Score Region", "region")
    score_region = coord_getter.get_region()
    
    print(f"\nRegion selected: {score_region}")
    print("\nStarting continuous OCR reading...")
    print("Press Ctrl+C to stop\n")
    
    # Initialize screen reader
    reader = ScreenReader(score_region)
    
    try:
        while True:
            # Read text
            text = reader.read_once()
            
            # Display result
            print(f"OCR Result: '{text}'")
            
            # Try to parse as float
            try:
                # Clean text
                cleaned = text.strip().replace('x', '').replace(',', '.')
                if cleaned:
                    number = float(cleaned)
                    print(f"  → Parsed: {number}")
            except ValueError:
                print(f"  → Cannot parse as number")
            
            print("-" * 40)
            time.sleep(0.5)  # Read every 0.5s
            
    except KeyboardInterrupt:
        print("\n\nTest stopped.")
        reader.close()
    
    # Option to save last image
    save = input("\nSave last captured image? (y/n): ").strip().lower()
    if save == 'y':
        filename = "test_capture.png"
        if reader.save_last_capture(filename):
            print(f"Saved to: {filename}")
        else:
            print("Failed to save image")

if __name__ == "__main__":
    test_screen_reader()