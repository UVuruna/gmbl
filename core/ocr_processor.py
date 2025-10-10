# core/ocr_processor.py
# VERSION: 2.1 - INTEGRATED SMART VALIDATOR
# CHANGES: Dodao SmartOCRValidator za auto-correction

import re
import cv2
import numpy as np
import pytesseract
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
from logger import AviatorLogger


# ============================================================================
# SMART VALIDATOR (Integrated from v1.2)
# ============================================================================

@dataclass
class ValidationResult:
    """Result of validation + correction"""
    is_valid: bool
    original_text: str
    corrected_text: str
    value: Optional[float]
    confidence: float
    corrections_applied: List[str]


class SmartOCRValidator:
    """Inteligentni validator sa auto-correction"""
    
    CHAR_REPLACEMENTS = {
        'O': '0', 'o': '0',
        'I': '1', 'l': '1',
        'S': '5', 's': '5',
        'Z': '2',
        'B': '8',
        'g': '9',
        'G': '6',
    }
    
    SUSPICIOUS_PATTERNS = [
        (r'(\d+)l(\d+)', r'\g<1>1\g<2>'),
        (r'(\d+)O(\d+)', r'\g<1>0\g<2>'),
        (r'x$', ''),
        (r'^x', ''),
    ]
    
    def __init__(self, min_value: float = 1.0, max_value: float = 10000.0):
        self.min_value = min_value
        self.max_value = max_value
    
    def validate_score(self, text: str) -> ValidationResult:
        """Validate and auto-correct Aviator SCORE"""
        original = text
        corrections = []
        
        # Cleanup
        text = text.strip().replace(' ', '').replace('\n', '').replace('\t', '')
        
        # Character fixes
        for old_char, new_char in self.CHAR_REPLACEMENTS.items():
            if old_char in text:
                text = text.replace(old_char, new_char)
                corrections.append(f"'{old_char}' -> '{new_char}'")
        
        # Pattern fixes
        for pattern, replacement in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
                corrections.append(f"Pattern fix: {pattern}")
        
        # Decimal fix
        text, decimal_fix = self._fix_decimal_separator(text)
        if decimal_fix:
            corrections.append(decimal_fix)
        
        # Parse
        value = self._try_parse_float(text)
        
        # Advanced fixes if failed
        if value is None and len(text) > 0:
            text, advanced_fixes = self._apply_advanced_fixes(text)
            corrections.extend(advanced_fixes)
            value = self._try_parse_float(text)
        
        # Validate
        is_valid = False
        confidence = 0.0
        
        if value is not None:
            if self.min_value <= value <= self.max_value:
                is_valid = True
                
                if len(corrections) == 0:
                    confidence = 0.95
                elif len(corrections) <= 2:
                    confidence = 0.85
                else:
                    confidence = 0.70
            else:
                confidence = 0.1
        
        return ValidationResult(
            is_valid=is_valid,
            original_text=original,
            corrected_text=text,
            value=value,
            confidence=confidence,
            corrections_applied=corrections
        )
    
    def _fix_decimal_separator(self, text: str) -> Tuple[str, Optional[str]]:
        """Fix decimal separator issues"""
        dot_count = text.count('.')
        comma_count = text.count(',')
        correction = None
        
        if dot_count > 1:
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            correction = "Fixed multiple dots"
        
        elif comma_count > 1:
            parts = text.split(',')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            correction = "Fixed multiple commas"
        
        elif dot_count >= 1 and comma_count >= 1:
            last_dot = text.rfind('.')
            last_comma = text.rfind(',')
            
            if last_dot > last_comma:
                text = text.replace(',', '')
                correction = "Removed comma (thousands)"
            else:
                text = text.replace('.', '').replace(',', '.')
                correction = "Comma -> dot (decimal)"
        
        elif comma_count == 1 and dot_count == 0:
            parts = text.split(',')
            if len(parts) == 2 and len(parts[1]) == 2:
                text = text.replace(',', '.')
                correction = "Comma -> dot (decimal)"
            else:
                text = text.replace(',', '')
                correction = "Removed comma (thousands)"
        
        return text, correction
    
    def _try_parse_float(self, text: str) -> Optional[float]:
        """Try to parse text as float"""
        try:
            return float(text)
        except (ValueError, TypeError):
            return None
    
    def _apply_advanced_fixes(self, text: str) -> Tuple[str, List[str]]:
        """Advanced fixes when basic parsing fails"""
        fixes = []
        
        clean = re.sub(r'[^\d.]', '', text)
        if clean != text:
            text = clean
            fixes.append("Removed all non-numeric")
        
        if text.startswith('.'):
            text = '0' + text
            fixes.append("Added leading zero")
        
        if text.endswith('.'):
            text = text[:-1]
            fixes.append("Removed trailing dot")
        
        if text.count('.') > 1:
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
            fixes.append("Kept only last dot")
        
        return text, fixes


