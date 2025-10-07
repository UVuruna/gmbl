# utils/easyocr_extractor.py
# VERSION: 1.0 - EasyOCR alternative to Tesseract
# Often MORE ACCURATE than Tesseract for clean text!

import re
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠️  EasyOCR not installed!")
    print("   Install with: pip install easyocr")


class EasyOCRExtractor:
    """
    Number extractor using EasyOCR.
    
    Advantages over Tesseract:
    - Better at recognizing small text
    - Better with colored text
    - More accurate decimal point detection
    - GPU support (faster if you have GPU)
    """
    
    def __init__(self, use_gpu: bool = False):
        """
        Initialize EasyOCR.
        
        Args:
            use_gpu: Use GPU if available (much faster!)
        """
        if not EASYOCR_AVAILABLE:
            raise ImportError("EasyOCR not installed! Run: pip install easyocr")
        
        print("🔧 Initializing EasyOCR (this takes 10-20 seconds first time)...")
        self.reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False)
        print("✅ EasyOCR ready!")
        
        self.use_gpu = use_gpu
    
    def preprocess_for_easyocr(
        self,
        image: np.ndarray,
        enhance: bool = True
    ) -> np.ndarray:
        """
        Light preprocessing for EasyOCR.
        EasyOCR handles colored text well, so less preprocessing needed.
        """
        if len(image.shape) == 2:
            # Already grayscale
            processed = image
        else:
            # EasyOCR works well with color images too
            # But for numbers, grayscale is fine
            processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if enhance:
            # Scale up slightly
            h, w = processed.shape
            processed = cv2.resize(
                processed,
                (w * 2, h * 2),
                interpolation=cv2.INTER_CUBIC
            )
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(processed)
        
        return processed
    
    def parse_numbers(self, ocr_results: List[Tuple]) -> List[float]:
        """
        Parse numbers from EasyOCR results.
        
        Args:
            ocr_results: List of (bbox, text, confidence) tuples
        
        Returns:
            List of extracted numbers
        """
        numbers = []
        
        for (bbox, text, confidence) in ocr_results:
            # Only use high-confidence results
            if confidence < 0.3:
                continue
            
            # Clean text
            text = text.strip().lower()
            
            # Pattern: extract number with optional 'x'
            # Examples: "1.98x", "24.10x", "379.02x", "1.98", "24.10"
            patterns = [
                r'(\d+\.\d+)\s*x',  # "24.10x"
                r'(\d+\.\d+)',       # "24.10"
                r'(\d+)\s*x',        # "24x"
                r'(\d+)',            # "24"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    try:
                        num = float(match)
                        
                        # Sanity check
                        if 0.5 <= num <= 10000:
                            numbers.append(num)
                            break  # Found valid number, stop trying patterns
                    except ValueError:
                        continue
        
        return numbers
    
    def extract(
        self,
        image_path: str,
        enhance: bool = True,
        debug: bool = False
    ) -> List[float]:
        """
        Extract numbers from image using EasyOCR.
        
        Args:
            image_path: Path to image
            enhance: Apply preprocessing
            debug: Save debug images
        
        Returns:
            List of extracted numbers
        """
        print(f"📷 Loading: {image_path}")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Could not load: {image_path}")
            return []
        
        # Preprocess
        processed = self.preprocess_for_easyocr(image, enhance)
        
        # Debug
        if debug:
            debug_dir = Path(image_path).parent / "debug_easyocr"
            debug_dir.mkdir(exist_ok=True)
            
            debug_path = debug_dir / f"{Path(image_path).stem}_preprocessed.png"
            cv2.imwrite(str(debug_path), processed)
            print(f"💾 Debug image: {debug_path}")
        
        # Run EasyOCR
        print("🔍 Running EasyOCR...")
        
        # EasyOCR expects RGB (we have grayscale, convert back)
        if len(processed.shape) == 2:
            processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        else:
            processed_rgb = processed
        
        results = self.reader.readtext(
            processed_rgb,
            detail=1,  # Return bbox, text, confidence
            paragraph=False,
            min_size=10,
            text_threshold=0.7,
            low_text=0.4
        )
        
        # Debug: print raw results
        if debug:
            print("\n   Raw OCR results:")
            for (bbox, text, conf) in results:
                print(f"      '{text}' (confidence: {conf:.2f})")
        
        # Parse numbers
        numbers = self.parse_numbers(results)
        
        # Remove duplicates but keep order
        seen = set()
        unique_numbers = []
        for num in numbers:
            if num not in seen:
                seen.add(num)
                unique_numbers.append(num)
        
        print(f"✅ Extracted {len(unique_numbers)} numbers")
        
        return unique_numbers
    
    def extract_with_comparison(
        self,
        image_path: str,
        expected_count: int = None
    ) -> dict:
        """
        Extract and provide detailed comparison.
        
        Returns dict with:
        - numbers: List of numbers
        - count: Number found
        - confidence: Average confidence
        - quality: Quality assessment
        """
        image = cv2.imread(image_path)
        if image is None:
            return {"numbers": [], "count": 0, "error": "Could not load image"}
        
        # Preprocess
        processed = self.preprocess_for_easyocr(image, enhance=True)
        
        if len(processed.shape) == 2:
            processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        else:
            processed_rgb = processed
        
        # Run OCR
        results = self.reader.readtext(processed_rgb, detail=1)
        
        # Parse
        numbers = self.parse_numbers(results)
        
        # Remove duplicates
        unique_numbers = sorted(list(set(numbers)))
        
        # Calculate average confidence
        confidences = [conf for (_, _, conf) in results if conf > 0.3]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Quality assessment
        if expected_count:
            diff = abs(len(unique_numbers) - expected_count)
            if diff == 0:
                quality = "PERFECT"
            elif diff <= expected_count * 0.05:
                quality = "EXCELLENT"
            elif diff <= expected_count * 0.10:
                quality = "GOOD"
            else:
                quality = "NEEDS_IMPROVEMENT"
        else:
            quality = "UNKNOWN"
        
        return {
            "numbers": unique_numbers,
            "count": len(unique_numbers),
            "avg_confidence": avg_confidence,
            "quality": quality,
            "raw_results": len(results)
        }


def quick_extract(
    image_path: str,
    use_gpu: bool = False,
    enhance: bool = True,
    debug: bool = False
) -> List[float]:
    """
    Quick extraction function.
    
    Args:
        image_path: Path to image
        use_gpu: Use GPU (faster if available)
        enhance: Apply preprocessing
        debug: Save debug images
    
    Returns:
        List of extracted numbers
    """
    extractor = EasyOCRExtractor(use_gpu=use_gpu)
    return extractor.extract(image_path, enhance, debug)


def compare_with_tesseract(image_path: str, expected_count: int = 60):
    """
    Compare EasyOCR vs Tesseract side-by-side.
    """
    print("\n" + "="*70)
    print("COMPARISON: EasyOCR vs Tesseract")
    print("="*70)
    
    # EasyOCR
    print("\n1️⃣  EasyOCR:")
    easy_extractor = EasyOCRExtractor(use_gpu=False)
    easy_numbers = easy_extractor.extract(image_path, debug=True)
    
    print(f"   Found: {len(easy_numbers)}/{expected_count}")
    print(f"   Numbers: {easy_numbers[:10]}...")
    
    # Tesseract
    print("\n2️⃣  Tesseract:")
    try:
        from utils.number_extractor_advanced import AdvancedNumberExtractor
        tess_extractor = AdvancedNumberExtractor()
        tess_numbers = tess_extractor.extract_best(image_path, debug=True)
        
        print(f"   Found: {len(tess_numbers)}/{expected_count}")
        print(f"   Numbers: {tess_numbers[:10]}...")
    except Exception as e:
        print(f"   Error: {e}")
        tess_numbers = []
    
    # Comparison
    print("\n" + "="*70)
    print("WINNER:")
    print("="*70)
    
    easy_diff = abs(len(easy_numbers) - expected_count)
    tess_diff = abs(len(tess_numbers) - expected_count)
    
    if easy_diff < tess_diff:
        print("🏆 EasyOCR is more accurate!")
    elif tess_diff < easy_diff:
        print("🏆 Tesseract is more accurate!")
    else:
        print("🤝 Both have same accuracy!")
    
    print(f"\nEasyOCR: {len(easy_numbers)}/{expected_count} ({easy_diff} difference)")
    print(f"Tesseract: {len(tess_numbers)}/{expected_count} ({tess_diff} difference)")
    print("="*70)


def main():
    """Command line interface."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python easyocr_extractor.py <image_path> [options]")
        print("\nOptions:")
        print("  --gpu          Use GPU (faster)")
        print("  --debug        Save debug images")
        print("  --compare      Compare with Tesseract")
        print("\nExamples:")
        print("  python easyocr_extractor.py screenshot.png")
        print("  python easyocr_extractor.py screenshot.png --debug --gpu")
        print("  python easyocr_extractor.py screenshot.png --compare")
        return
    
    image_path = sys.argv[1]
    
    use_gpu = '--gpu' in sys.argv
    debug = '--debug' in sys.argv
    compare = '--compare' in sys.argv
    
    if compare:
        compare_with_tesseract(image_path)
        return
    
    # Extract
    numbers = quick_extract(image_path, use_gpu, enhance=True, debug=debug)
    
    # Display
    print("\n" + "="*70)
    print(f"EXTRACTED {len(numbers)} NUMBERS")
    print("="*70)
    
    if numbers:
        for i in range(0, len(numbers), 10):
            row = numbers[i:i+10]
            print("   " + "  ".join(f"{n:7.2f}x" for n in row))
        
        print("\n" + "-"*70)
        print(f"Min:  {min(numbers):7.2f}x")
        print(f"Max:  {max(numbers):7.2f}x")
        print(f"Avg:  {sum(numbers)/len(numbers):7.2f}x")
    else:
        print("❌ No numbers extracted!")
    
    print("="*70)


if __name__ == "__main__":
    if not EASYOCR_AVAILABLE:
        print("\n" + "="*70)
        print("⚠️  EasyOCR NOT INSTALLED")
        print("="*70)
        print("\nTo install EasyOCR:")
        print("  pip install easyocr")
        print("\nNote: First run will download ~500MB of models")
        print("="*70)
    else:
        main()
