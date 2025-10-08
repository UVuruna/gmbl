# tests/ultimate_ocr_battle.py
# VERSION: 2.0 - KOMPLETNA IMPLEMENTACIJA
# CHANGES: Sve 3 OCR engine-a implementirane + detaljno poređenje

import cv2
import numpy as np
import re
from pathlib import Path


# ==================================================================
# SMART FIX FUNKCIJA
# ==================================================================
def fix_decimal_errors(numbers: list) -> list:
    """
    Ispravi decimalne greške kod OCR-a.
    
    Pravila:
    - Ako je broj 241 a prethodni je 240 -> 24.1 (nedostaje tačka)
    - Ako je broj duplikat -> ukloni
    - Ako je broj 2400 a prethodni 24.0 -> duplikat, ukloni
    """
    if not numbers:
        return []
    
    fixed = []
    prev = None
    
    for num in sorted(numbers):
        # Preskoči duplikate
        if prev is not None and abs(num - prev) < 0.01:
            continue
        
        # Detektuj missing decimal: 241 -> 24.1
        if prev is not None and num > 10 * prev:
            # Možda nedostaje decimalna tačka
            potential = num / 10
            if abs(potential - prev) > 0.2:  # Nije očigledan duplikat
                fixed.append(potential)
                prev = potential
                continue
        
        fixed.append(num)
        prev = num
    
    return fixed


# ==================================================================
# SETUP
# ==================================================================
print("="*80)
print("🏆 ULTIMATE OCR BATTLE - Complete Edition")
print("="*80)

# Test slika
image_path = "tests/test_images/history_60.png"

# Proveri da li slika postoji
if not Path(image_path).exists():
    print(f"\n❌ Error: Image not found: {image_path}")
    print("Please create test image or update path")
    exit(1)

print(f"\n📷 Test Image: {image_path}")
print(f"   Expected: 60 numbers\n")

# Load image
img = cv2.imread(image_path)
if img is None:
    print(f"❌ Cannot load image: {image_path}")
    exit(1)

expected_count = 60


# ====================================================================
# TEST 1: TESSERACT + FIX
# ====================================================================
print("\n" + "="*80)
print("🔵 TEST 1: Tesseract OCR + Smart Fix")
print("="*80)

try:
    import pytesseract
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Basic preprocessing
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # OCR
    config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.x'
    text = pytesseract.image_to_string(binary, config=config)
    
    # Extract numbers
    tess_raw = []
    for line in text.split('\n'):
        line = line.strip().lower().replace('x', '')
        matches = re.findall(r'(\d+\.?\d*)', line)
        for match in matches:
            try:
                num = float(match)
                if 0.5 <= num <= 10000:
                    tess_raw.append(num)
            except:
                pass
    
    # Remove duplicates
    tess_raw = sorted(list(set(tess_raw)))
    
    print(f"\n📊 Tesseract RAW: {len(tess_raw)} numbers")
    if tess_raw:
        print("   First 10:", [f"{n:.2f}x" for n in tess_raw[:10]])
    
    # Apply fix
    tess_fixed = fix_decimal_errors(tess_raw)
    
    print(f"\n📊 Tesseract FIXED: {len(tess_fixed)} numbers")
    if tess_fixed:
        print("   First 10:", [f"{n:.2f}x" for n in tess_fixed[:10]])
        
        # Show ALL
        print("\n   ALL FIXED NUMBERS:")
        for i in range(0, len(tess_fixed), 10):
            row = tess_fixed[i:i+10]
            print("      " + "  ".join(f"{n:6.2f}x" for n in row))
    
    tess_diff = abs(len(tess_fixed) - expected_count)
    tess_score = tess_diff * 2 if len(tess_fixed) > expected_count else tess_diff
    print(f"\n   → Difference: {tess_diff} | Score: {tess_score}")
    
except ImportError:
    print("⚠️  Tesseract not installed")
    tess_fixed = []
    tess_score = 999
    tess_diff = 999
except Exception as e:
    print(f"❌ Error: {e}")
    tess_fixed = []
    tess_score = 999
    tess_diff = 999


