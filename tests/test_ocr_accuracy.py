# tests/test_ocr_accuracy.py
# VERSION: 5.0.1
# CHANGES: Added missing PIL import, complete file

import cv2
import numpy as np
from PIL import Image
import mss
from core.ocr_processor import AdvancedOCRReader, OCRValidator
from logger import init_logging, AviatorLogger
import time


class OCRAccuracyTester:
    """Test OCR accuracy on captured images."""
    
    def __init__(self):
        init_logging()
        self.logger = AviatorLogger.get_logger("OCRTester")
        self.ocr = AdvancedOCRReader()
    
    def test_score_ocr(self, test_cases: list):
        """
        Test score OCR accuracy.
        
        test_cases: List of (image_path, expected_value)
        """
        self.logger.info("="*60)
        self.logger.info("TESTING SCORE OCR")
        self.logger.info("="*60)
        
        correct = 0
        total = len(test_cases)
        
        for img_path, expected in test_cases:
            img = cv2.imread(img_path)
            if img is None:
                self.logger.error(f"❌ Cannot load image: {img_path}")
                continue
                
            result = self.ocr.read_score(img)
            
            if result is not None and abs(result - expected) < 0.01:
                self.logger.info(f"✅ {img_path}: {result} (expected {expected})")
                correct += 1
            else:
                self.logger.error(f"❌ {img_path}: {result} (expected {expected})")
        
        accuracy = (correct / total * 100) if total > 0 else 0
        self.logger.info(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")
        
        return accuracy
    
    def interactive_test(self, region_type: str):
        """
        Interactive OCR testing - capture from screen regions.
        
        region_type: 'score', 'money_small', 'money_medium', 'player_count'
        """
        from core.coord_getter import CoordGetter
        
        self.logger.info(f"Interactive test for {region_type}")
        
        # Get region
        getter = CoordGetter("Test", region_type, "region")
        region = getter.get_region()
        
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("="*60)
        
        try:
            sct = mss.mss()
            
            while True:
                # Capture
                sct_img = sct.grab(region)
                img_rgb = np.array(Image.frombytes('RGB', sct_img.size, sct_img.rgb))
                img_bgr = img_rgb[:, :, ::-1].copy()
                
                # OCR
                start = time.time()
                
                if region_type == 'score':
                    result = self.ocr.read_score(img_bgr)
                elif region_type in ['money_small', 'money_medium']:
                    size = region_type.split('_')[1]
                    result = self.ocr.read_money(img_bgr, size_type=size)
                elif region_type == 'player_count':
                    result = self.ocr.read_player_count(img_bgr)
                else:
                    result = None
                
                elapsed = (time.time() - start) * 1000
                
                # Display
                print(f"{region_type}: {result} ({elapsed:.1f}ms)")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            self.logger.info("Test stopped")
        finally:
            sct.close()


def test_validation():
    """Test validation logic."""
    init_logging()
    logger = AviatorLogger.get_logger("ValidationTest")
    validator = OCRValidator()
    
    logger.info("="*60)
    logger.info("VALIDATION TESTS")
    logger.info("="*60)
    
    # Test score validation
    score_tests = [
        ("1.23x", True, 1.23),
        ("12.34x", True, 12.34),
        ("1,234.56x", True, 1234.56),
        ("12.123.45x", True, 12123.45),  # OCR error correction
        ("no number", False, None),
        ("999.99x", True, 999.99),
        ("O.23x", True, 0.23),  # O -> 0 correction
        ("I2.34x", True, 12.34),  # I -> 1 correction
    ]
    
    logger.info("\nScore validation tests:")
    for text, should_pass, expected_val in score_tests:
        result = validator.validate_score(text)
        status = "✅" if result.is_valid == should_pass else "❌"
        logger.info(f"{status} '{text}' -> Valid: {result.is_valid}, Value: {result.cleaned_text}")
        if result.error_message:
            logger.info(f"   Error: {result.error_message}")
    
    # Test money validation
    money_tests = [
        ("123.45", True, 123.45),
        ("1,234.56", True, 1234.56),
        ("12.123.45", True, 12123.45),  # OCR error
        ("O,234.56", True, 0234.56),  # O -> 0
        ("invalid", False, None),
    ]
    
    logger.info("\nMoney validation tests:")
    for text, should_pass, expected_val in money_tests:
        result = validator.validate_money(text)
        status = "✅" if result.is_valid == should_pass else "❌"
        logger.info(f"{status} '{text}' -> Valid: {result.is_valid}, Value: {result.cleaned_text}")
    
    # Test player count validation
    count_tests = [
        ("123/456", True, (123, 456)),
        ("1234/5678", True, (1234, 5678)),
        ("123 opklada / 456", True, (123, 456)),
        ("betting 123/456", True, (123, 456)),
        ("invalid", False, None),
        ("456/123", False, None),  # current > total (invalid)
        ("IAGI/456", False, None),  # OCR garbage
        ("12I/456", True, (121, 456)),  # I -> 1 correction
    ]
    
    logger.info("\nPlayer count validation tests:")
    for text, should_pass, expected_val in count_tests:
        result = validator.validate_player_count(text)
        status = "✅" if result.is_valid == should_pass else "❌"
        logger.info(f"{status} '{text}' -> Valid: {result.is_valid}, Value: {result.cleaned_text}")
        if result.error_message:
            logger.info(f"   Error: {result.error_message}")


def main():
    """Run OCR tests."""
    tester = OCRAccuracyTester()
    
    print("\n" + "="*60)
    print("OCR ACCURACY TESTING TOOL v5.0")
    print("="*60)
    print("\n1. Test score OCR (interactive)")
    print("2. Test money OCR - small (interactive)")
    print("3. Test money OCR - medium (interactive)")
    print("4. Test player count OCR (interactive)")
    print("5. Run validation unit tests")
    print("6. Test from saved images")
    
    choice = input("\nChoice (1-6): ").strip()
    
    if choice == '1':
        tester.interactive_test('score')
    elif choice == '2':
        tester.interactive_test('money_small')
    elif choice == '3':
        tester.interactive_test('money_medium')
    elif choice == '4':
        tester.interactive_test('player_count')
    elif choice == '5':
        test_validation()
    elif choice == '6':
        # Test from saved images
        print("\nPlace test images in tests/images/ directory")
        print("Format: score_123.45.png for score=123.45")
        
        import os
        test_dir = "tests/images"
        if not os.path.exists(test_dir):
            print(f"Directory {test_dir} does not exist!")
            return
        
        # Parse filenames for expected values
        score_tests = []
        for filename in os.listdir(test_dir):
            if filename.startswith('score_') and filename.endswith('.png'):
                # Extract expected value from filename
                value_str = filename.replace('score_', '').replace('.png', '')
                try:
                    expected = float(value_str)
                    score_tests.append((os.path.join(test_dir, filename), expected))
                except ValueError:
                    print(f"Skip invalid filename: {filename}")
        
        if score_tests:
            accuracy = tester.test_score_ocr(score_tests)
            print(f"\nFinal accuracy: {accuracy:.1f}%")
        else:
            print("No test images found!")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()