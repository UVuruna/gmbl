# utils/number_extractor.py
# VERSION: 1.0
# Simple OCR to extract numbers from images (e.g., game history scores)

import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from logger import AviatorLogger


class NumberExtractor:
    """
    Extract numbers from images using OCR.
    
    Optimized for reading game score history like:
    1.00x  1.47x  15.97x  5.49x  8.90x  ...
    
    Returns list of float numbers.
    """
    
    def __init__(self):
        self.logger = AviatorLogger.get_logger("NumberExtractor")
        
        # Tesseract configuration
        pytesseract.pytesseract.tesseract_cmd = config.ocr.tesseract_path
        
        # OCR config optimized for numbers
        # Whitelist: digits, decimal point, 'x' character
        self.tesseract_config = '--psm 6 -c tessedit_char_whitelist=0123456789.x'
    
    def preprocess_image(
        self, 
        image: np.ndarray,
        invert: bool = False,
        threshold_value: int = 127,
        scale_factor: int = 2
    ) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        
        Args:
            image: Input image (BGR or grayscale)
            invert: Invert colors (white text on black -> black on white)
            threshold_value: Threshold for binarization
            scale_factor: Scale up for better OCR (2x or 3x)
        
        Returns:
            Preprocessed grayscale image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Scale up (OCR works better on larger images)
        if scale_factor > 1:
            height, width = gray.shape
            gray = cv2.resize(
                gray, 
                (width * scale_factor, height * scale_factor),
                interpolation=cv2.INTER_CUBIC
            )
        
        # Invert if text is light on dark background
        if invert:
            gray = cv2.bitwise_not(gray)
        
        # Thresholding - convert to pure black and white
        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Slight denoising
        denoised = cv2.medianBlur(binary, 3)
        
        return denoised
    
    def extract_text(
        self, 
        image: np.ndarray,
        preprocess: bool = True,
        **preprocess_kwargs
    ) -> str:
        """
        Extract text from image using Tesseract.
        
        Args:
            image: Input image
            preprocess: Whether to preprocess image
            **preprocess_kwargs: Arguments for preprocessing
        
        Returns:
            Raw OCR text
        """
        if preprocess:
            processed = self.preprocess_image(image, **preprocess_kwargs)
        else:
            processed = image
        
        # Run Tesseract OCR
        try:
            text = pytesseract.image_to_string(
                processed,
                config=self.tesseract_config
            )
            return text
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return ""
    
    def parse_numbers(self, text: str) -> List[float]:
        """
        Parse numbers from OCR text.
        
        Handles formats like:
        - "1.00x"
        - "15.97x"
        - "308.92x"
        - "1.47"
        
        Args:
            text: Raw OCR text
        
        Returns:
            List of extracted numbers
        """
        # Pattern: number (int or float) optionally followed by 'x'
        # Examples: 1.00x, 15.97x, 308.92x, 1.47, 2.03
        pattern = r'(\d+\.?\d*)x?'
        
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                num = float(match)
                # Sanity check: game scores are typically between 1.00 and 1000.00
                if 0.5 <= num <= 10000:
                    numbers.append(num)
            except ValueError:
                continue
        
        return numbers
    
    def extract_numbers_from_image(
        self,
        image_path: str,
        invert: bool = True,
        scale_factor: int = 2,
        debug: bool = False
    ) -> List[float]:
        """
        Complete pipeline: load image, OCR, extract numbers.
        
        Args:
            image_path: Path to image file
            invert: Invert colors (True if text is light on dark background)
            scale_factor: Scale factor for OCR
            debug: Save preprocessed image for debugging
        
        Returns:
            List of extracted numbers
        """
        self.logger.info(f"Processing image: {image_path}")
        
        # Load image
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
        except Exception as e:
            self.logger.error(f"Error loading image: {e}")
            return []
        
        # Preprocess
        processed = self.preprocess_image(
            image,
            invert=invert,
            scale_factor=scale_factor
        )
        
        # Debug: save preprocessed image
        if debug:
            debug_path = Path(image_path).parent / f"{Path(image_path).stem}_preprocessed.png"
            cv2.imwrite(str(debug_path), processed)
            self.logger.info(f"Debug image saved: {debug_path}")
        
        # OCR
        text = pytesseract.image_to_string(processed, config=self.tesseract_config)
        
        self.logger.debug(f"Raw OCR text:\n{text}")
        
        # Parse numbers
        numbers = self.parse_numbers(text)
        
        self.logger.info(f"Extracted {len(numbers)} numbers")
        
        return numbers
    
    def extract_from_region(
        self,
        image_path: str,
        region: Tuple[int, int, int, int],
        **kwargs
    ) -> List[float]:
        """
        Extract numbers from specific region of image.
        
        Args:
            image_path: Path to image
            region: (left, top, width, height) tuple
            **kwargs: Additional arguments for extraction
        
        Returns:
            List of extracted numbers
        """
        # Load full image
        image = cv2.imread(image_path)
        if image is None:
            self.logger.error(f"Could not load image: {image_path}")
            return []
        
        # Crop region
        left, top, width, height = region
        cropped = image[top:top+height, left:left+width]
        
        # Save cropped as temp file
        temp_path = Path(image_path).parent / "temp_cropped.png"
        cv2.imwrite(str(temp_path), cropped)
        
        # Extract from cropped
        numbers = self.extract_numbers_from_image(str(temp_path), **kwargs)
        
        # Cleanup
        temp_path.unlink()
        
        return numbers


