# ai/phase_predictor.py
# Refactored from predict_color.py

import numpy as np
import pickle
import mss
import pyautogui
import time
from root.logger import AviatorLogger


class PhasePredictor:
    """Real-time game phase prediction using trained model"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.regions = {}
        self.logger = AviatorLogger.get_logger("PhasePredictor")
        
        self._load_model()
    
    def _load_model(self):
        """Load trained model"""
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        self.logger.info(f"Model loaded: {self.model_path}")
    
    def setup_region(self, bookmaker: str):
        """Interactive region setup"""
        print(f"\n=== Setup region for {bookmaker} ===")
        print("Click TopLeft...")
        input("Press Enter")
        x1, y1 = pyautogui.position()
        
        print("Click BottomRight...")
        input("Press Enter")
        x2, y2 = pyautogui.position()
        
        self.regions[bookmaker] = {
            "top": min(y1, y2),
            "left": min(x1, x2),
            "width": abs(x2 - x1),
            "height": abs(y2 - y1)
        }
        self.logger.info(f"Region set for {bookmaker}")
    
    def predict_phase(self, bookmaker: str):
        """Predict phase for bookmaker"""
        if bookmaker not in self.regions:
            raise ValueError(f"Region not set for {bookmaker}")
        
        sct = mss.mss()
        bbox = self.regions[bookmaker]
        
        img = np.array(sct.grab(bbox))[:, :, :3]
        mean_color = img.mean(axis=(0, 1))
        rgb = mean_color[::-1]  # BGR to RGB
        r, g, b = map(float, rgb)
        
        cluster = self.model.predict(np.array([[r, g, b]]))[0]
        
        return cluster, (int(r), int(g), int(b))
    
    def start_prediction(self, bookmakers: list, delay: float = 0.5):
        """Start continuous prediction"""
        self.logger.info(f"Starting prediction for {len(bookmakers)} bookmakers")
        self.logger.info(f"Delay: {delay}s per bookmaker")
        
        index = 0
        try:
            while True:
                bookmaker = bookmakers[index % len(bookmakers)]
                cluster, rgb = self.predict_phase(bookmaker)
                
                self.logger.info(
                    f"{bookmaker:15s} -> RGB{rgb} -> Cluster {cluster}"
                )
                
                index += 1
                time.sleep(delay)
        
        except KeyboardInterrupt:
            self.logger.info("Prediction stopped")


def main():
    from root.logger import init_logging
    
    init_logging()
    
    print("=" * 60)
    print("PHASE PREDICTOR - Real-time Prediction")
    print("=" * 60)
    
    model_name = input("\nModel name (default 'game_phase_kmeans'): ").strip() or "game_phase_kmeans"
    model_path = f"models/{model_name}.pkl"
    
    delay = float(input("Delay per bookmaker in seconds (default 0.5): ").strip() or "0.5")
    
    predictor = PhasePredictor(model_path)
    
    # Setup bookmakers
    bookmakers = []
    while True:
        bm = input("Bookmaker name (empty to finish): ").strip()
        if not bm:
            break
        bookmakers.append(bm)
        predictor.setup_region(bm)
    
    if not bookmakers:
        print("No bookmakers added!")
        return
    
    print("\nStarting prediction. Press Ctrl+C to stop.")
    predictor.start_prediction(bookmakers, delay)


if __name__ == "__main__":
    main()
