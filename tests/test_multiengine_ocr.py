# tests/test_multiengine_ocr.py
# VERSION: 1.0
# CHANGES: Test multi-engine OCR integration

import cv2
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ocr_processor import AdvancedOCRReader
from logger import init_logging, AviatorLogger


def test_all_engines():
    """Test all OCR engines on sample images."""
    
    init_logging()
    logger = AviatorLogger.get_logger("MultiEngineTest")
    
    print("="*80)
    print("🧪 MULTI-ENGINE OCR INTEGRATION TEST")
    print("="*80)
    
    # Initialize OCR
    ocr = AdvancedOCRReader()
    
    # Test cases
    test_cases = [
        {
            'name': 'Score Test',
            'image': 'tests/test_images/score_sample.png',
            'expected': 24.56,
            'type': 'score'
        },
        {
            'name': 'Money (Medium) Test',
            'image': 'tests/test_images/money_medium.png',
            'expected': 1234.50,
            'type': 'money_medium'
        },
        {
            'name': 'Money (Small) Test',
            'image': 'tests/test_images/money_small.png',
            'expected': 567.89,
            'type': 'money_small'
        },
        {
            'name': 'Player Count Test',
            'image': 'tests/test_images/player_count.png',
            'expected': (125, 456),
            'type': 'player_count'
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n{'='*80}")
        print(f"📝 {test['name']}")
        print(f"   Image: {test['image']}")
        print(f"   Expected: {test['expected']}")
        print(f"{'='*80}")
        
        # Check if image exists
        if not Path(test['image']).exists():
            print(f"⚠️  Image not found, skipping...")
            continue
        
        # Load image
        img = cv2.imread(test['image'])
        if img is None:
            print(f"❌ Cannot load image")
            continue
        
        # Run OCR
        try:
            if test['type'] == 'score':
                result = ocr.read_score(img)
            elif test['type'] == 'money_medium':
                result = ocr.read_money(img, size_type='medium')
            elif test['type'] == 'money_small':
                result = ocr.read_money(img, size_type='small')
            elif test['type'] == 'player_count':
                result = ocr.read_player_count(img)
            
            # Check result
            if result is not None:
                if test['type'] == 'player_count':
                    success = result == test['expected']
                else:
                    success = abs(result - test['expected']) < 0.5
                
                if success:
                    print(f"✅ SUCCESS: {result}")
                    results.append((test['name'], True))
                else:
                    print(f"⚠️  MISMATCH: Got {result}, expected {test['expected']}")
                    results.append((test['name'], False))
            else:
                print(f"❌ FAILED: No result")
                results.append((test['name'], False))
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test['name'], False))
    
    # Summary
    print(f"\n\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}")


def test_live_capture():
    """Test live screen capture (interactive)."""
    
    init_logging()
    logger = AviatorLogger.get_logger("LiveTest")
    
    print("\n\n" + "="*80)
    print("🎥 LIVE CAPTURE TEST")
    print("="*80)
    
    from core.screen_reader import ScreenReader
    from core.coord_getter import CoordGetter
    
    print("\n⚠️  This test requires you to select a region on screen")
    print("   showing a score value (like 24.56x)\n")
    
    input("Press Enter to start region selection...")
    
    # Get region
    coord_getter = CoordGetter("Test", "Score Region", "region")
    region = coord_getter.get_region()
    
    print(f"\n✅ Region selected: {region}")
    print("\nCapturing and reading with multi-engine OCR...")
    
    # Initialize screen reader
    reader = ScreenReader(region, ocr_type='score')
    
    # Read 5 times
    for i in range(5):
        result = reader.read_with_advanced_ocr('score')
        print(f"\n   Attempt {i+1}: {result}")
    
    # Save last capture
    reader.save_last_capture("tests/live_capture.png")
    print(f"\n✅ Saved last capture to: tests/live_capture.png")
    
    reader.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'live':
        test_live_capture()
    else:
        test_all_engines()
        
        # Ask if user wants to test live
        print("\n\n")
        choice = input("Would you like to test live capture? (y/n): ").strip().lower()
        if choice == 'y':
            test_live_capture()