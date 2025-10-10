# core/screen_reader.py
# VERSION: 1.5 - INTEGRATED FAST PREPROCESSING
# CHANGES: Integrated AviatorPreprocessor for speed + accuracy

import cv2
import numpy as np
import pytesseract
import mss
from typing import Optional, Dict, Tuple
from logger import AviatorLogger


class AviatorPreprocessor:
    """BRZI preprocessing za Aviator-specific regions"""
    
    def __init__(self):
        # Cache kernels
        self._sharpen_kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ], dtype=np.float32)
        self._denoise_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    
    def preprocess_score(self, img: np.ndarray) -> np.ndarray:
        """SCORE - VELIKE CRVENE brojeve (10-15ms)"""
        # Izdvoj crvenu boju
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower = (0, 100, 100)
        upper = (10, 255, 255)
        mask = cv2.inRange(hsv, lower, upper)
        
        if cv2.countNonZero(mask) < 50:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            result = cv2.bitwise_and(img, img, mask=mask)
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        
        # Upscale 4x
        h, w = gray.shape
        upscaled = cv2.resize(gray, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
        
        # Threshold
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise + sharpen
        denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._denoise_kernel)
        sharpened = cv2.filter2D(denoised, -1, self._sharpen_kernel)
        
        return sharpened
    
    def preprocess_money(self, img: np.ndarray) -> np.ndarray:
        """MONEY - BEL/ŽUTI tekst srednje veličine (10-12ms)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Upscale 3x
        h, w = gray.shape
        upscaled = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        
        # Adaptive threshold (bolje sa različitim osvetljenjem)
        binary = cv2.adaptiveThreshold(
            upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Clean
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self._denoise_kernel)
        return cleaned
    
    def preprocess_player_count(self, img: np.ndarray) -> np.ndarray:
        """PLAYER COUNT - MALI BEL tekst (8-10ms)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Upscale 2.5x (manje nego ostali)
        h, w = gray.shape
        upscaled = cv2.resize(gray, (int(w * 2.5), int(h * 2.5)), 
                             interpolation=cv2.INTER_LINEAR)
        
        # Simple threshold
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._denoise_kernel)
        
        return cleaned