# ====================================================================
# TEST 2: EASYOCR + FIX
# ====================================================================
print("\n\n" + "="*80)
print("🟠 TEST 2: EasyOCR + Smart Fix")
print("="*80)

try:
    import easyocr
    
    print("🔧 Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False)
    
    print(f"📷 Processing: {image_path}")
    
    # Run OCR
    results = reader.readtext(image_path)
    
    # Extract numbers
    easy_raw = []
    
    for (bbox, text, confidence) in results:
        # Only use high confidence
        if confidence < 0.3:
            continue
        
        # Extract numbers from text
        text = text.lower().replace('x', '')
        matches = re.findall(r'(\d+\.?\d*)', text)
        
        for match in matches:
            try:
                num = float(match)
                if 0.5 <= num <= 10000:
                    easy_raw.append(num)
            except:
                pass
    
    # Remove duplicates
    easy_raw = sorted(list(set(easy_raw)))
    
    print(f"\n📊 EasyOCR RAW: {len(easy_raw)} numbers")
    if easy_raw:
        print("   First 10:", [f"{n:.2f}x" for n in easy_raw[:10]])
    
    # Apply fix
    easy_fixed = fix_decimal_errors(easy_raw)
    
    print(f"\n📊 EasyOCR FIXED: {len(easy_fixed)} numbers")
    if easy_fixed:
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
    print("⚠️  EasyOCR not installed")
    print("   Install: pip install easyocr")
    easy_fixed = []
    easy_score = 999
    easy_diff = 999
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    easy_fixed = []
    easy_score = 999
    easy_diff = 999


# ====================================================================
# TEST 3: PADDLEOCR + FIX
# ====================================================================
print("\n\n" + "="*80)
print("🟢 TEST 3: PaddleOCR + Smart Fix")
print("="*80)

try:
    from paddleocr import PaddleOCR
    
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
            text = text.lower().replace('x', '')
            patterns = [
                r'(\d+\.\d+)',  # 24.10
                r'(\d+)',        # 24
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
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
    paddle_diff = 999
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    paddle_fixed = []
    paddle_score = 999
    paddle_diff = 999


# ====================================================================
# FINAL COMPARISON
# ====================================================================
print("\n\n" + "="*80)
print("🏆 FINAL RESULTS")
print("="*80)

results = [
    ("Tesseract + Fix", len(tess_fixed), tess_diff, tess_score),
    ("EasyOCR + Fix", len(easy_fixed), easy_diff, easy_score),
    ("PaddleOCR + Fix", len(paddle_fixed), paddle_diff, paddle_score),
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
    
    # Show winner's data
    if winner[0].startswith("Tesseract") and tess_fixed:
        print(f"\n   Winner's numbers: {tess_fixed[:20]}")
    elif winner[0].startswith("EasyOCR") and easy_fixed:
        print(f"\n   Winner's numbers: {easy_fixed[:20]}")
    elif winner[0].startswith("PaddleOCR") and paddle_fixed:
        print(f"\n   Winner's numbers: {paddle_fixed[:20]}")
else:
    print("❌ All engines failed or not installed")

print("="*80)


# ====================================================================
# USER EVALUATION HELPER
# ====================================================================
print("\n\n" + "="*80)
print("📋 YOUR EVALUATION")
print("="*80)

print("\nCompare these results with the actual image:")
print(f"Expected: {expected_count} numbers")
print()

if tess_fixed:
    print(f"1. Tesseract: {len(tess_fixed)} numbers")
    print(f"   Preview: {tess_fixed[:5]}")

if easy_fixed:
    print(f"\n2. EasyOCR: {len(easy_fixed)} numbers")
    print(f"   Preview: {easy_fixed[:5]}")

if paddle_fixed:
    print(f"\n3. PaddleOCR: {len(paddle_fixed)} numbers")
    print(f"   Preview: {paddle_fixed[:5]}")

print("\n💡 TIP: Check which one has numbers closest to what you see in image!")
print("="*80)