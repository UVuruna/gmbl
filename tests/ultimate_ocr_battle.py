#!/usr/bin/env python3
# ultimate_ocr_test.py - Test all 3 OCR engines with fixes

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

# ====================================================================
# CONFIGURATION
# ====================================================================
image_path = "C:/Users/vurun/OneDrive/Pictures/Screenshots/1.png"
expected_count = 60

print("\n" + "="*80)
print("🏆 ULTIMATE OCR BATTLE - 3 Engines with Smart Fixes")
print("="*80)
print(f"\nImage: {image_path}")
print(f"Expected: {expected_count} numbers")
print("="*80)


# ====================================================================
# SMART FIX FUNCTIONS
# ====================================================================
def fix_decimal_errors(numbers: list) -> list:
    """
    Smart fix for common OCR decimal errors.
    
    Patterns:
    - 2410 → 24.10 (missing decimal)
    - 111 → 1.11 (wrong decimal position)
    - 454 → 4.54
    - 915 → 9.15
    """
    fixed = []
    
    for num in numbers:
        # Skip if already in reasonable range
        if 0.5 <= num <= 50.0:
            fixed.append(num)
            continue
        
        # Rule 1: 100-10000 range - likely missing decimal
        if 100 <= num < 10000:
            # Try /100
            candidate = num / 100
            if 1.0 <= candidate <= 100.0:
                fixed.append(candidate)
                continue
        
        # Rule 2: Three digit numbers (100-999)
        if 100 <= num < 1000 and num % 1 == 0:
            str_num = str(int(num))
            
            # Pattern: ABC → A.BC
            if len(str_num) == 3:
                fixed_num = float(f"{str_num[0]}.{str_num[1:]}")
                if 1.0 <= fixed_num < 10.0:
                    fixed.append(fixed_num)
                    continue
        
        # Rule 3: Four+ digit numbers
        if num >= 1000:
            # Try finding reasonable decimal position
            str_num = str(int(num))
            
            # Pattern: ABCD → AB.CD
            if len(str_num) == 4:
                fixed_num = float(f"{str_num[:2]}.{str_num[2:]}")
                if 1.0 <= fixed_num <= 100.0:
                    fixed.append(fixed_num)
                    continue
        
        # If no rule applied, keep original
        fixed.append(num)
    
    # Remove duplicates while keeping order
    seen = set()
    unique = []
    for n in fixed:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    
    return unique


def fix_easyocr_fragments(numbers: list) -> list:
    """
    Fix EasyOCR's tendency to split numbers into fragments.
    
    EasyOCR sees "24.10x" as:
    - 24.10 ✓
    - 10.00 ✗ (fragment)
    - 24.00 ✗ (fragment)
    
    Strategy: Remove numbers that are clear fragments of other numbers.
    """
    if not numbers:
        return []
    
    # Sort for easier comparison
    sorted_nums = sorted(numbers)
    
    keep = []
    
    for i, num in enumerate(sorted_nums):
        is_fragment = False
        
        # Check if this number is a fragment of another
        for other in sorted_nums:
            if other == num:
                continue
            
            # Check if num is the decimal part of other
            # Example: 24.10 and 10.00 → 10 is fragment
            if num < other:
                decimal_part = other - int(other)  # Get .10 from 24.10
                if abs(num - decimal_part * 100) < 0.01:  # 10.00 ≈ .10 * 100
                    is_fragment = True
                    break
                
                # Check if num is integer part
                int_part = int(other)
                if abs(num - int_part) < 0.01:
                    is_fragment = True
                    break
        
        if not is_fragment:
            keep.append(num)
    
    return keep


# ====================================================================
# TEST 1: TESSERACT + FIX
# ====================================================================
print("\n" + "="*80)
print("🔴 TEST 1: Tesseract + Smart Fix")
print("="*80)

