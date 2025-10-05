# core/screen_reader.py
# VERSION: 5.0
# CHANGES: Integration with AdvancedOCRReader, OpenCV support

import mss
import numpy as np
from PIL import Image
from typing import Dict, Optional
from logger import AviatorLogger
from core.ocr_processor import AdvancedOCRReader


class ScreenReader:
    """
    High-performance screen capture with advanced OCR.
    VERSION: 5.0
    """
    
    def __init__(self, region: Dict[str, int], ocr_type: str = 'auto'):
        """
        Initialize screen reader.
        
        Args:
            region: Dictionary with 'top', 'left', 'width', 'height'
            ocr_type: Type of OCR to use ('score', 'money_medium', 'money_small', 
                     'player_count', or 'auto' for legacy)
        """
        self.region = self._validate_region(region)
        self.ocr_type = ocr_type
        self._sct = None
        self._last_image = None
        
        self.logger = AviatorLogger.get_logger("ScreenReader")
        self.advanced_ocr = AdvancedOCRReader()
    
    def _validate_region(self, region: Dict[str, int]) -> Dict[str, int]:
        """Validate and normalize region coordinates."""
        required_keys = ['top', 'left', 'width', 'height']
        if not all(key in region for key in required_keys):
            raise ValueError(f"Region must contain keys: {required_keys}")
        
        return {
            'top': max(0, region['top']),
            'left': max(0, region['left']),
            'width': max(1, region['width']),
            'height': max(1, region['height'])
        }
    
    def capture_image(self) -> np.ndarray:
        """
        Capture screen region as OpenCV image (BGR).
        
        Returns:
            numpy array (BGR format for OpenCV)
        """
        if self._sct is None:
            self._sct = mss.mss()
        
        try:
            sct_img = self._sct.grab(self.region)
            
            # Convert to PIL Image
            pil_image = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            
            # Convert to numpy (RGB)
            img_rgb = np.array(pil_image)
            
            # Convert RGB to BGR (OpenCV format)
            img_bgr = img_rgb[:, :, ::-1].copy()
            
            self._last_image = img_bgr
            return img_bgr
            
        except Exception as e:
            self.logger.error(f"Capture error: {e}")
            if self._sct:
                self._sct.close()
                self._sct = mss.mss()
            raise
    
    def read_with_advanced_ocr(self, ocr_type: Optional[str] = None) -> Optional[any]:
        """
        Read using advanced OCR processor.
        
        Args:
            ocr_type: Override the default OCR type
            
        Returns:
            Parsed value (float for score/money, tuple for player count)
        """
        ocr_type = ocr_type or self.ocr_type
        
        try:
            img = self.capture_image()
            
            if ocr_type == 'score':
                return self.advanced_ocr.read_score(img)
            
            elif ocr_type == 'money_medium':
                return self.advanced_ocr.read_money(img, size_type='medium')
            
            elif ocr_type == 'money_small':
                return self.advanced_ocr.read_money(img, size_type='small')
            
            elif ocr_type == 'player_count':
                return self.advanced_ocr.read_player_count(img)
            
            else:
                self.logger.error(f"Unknown OCR type: {ocr_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Advanced OCR error: {e}")
            return None
    
    def read_once(self) -> str:
        """
        Legacy method for compatibility.
        Captures and returns raw OCR text.
        """
        import pytesseract
        
        try:
            img = self.capture_image()
            
            # Convert BGR to RGB for pytesseract
            img_rgb = img[:, :, ::-1]
            
            # Basic OCR
            text = pytesseract.image_to_string(img_rgb, config='--oem 3 --psm 6')
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return ""
    
    def save_last_capture(self, filename: str) -> bool:
        """Save last captured image for debugging."""
        if self._last_image is not None:
            try:
                import cv2
                cv2.imwrite(filename, self._last_image)
                return True
            except Exception as e:
                self.logger.error(f"Save error: {e}")
        return False
    
    def close(self) -> None:
        """Clean up resources."""
        if self._sct:
            self._sct.close()
            self._sct = None