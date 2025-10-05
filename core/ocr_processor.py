# core/ocr_processor.py
# VERSION: 5.0
# CHANGES: Advanced OCR preprocessing and validation system

import cv2
import numpy as np
import pytesseract
import re
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from logger import AviatorLogger


@dataclass
class OCRResult:
    """OCR result with metadata"""
    text: str
    confidence: float
    cleaned_text: str
    is_valid: bool
    error_message: Optional[str] = None


class OCRPreprocessor:
    """
    Advanced image preprocessing for OCR optimization.
    Different strategies for different text types.
    """
    
    @staticmethod
    def preprocess_large_number(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
        """
        Preprocess for SCORE (largest text).
        
        Args:
            img: Input BGR image
            scale: Upscale factor for better OCR
        """
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Upscale significantly (score is large, upscaling helps)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, 
                         interpolation=cv2.INTER_CUBIC)
        
        # Bilateral filter to reduce noise while preserving edges
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        return binary
    
    @staticmethod
    def preprocess_medium_number(img: np.ndarray, scale: float = 2.5) -> np.ndarray:
        """Preprocess for OTHER_MONEY (medium text)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        
        # Gaussian blur + threshold
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(gray, 0, 255, 
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    @staticmethod
    def preprocess_small_number(img: np.ndarray, scale: float = 4.0) -> np.ndarray:
        """
        Preprocess for MY_MONEY (smaller text).
        More aggressive upscaling.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aggressive upscaling for small text
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        
        # Denoise heavily
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Sharpen
        kernel_sharpen = np.array([[-1,-1,-1],
                                   [-1, 9,-1],
                                   [-1,-1,-1]])
        gray = cv2.filter2D(gray, -1, kernel_sharpen)
        
        # Binary threshold
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    @staticmethod
    def preprocess_tiny_text(img: np.ndarray, scale: float = 5.0) -> np.ndarray:
        """
        Preprocess for OTHER_COUNT (very small text).
        Maximum upscaling and enhancement.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Maximum upscaling
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_LANCZOS4)
        
        # Strong denoising
        gray = cv2.fastNlMeansDenoising(gray, None, 12, 7, 21)
        
        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Sharpen aggressively
        kernel_sharpen = np.array([[-1,-1,-1],
                                   [-1, 10,-1],
                                   [-1,-1,-1]])
        gray = cv2.filter2D(gray, -1, kernel_sharpen)
        
        # Binary threshold
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphology to connect broken characters
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary


class OCRValidator:
    """
    Validation and error correction for OCR results.
    Type-specific validation rules.
    """
    
    # Common OCR mistakes
    CHAR_CORRECTIONS = {
        'O': '0', 'o': '0',
        'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5',
        'Z': '2', 'z': '2',
        'B': '8',
        'G': '6', 'g': '6'
    }
    
    @classmethod
    def validate_score(cls, text: str) -> OCRResult:
        """
        Validate and clean SCORE format: 1,234.56x
        
        Rules:
        - Must end with 'x'
        - Contains digits, '.', ','
        - Format: number with optional thousands separator
        """
        original = text.strip()
        
        # Apply character corrections
        corrected = cls._apply_corrections(original)
        
        # Remove spaces
        corrected = corrected.replace(' ', '')
        
        # Must end with 'x' or 'X'
        if not corrected.lower().endswith('x'):
            return OCRResult(
                text=original,
                confidence=0.0,
                cleaned_text="",
                is_valid=False,
                error_message="Score must end with 'x'"
            )
        
        # Remove 'x' from end
        number_part = corrected[:-1]
        
        # Clean number: remove all commas, handle multiple dots
        number_part = cls._clean_money_number(number_part)
        
        # Validate it's a valid float
        try:
            value = float(number_part)
            
            # Sanity check: score usually between 1.00 and 1000.00
            if not (1.0 <= value <= 10000.0):
                return OCRResult(
                    text=original,
                    confidence=0.3,
                    cleaned_text=number_part,
                    is_valid=False,
                    error_message=f"Score {value} out of expected range"
                )
            
            return OCRResult(
                text=original,
                confidence=1.0,
                cleaned_text=number_part,
                is_valid=True
            )
            
        except ValueError as e:
            return OCRResult(
                text=original,
                confidence=0.0,
                cleaned_text=number_part,
                is_valid=False,
                error_message=f"Cannot parse as float: {e}"
            )
    
    @classmethod
    def validate_money(cls, text: str, min_val: float = 0, 
                       max_val: float = 1000000) -> OCRResult:
        """
        Validate and clean MONEY format: 1,234.56
        
        Rules:
        - No 'x' at end
        - Contains digits, '.', ','
        """
        original = text.strip()
        
        # Apply corrections
        corrected = cls._apply_corrections(original)
        corrected = corrected.replace(' ', '')
        
        # Clean number
        cleaned = cls._clean_money_number(corrected)
        
        # Validate
        try:
            value = float(cleaned)
            
            # Range check
            if not (min_val <= value <= max_val):
                return OCRResult(
                    text=original,
                    confidence=0.3,
                    cleaned_text=cleaned,
                    is_valid=False,
                    error_message=f"Value {value} out of range [{min_val}, {max_val}]"
                )
            
            return OCRResult(
                text=original,
                confidence=1.0,
                cleaned_text=cleaned,
                is_valid=True
            )
            
        except ValueError as e:
            return OCRResult(
                text=original,
                confidence=0.0,
                cleaned_text=cleaned,
                is_valid=False,
                error_message=f"Cannot parse as float: {e}"
            )
    
    @classmethod
    def validate_player_count(cls, text: str) -> OCRResult:
        """
        Validate and clean PLAYER COUNT format: 123/456
        
        Rules:
        - Format: INT/INT
        - No decimals
        - May contain extra text like "opklada" or "betting"
        """
        original = text.strip()
        
        # Apply corrections
        corrected = cls._apply_corrections(original)
        
        # Remove common extra words
        words_to_remove = ['opklada', 'betting', 'bet', 'bets', 'players', 'igraca']
        for word in words_to_remove:
            corrected = re.sub(word, '', corrected, flags=re.IGNORECASE)
        
        # Remove spaces
        corrected = corrected.replace(' ', '')
        
        # Extract pattern: digits/digits
        match = re.search(r'(\d{1,4})\s*/\s*(\d{1,4})', corrected)
        
        if not match:
            return OCRResult(
                text=original,
                confidence=0.0,
                cleaned_text="",
                is_valid=False,
                error_message="No valid XXX/YYY pattern found"
            )
        
        current = int(match.group(1))
        total = int(match.group(2))
        
        # Validation: current <= total
        if current > total:
            return OCRResult(
                text=original,
                confidence=0.5,
                cleaned_text=f"{current}/{total}",
                is_valid=False,
                error_message=f"Current ({current}) > Total ({total})"
            )
        
        # Range check: usually not more than 10000 players
        if total > 10000:
            return OCRResult(
                text=original,
                confidence=0.3,
                cleaned_text=f"{current}/{total}",
                is_valid=False,
                error_message=f"Total players {total} seems too high"
            )
        
        return OCRResult(
            text=original,
            confidence=1.0,
            cleaned_text=f"{current}/{total}",
            is_valid=True
        )
    
    @staticmethod
    def _apply_corrections(text: str) -> str:
        """Apply common OCR error corrections"""
        corrected = text
        for wrong, right in OCRValidator.CHAR_CORRECTIONS.items():
            corrected = corrected.replace(wrong, right)
        return corrected
    
    @staticmethod
    def _clean_money_number(text: str) -> str:
        """
        Clean money format.
        
        Handle cases like:
        - "1,234.56" -> "1234.56"
        - "12.123.12" (OCR error) -> "12123.12"
        - "12.123,12" (OCR error) -> "12123.12"
        """
        # Count dots and commas
        dot_count = text.count('.')
        comma_count = text.count(',')
        
        # Case 1: Multiple dots (OCR error)
        if dot_count > 1:
            # Keep only last dot (decimal separator)
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
        
        # Case 2: Both dot and comma
        elif dot_count >= 1 and comma_count >= 1:
            # Determine which is decimal separator
            # Usually: 1,234.56 (comma is thousands, dot is decimal)
            # But can be: 1.234,56 (European format)
            
            last_dot = text.rfind('.')
            last_comma = text.rfind(',')
            
            if last_dot > last_comma:
                # Format: 1,234.56 - dot is decimal
                text = text.replace(',', '')
            else:
                # Format: 1.234,56 - comma is decimal
                text = text.replace('.', '').replace(',', '.')
        
        # Case 3: Only commas (European format or thousands separator)
        elif comma_count > 0:
            if comma_count == 1 and len(text.split(',')[1]) == 2:
                # Likely decimal: 123,45
                text = text.replace(',', '.')
            else:
                # Thousands separator: 1,234,567
                text = text.replace(',', '')
        
        return text


class AdvancedOCRReader:
    """
    Advanced OCR reader with multiple attempts and confidence checking.
    """
    
    def __init__(self, logger_name: str = "AdvancedOCR"):
        self.logger = AviatorLogger.get_logger(logger_name)
        self.preprocessor = OCRPreprocessor()
        self.validator = OCRValidator()
    
    def read_score(self, img: np.ndarray, attempts: int = 3) -> Optional[float]:
        """
        Read SCORE with multiple preprocessing attempts.
        
        Returns:
            Float score value or None if all attempts fail
        """
        best_result = None
        best_confidence = 0.0
        
        # Try multiple preprocessing strategies
        strategies = [
            ('standard', lambda: self.preprocessor.preprocess_large_number(img, scale=3.0)),
            ('high_scale', lambda: self.preprocessor.preprocess_large_number(img, scale=4.0)),
            ('low_scale', lambda: self.preprocessor.preprocess_large_number(img, scale=2.5)),
        ]
        
        for strategy_name, preprocess_func in strategies[:attempts]:
            try:
                processed = preprocess_func()
                
                # OCR with whitelist
                config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,x'
                text = pytesseract.image_to_string(processed, config=config)
                
                # Validate
                result = self.validator.validate_score(text)
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                
                # If we got perfect result, stop
                if result.is_valid and result.confidence == 1.0:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Strategy {strategy_name} failed: {e}")
                continue
        
        if best_result and best_result.is_valid:
            value = float(best_result.cleaned_text)
            self.logger.debug(f"Score read: {value}x (confidence: {best_confidence})")
            return value
        else:
            if best_result:
                self.logger.warning(
                    f"Score OCR failed: {best_result.error_message} "
                    f"(text: '{best_result.text}')"
                )
            return None
    
    def read_money(self, img: np.ndarray, 
                   size_type: str = 'medium',
                   attempts: int = 3) -> Optional[float]:
        """
        Read MONEY amount (my_money or other_money).
        
        Args:
            img: Input image
            size_type: 'medium' for other_money, 'small' for my_money
            attempts: Number of preprocessing attempts
        """
        best_result = None
        best_confidence = 0.0
        
        # Choose preprocessing based on size
        if size_type == 'small':
            preprocess_func = self.preprocessor.preprocess_small_number
            scales = [4.0, 5.0, 3.5]
        else:  # medium
            preprocess_func = self.preprocessor.preprocess_medium_number
            scales = [2.5, 3.0, 2.0]
        
        for scale in scales[:attempts]:
            try:
                processed = preprocess_func(img, scale=scale)
                
                # OCR with whitelist (no 'x')
                config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
                text = pytesseract.image_to_string(processed, config=config)
                
                # Validate
                result = self.validator.validate_money(text)
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                
                if result.is_valid and result.confidence == 1.0:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Money read attempt (scale={scale}) failed: {e}")
                continue
        
        if best_result and best_result.is_valid:
            value = float(best_result.cleaned_text)
            self.logger.debug(
                f"Money read: {value} ({size_type}, confidence: {best_confidence})"
            )
            return value
        else:
            if best_result:
                self.logger.warning(
                    f"Money OCR failed: {best_result.error_message} "
                    f"(text: '{best_result.text}')"
                )
            return None
    
    def read_player_count(self, img: np.ndarray, 
                          attempts: int = 3) -> Optional[Tuple[int, int]]:
        """
        Read PLAYER COUNT (current/total).
        
        Returns:
            Tuple (current_players, total_players) or None
        """
        best_result = None
        best_confidence = 0.0
        
        scales = [5.0, 6.0, 4.5]
        
        for scale in scales[:attempts]:
            try:
                processed = self.preprocessor.preprocess_tiny_text(img, scale=scale)
                
                # OCR with whitelist (numbers and slash)
                config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/'
                text = pytesseract.image_to_string(processed, config=config)
                
                # Validate
                result = self.validator.validate_player_count(text)
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                
                if result.is_valid and result.confidence == 1.0:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Player count attempt (scale={scale}) failed: {e}")
                continue
        
        if best_result and best_result.is_valid:
            # Parse "123/456"
            parts = best_result.cleaned_text.split('/')
            current = int(parts[0])
            total = int(parts[1])
            
            self.logger.debug(
                f"Player count read: {current}/{total} (confidence: {best_confidence})"
            )
            return (current, total)
        else:
            if best_result:
                self.logger.warning(
                    f"Player count OCR failed: {best_result.error_message} "
                    f"(text: '{best_result.text}')"
                )
            return None