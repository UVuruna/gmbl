# utils/quick_test.py
# VERSION: 1.0
# PURPOSE: Quick system test for coordinate system
# Tests: JSON format, CoordsManager, coordinate calculation

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.coord_manager import CoordsManager
import json


def test_json_format():
    """Test JSON file format."""
    print("\n" + "="*70)
    print("TEST 1: JSON FORMAT")
    print("="*70)
    
    coords_file = Path("data/coordinates/bookmaker_coords.json")
    
    if not coords_file.exists():
        print("❌ FAIL: bookmaker_coords.json not found!")
        print(f"   Expected: {coords_file}")
        return False
    
    try:
        with open(coords_file, 'r') as f:
            data = json.load(f)
        
        # Check structure
        if "positions" not in data:
            print("❌ FAIL: Missing 'positions' key in JSON!")
            return False
        
        if "bookmakers" not in data:
            print("❌ FAIL: Missing 'bookmakers' key in JSON!")
            return False
        
        print("✅ PASS: JSON structure is correct")
        print(f"   Positions: {len(data['positions'])}")
        print(f"   Bookmakers: {len(data['bookmakers'])}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Invalid JSON format!")
        print(f"   Error: {e}")
        return False


def test_coords_manager():
    """Test CoordsManager functionality."""
    print("\n" + "="*70)
    print("TEST 2: COORDS MANAGER")
    print("="*70)
    
    try:
        manager = CoordsManager()
        
        # Test get_available_positions
        positions = manager.get_available_positions()
        print(f"✅ Available positions: {positions}")
        
        if not positions:
            print("⚠️  WARNING: No positions configured!")
            print("   Add positions to bookmaker_coords.json")
        
        # Test get_available_bookmakers
        bookmakers = manager.get_available_bookmakers()
        print(f"✅ Available bookmakers: {bookmakers}")
        
        if not bookmakers:
            print("⚠️  WARNING: No bookmakers configured!")
            print("   Run: python utils/region_editor.py")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: CoordsManager error!")
        print(f"   Error: {e}")
        return False


def test_coordinate_calculation():
    """Test coordinate calculation."""
    print("\n" + "="*70)
    print("TEST 3: COORDINATE CALCULATION")
    print("="*70)
    
    try:
        manager = CoordsManager()
        
        bookmakers = manager.get_available_bookmakers()
        positions = manager.get_available_positions()
        
        if not bookmakers or not positions:
            print("⚠️  SKIP: No bookmakers or positions to test")
            return True
        
        # Test first bookmaker + first position
        test_bookmaker = bookmakers[0]
        test_position = positions[0]
        
        print(f"\nTesting: {test_bookmaker} @ {test_position}")
        
        coords = manager.calculate_coords(test_bookmaker, test_position)
        
        if coords is None:
            print("❌ FAIL: Coordinate calculation returned None!")
            return False
        
        # Check required regions
        required_regions = [
            'score_region',
            'my_money_region',
            'other_count_region',
            'other_money_region',
            'phase_region'
        ]
        
        missing = []
        for region in required_regions:
            if region not in coords:
                missing.append(region)
        
        if missing:
            print(f"❌ FAIL: Missing required regions: {missing}")
            return False
        
        print("✅ PASS: All required regions present")
        
        # Display sample coordinates
        print("\nSample calculated coordinates:")
        for region_name in required_regions[:3]:
            region = coords[region_name]
            print(f"  {region_name:20s} → ({region['left']:4d}, {region['top']:4d}, {region['width']:4d}x{region['height']:3d})")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Coordinate calculation error!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_combinations():
    """Test all bookmaker + position combinations."""
    print("\n" + "="*70)
    print("TEST 4: ALL COMBINATIONS")
    print("="*70)
    
    try:
        manager = CoordsManager()
        
        bookmakers = manager.get_available_bookmakers()
        positions = manager.get_available_positions()
        
        if not bookmakers or not positions:
            print("⚠️  SKIP: No bookmakers or positions to test")
            return True
        
        total_tests = len(bookmakers) * len(positions)
        passed = 0
        failed = 0
        
        print(f"\nTesting {total_tests} combinations...")
        
        for bookmaker in bookmakers:
            for position in positions:
                coords = manager.calculate_coords(bookmaker, position)
                
                if coords and 'score_region' in coords:
                    passed += 1
                    print(f"  ✅ {bookmaker:15s} @ {position:3s}")
                else:
                    failed += 1
                    print(f"  ❌ {bookmaker:15s} @ {position:3s} FAILED")
        
        print(f"\nResults: {passed}/{total_tests} passed")
        
        if failed > 0:
            print(f"❌ FAIL: {failed} combinations failed!")
            return False
        
        print("✅ PASS: All combinations work!")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing combinations!")
        print(f"   Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("AVIATOR COORDINATE SYSTEM - QUICK TEST")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("JSON Format", test_json_format()))
    results.append(("CoordsManager", test_coords_manager()))
    results.append(("Coordinate Calculation", test_coordinate_calculation()))
    results.append(("All Combinations", test_all_combinations()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:30s} {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print("\n" + "="*70)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    print("="*70)
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("   System is ready to use!")
        print("\nNext steps:")
        print("  1. Inject CSS into browsers")
        print("  2. Run: python apps/main_data_collector.py")
    else:
        print("\n⚠️  SOME TESTS FAILED!")
        print("   Fix issues above before running apps")
        print("\nCommon fixes:")
        print("  • Run region_editor.py to create coordinates")
        print("  • Check JSON format in bookmaker_coords.json")
        print("  • Ensure positions are defined")
    
    print("="*70 + "\n")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