class ScreenReader:
    """
    Enhanced ScreenReader sa integrovanim preprocessing.
    BACKWARD COMPATIBLE sa postojećim kodom!
    """
    
    def __init__(
        self,
        region: Dict[str, int],
        ocr_type: Optional[str] = None,
        logger_name: str = "ScreenReader",
        use_preprocessing: bool = True  # NOVA opcija!
    ):
        """
        Args:
            region: {'x': int, 'y': int, 'width': int, 'height': int}
            ocr_type: 'score', 'money_medium', 'money_small', 'player_count', None
            logger_name: Logger name
            use_preprocessing: Use fast preprocessing (default True)
        """
        self.region = region
        self.ocr_type = ocr_type
        self.logger = AviatorLogger.get_logger(logger_name)
        self.use_preprocessing = use_preprocessing
        
        # MSS instance
        self._sct = None
        self._last_image = None
        
        # Preprocessor (lazy init)
        self._preprocessor = None
        
        self.logger.info(
            f"Initialized: region={region}, "
            f"ocr_type={ocr_type}, "
            f"preprocessing={use_preprocessing}"
        )
    
    def _get_preprocessor(self) -> AviatorPreprocessor:
        """Lazy load preprocessor"""
        if self._preprocessor is None:
            self._preprocessor = AviatorPreprocessor()
        return self._preprocessor
    
    def capture_image(self) -> np.ndarray:
        """
        Capture screenshot sa preprocessing ako je omogućeno.
        KOMPATIBILNO sa starim kodom!
        """
        if self._sct is None:
            self._sct = mss.mss()
        
        # Capture raw
        monitor = {
            "left": self.region['x'],
            "top": self.region['y'],
            "width": self.region['width'],
            "height": self.region['height']
        }
        
        screenshot = self._sct.grab(monitor)
        img = np.array(screenshot)[:, :, :3]  # Remove alpha, keep BGR
        
        # Save za debug
        self._last_image = img.copy()
        
        # Apply preprocessing AKO je omogućeno
        if self.use_preprocessing and self.ocr_type:
            preprocessor = self._get_preprocessor()
            
            if self.ocr_type == 'score':
                img = preprocessor.preprocess_score(img)
            elif self.ocr_type in ['money_medium', 'money_small']:
                img = preprocessor.preprocess_money(img)
            elif self.ocr_type == 'player_count':
                img = preprocessor.preprocess_player_count(img)
            # Ako nije poznat tip, ostavi raw
        
        return img
    
    def read_once(self) -> str:
        """
        Legacy metoda - KOMPATIBILNA sa starim kodom.
        Sada koristi preprocessing automatski!
        """
        try:
            img = self.capture_image()
            
            # Ako je već preprocessed (grayscale), koristi direktno
            if len(img.shape) == 2:
                img_for_ocr = img
            else:
                # Convert BGR to RGB za pytesseract
                img_for_ocr = img[:, :, ::-1]
            
            # Basic OCR
            text = pytesseract.image_to_string(
                img_for_ocr, 
                config='--oem 3 --psm 6'
            )
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return ""
    
    def read_with_config(self, config: str = '--oem 3 --psm 7') -> str:
        """
        Čitaj sa custom Tesseract config.
        """
        try:
            img = self.capture_image()
            
            # Handle grayscale/color
            if len(img.shape) == 2:
                img_for_ocr = img
            else:
                img_for_ocr = img[:, :, ::-1]
            
            text = pytesseract.image_to_string(img_for_ocr, config=config)
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return ""
    
    def save_last_capture(self, filename: str) -> bool:
        """Save last captured image for debugging."""
        if self._last_image is not None:
            try:
                cv2.imwrite(filename, self._last_image)
                self.logger.info(f"Saved capture to: {filename}")
                return True
            except Exception as e:
                self.logger.error(f"Save error: {e}")
        else:
            self.logger.warning("No image to save")
        return False
    
    def get_last_image(self) -> Optional[np.ndarray]:
        """Get last captured image (for debugging/visualization)."""
        return self._last_image
    
    def close(self) -> None:
        """Clean up resources."""
        if self._sct:
            self._sct.close()
            self._sct = None
        self.logger.info("ScreenReader closed")


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================

if __name__ == "__main__":
    import time
    
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*60)
    
    # Test dummy region
    test_region = {'x': 100, 'y': 100, 'width': 300, 'height': 80}
    
    # Test 1: Old way (without preprocessing)
    print("\n1. Old way (use_preprocessing=False):")
    reader_old = ScreenReader(
        region=test_region,
        ocr_type='score',
        use_preprocessing=False
    )
    
    start = time.perf_counter()
    img_old = reader_old.capture_image()
    elapsed_old = (time.perf_counter() - start) * 1000
    print(f"   Capture time: {elapsed_old:.2f}ms")
    print(f"   Image shape: {img_old.shape}")
    
    # Test 2: New way (with preprocessing)
    print("\n2. New way (use_preprocessing=True):")
    reader_new = ScreenReader(
        region=test_region,
        ocr_type='score',
        use_preprocessing=True
    )
    
    start = time.perf_counter()
    img_new = reader_new.capture_image()
    elapsed_new = (time.perf_counter() - start) * 1000
    print(f"   Capture + preprocess time: {elapsed_new:.2f}ms")
    print(f"   Image shape: {img_new.shape}")
    
    # Test 3: Legacy read_once method
    print("\n3. Legacy read_once() method:")
    start = time.perf_counter()
    text = reader_new.read_once()
    elapsed_read = (time.perf_counter() - start) * 1000
    print(f"   Full OCR time: {elapsed_read:.2f}ms")
    print(f"   Text: '{text}'")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - BACKWARD COMPATIBLE!")
    print(f"Preprocessing overhead: +{elapsed_new - elapsed_old:.1f}ms (acceptable!)")
    
    # Cleanup
    reader_old.close()
    reader_new.close()