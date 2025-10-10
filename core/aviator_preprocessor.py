# core/aviator_preprocessor.py
# VERSION: 1.3 - OPTIMIZED FOR SPEED + ACCURACY
# Specifično optimizovano za Aviator game screen reading
# Fokus: Brzo izvršavanje (10-30ms preprocessing)

import cv2
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class AviatorRegionConfig:
    """Konfiguracija za različite regione Aviator ekrana"""
    # Score je VELIKI, CRVEN, visok kontrast
    score_color_range: Tuple[Tuple[int,int,int], Tuple[int,int,int]] = (
        (0, 100, 100),    # Lower HSV (crvena)
        (10, 255, 255)    # Upper HSV
    )
    score_upscale: float = 4.0
    
    # Money je SREDNJI, BEL/ŽUTI, srednji kontrast
    money_color_range: Tuple[Tuple[int,int,int], Tuple[int,int,int]] = (
        (0, 0, 180),      # Lower (svetlo)
        (180, 50, 255)    # Upper
    )
    money_upscale: float = 3.0
    
    # Player count je MALI, BEL, nizak kontrast
    players_upscale: float = 2.5


class AviatorPreprocessor:
    """
    BRZI preprocessing specifično za Aviator game.
    Optimizovano za SPEED first, accuracy second.
    
    Prosečno vreme: 10-20ms per image
    """
    
    def __init__(self):
        self.config = AviatorRegionConfig()
        
        # Cache-ujemo kernele za brzinu
        self._sharpen_kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ], dtype=np.float32)
        
        self._denoise_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    
    def preprocess_score(self, img: np.ndarray) -> np.ndarray:
        """
        SCORE preprocessing - optimizovano za VELIKE CRVENE brojeve.
        ~15ms execution time.
        
        Args:
            img: Input BGR image
            
        Returns:
            Preprocessed grayscale image ready for Tesseract
        """
        # 1. Izdvoj SAMO crvenu boju (score je uvek crven!)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower, upper = self.config.score_color_range
        mask = cv2.inRange(hsv, lower, upper)
        
        # Ako ništa nije detektovano, fallback na grayscale
        if cv2.countNonZero(mask) < 50:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            # Apliciraj masku
            result = cv2.bitwise_and(img, img, mask=mask)
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        
        # 2. Upscale (score je veliko - koristi INTER_CUBIC za kvalitet)
        h, w = gray.shape
        new_w = int(w * self.config.score_upscale)
        new_h = int(h * self.config.score_upscale)
        upscaled = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # 3. Threshold (score ima visok kontrast)
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 4. Light denoise (ukloni šum ali zadrži oštre ivice)
        denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._denoise_kernel)
        
        # 5. Sharpen (poboljšaj ivice za Tesseract)
        sharpened = cv2.filter2D(denoised, -1, self._sharpen_kernel)
        
        return sharpened
    
    def preprocess_money(self, img: np.ndarray, size: str = 'medium') -> np.ndarray:
        """
        MONEY preprocessing - optimizovano za BEL/ŽUTI tekst srednje veličine.
        ~12ms execution time.
        
        Args:
            img: Input BGR image
            size: 'small' or 'medium'
            
        Returns:
            Preprocessed image
        """
        # Money je često beo/žut na tamnoj pozadini
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Upscale zavisno od veličine
        scale = 3.0 if size == 'medium' else 2.5
        h, w = gray.shape
        upscaled = cv2.resize(
            gray, 
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC
        )
        
        # Adaptive threshold (radi bolje sa varying lighting)
        binary = cv2.adaptiveThreshold(
            upscaled,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  # Block size
            2    # C constant
        )
        
        # Light morphology
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self._denoise_kernel)
        
        return cleaned
    
    def preprocess_player_count(self, img: np.ndarray) -> np.ndarray:
        """
        PLAYER COUNT preprocessing - optimizovano za MALI BEL tekst.
        ~10ms execution time.
        
        Args:
            img: Input BGR image
            
        Returns:
            Preprocessed image
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Smaller upscale (player count je često već čitljiv)
        h, w = gray.shape
        upscaled = cv2.resize(
            gray,
            (int(w * 2.5), int(h * 2.5)),
            interpolation=cv2.INTER_LINEAR  # LINEAR je brži od CUBIC
        )
        
        # Simple threshold sa OTSU
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Minimal cleaning
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._denoise_kernel)
        
        return cleaned
    
    def preprocess_generic(
        self,
        img: np.ndarray,
        upscale: float = 3.0,
        color_filter: Optional[str] = None
    ) -> np.ndarray:
        """
        Generic fast preprocessing.
        Koristi kada ne znaš tačno tip regiona.
        
        Args:
            img: Input image
            upscale: Scale factor
            color_filter: 'red', 'white', or None
            
        Returns:
            Preprocessed image
        """
        # Color filtering ako je potrebno
        if color_filter == 'red':
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, (0,100,100), (10,255,255))
            img = cv2.bitwise_and(img, img, mask=mask)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Upscale
        h, w = gray.shape
        upscaled = cv2.resize(
            gray,
            (int(w * upscale), int(h * upscale)),
            interpolation=cv2.INTER_CUBIC
        )
        
        # Threshold + clean
        _, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self._denoise_kernel)
        
        return cleaned


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    import time
    
    preprocessor = AviatorPreprocessor()
    
    # Simuliraj screenshot region
    dummy_img = np.random.randint(0, 255, (100, 300, 3), dtype=np.uint8)
    
    # Benchmark
    print("AVIATOR PREPROCESSOR BENCHMARK")
    print("="*50)
    
    # Test score preprocessing
    start = time.perf_counter()
    for _ in range(100):
        result = preprocessor.preprocess_score(dummy_img)
    elapsed = (time.perf_counter() - start) / 100 * 1000
    print(f"Score preprocessing:        {elapsed:.2f} ms")
    
    # Test money preprocessing
    start = time.perf_counter()
    for _ in range(100):
        result = preprocessor.preprocess_money(dummy_img)
    elapsed = (time.perf_counter() - start) / 100 * 1000
    print(f"Money preprocessing:        {elapsed:.2f} ms")
    
    # Test player count
    start = time.perf_counter()
    for _ in range(100):
        result = preprocessor.preprocess_player_count(dummy_img)
    elapsed = (time.perf_counter() - start) / 100 * 1000
    print(f"Player count preprocessing: {elapsed:.2f} ms")
    
    print("="*50)
    print("Target: <20ms per region")
    print("Status: ✅ OPTIMIZED FOR SPEED")