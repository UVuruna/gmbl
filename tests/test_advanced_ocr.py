#!/usr/bin/env python3
# test_advanced.py - Quick test for advanced OCR

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.number_extractor_advanced import quick_extract, AdvancedNumberExtractor
from pathlib import Path

# ====================================================================
# CONFIGURATION
# ====================================================================
image_path = "C:/Users/vurun/OneDrive/Pictures/Screenshots/1.png"

# Expected count (for validation)
expected_count = 60  # Koliko brojeva očekuješ


# ====================================================================
# HELPER: Calculate accuracy
# ====================================================================
def calculate_accuracy(found: int, expected: int) -> tuple:
    """
    Calculate accuracy properly.
    
    Returns: (accuracy_percent, quality_rating, is_good)
    
    Rules:
    - Best = closest to expected (not most!)
    - If found > expected: FALSE POSITIVES
    - If found < expected: MISSING numbers
    - If found == expected: PERFECT (but might have wrong numbers)
    """
    diff = abs(found - expected)
    
    if found > expected:
        # False positives detected
        false_positives = found - expected
        accuracy = max(0, 100 - (false_positives / expected * 100))
        quality = f"{accuracy:.1f}% (but {false_positives} FALSE POSITIVES! ⚠️)"
        is_good = False  # False positives are BAD
    elif found == expected:
        accuracy = 100.0
        quality = "100% PERFECT COUNT! ✅"
        is_good = True
    else:
        # Missing numbers
        accuracy = (found / expected) * 100
        missing = expected - found
        quality = f"{accuracy:.1f}% ({missing} missing)"
        is_good = (accuracy >= 90)  # 90%+ is acceptable
    
    return accuracy, quality, is_good


# ====================================================================
# TEST 1: BEST METHOD (most numbers found)
# ====================================================================
print("\n" + "="*70)
print("TEST 1: BEST METHOD (automatic)")
print("="*70)

numbers = quick_extract(image_path, method='best', debug=True)

accuracy, quality, is_good = calculate_accuracy(len(numbers), expected_count)
print(f"\n📊 Result: {len(numbers)}/{expected_count} numbers")
print(f"   Quality: {quality}")

if numbers:
    print("\n   ALL NUMBERS FOUND:")
    for i in range(0, len(numbers), 10):
        row = numbers[i:i+10]
        print("      " + "  ".join(f"{n:7.2f}x" for n in row))


# ====================================================================
# TEST 2: COMBINED METHOD (all methods merged)
# ====================================================================
print("\n\n" + "="*70)
print("TEST 2: COMBINED METHOD (merge all)")
print("="*70)

numbers_combined = quick_extract(image_path, method='combined', debug=False)

accuracy, quality, is_good = calculate_accuracy(len(numbers_combined), expected_count)
print(f"\n📊 Result: {len(numbers_combined)}/{expected_count} numbers")
print(f"   Quality: {quality}")

if numbers_combined:
    print("\n   ALL NUMBERS FOUND:")
    for i in range(0, len(numbers_combined), 10):
        row = numbers_combined[i:i+10]
        print("      " + "  ".join(f"{n:7.2f}x" for n in row))


# ====================================================================
# TEST 3: COMPARE METHODS
# ====================================================================
print("\n\n" + "="*70)
print("TEST 3: METHOD COMPARISON")
print("="*70)

extractor = AdvancedNumberExtractor()
all_results = extractor.extract_multi_method(image_path, debug=False)

print("\nResults by method:")
print(f"{'Method':<15} {'Found':<6} {'Expected':<10} {'Quality':<40}")
print("-" * 80)

method_scores = []
for method, nums in all_results.items():
    accuracy, quality, is_good = calculate_accuracy(len(nums), expected_count)
    method_scores.append((method, len(nums), accuracy, is_good))
    print(f"{method:<15} {len(nums):<6} {expected_count:<10} {quality}")


# ====================================================================
# FIND BEST RESULT (closest to expected, not most numbers!)
# ====================================================================
def find_best_result(results_dict, expected):
    """
    Find result CLOSEST to expected count.
    Penalize false positives MORE than missing numbers.
    """
    best = None
    best_score = float('-inf')
    best_name = None
    
    for name, result in results_dict.items():
        found = len(result)
        diff = found - expected
        
        if diff == 0:
            # Perfect count
            score = 1000
        elif diff < 0:
            # Missing numbers: less penalty
            score = 100 - abs(diff)
        else:
            # False positives: MORE penalty
            score = 50 - (diff * 2)
        
        if score > best_score:
            best_score = score
            best = result
            best_name = name
    
    return best, best_name

# Combine all results
all_results_dict = {
    'best_method': numbers,
    'combined': numbers_combined,
    **all_results
}

best_result, best_name = find_best_result(all_results_dict, expected_count)

print("\n" + "="*70)
print("✅ BEST RESULT (closest to expected)")
print("="*70)

accuracy, quality, is_good = calculate_accuracy(len(best_result), expected_count)
print(f"Best method: {best_name}")
print(f"Numbers found: {len(best_result)}/{expected_count}")
print(f"Quality: {quality}")

# Show ALL numbers
print("\nALL NUMBERS FROM BEST METHOD:")
for i in range(0, len(best_result), 10):
    row = best_result[i:i+10]
    print("   " + "  ".join(f"{n:7.2f}x" for n in row))

# Rating
diff = abs(len(best_result) - expected_count)
if diff == 0:
    print("\n🎉 PERFECT! Extracted exactly the right amount!")
elif diff <= expected_count * 0.05:  # Within 5%
    print(f"\n👍 EXCELLENT! Within 5% of expected ({diff} difference)")
elif diff <= expected_count * 0.10:  # Within 10%
    print(f"\n✅ GOOD! Within 10% of expected ({diff} difference)")
elif diff <= expected_count * 0.20:  # Within 20%
    print(f"\n⚠️  ACCEPTABLE: Within 20% of expected ({diff} difference)")
else:
    print(f"\n❌ NEEDS IMPROVEMENT: {diff} difference from expected")

# Check for false positives
if len(best_result) > expected_count:
    fps = len(best_result) - expected_count
    print(f"\n⚠️⚠️⚠️  WARNING: {fps} FALSE POSITIVES detected!")
    print("    OCR is hallucinating numbers that don't exist!")

print(f"\n💾 Debug images saved to: {Path(image_path).parent / 'debug'}")
print("="*70)


# ====================================================================
# EXPORT
# ====================================================================
export = input("\n💾 Export best result to file? (yes/no): ").strip().lower()

if export in ['yes', 'y']:
    output_file = "extracted_numbers.txt"
    
    with open(output_file, 'w') as f:
        f.write(f"Extracted Numbers ({len(best_result)}/{expected_count})\n")
        f.write("="*70 + "\n\n")
        
        for num in best_result:
            f.write(f"{num}\n")
        
        f.write(f"\nStatistics:\n")
        f.write(f"Count: {len(best_result)}\n")
        f.write(f"Min: {min(best_result):.2f}\n")
        f.write(f"Max: {max(best_result):.2f}\n")
        f.write(f"Avg: {sum(best_result)/len(best_result):.2f}\n")
    
    print(f"✅ Exported to: {output_file}")