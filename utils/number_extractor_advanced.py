# utils/number_extractor_advanced.py
# VERSION: 5.0 - Optimized for colored text
# Better preprocessing for colored numbers

import re
from pathlib import Path
from typing import List, Tuple, Dict

import cv2
import numpy as np
import pytesseract
from PIL import Image


class AdvancedNumberExtractor:
    """
    Advanced number extractor optimized for colored text.
    
    Handles:
    - Colored text (cyan, magenta, etc.)
    - Multiple preprocessing strategies
    - Channel-based extraction
    """
    
    def __init__(self, tesseract_path: str = None, debug: bool = None):
        """
        Initialize extractor.
        
        Args:
            tesseract_path: Path to tesseract (optional)
            debug: Debug mode (uses config.debug if not specified)
        """
        # Import config
        try:
            from config import config
            if debug is None:
                self.debug = config.debug
            else:
                self.debug = debug
            
            if tesseract_path is None:
                tesseract_path = config.ocr.tesseract_path
        except:
            self.debug = debug if debug is not None else False
            if tesseract_path is None:
                tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        if tesseract_path and Path(tesseract_path).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Multiple OCR configs to try
        self.tesseract_configs = [
            '--psm 6 -c tessedit_char_whitelist=0123456789.x',  # Block of text
            '--psm 11 -c tessedit_char_whitelist=0123456789.x', # Sparse text
            '--psm 12 -c tessedit_char_whitelist=0123456789.x', # Sparse text + OSD
        ]
    
    def preprocess_colored_text(
        self,
        image: np.ndarray,
        method: str = 'lightness'
    ) -> np.ndarray:
        """
        Preprocess colored text for better OCR.
        
        Args:
            image: Input BGR image
            method: 'lightness', 'saturation', 'value', 'channels', 'adaptive'
        
        Returns:
            Preprocessed grayscale image
        """
        if method == 'lightness':
            # Convert to HSV and extract lightness (Value channel)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            gray = hsv[:, :, 2]  # V channel
        
        elif method == 'saturation':
            # High saturation = colored text
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            gray = hsv[:, :, 1]  # S channel
        
        elif method == 'value':
            # Combine channels with weighted average
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            # Emphasize saturated colors
            gray = cv2.addWeighted(hsv[:, :, 2], 0.7, hsv[:, :, 1], 0.3, 0)
        
        elif method == 'channels':
            # Take max of all channels (colored text will be bright in some channel)
            b, g, r = cv2.split(image)
            gray = cv2.max(cv2.max(b, g), r)
        
        elif method == 'adaptive':
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        else:
            # Default: standard grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        return gray
    
    def enhance_text(
        self,
        gray: np.ndarray,
        scale_factor: int = 3,
        use_clahe: bool = True
    ) -> np.ndarray:
        """
        Enhance text for better OCR.
        
        Args:
            gray: Grayscale image
            scale_factor: Scale up factor (2-4 recommended)
            use_clahe: Use CLAHE for contrast enhancement
        
        Returns:
            Enhanced image
        """
        # CLAHE - contrast enhancement
        if use_clahe:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        
        # Scale up
        if scale_factor > 1:
            h, w = gray.shape
            gray = cv2.resize(
                gray,
                (w * scale_factor, h * scale_factor),
                interpolation=cv2.INTER_CUBIC
            )
        
        # Invert (colored text on dark bg -> black text on white)
        gray = cv2.bitwise_not(gray)
        
        # Bilateral filter - preserves edges while smoothing
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive threshold - better than global threshold for uneven lighting
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  # Block size
            2    # Constant
        )
        
        # Morphological operations - clean up noise
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary
    
    def parse_numbers(self, text: str) -> List[float]:
        """Parse numbers from OCR text with better regex."""
        # More flexible pattern
        # Matches: 1.98x, 24.10x, 379.02x, 1.98, 24.10, etc.
        pattern = r'(\d+(?:\.\d+)?)\s*x?'
        
        matches = re.finditer(pattern, text.lower())
        
        numbers = []
        seen = set()  # Avoid duplicates
        
        for match in matches:
            try:
                num_str = match.group(1)
                num = float(num_str)
                
                # Sanity checks
                if 0.5 <= num <= 10000:
                    # Avoid duplicates (same number close together)
                    if num not in seen or abs(num - list(seen)[-1] if seen else 0) > 0.01:
                        numbers.append(num)
                        seen.add(num)
            except (ValueError, IndexError):
                continue
        
        return numbers
    
    def extract_multi_method(
        self,
        image_path: str,
        debug: bool = None
    ) -> Dict[str, List[float]]:
        """
        Try multiple preprocessing methods and return all results.
        
        Args:
            image_path: Path to image
            debug: Override debug setting (uses self.debug if None)
        
        Returns:
            Dict with results from each method
        """
        if debug is None:
            debug = self.debug
        
        print(f"📷 Loading: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Could not load: {image_path}")
            return {}
        
        methods = ['lightness', 'channels', 'value', 'saturation']
        results = {}
        
        for method in methods:
            print(f"\n🔍 Trying method: {method}")
            
            # Preprocess
            gray = self.preprocess_colored_text(image, method)
            enhanced = self.enhance_text(gray, scale_factor=3, use_clahe=True)
            
            # Debug - save to SAME folder as image
            if debug:
                # Save debug images NEXT TO the original image
                image_dir = Path(image_path).parent
                debug_dir = image_dir / "debug"
                debug_dir.mkdir(exist_ok=True)
                
                debug_path_gray = debug_dir / f"{Path(image_path).stem}_step1_gray_{method}.png"
                debug_path_enhanced = debug_dir / f"{Path(image_path).stem}_step2_enhanced_{method}.png"
                
                cv2.imwrite(str(debug_path_gray), gray)
                cv2.imwrite(str(debug_path_enhanced), enhanced)
                
                if method == 'lightness':  # Print once
                    print(f"\n   💾 Debug images: {debug_dir}")
            
            # Try multiple OCR configs
            all_numbers = []
            for config in self.tesseract_configs:
                text = pytesseract.image_to_string(enhanced, config=config)
                numbers = self.parse_numbers(text)
                all_numbers.extend(numbers)
            
            # Remove duplicates but keep order
            seen = set()
            unique_numbers = []
            for num in all_numbers:
                if num not in seen:
                    seen.add(num)
                    unique_numbers.append(num)
            
            results[method] = unique_numbers
            
            # Show ALL numbers for evaluation
            print(f"   → Found {len(unique_numbers)} numbers:")
            if unique_numbers:
                # Show ALL numbers, not just first 10!
                print(f"      FULL LIST:")
                for i in range(0, len(unique_numbers), 10):
                    row = unique_numbers[i:i+10]
                    print("      " + "  ".join(f"{n:7.2f}x" for n in row))
            else:
                print(f"      (none)")
        
        return results
        
        return results
    
    def extract_best(
        self,
        image_path: str,
        debug: bool = False
    ) -> List[float]:
        """
        Extract using best method (most numbers found).
        
        Args:
            image_path: Path to image
            debug: Save debug images
        
        Returns:
            List of numbers from best method
        """
        results = self.extract_multi_method(image_path, debug)
        
        if not results:
            return []
        
        # Find method with most numbers
        best_method = max(results.items(), key=lambda x: len(x[1]))
        method_name, numbers = best_method
        
        print(f"\n✅ Best method: {method_name} ({len(numbers)} numbers)")
        
        return numbers
    
    def extract_combined(
        self,
        image_path: str,
        debug: bool = False
    ) -> List[float]:
        """
        Extract using all methods and combine results.
        
        Args:
            image_path: Path to image
            debug: Save debug images
        
        Returns:
            Combined list of unique numbers
        """
        results = self.extract_multi_method(image_path, debug)
        
        if not results:
            return []
        
        # Combine all results
        all_numbers = []
        for numbers in results.values():
            all_numbers.extend(numbers)
        
        # Remove duplicates and sort
        unique_numbers = sorted(list(set(all_numbers)))
        
        print(f"\n✅ Combined: {len(unique_numbers)} unique numbers")
        
        return unique_numbers