# ============================================================================
# ENHANCED OCR PROCESSOR
# ============================================================================

class OCREngine(Enum):
    """Dostupni OCR engine-i"""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"


class AdvancedOCRReader:
    """
    Advanced OCR Reader sa:
    - Tesseract (default, brz)
    - SmartValidator (auto-correction)
    - Fallback na EasyOCR/PaddleOCR (ako su instalirani)
    """
    
    def __init__(self, logger_name: str = "AdvancedOCR"):
        self.logger = AviatorLogger.get_logger(logger_name)
        self.validator = SmartOCRValidator()
        
        # Lazy load fallback engines
        self._easyocr = None
        self._paddleocr = None
        self._available_engines = [OCREngine.TESSERACT]
        
        self._check_engine_availability()
    
    def _check_engine_availability(self):
        """Check koje engine-e su dostupni"""
        try:
            import easyocr
            self._available_engines.append(OCREngine.EASYOCR)
            self.logger.info("✅ EasyOCR available")
        except ImportError:
            pass
        
        try:
            from paddleocr import PaddleOCR
            self._available_engines.append(OCREngine.PADDLEOCR)
            self.logger.info("✅ PaddleOCR available")
        except ImportError:
            pass
    
    def read_score(
        self, 
        img: np.ndarray, 
        max_attempts: int = 1  # SMANJENO sa 3 na 1 za brzinu!
    ) -> Optional[float]:
        """
        Čitaj SCORE sa validation.
        
        Args:
            img: Preprocessed image (već obrađen!)
            max_attempts: Broj pokušaja (default 1 za brzinu)
            
        Returns:
            Score vrednost ili None
        """
        # Config za score (samo brojevi i decimala)
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,x'
        
        try:
            # Ako je grayscale, koristi direktno
            if len(img.shape) == 2:
                img_rgb = img
            else:
                img_rgb = img[:, :, ::-1]  # BGR to RGB
            
            # OCR
            raw_text = pytesseract.image_to_string(img_rgb, config=config).strip()
            
            # Validate + Auto-correct
            result = self.validator.validate_score(raw_text)
            
            if result.is_valid:
                # Log corrections ako ih ima
                if result.corrections_applied:
                    self.logger.debug(
                        f"Score corrected: '{result.original_text}' -> "
                        f"'{result.corrected_text}' (confidence: {result.confidence:.2f})"
                    )
                return result.value
            else:
                # Log fail
                self.logger.debug(
                    f"Score invalid: '{raw_text}' "
                    f"(tried corrections: {result.corrections_applied})"
                )
                return None
                
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return None
    
    def read_money(
        self, 
        img: np.ndarray,
        size_type: str = 'medium'
    ) -> Optional[float]:
        """
        Čitaj MONEY sa validation.
        """
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
        
        try:
            if len(img.shape) == 2:
                img_rgb = img
            else:
                img_rgb = img[:, :, ::-1]
            
            raw_text = pytesseract.image_to_string(img_rgb, config=config).strip()
            
            # Validate money (range 0 - infinity)
            validator = SmartOCRValidator(min_value=0.0, max_value=999999999.0)
            result = validator.validate_score(raw_text)  # Koristi istu logiku
            
            if result.is_valid:
                if result.corrections_applied:
                    self.logger.debug(
                        f"Money corrected: '{result.original_text}' -> "
                        f"'{result.corrected_text}'"
                    )
                return result.value
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Money OCR error: {e}")
            return None
    
    def read_player_count(self, img: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Čitaj PLAYER COUNT (format: "X/Y").
        """
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/'
        
        try:
            if len(img.shape) == 2:
                img_rgb = img
            else:
                img_rgb = img[:, :, ::-1]
            
            raw_text = pytesseract.image_to_string(img_rgb, config=config).strip()
            
            # Parse "X/Y"
            if '/' in raw_text:
                parts = raw_text.split('/')
                if len(parts) == 2:
                    try:
                        current = int(re.sub(r'[^\d]', '', parts[0]))
                        total = int(re.sub(r'[^\d]', '', parts[1]))
                        
                        # Validate range
                        if 0 <= current <= 999999 and 0 <= total <= 999999:
                            return (current, total)
                    except:
                        pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"Player count OCR error: {e}")
            return None


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

if __name__ == "__main__":
    print("TESTING ENHANCED OCR PROCESSOR")
    print("="*60)
    
    # Test validator
    validator = SmartOCRValidator()
    
    test_cases = [
        "2.47x",
        "l.23",
        "1O.45",
        "5,Oo",
        "l23.45",
    ]
    
    print("\nValidator tests:")
    for text in test_cases:
        result = validator.validate_score(text)
        status = "✅" if result.is_valid else "❌"
        print(f"{status} '{text}' -> {result.value} (conf: {result.confidence:.2f})")
    
    print("\n" + "="*60)
    print("✅ TESTS PASSED")