def quick_extract(image_path: str, invert: bool = True, debug: bool = False) -> List[float]:
    """
    Quick function to extract numbers from image.
    
    Usage:
        numbers = quick_extract("screenshot.png")
        print(numbers)  # [1.00, 1.47, 15.97, ...]
    
    Args:
        image_path: Path to image
        invert: Invert colors (True for light text on dark background)
        debug: Save debug images
    
    Returns:
        List of extracted numbers
    """
    extractor = NumberExtractor()
    return extractor.extract_numbers_from_image(image_path, invert=invert, debug=debug)


def main():
    """Interactive CLI for number extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract numbers from images using OCR"
    )
    parser.add_argument(
        "image",
        help="Path to image file"
    )
    parser.add_argument(
        "--no-invert",
        action="store_true",
        help="Don't invert colors (use if text is dark on light background)"
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Scale factor for OCR (default: 2)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save preprocessed image for debugging"
    )
    parser.add_argument(
        "--region",
        type=str,
        help="Extract from region only: 'left,top,width,height'"
    )
    
    args = parser.parse_args()
    
    # Initialize
    extractor = NumberExtractor()
    
    # Extract
    if args.region:
        # Parse region
        try:
            region = tuple(map(int, args.region.split(',')))
            if len(region) != 4:
                raise ValueError("Region must have 4 values")
        except Exception as e:
            print(f"❌ Invalid region format: {e}")
            print("   Use: left,top,width,height (e.g., 100,200,800,100)")
            return
        
        numbers = extractor.extract_from_region(
            args.image,
            region,
            invert=not args.no_invert,
            scale_factor=args.scale,
            debug=args.debug
        )
    else:
        numbers = extractor.extract_numbers_from_image(
            args.image,
            invert=not args.no_invert,
            scale_factor=args.scale,
            debug=args.debug
        )
    
    # Display results
    print("\n" + "="*60)
    print(f"📊 EXTRACTED NUMBERS ({len(numbers)} total)")
    print("="*60)
    
    if numbers:
        # Show in rows of 10
        for i in range(0, len(numbers), 10):
            row = numbers[i:i+10]
            print("  " + "  ".join(f"{n:.2f}x" for n in row))
        
        # Statistics
        print("\n" + "-"*60)
        print(f"Min:  {min(numbers):.2f}x")
        print(f"Max:  {max(numbers):.2f}x")
        print(f"Avg:  {sum(numbers)/len(numbers):.2f}x")
        print("="*60)
        
        # Export option
        export = input("\nExport to file? (yes/no): ").strip().lower()
        if export in ['yes', 'y']:
            output_file = Path(args.image).stem + "_numbers.txt"
            with open(output_file, 'w') as f:
                for num in numbers:
                    f.write(f"{num}\n")
            print(f"✅ Exported to: {output_file}")
    else:
        print("❌ No numbers extracted!")
        print("\nTroubleshooting:")
        print("  1. Check if image is clear and readable")
        print("  2. Try with --debug flag to see preprocessed image")
        print("  3. Try --no-invert if text is dark on light background")
        print("  4. Check Tesseract installation")


if __name__ == "__main__":
    main()