def quick_extract(
    image_path: str,
    method: str = 'best',  # 'best', 'combined', or specific method
    debug: bool = False
) -> List[float]:
    """
    Quick extraction function.
    
    Args:
        image_path: Path to image
        method: 'best' (most numbers), 'combined' (all methods), or 
                'lightness', 'channels', 'value', 'saturation'
        debug: Save debug images
    
    Returns:
        List of extracted numbers
    """
    extractor = AdvancedNumberExtractor()
    
    if method == 'best':
        return extractor.extract_best(image_path, debug)
    elif method == 'combined':
        return extractor.extract_combined(image_path, debug)
    else:
        # Specific method
        results = extractor.extract_multi_method(image_path, debug)
        return results.get(method, [])


def main():
    """Command line interface."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python number_extractor_advanced.py <image_path> [options]")
        print("\nOptions:")
        print("  --method <name>   Method: best, combined, lightness, channels, value, saturation")
        print("  --debug           Save debug images to debug/ folder")
        print("\nExamples:")
        print("  python number_extractor_advanced.py screenshot.png")
        print("  python number_extractor_advanced.py screenshot.png --method combined --debug")
        return
    
    image_path = sys.argv[1]
    
    # Parse options
    method = 'best'
    if '--method' in sys.argv:
        idx = sys.argv.index('--method')
        if idx + 1 < len(sys.argv):
            method = sys.argv[idx + 1]
    
    debug = '--debug' in sys.argv
    
    # Extract
    print("\n" + "="*70)
    print(f"ADVANCED NUMBER EXTRACTION")
    print(f"Method: {method}")
    print("="*70 + "\n")
    
    numbers = quick_extract(image_path, method, debug)
    
    # Display
    print("\n" + "="*70)
    print(f"✅ EXTRACTED {len(numbers)} NUMBERS")
    print("="*70)
    
    if numbers:
        # Show in rows of 10
        for i in range(0, len(numbers), 10):
            row = numbers[i:i+10]
            print("  " + "  ".join(f"{n:7.2f}x" for n in row))
        
        # Statistics
        print("\n" + "-"*70)
        print(f"Count: {len(numbers)}")
        print(f"Min:   {min(numbers):7.2f}x")
        print(f"Max:   {max(numbers):7.2f}x")
        print(f"Avg:   {sum(numbers)/len(numbers):7.2f}x")
        print("="*70)
        
        if debug:
            print("\n💾 Debug images saved to debug/ folder")
            print("   Check step1_gray_*.png and step2_enhanced_*.png")
    else:
        print("❌ No numbers extracted!")


if __name__ == "__main__":
    main()