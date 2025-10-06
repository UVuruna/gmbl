# apps/prediction_agent.py
# VERSION: 1.0 - Integrated with v5.0 system
# PROGRAM 4: Prediction model training and testing
# Uses data from main_game_data.db to train ML models

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib

from apps.base_app import BaseAviatorApp
from config import config
from logger import AviatorLogger


class PredictionAgent(BaseAviatorApp):
    """
    ML Prediction Agent - trains models to predict game outcomes.
    
    Uses historical data from main_game_data.db to:
    - Train Random Forest and Gradient Boosting models
    - Predict if next round will be high (>2.0x) or low (<1.5x)
    - Analyze feature importance
    - Save trained models for future use
    """
    
    def __init__(self):
        super().__init__("PredictionAgent")
        self.db_path = config.paths.main_game_db
        
        # Models
        self.rf_model = None
        self.gb_model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        
        # Configuration
        self.lookback_window = 10
        self.model_path = config.paths.models_dir / "prediction_ensemble.pkl"
    
    def load_data(self, limit: int = 100000) -> pd.DataFrame:
        """Load training data from main_game_data.db."""
        self.logger.info(f"Loading data from {self.db_path}...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f"""
            SELECT 
                bookmaker,
                timestamp,
                final_score as score,
                total_players,
                total_money
            FROM rounds
            ORDER BY bookmaker, timestamp DESC
            LIMIT {limit}
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.logger.info(f"Loaded {len(df)} rounds")
            
            if len(df) == 0:
                raise ValueError("No data in database! Run main_data_collector first.")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}", exc_info=True)
            raise
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create ML features from raw data."""
        self.logger.info("Engineering features...")
        
        df = df.sort_values(['bookmaker', 'timestamp']).reset_index(drop=True)
        
        feature_df = pd.DataFrame()
        
        for bookmaker in df['bookmaker'].unique():
            bm_df = df[df['bookmaker'] == bookmaker].copy()
            
            # Historical scores (lag features)
            for i in range(1, self.lookback_window + 1):
                bm_df[f'score_lag_{i}'] = bm_df['score'].shift(i)
            
            # Rolling statistics (5 rounds)
            bm_df['score_mean_5'] = bm_df['score'].rolling(5, min_periods=1).mean()
            bm_df['score_std_5'] = bm_df['score'].rolling(5, min_periods=1).std()
            bm_df['score_min_5'] = bm_df['score'].rolling(5, min_periods=1).min()
            bm_df['score_max_5'] = bm_df['score'].rolling(5, min_periods=1).max()
            
            # Rolling statistics (10 rounds)
            bm_df['score_mean_10'] = bm_df['score'].rolling(10, min_periods=1).mean()
            bm_df['score_std_10'] = bm_df['score'].rolling(10, min_periods=1).std()
            
            # Trend features
            bm_df['score_diff_1'] = bm_df['score'].diff(1)
            bm_df['score_diff_2'] = bm_df['score'].diff(2)
            
            # Player behavior
            bm_df['players_mean_5'] = bm_df['total_players'].rolling(5, min_periods=1).mean()
            bm_df['players_std_5'] = bm_df['total_players'].rolling(5, min_periods=1).std()
            
            # Money patterns
            bm_df['money_mean_5'] = bm_df['total_money'].rolling(5, min_periods=1).mean()
            bm_df['money_std_5'] = bm_df['total_money'].rolling(5, min_periods=1).std()
            
            # Time features
            bm_df['timestamp'] = pd.to_datetime(bm_df['timestamp'])
            bm_df['hour'] = bm_df['timestamp'].dt.hour
            bm_df['day_of_week'] = bm_df['timestamp'].dt.dayofweek
            
            feature_df = pd.concat([feature_df, bm_df], ignore_index=True)
        
        # Fill NaN
        feature_df = feature_df.fillna(method='bfill').fillna(0)
        
        # Create targets
        feature_df['target_high'] = (feature_df['score'] >= 2.0).astype(int)
        feature_df['target_low'] = (feature_df['score'] < 1.5).astype(int)
        feature_df['target_very_high'] = (feature_df['score'] >= 5.0).astype(int)
        
        self.logger.info(f"Created {len(feature_df.columns)} features")
        
        return feature_df
    
    def prepare_training_data(
        self, 
        df: pd.DataFrame,
        target_col: str = 'target_high'
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare X, y for training."""
        exclude_cols = [
            'bookmaker', 'timestamp', 'score',
            'target_high', 'target_low', 'target_very_high'
        ]
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].values
        y = df[target_col].values
        
        self.logger.info(f"Training data: X={X.shape}, y={y.shape}")
        self.logger.info(f"Target distribution: {np.bincount(y)}")
        
        return X, y, feature_cols
    
    def train_models(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        """Train Random Forest and Gradient Boosting."""
        self.logger.info("Training models...")
        
        # Scale
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Random Forest
        self.logger.info("Training Random Forest...")
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        self.rf_model.fit(X_train_scaled, y_train)
        rf_score = self.rf_model.score(X_test_scaled, y_test)
        
        # Gradient Boosting
        self.logger.info("Training Gradient Boosting...")
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.gb_model.fit(X_train_scaled, y_train)
        gb_score = self.gb_model.score(X_test_scaled, y_test)
        
        # Predictions
        rf_pred = self.rf_model.predict(X_test_scaled)
        gb_pred = self.gb_model.predict(X_test_scaled)
        
        # Reports
        print("\n" + "="*60)
        print("RANDOM FOREST PERFORMANCE")
        print("="*60)
        print(classification_report(y_test, rf_pred))
        
        print("\n" + "="*60)
        print("GRADIENT BOOSTING PERFORMANCE")
        print("="*60)
        print(classification_report(y_test, gb_pred))
        
        return {
            'rf_accuracy': rf_score,
            'gb_accuracy': gb_score
        }
    
    def analyze_feature_importance(self) -> pd.DataFrame:
        """Show most important features."""
        if self.rf_model is None:
            raise ValueError("Model not trained!")
        
        importances = self.rf_model.feature_importances_
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        print("\n" + "="*60)
        print("TOP 15 MOST IMPORTANT FEATURES")
        print("="*60)
        for _, row in importance_df.head(15).iterrows():
            print(f"{row['feature']:30s} {row['importance']:.4f}")
        
        return importance_df
    
    def save_models(self):
        """Save trained models."""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            
            joblib.dump({
                'rf_model': self.rf_model,
                'gb_model': self.gb_model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, self.model_path)
            
            self.logger.info(f"✅ Models saved: {self.model_path}")
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    def load_models(self):
        """Load pre-trained models."""
        try:
            data = joblib.load(self.model_path)
            self.rf_model = data['rf_model']
            self.gb_model = data['gb_model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            
            self.logger.info(f"✅ Models loaded: {self.model_path}")
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """Make ensemble prediction."""
        if self.rf_model is None or self.gb_model is None:
            raise ValueError("Models not trained!")
        
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        rf_proba = self.rf_model.predict_proba(features_scaled)[0]
        gb_proba = self.gb_model.predict_proba(features_scaled)[0]
        
        ensemble_proba = (rf_proba + gb_proba) / 2
        
        return {
            'probability_high': ensemble_proba[1],
            'probability_low': ensemble_proba[0],
            'prediction': int(ensemble_proba[1] > 0.5)
        }
    
    def create_process(self, bookmaker, layout, position, coords, **kwargs):
        """Not used for prediction agent - training only."""
        return None
    
    def run(self):
        """Main training workflow."""
        print("\n" + "="*60)
        print("🤖 PREDICTION AGENT v1.0")
        print("="*60)
        print("\nTrains ML models to predict game outcomes")
        print("Uses data from main_game_data.db")
        print("="*60)
        
        # Check if database exists
        if not self.db_path.exists():
            print(f"\n❌ Database not found: {self.db_path}")
            print("   Run main_data_collector.py first to collect data!")
            return
        
        # Load data
        df = self.load_data(limit=50000)
        
        if len(df) < 100:
            print(f"\n⚠️  Only {len(df)} rounds in database")
            print("   Collect more data for better model training!")
            response = input("\nContinue anyway? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                return
        
        # Feature engineering
        df_features = self.engineer_features(df)
        
        # Prepare data
        X, y, feature_names = self.prepare_training_data(df_features)
        self.feature_names = feature_names
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train
        results = self.train_models(X_train, y_train, X_test, y_test)
        
        # Feature importance
        self.analyze_feature_importance()
        
        # Save
        self.save_models()
        
        print("\n" + "="*60)
        print("✅ TRAINING COMPLETED")
        print("="*60)
        print(f"Random Forest Accuracy: {results['rf_accuracy']:.4f}")
        print(f"Gradient Boosting Accuracy: {results['gb_accuracy']:.4f}")
        print(f"\nModels saved to: {self.model_path}")
        print("="*60)


if __name__ == "__main__":
    app = PredictionAgent()
    app.run()