# screen_reader.py

from config import AppConstants
from logger import AviatorLogger

import mss
import pytesseract
from PIL import Image
from typing import Dict


class ScreenReader:
    """
    High-performance screen capture and OCR text extraction.
    Optimized for gaming applications requiring fast and accurate text reading.
    """
    
    TESSERACT_CONFIG = '--oem 3 --psm 6'
    
    def __init__(self, region: Dict[str, int]):
        """
        Initialize screen reader for specific region.
        
        Args:
            region: Dictionary with 'top', 'left', 'width', 'height' keys
        """
        self.region = self._validate_region(region)
        self._setup_tesseract()
        self._sct = None
        self._last_image = None
        self.logger = AviatorLogger.get_logger("ScreenReader")
        
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
    
    def _setup_tesseract(self) -> None:
        """Setup tesseract configuration from AppConstants."""
        pytesseract.pytesseract.tesseract_cmd = AppConstants.tesseract_path
    
    def read_once(self) -> str:
        """
        Capture screen region and extract text using OCR.
        
        Returns:
            Extracted text as string
        """
        try:
            image = self._capture_region()
            text = self._extract_text(image)
            
            if AppConstants.debug:
                self._log_debug_info(text, image)
            
            return text.strip()
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error reading text: {e}")
            return ""
    
    def _capture_region(self) -> Image.Image:
        """Capture screen region efficiently."""
        if self._sct is None:
            self._sct = mss.mss()
        
        try:
            sct_img = self._sct.grab(self.region)
            image = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            self._last_image = image
            return image
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Capture error: {e}")
            self._sct = mss.mss()
            raise
    
    def _extract_text(self, image: Image.Image) -> str:
        """Extract text from processed image using OCR."""
        return pytesseract.image_to_string(image, config=self.TESSERACT_CONFIG)
    
    def _log_debug_info(self, text: str, image: Image.Image) -> None:
        """Log debug information."""
        self.logger.debug(f"Region: {self.region}")
        self.logger.debug(f"Text: '{text}'")
        self.logger.debug(f"Image size: {image.size}")
    
    def save_last_capture(self, filename: str) -> bool:
        """Save last captured image for debugging."""
        if self._last_image:
            try:
                self._last_image.save(filename)
                return True
            except Exception as e:
                if AppConstants.debug:
                    self.logger.error(f"Save error: {e}")
        return False
    
    def close(self) -> None:
        """Clean up resources."""
        if self._sct:
            self._sct.close()
            self._sct = None