# region_GamePhase.py
# VERSION: 2.1
# CHANGES: Fixed cluster ID mapping (removed +1), improved error handling

from core.screen_reader import ScreenReader
from regions.base_region import Region
from logger import AviatorLogger
from config import AppConstants, GamePhase

import pickle
import numpy as np
import mss
from typing import Optional, Dict


class GamePhaseDetector(Region):
    """
    Detects game phase using color-based K-means clustering.
    Much faster and more reliable than OCR for phase detection.
    
    K-Means Model returns clusters 0-5 which directly map to GamePhase enum values.
    """
    
    def __init__(
        self,
        screen_reader: ScreenReader,
        model_path: str = AppConstants.model_file
    ):
        super().__init__(screen_reader)
        self.logger = AviatorLogger.get_logger("GamePhaseDetector")
        self.model_path = model_path
        self.kmeans = self._load_model()
        self._sct = None
    
    def _load_model(self):
        """Load K-means model from pickle file"""
        try:
            with open(self.model_path, "rb") as f:
                kmeans = pickle.load(f)
            self.logger.info(f"Loaded K-means model from {self.model_path}")
            return kmeans
        except FileNotFoundError:
            self.logger.error(f"Model file not found: {self.model_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise
    
    def read_text(self) -> Optional[Dict]:
        """
        Detect game phase using color analysis.
        
        Returns:
            Dict with 'phase' (GamePhase enum) or None if error
        """
        try:
            rgb = self._get_mean_rgb()
            if rgb is None:
                return None
            
            phase = self._predict_phase(rgb)
            
            # Validate phase is within enum range
            if not self._is_valid_phase(phase):
                if AppConstants.debug:
                    self.logger.warning(f"Invalid phase {phase}, RGB: {rgb}")
                return None
            
            if AppConstants.debug:
                self.logger.debug(f"RGB: {rgb}, Phase: {GamePhase(phase).name}")
            
            return {'phase': phase}
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error detecting phase: {e}")
            return None
    
    def _get_mean_rgb(self) -> Optional[np.ndarray]:
        """Capture region and calculate mean RGB color"""
        try:
            if self._sct is None:
                self._sct = mss.mss()
            
            bbox = {
                'top': self.screen_reader.region['top'],
                'left': self.screen_reader.region['left'],
                'width': self.screen_reader.region['width'],
                'height': self.screen_reader.region['height']
            }
            
            img = np.array(self._sct.grab(bbox))[:, :, :3]
            mean_color = img.mean(axis=(0, 1))
            rgb = mean_color[::-1]
            
            return rgb.reshape(1, -1)
            
        except Exception as e:
            if AppConstants.debug:
                self.logger.error(f"Error capturing RGB: {e}")
            return None
    
    def _predict_phase(self, rgb: np.ndarray) -> int:
        """
        Predict game phase using K-means model.
        
        CRITICAL FIX: Model returns cluster IDs 0-5 which directly map to GamePhase enum.
        Previously had "+ 1" which caused values 1-6, breaking the enum mapping.
        """
        cluster = self.kmeans.predict(rgb)[0]
        return int(cluster)  # Direct mapping, NO +1
    
    def _is_valid_phase(self, phase: int) -> bool:
        """Check if phase is a valid GamePhase enum value"""
        try:
            GamePhase(phase)
            return True
        except ValueError:
            return False
    
    def get_phase(self) -> Optional[GamePhase]:
        """Get current game phase as enum."""
        result = self.read_text()
        if result:
            return GamePhase(result['phase'])
        return None
    
    def is_game_ended(self) -> bool:
        """Check if game has ended (Phase ENDED)"""
        phase = self.get_phase()
        return phase == GamePhase.ENDED if phase else False
    
    def is_game_running(self) -> bool:
        """Check if game is running (SCORE_LOW, SCORE_MID, SCORE_HIGH)"""
        phase = self.get_phase()
        return phase in [GamePhase.SCORE_LOW, GamePhase.SCORE_MID, GamePhase.SCORE_HIGH] if phase else False
    
    def is_loading(self) -> bool:
        """Check if game is in loading phase (LOADING)"""
        phase = self.get_phase()
        return phase == GamePhase.LOADING if phase else False
    
    def is_betting_time(self) -> bool:
        """Check if in betting time (BETTING)"""
        phase = self.get_phase()
        return phase == GamePhase.BETTING if phase else False
    
    def close(self) -> None:
        """Clean up resources"""
        if self._sct:
            self._sct.close()
            self._sct = None