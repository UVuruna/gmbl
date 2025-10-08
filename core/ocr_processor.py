# core/ocr_processor.py
# VERSION: 6.0 - KOMPLETNA IMPLEMENTACIJA
# CHANGES: Dodato EasyOCR + PaddleOCR + inteligentno prebacivanje

import cv2
import numpy as np
import pytesseract
import re
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from logger import AviatorLogger
from enum import Enum


class OCREngine(Enum):
    """Dostupni OCR engine-i"""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"


@dataclass
class OCRResult:
    """OCR rezultat sa metapodacima"""
    text: str
    confidence: float
    cleaned_text: str
    is_valid: bool
    engine: str
    error_message: Optional[str] = None


class OCRPreprocessor:
    """Napredna predobrada slika za OCR optimizaciju"""
    
    @staticmethod
    def preprocess_large_number(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
        """Predobrada za SCORE (najveći tekst)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, 
                         interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        return binary
    
    @staticmethod
    def preprocess_medium_number(img: np.ndarray, scale: float = 2.5) -> np.ndarray:
        """Predobrada za OTHER_MONEY (srednji tekst)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(gray, 0, 255, 
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    @staticmethod
    def preprocess_small_number(img: np.ndarray, scale: float = 4.0) -> np.ndarray:
        """Predobrada za MY_MONEY (manji tekst) - agresivnije skaliranje"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 5, 50, 50)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return binary
    
    @staticmethod
    def preprocess_tiny_text(img: np.ndarray, scale: float = 5.0) -> np.ndarray:
        """Predobrada za PLAYER_COUNT (najmanji tekst) - maksimalno skaliranje"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        gray = clahe.apply(gray)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)
        binary = cv2.erode(binary, kernel, iterations=1)
        return binary


class OCRValidator:
    """Validacija i korekcija OCR rezultata"""
    
    CHAR_CORRECTIONS = {
        'O': '0', 'o': '0', 'Q': '0',
        'I': '1', 'l': '1', '|': '1',
        'Z': '2', 'z': '2',
        'S': '5', 's': '5',
        'B': '8', 'b': '8',
        'g': '9', 'q': '9',
    }
    
    @staticmethod
    def validate_score(text: str) -> OCRResult:
        """Validacija SCORE vrednosti (1.00 - 9999.99)"""
        original = text
        text = OCRValidator._apply_corrections(text)
        text = text.strip().replace('x', '').replace(',', '.')
        
        pattern = r'(\d+\.?\d*)'
        match = re.search(pattern, text)
        
        if not match:
            return OCRResult(
                text=original, confidence=0.0, cleaned_text="",
                is_valid=False, engine="validator",
                error_message="No number found"
            )
        
        cleaned = match.group(1)
        
        try:
            value = float(cleaned)
            
            if not (1.00 <= value <= 9999.99):
                return OCRResult(
                    text=original, confidence=0.3, cleaned_text=cleaned,
                    is_valid=False, engine="validator",
                    error_message=f"Out of range: {value}"
                )
            
            return OCRResult(
                text=original, confidence=1.0, cleaned_text=cleaned,
                is_valid=True, engine="validator"
            )
            
        except ValueError:
            return OCRResult(
                text=original, confidence=0.0, cleaned_text=cleaned,
                is_valid=False, engine="validator",
                error_message=f"Cannot parse: {cleaned}"
            )
    
    @staticmethod
    def validate_money(text: str) -> OCRResult:
        """Validacija MONEY vrednosti"""
        original = text
        text = OCRValidator._apply_corrections(text)
        text = OCRValidator._clean_money_number(text)
        
        pattern = r'(\d+\.?\d*)'
        match = re.search(pattern, text)
        
        if not match:
            return OCRResult(
                text=original, confidence=0.0, cleaned_text="",
                is_valid=False, engine="validator",
                error_message="No number found"
            )
        
        cleaned = match.group(1)
        
        try:
            value = float(cleaned)
            
            if value < 0 or value > 1000000:
                return OCRResult(
                    text=original, confidence=0.3, cleaned_text=cleaned,
                    is_valid=False, engine="validator",
                    error_message=f"Out of range: {value}"
                )
            
            return OCRResult(
                text=original, confidence=1.0, cleaned_text=cleaned,
                is_valid=True, engine="validator"
            )
            
        except ValueError:
            return OCRResult(
                text=original, confidence=0.0, cleaned_text=cleaned,
                is_valid=False, engine="validator",
                error_message=f"Cannot parse: {cleaned}"
            )
    
    @staticmethod
    def validate_player_count(text: str) -> OCRResult:
        """Validacija PLAYER_COUNT (format: 123/456)"""
        original = text
        text = OCRValidator._apply_corrections(text)
        
        pattern = r'(\d+)\s*/\s*(\d+)'
        match = re.search(pattern, text)
        
        if not match:
            return OCRResult(
                text=original, confidence=0.0, cleaned_text="",
                is_valid=False, engine="validator",
                error_message="Invalid format (expected: X/Y)"
            )
        
        current = int(match.group(1))
        total = int(match.group(2))
        
        if current > total:
            return OCRResult(
                text=original, confidence=0.5, cleaned_text=f"{current}/{total}",
                is_valid=False, engine="validator",
                error_message=f"Current ({current}) > Total ({total})"
            )
        
        if total > 10000:
            return OCRResult(
                text=original, confidence=0.3, cleaned_text=f"{current}/{total}",
                is_valid=False, engine="validator",
                error_message=f"Total {total} too high"
            )
        
        return OCRResult(
            text=original, confidence=1.0, cleaned_text=f"{current}/{total}",
            is_valid=True, engine="validator"
        )
    
    @staticmethod
    def _apply_corrections(text: str) -> str:
        """Primeni uobičajene OCR korekcije"""
        corrected = text
        for wrong, right in OCRValidator.CHAR_CORRECTIONS.items():
            corrected = corrected.replace(wrong, right)
        return corrected
    
    @staticmethod
    def _clean_money_number(text: str) -> str:
        """Očisti format novca (1,234.56 ili 12.123,12)"""
        dot_count = text.count('.')
        comma_count = text.count(',')
        
        if dot_count > 1:
            parts = text.split('.')
            text = ''.join(parts[:-1]) + '.' + parts[-1]
        
        elif dot_count >= 1 and comma_count >= 1:
            last_dot = text.rfind('.')
            last_comma = text.rfind(',')
            
            if last_dot > last_comma:
                text = text.replace(',', '')
            else:
                text = text.replace('.', '').replace(',', '.')
        
        elif comma_count > 0:
            if comma_count == 1 and len(text.split(',')[1]) == 2:
                text = text.replace(',', '.')
            else:
                text = text.replace(',', '')
        
        return text


class AdvancedOCRReader:
    """
    Napredni OCR reader sa SVIM engine-ima:
    - Tesseract (default, brz)
    - EasyOCR (backup, sporiji ali precizniji)
    - PaddleOCR (backup, dobar za manje fontove)
    """
    
    def __init__(self, logger_name: str = "AdvancedOCR"):
        self.logger = AviatorLogger.get_logger(logger_name)
        self.preprocessor = OCRPreprocessor()
        self.validator = OCRValidator()
        
        # Inicijalizuj engine-e (lazy loading)
        self._easyocr = None
        self._paddleocr = None
        self._available_engines = [OCREngine.TESSERACT]  # Uvek dostupan
        
        # Proveri dostupnost
        self._check_engine_availability()
    
    def _check_engine_availability(self):
        """Proveri koji OCR engine-i su dostupni"""
        # EasyOCR
        try:
            import easyocr
            self._available_engines.append(OCREngine.EASYOCR)
            self.logger.info("✅ EasyOCR available")
        except ImportError:
            self.logger.warning("⚠️  EasyOCR not available (pip install easyocr)")
        
        # PaddleOCR
        try:
            from paddleocr import PaddleOCR
            self._available_engines.append(OCREngine.PADDLEOCR)
            self.logger.info("✅ PaddleOCR available")
        except ImportError:
            self.logger.warning("⚠️  PaddleOCR not available (pip install paddleocr)")
    
    def _get_easyocr(self):
        """Lazy load EasyOCR"""
        if self._easyocr is None and OCREngine.EASYOCR in self._available_engines:
            import easyocr
            self._easyocr = easyocr.Reader(['en'], gpu=False)
            self.logger.info("Initialized EasyOCR")
        return self._easyocr
    
    def _get_paddleocr(self):
        """Lazy load PaddleOCR"""
        if self._paddleocr is None and OCREngine.PADDLEOCR in self._available_engines:
            from paddleocr import PaddleOCR
            self._paddleocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            self.logger.info("Initialized PaddleOCR")
        return self._paddleocr
    
    def _ocr_with_tesseract(self, img: np.ndarray, config: str) -> str:
        """OCR sa Tesseract"""
        return pytesseract.image_to_string(img, config=config).strip()
    
    def _ocr_with_easyocr(self, img: np.ndarray) -> str:
        """OCR sa EasyOCR"""
        reader = self._get_easyocr()
        if reader is None:
            return ""
        
        results = reader.readtext(img)
        if results:
            # Uzmi najbolji rezultat (najviši confidence)
            best = max(results, key=lambda x: x[2])
            return best[1]  # Tekst
        return ""
    
    def _ocr_with_paddleocr(self, img: np.ndarray) -> str:
        """OCR sa PaddleOCR"""
        ocr = self._get_paddleocr()
        if ocr is None:
            return ""
        
        result = ocr.ocr(img, cls=True)
        if result and result[0]:
            # Uzmi najbolji rezultat
            texts = [line[1][0] for line in result[0] if line[1][1] > 0.3]
            return ' '.join(texts)
        return ""
    
    def read_score(self, img: np.ndarray, max_attempts: int = 3) -> Optional[float]:
        """
        Čitaj SCORE sa fallback mehanizmom:
        1. Tesseract (brz, pokušaj 3 strategije)
        2. Ako fail -> EasyOCR
        3. Ako fail -> PaddleOCR
        """
        best_result = None
        best_confidence = 0.0
        
        # TESSERACT pokušaji
        strategies = [
            ('tess_standard', OCREngine.TESSERACT, 
             lambda: self.preprocessor.preprocess_large_number(img, scale=3.0)),
            ('tess_high', OCREngine.TESSERACT,
             lambda: self.preprocessor.preprocess_large_number(img, scale=4.0)),
            ('tess_low', OCREngine.TESSERACT,
             lambda: self.preprocessor.preprocess_large_number(img, scale=2.5)),
        ]
        
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,x'
        
        for name, engine, preprocess_func in strategies:
            if len(self._available_engines) == 1:
                # Samo Tesseract dostupan, pokušaj sve strategije
                max_tesseract_attempts = 3
            else:
                # Drugi engine-i dostupni, 1 Tesseract pokušaj pa prelazi dalje
                max_tesseract_attempts = 1
            
            if name.startswith('tess_') and strategies.index((name, engine, preprocess_func)) >= max_tesseract_attempts:
                break
            
            try:
                processed = preprocess_func()
                text = self._ocr_with_tesseract(processed, config)
                result = self.validator.validate_score(text)
                result.engine = engine.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                
                if result.is_valid and result.confidence == 1.0:
                    break  # Savršen rezultat, stop
                    
            except Exception as e:
                self.logger.debug(f"Strategy {name} failed: {e}")
                continue
        
        # Ako Tesseract fail, pokušaj EASYOCR
        if (best_result is None or best_confidence < 0.8) and OCREngine.EASYOCR in self._available_engines:
            try:
                processed = self.preprocessor.preprocess_large_number(img, scale=3.0)
                # EasyOCR treba RGB
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                text = self._ocr_with_easyocr(processed_rgb)
                result = self.validator.validate_score(text)
                result.engine = OCREngine.EASYOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ EasyOCR saved the day: {text}")
                    
            except Exception as e:
                self.logger.debug(f"EasyOCR failed: {e}")
        
        # Ako još uvek fail, pokušaj PADDLEOCR
        if (best_result is None or best_confidence < 0.8) and OCREngine.PADDLEOCR in self._available_engines:
            try:
                processed = self.preprocessor.preprocess_large_number(img, scale=3.0)
                text = self._ocr_with_paddleocr(processed)
                result = self.validator.validate_score(text)
                result.engine = OCREngine.PADDLEOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ PaddleOCR saved the day: {text}")
                    
            except Exception as e:
                self.logger.debug(f"PaddleOCR failed: {e}")
        
        # Vrati najbolji rezultat
        if best_result and best_result.is_valid:
            value = float(best_result.cleaned_text)
            self.logger.debug(
                f"Score: {value}x (engine: {best_result.engine}, "
                f"confidence: {best_confidence:.2f})"
            )
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
                   max_attempts: int = 3) -> Optional[float]:
        """
        Čitaj MONEY vrednost sa fallback mehanizmom.
        
        Args:
            size_type: 'medium' (other_money) ili 'small' (my_money)
        """
        best_result = None
        best_confidence = 0.0
        
        # Odaberi preprocessing
        if size_type == 'small':
            preprocess = self.preprocessor.preprocess_small_number
        else:
            preprocess = self.preprocessor.preprocess_medium_number
        
        # TESSERACT pokušaj
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,'
        
        try:
            processed = preprocess(img)
            text = self._ocr_with_tesseract(processed, config)
            result = self.validator.validate_money(text)
            result.engine = OCREngine.TESSERACT.value
            
            if result.is_valid:
                best_result = result
                best_confidence = result.confidence
                
        except Exception as e:
            self.logger.debug(f"Tesseract money failed: {e}")
        
        # EASYOCR fallback
        if (best_result is None or best_confidence < 0.8) and OCREngine.EASYOCR in self._available_engines:
            try:
                processed = preprocess(img)
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                text = self._ocr_with_easyocr(processed_rgb)
                result = self.validator.validate_money(text)
                result.engine = OCREngine.EASYOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ EasyOCR money: {text}")
                    
            except Exception as e:
                self.logger.debug(f"EasyOCR money failed: {e}")
        
        # PADDLEOCR fallback
        if (best_result is None or best_confidence < 0.8) and OCREngine.PADDLEOCR in self._available_engines:
            try:
                processed = preprocess(img)
                text = self._ocr_with_paddleocr(processed)
                result = self.validator.validate_money(text)
                result.engine = OCREngine.PADDLEOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ PaddleOCR money: {text}")
                    
            except Exception as e:
                self.logger.debug(f"PaddleOCR money failed: {e}")
        
        # Vrati rezultat
        if best_result and best_result.is_valid:
            value = float(best_result.cleaned_text)
            self.logger.debug(
                f"Money ({size_type}): {value:.2f} "
                f"(engine: {best_result.engine})"
            )
            return value
        else:
            if best_result:
                self.logger.warning(f"Money OCR failed: {best_result.error_message}")
            return None
    
    def read_player_count(self, img: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Čitaj PLAYER_COUNT (123/456) sa fallback.
        
        Returns:
            (current, total) ili None
        """
        best_result = None
        best_confidence = 0.0
        
        # TESSERACT pokušaj
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/'
        
        try:
            processed = self.preprocessor.preprocess_tiny_text(img)
            text = self._ocr_with_tesseract(processed, config)
            result = self.validator.validate_player_count(text)
            result.engine = OCREngine.TESSERACT.value
            
            if result.is_valid:
                best_result = result
                best_confidence = result.confidence
                
        except Exception as e:
            self.logger.debug(f"Tesseract player_count failed: {e}")
        
        # EASYOCR fallback
        if (best_result is None or best_confidence < 0.8) and OCREngine.EASYOCR in self._available_engines:
            try:
                processed = self.preprocessor.preprocess_tiny_text(img)
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
                text = self._ocr_with_easyocr(processed_rgb)
                result = self.validator.validate_player_count(text)
                result.engine = OCREngine.EASYOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ EasyOCR player_count: {text}")
                    
            except Exception as e:
                self.logger.debug(f"EasyOCR player_count failed: {e}")
        
        # PADDLEOCR fallback
        if (best_result is None or best_confidence < 0.8) and OCREngine.PADDLEOCR in self._available_engines:
            try:
                processed = self.preprocessor.preprocess_tiny_text(img)
                text = self._ocr_with_paddleocr(processed)
                result = self.validator.validate_player_count(text)
                result.engine = OCREngine.PADDLEOCR.value
                
                if result.is_valid and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
                    self.logger.info(f"✅ PaddleOCR player_count: {text}")
                    
            except Exception as e:
                self.logger.debug(f"PaddleOCR player_count failed: {e}")
        
        # Vrati rezultat
        if best_result and best_result.is_valid:
            match = re.search(r'(\d+)/(\d+)', best_result.cleaned_text)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                self.logger.debug(
                    f"Player count: {current}/{total} "
                    f"(engine: {best_result.engine})"
                )
                return (current, total)
        else:
            if best_result:
                self.logger.warning(
                    f"Player count OCR failed: {best_result.error_message}"
                )
        
        return None