try:
    from utils.number_extractor_advanced import AdvancedNumberExtractor
    
    extractor = AdvancedNumberExtractor()
    tess_raw = extractor.extract_best(image_path, debug=False)
    
    print(f"\n📊 Tesseract RAW: {len(tess_raw)} numbers")
    print("   First 10:", [f"{n:.2f}x" for n in tess_raw[:10]])
    
    # Apply fix
    tess_fixed = fix_decimal_errors(tess_raw)
    
    print(f"\n📊 Tesseract FIXED: {len(tess_fixed)} numbers")
    print("   First 10:", [f"{n:.2f}x" for n in tess_fixed[:10]])
    
    # Show ALL
    print("\n   ALL FIXED NUMBERS:")
    for i in range(0, len(tess_fixed), 10):
        row = tess_fixed[i:i+10]
        print("      " + "  ".join(f"{n:6.2f}x" for n in row))
    
    tess_diff = abs(len(tess_fixed) - expected_count)
    tess_score = tess_diff * 2 if len(tess_fixed) > expected_count else tess_diff
    print(f"\n   → Difference: {tess_diff} | Score: {tess_score}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    tess_fixed = []
    tess_score = 999


# ====================================================================
# TEST 2: EASYOCR + FIX
# ====================================================================
'''print("\n\n" + "="*80)
print("🔵 TEST 2: EasyOCR + Smart Fix")
print("="*80)

try:
    from utils.easyocr_extractor import EasyOCRExtractor
    
    print("🔧 Initializing EasyOCR...")
    extractor = EasyOCRExtractor(use_gpu=False)
    
    easy_raw = extractor.extract(image_path, enhance=True, debug=False)
    
    print(f"\n📊 EasyOCR RAW: {len(easy_raw)} numbers")
    print("   First 10:", [f"{n:.2f}x" for n in easy_raw[:10]])
    
    # Apply fixes
    easy_step1 = fix_decimal_errors(easy_raw)
    easy_fixed = fix_easyocr_fragments(easy_step1)
    
    print(f"\n📊 EasyOCR FIXED: {len(easy_fixed)} numbers")
    print("   First 10:", [f"{n:.2f}x" for n in easy_fixed[:10]])
    
    # Show ALL
    print("\n   ALL FIXED NUMBERS:")
    for i in range(0, len(easy_fixed), 10):
        row = easy_fixed[i:i+10]
        print("      " + "  ".join(f"{n:6.2f}x" for n in row))
    
    easy_diff = abs(len(easy_fixed) - expected_count)
    easy_score = easy_diff * 2 if len(easy_fixed) > expected_count else easy_diff
    print(f"\n   → Difference: {easy_diff} | Score: {easy_score}")
    
except ImportError:
    print("⚠️  EasyOCR not installed: pip install easyocr")
    easy_fixed = []
    easy_score = 999
except Exception as e:
    print(f"❌ Error: {e}")
    easy_fixed = []
    easy_score = 999'''


# ====================================================================
# TEST 3: PADDLEOCR + FIX
# ====================================================================
print("\n\n" + "="*80)
print("🟢 TEST 3: PaddleOCR + Smart Fix")
print("="*80)

'''try:
    from paddleocr import PaddleOCR
    import cv2
    
    print("🔧 Initializing PaddleOCR (first time downloads models)...")
    
    # Initialize with English
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    
    print(f"📷 Processing: {image_path}")
    
    # Run OCR
    result = ocr.ocr(image_path, cls=True)
    
    # Extract numbers
    paddle_raw = []
    
    if result and result[0]:
        for line in result[0]:
            text = line[1][0]  # Get text
            confidence = line[1][1]  # Get confidence
            
            # Only use high confidence
            if confidence < 0.3:
                continue
            
            # Extract numbers from text
            patterns = [
                r'(\d+\.\d+)',  # 24.10
                r'(\d+)',        # 24
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text.lower().replace('x', ''))
                for match in matches:
                    try:
                        num = float(match)
                        if 0.5 <= num <= 10000:
                            paddle_raw.append(num)
                    except:
                        pass
    
    # Remove duplicates
    paddle_raw = sorted(list(set(paddle_raw)))
    
    print(f"\n📊 PaddleOCR RAW: {len(paddle_raw)} numbers")
    if paddle_raw:
        print("   First 10:", [f"{n:.2f}x" for n in paddle_raw[:10]])
    
    # Apply fix
    paddle_fixed = fix_decimal_errors(paddle_raw)
    
    print(f"\n📊 PaddleOCR FIXED: {len(paddle_fixed)} numbers")
    if paddle_fixed:
        print("   First 10:", [f"{n:.2f}x" for n in paddle_fixed[:10]])
        
        # Show ALL
        print("\n   ALL FIXED NUMBERS:")
        for i in range(0, len(paddle_fixed), 10):
            row = paddle_fixed[i:i+10]
            print("      " + "  ".join(f"{n:6.2f}x" for n in row))
    
    paddle_diff = abs(len(paddle_fixed) - expected_count)
    paddle_score = paddle_diff * 2 if len(paddle_fixed) > expected_count else paddle_diff
    print(f"\n   → Difference: {paddle_diff} | Score: {paddle_score}")
    
except ImportError:
    print("⚠️  PaddleOCR not installed!")
    print("   Install: pip install paddleocr paddlepaddle")
    paddle_fixed = []
    paddle_score = 999
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    paddle_fixed = []
    paddle_score = 999'''


# ====================================================================
# FINAL COMPARISON
# ====================================================================
'''print("\n\n" + "="*80)
print("🏆 FINAL RESULTS")
print("="*80)

results = [
    ("Tesseract + Fix", len(tess_fixed), tess_diff if 'tess_diff' in locals() else 999, tess_score),
    ("EasyOCR + Fix", len(easy_fixed), easy_diff if 'easy_diff' in locals() else 999, easy_score),
    ("PaddleOCR + Fix", len(paddle_fixed), paddle_diff if 'paddle_diff' in locals() else 999, paddle_score),
]

print(f"\n{'Engine':<20} {'Found':<10} {'Expected':<10} {'Diff':<10} {'Score':<10}")
print("-" * 80)

for name, found, diff, score in results:
    print(f"{name:<20} {found:<10} {expected_count:<10} {diff:<10} {score:<10}")

# Find winner (lowest score)
winner = min(results, key=lambda x: x[3])

print("\n" + "="*80)
if winner[3] < 999:
    print(f"🏆 WINNER: {winner[0]}")
    print(f"   Found: {winner[1]}/{expected_count}")
    print(f"   Difference: {winner[2]}")
    print(f"   Score: {winner[3]}")
else:
    print("❌ All engines failed or not installed")

print("="*80)'''


# ====================================================================
# USER EVALUATION HELPER
# ====================================================================
'''print("\n\n" + "="*80)
print("📋 YOUR EVALUATION")
print("="*80)

print("\nCompare these results with the actual image:")
print("Expected: 60 numbers")
print()

if tess_fixed:
    print(f"1. Tesseract: {len(tess_fixed)} numbers")
    print(f"   Preview: {tess_fixed[:5]}")

if easy_fixed:
    print(f"\n2. EasyOCR: {len(easy_fixed)} numbers")
    print(f"   Preview: {easy_fixed[:5]}")

if paddle_fixed:
    print(f"\n3. PaddleOCR: {len(paddle_fixed)} numbers")
    print(f"   Preview: {paddle_fixed[:5]}")'''

print("\n💡 TIP: Check which one has numbers closest to what you see in image!")
print("="*80)
