#!/usr/bin/env python3
# test_ocr_comparison.py - EasyOCR vs Tesseract comparison

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ====================================================================
# CONFIGURATION
# ====================================================================
image_path = "C:/Users/vurun/OneDrive/Pictures/Screenshots/1.png"
expected_count = 60

# Expected numbers (for validation)
expected_numbers = [
    1.98, 1.09, 24.10, 3.92, 12.73, 1.66, 1.11, 1.74, 1.10, 2.40,
    1.73, 1.77, 1.02, 2.61, 1.39, 5.69, 2.87, 1.82, 1.10, 1.65,
    1.00, 4.32, 1.65, 1.17, 4.47, 1.70, 5.13, 1.55, 2.35, 3.99,
    1.58, 1.66, 3.30, 1.25, 1.49, 17.47, 1.48, 5.95, 6.53, 379.02,
    1.80, 1.34, 4.54, 1.06, 5.71, 1.18, 24.94, 3.13, 1.53, 9.15,
    1.23, 18.20, 3.23, 2.35, 1.21, 3.67, 3.70, 6.68, 16.50, 1.84
]


# ====================================================================
# HELPER FUNCTIONS
# ====================================================================
def calculate_match_score(extracted: list, expected: list) -> tuple:
    """
    Calculate how many numbers match.
    
    Returns: (matched, missing, false_positives)
    """
    matched = 0
    missing = []
    false_positives = []
    
    # Check matches
    for exp_num in expected:
        if any(abs(exp_num - ext) < 0.01 for ext in extracted):
            matched += 1
        else:
            missing.append(exp_num)
    
    # Check false positives
    for ext_num in extracted:
        if not any(abs(ext_num - exp) < 0.01 for exp in expected):
            false_positives.append(ext_num)
    
    return matched, missing, false_positives


# ====================================================================
# TEST EASYOCR
# ====================================================================
print("\n" + "="*70)
print("🔵 TEST 1: EasyOCR")
print("="*70)

try:
    from utils.easyocr_extractor import EasyOCRExtractor
    
    print("\n🔧 Initializing EasyOCR (first time takes 10-20 seconds)...")
    extractor_easy = EasyOCRExtractor(use_gpu=False)
    
    print(f"📷 Processing: {image_path}")
    easy_numbers = extractor_easy.extract(image_path, enhance=True, debug=True)
    
    print(f"\n📊 EasyOCR Results:")
    print(f"   Found: {len(easy_numbers)}/{expected_count} numbers")
    
    # Show ALL numbers
    print("\n   ALL NUMBERS:")
    for i in range(0, len(easy_numbers), 10):
        row = easy_numbers[i:i+10]
        print("      " + "  ".join(f"{n:7.2f}x" for n in row))
    
    # Calculate accuracy
    matched, missing, fps = calculate_match_score(easy_numbers, expected_numbers)
    match_rate = (matched / len(expected_numbers)) * 100
    
    print(f"\n   ✅ Correctly matched: {matched}/{len(expected_numbers)} ({match_rate:.1f}%)")
    if missing:
        print(f"   ❌ Missing: {len(missing)} numbers")
    if fps:
        print(f"   ⚠️  False positives: {len(fps)} numbers")
    
    easy_score = matched
    
except ImportError:
    print("\n⚠️  EasyOCR not installed!")
    print("   Install with: pip install easyocr")
    easy_numbers = []
    easy_score = 0
except Exception as e:
    print(f"\n❌ Error: {e}")
    easy_numbers = []
    easy_score = 0


# ====================================================================
# TEST TESSERACT
# ====================================================================
print("\n\n" + "="*70)
print("🔴 TEST 2: Tesseract")
print("="*70)

