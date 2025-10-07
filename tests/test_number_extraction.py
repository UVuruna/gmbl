# tests/test_number_extraction.py
# VERSION: 1.0
# Test script for number extraction

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.number_extractor import NumberExtractor, quick_extract


def test_basic_extraction():
    """Test basic number extraction."""
    print("\n" + "="*60)
    print("TEST: Basic Number Extraction")
    print("="*60)
    
    # Example: test with a screenshot
    image_path = input("Enter path to image (or press Enter for example): ").strip()
    
    if not image_path:
        print("\n⚠️  No image provided. Please provide an image path.")
        print("\nExample usage:")
        print("  python tests/test_number_extraction.py")
        print("  Then enter path like: screenshots/game_history.png")
        return
    
    if not Path(image_path).exists():
        print(f"\n❌ Image not found: {image_path}")
        return
    
    # Extract numbers
    print("\n🔍 Extracting numbers...")
    numbers = quick_extract(image_path, invert=True, debug=True)
    
    # Display results
    print("\n" + "="*60)
    print(f"✅ EXTRACTED {len(numbers)} NUMBERS")
    print("="*60)
    
    if numbers:
        # Show in formatted rows
        print("\nNumbers found:")
        for i in range(0, len(numbers), 10):
            row = numbers[i:i+10]
            print("  " + "  ".join(f"{n:6.2f}x" for n in row))
        
        # Statistics
        print("\n" + "-"*60)
        print("Statistics:")
        print(f"  Count: {len(numbers)}")
        print(f"  Min:   {min(numbers):.2f}x")
        print(f"  Max:   {max(numbers):.2f}x")
        print(f"  Avg:   {sum(numbers)/len(numbers):.2f}x")
        print("="*60)
    else:
        print("\n❌ No numbers extracted!")
        print("\nTips:")
        print("  - Check if text is visible in the image")
        print("  - Look at *_preprocessed.png to see what OCR sees")
        print("  - Try adjusting invert parameter")


def test_with_region():
    """Test extraction from specific region."""
    print("\n" + "="*60)
    print("TEST: Region-based Extraction")
    print("="*60)
    
    image_path = input("Enter path to image: ").strip()
    
    if not Path(image_path).exists():
        print(f"\n❌ Image not found: {image_path}")
        return
    
    print("\nEnter region coordinates:")
    print("Format: left,top,width,height")
    print("Example: 100,200,1200,80")
    region_str = input("Region: ").strip()
    
    try:
        region = tuple(map(int, region_str.split(',')))
        if len(region) != 4:
            raise ValueError("Must have 4 values")
    except Exception as e:
        print(f"❌ Invalid region: {e}")
        return
    
    # Extract
    extractor = NumberExtractor()
    numbers = extractor.extract_from_region(
        image_path,
        region,
        invert=True,
        debug=True
    )
    
    # Display
    print(f"\n✅ Extracted {len(numbers)} numbers from region")
    if numbers:
        for i in range(0, len(numbers), 10):
            row = numbers[i:i+10]
            print("  " + "  ".join(f"{n:.2f}x" for n in row))


def test_quick_api():
    """Test quick API usage."""
    print("\n" + "="*60)
    print("TEST: Quick API")
    print("="*60)
    
    print("\nExample code:")
    print("""
from utils.number_extractor import quick_extract

# Simple usage
numbers = quick_extract("screenshot.png")
print(f"Found {len(numbers)} numbers: {numbers}")

# With debugging
numbers = quick_extract("screenshot.png", debug=True)
# This saves a preprocessed image showing what OCR sees
    """)
    
    # Try it
    image_path = input("\nTry it now - enter image path (or press Enter to skip): ").strip()
    
    if image_path and Path(image_path).exists():
        numbers = quick_extract(image_path, debug=True)
        print(f"\n✅ Result: {numbers}")


def benchmark_preprocessing():
    """Benchmark different preprocessing parameters."""
    print("\n" + "="*60)
    print("TEST: Preprocessing Benchmark")
    print("="*60)
    
    image_path = input("Enter path to image: ").strip()
    
    if not Path(image_path).exists():
        print(f"\n❌ Image not found: {image_path}")
        return
    
    extractor = NumberExtractor()
    
    # Test different configurations
    configs = [
        {"invert": True, "scale_factor": 2, "name": "Default (invert + 2x scale)"},
        {"invert": False, "scale_factor": 2, "name": "No invert + 2x scale"},
        {"invert": True, "scale_factor": 3, "name": "Invert + 3x scale"},
        {"invert": False, "scale_factor": 1, "name": "No preprocessing"},
    ]
    
    print("\nTesting different configurations...\n")
    
    results = []
    for config in configs:
        name = config.pop("name")
        numbers = extractor.extract_numbers_from_image(image_path, **config)
        results.append((name, len(numbers), numbers))
        print(f"{name:40s} → {len(numbers)} numbers")
    
    # Show best result
    best = max(results, key=lambda x: x[1])
    print("\n" + "="*60)
    print(f"✅ Best configuration: {best[0]}")
    print(f"   Extracted {best[1]} numbers")
    if best[2]:
        print(f"   Numbers: {best[2][:10]}...")  # Show first 10


def main():
    """Main test menu."""
    print("\n" + "="*60)
    print("🧪 NUMBER EXTRACTOR - TEST SUITE")
    print("="*60)
    
    print("\nAvailable tests:")
    print("  1. Basic extraction")
    print("  2. Region-based extraction")
    print("  3. Quick API demo")
    print("  4. Preprocessing benchmark")
    print("  5. Exit")
    
    choice = input("\nChoice (1-5): ").strip()
    
    if choice == '1':
        test_basic_extraction()
    elif choice == '2':
        test_with_region()
    elif choice == '3':
        test_quick_api()
    elif choice == '4':
        benchmark_preprocessing()
    elif choice == '5':
        print("Goodbye!")
        return
    else:
        print("Invalid choice!")
        return
    
    # Ask to run another test
    again = input("\n\nRun another test? (yes/no): ").strip().lower()
    if again in ['yes', 'y']:
        main()


if __name__ == "__main__":
    main()