try:
    from utils.number_extractor_advanced import AdvancedNumberExtractor
    
    extractor_tess = AdvancedNumberExtractor()
    
    print(f"\n📷 Processing: {image_path}")
    tess_numbers = extractor_tess.extract_best(image_path, debug=True)
    
    print(f"\n📊 Tesseract Results:")
    print(f"   Found: {len(tess_numbers)}/{expected_count} numbers")
    
    # Show ALL numbers
    print("\n   ALL NUMBERS:")
    for i in range(0, len(tess_numbers), 10):
        row = tess_numbers[i:i+10]
        print("      " + "  ".join(f"{n:7.2f}x" for n in row))
    
    # Calculate accuracy
    matched, missing, fps = calculate_match_score(tess_numbers, expected_numbers)
    match_rate = (matched / len(expected_numbers)) * 100
    
    print(f"\n   ✅ Correctly matched: {matched}/{len(expected_numbers)} ({match_rate:.1f}%)")
    if missing:
        print(f"   ❌ Missing: {len(missing)} numbers")
    if fps:
        print(f"   ⚠️  False positives: {len(fps)} numbers")
    
    tess_score = matched
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    tess_numbers = []
    tess_score = 0


# ====================================================================
# COMPARISON
# ====================================================================
print("\n\n" + "="*70)
print("⚔️  FINAL COMPARISON")
print("="*70)

print(f"\n{'Metric':<25} {'EasyOCR':<15} {'Tesseract':<15} {'Winner'}")
print("-" * 70)

# Count
easy_count_score = abs(len(easy_numbers) - expected_count)
tess_count_score = abs(len(tess_numbers) - expected_count)
count_winner = "🔵 EasyOCR" if easy_count_score < tess_count_score else "🔴 Tesseract" if tess_count_score < easy_count_score else "🤝 TIE"
print(f"{'Numbers found':<25} {len(easy_numbers):<15} {len(tess_numbers):<15} {count_winner}")

# Accuracy
easy_acc = (easy_score / expected_count) * 100
tess_acc = (tess_score / expected_count) * 100
acc_winner = "🔵 EasyOCR" if easy_score > tess_score else "🔴 Tesseract" if tess_score > easy_score else "🤝 TIE"
print(f"{'Correct matches':<25} {easy_score} ({easy_acc:.1f}%){'':<3} {tess_score} ({tess_acc:.1f}%){'':<3} {acc_winner}")

# False positives
easy_fps = len(easy_numbers) - easy_score if len(easy_numbers) > easy_score else 0
tess_fps = len(tess_numbers) - tess_score if len(tess_numbers) > tess_score else 0
fp_winner = "🔵 EasyOCR" if easy_fps < tess_fps else "🔴 Tesseract" if tess_fps < easy_fps else "🤝 TIE"
print(f"{'False positives (less=better)':<25} {easy_fps:<15} {tess_fps:<15} {fp_winner}")

# Overall
print("\n" + "="*70)
if easy_score > tess_score:
    print("🏆 WINNER: EasyOCR")
    print(f"   Better accuracy: {easy_acc:.1f}% vs {tess_acc:.1f}%")
elif tess_score > easy_score:
    print("🏆 WINNER: Tesseract")
    print(f"   Better accuracy: {tess_acc:.1f}% vs {easy_acc:.1f}%")
else:
    print("🤝 TIE - Both equally good/bad")

print("="*70)


# ====================================================================
# RECOMMENDATIONS
# ====================================================================
print("\n" + "="*70)
print("💡 RECOMMENDATIONS")
print("="*70)

if easy_score >= expected_count * 0.95:
    print("\n✅ EasyOCR is EXCELLENT (>95% accuracy)")
    print("   → Use EasyOCR for this type of image")
elif tess_score >= expected_count * 0.95:
    print("\n✅ Tesseract is EXCELLENT (>95% accuracy)")
    print("   → Use Tesseract for this type of image")
elif easy_score > tess_score:
    print(f"\n✅ EasyOCR is better ({easy_acc:.1f}% vs {tess_acc:.1f}%)")
    print("   → Use EasyOCR")
    if easy_acc < 90:
        print("   ⚠️  But still not great - consider manual verification")
elif tess_score > easy_score:
    print(f"\n✅ Tesseract is better ({tess_acc:.1f}% vs {easy_acc:.1f}%)")
    print("   → Use Tesseract")
    if tess_acc < 90:
        print("   ⚠️  But still not great - consider manual verification")
else:
    print("\n⚠️  Both OCR engines struggle with this image")
    print("   Possible reasons:")
    print("   - Font too small")
    print("   - Colors too similar to background")
    print("   - Image resolution too low")
    print("\n   Solutions:")
    print("   - Use higher resolution screenshots")
    print("   - Crop to just the numbers region")
    print("   - Manual data entry might be faster")

print("="*70)