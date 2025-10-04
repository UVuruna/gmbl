# prediction_analyzer.py
# VERSION: 3.0 - IMPROVED PREDICTION SYSTEM
# CHANGES: Multi-feature analysis, better model training, performance metrics

import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from typing import Dict, List, Tuple, Optional
from root.logger import AviatorLogger


class PredictionAnalyzer:
    """
    Advanced prediction system using multiple features.
    
    FEATURES (instead of just RGB):
    1. Historical game scores (last 5-10 rounds)
    2. Time patterns (time of day, day of week)
    3. Player behavior (total players, betting patterns)
    4. Statistical features (mean, std, trends)
    5. RGB values (as supplementary data)
    
    MODELS:
    - Random Forest (primary)
    - Gradient Boosting (secondary)
    - Ensemble voting
    """
    
    def __init__(self, db_path: str = 'aviator.db'):
        self.db_path = db_path
        self.logger = AviatorLogger.get_logger("PredictionAnalyzer")
        
        # Models
        self.rf_model = None
        self.gb_model = None
        self.scaler = StandardScaler()
        
        # Feature configuration
        self.lookback_window = 10  # Last 10 rounds for features
        self.feature_names = []
    
    def load_data(self, limit: int = 100000) -> pd.DataFrame:
        """
        Load data from database with enhanced features.
        
        Args:
            limit: Maximum number of records to load
            
        Returns:
            DataFrame with features and target
        """
        self.logger.info(f"Loading data from {self.db_path}...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load main rounds data
            query = f"""
            SELECT 
                r.round_ID,
                r.bookmaker,
                r.score,
                r.total_win,
                r.total_players,
                r.timestamp,
                e.bet_amount,
                e.auto_stop,
                e.balance
            FROM rounds r
            LEFT JOIN earnings e ON r.round_ID = e.round_ID
            ORDER BY r.timestamp DESC
            LIMIT {limit}
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.logger.info(f"Loaded {len(df)} rounds")
            
            if len(df) == 0:
                raise ValueError("No data in database!")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}", exc_info=True)
            raise
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create advanced features from raw data.
        
        FEATURES CREATED:
        - Historical scores (last N rounds)
        - Score statistics (mean, std, min, max)
        - Trends (increasing/decreasing)
        - Time-based features
        - Player behavior patterns
        """
        self.logger.info("Engineering features...")
        
        # Sort by bookmaker and timestamp
        df = df.sort_values(['bookmaker', 'timestamp']).reset_index(drop=True)
        
        # Group by bookmaker for historical features
        feature_df = pd.DataFrame()
        
        for bookmaker in df['bookmaker'].unique():
            bm_df = df[df['bookmaker'] == bookmaker].copy()
            
            # Historical scores (last N rounds)
            for i in range(1, self.lookback_window + 1):
                bm_df[f'score_lag_{i}'] = bm_df['score'].shift(i)
            
            # Rolling statistics
            bm_df['score_mean_5'] = bm_df['score'].rolling(window=5, min_periods=1).mean()
            bm_df['score_std_5'] = bm_df['score'].rolling(window=5, min_periods=1).std()
            bm_df['score_min_5'] = bm_df['score'].rolling(window=5, min_periods=1).min()
            bm_df['score_max_5'] = bm_df['score'].rolling(window=5, min_periods=1).max()
            
            bm_df['score_mean_10'] = bm_df['score'].rolling(window=10, min_periods=1).mean()
            bm_df['score_std_10'] = bm_df['score'].rolling(window=10, min_periods=1).std()
            
            # Trend features
            bm_df['score_diff_1'] = bm_df['score'].diff(1)
            bm_df['score_diff_2'] = bm_df['score'].diff(2)
            
            # Player behavior
            bm_df['players_mean_5'] = bm_df['total_players'].rolling(window=5, min_periods=1).mean()
            bm_df['players_std_5'] = bm_df['total_players'].rolling(window=5, min_periods=1).std()
            
            # Win patterns
            bm_df['win_mean_5'] = bm_df['total_win'].rolling(window=5, min_periods=1).mean()
            
            # Time features (if timestamp is datetime)
            if pd.api.types.is_datetime64_any_dtype(bm_df['timestamp']):
                bm_df['hour'] = pd.to_datetime(bm_df['timestamp']).dt.hour
                bm_df['day_of_week'] = pd.to_datetime(bm_df['timestamp']).dt.dayofweek
            
            feature_df = pd.concat([feature_df, bm_df], ignore_index=True)
        
        # Fill NaN values
        feature_df = feature_df.fillna(feature_df.mean(numeric_only=True))
        
        # Create target variable (binary: crash above 2.0x or not)
        feature_df['target_high'] = (feature_df['score'] >= 2.0).astype(int)
        feature_df['target_low'] = (feature_df['score'] < 1.5).astype(int)
        
        self.logger.info(f"Created {len(feature_df.columns)} features")
        
        return feature_df
    
    def prepare_training_data(
        self, 
        df: pd.DataFrame,
        target_col: str = 'target_high'
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare data for training.
        
        Args:
            df: DataFrame with features
            target_col: Target column name
            
        Returns:
            Tuple of (X, y, feature_names)
        """
        # Select feature columns (exclude metadata and target)
        exclude_cols = [
            'round_ID', 'bookmaker', 'timestamp', 'score',
            'target_high', 'target_low', 'balance'
        ]
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].values
        y = df[target_col].values
        
        self.logger.info(f"Training data shape: X={X.shape}, y={y.shape}")
        self.logger.info(f"Target distribution: {np.bincount(y)}")
        
        return X, y, feature_cols
    
    def train_models(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Train multiple models and evaluate.
        
        Returns:
            Dict with performance metrics
        """
        self.logger.info("Training models...")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Random Forest
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
        
        # Train Gradient Boosting
        self.logger.info("Training Gradient Boosting...")
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.gb_model.fit(X_train_scaled, y_train)
        gb_score = self.gb_model.score(X_test_scaled, y_test)
        
        # Evaluate
        rf_pred = self.rf_model.predict(X_test_scaled)
        gb_pred = self.gb_model.predict(X_test_scaled)
        
        self.logger.info("=" * 60)
        self.logger.info("RANDOM FOREST PERFORMANCE")
        self.logger.info("=" * 60)
        self.logger.info(f"\n{classification_report(y_test, rf_pred)}")
        
        self.logger.info("=" * 60)
        self.logger.info("GRADIENT BOOSTING PERFORMANCE")
        self.logger.info("=" * 60)
        self.logger.info(f"\n{classification_report(y_test, gb_pred)}")
        
        return {
            'rf_accuracy': rf_score,
            'gb_accuracy': gb_score,
            'rf_predictions': rf_pred,
            'gb_predictions': gb_pred
        }
    
    def save_models(self, model_path: str = 'prediction_models.pkl'):
        """Save trained models to file."""
        try:
            joblib.dump({
                'rf_model': self.rf_model,
                'gb_model': self.gb_model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, model_path)
            
            self.logger.info(f"✅ Models saved to {model_path}")
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")
    
    def load_models(self, model_path: str = 'prediction_models.pkl'):
        """Load trained models from file."""
        try:
            data = joblib.load(model_path)
            self.rf_model = data['rf_model']
            self.gb_model = data['gb_model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            
            self.logger.info(f"✅ Models loaded from {model_path}")
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """
        Make prediction using ensemble of models.
        
        Args:
            features: Feature array (must match training features)
            
        Returns:
            Dict with prediction probabilities
        """
        if self.rf_model is None or self.gb_model is None:
            raise ValueError("Models not trained! Call train_models() first.")
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Get predictions from both models
        rf_proba = self.rf_model.predict_proba(features_scaled)[0]
        gb_proba = self.gb_model.predict_proba(features_scaled)[0]
        
        # Ensemble: average probabilities
        ensemble_proba = (rf_proba + gb_proba) / 2
        
        return {
            'probability_high': ensemble_proba[1],
            'probability_low': ensemble_proba[0],
            'prediction': int(ensemble_proba[1] > 0.5),
            'rf_prob': rf_proba[1],
            'gb_prob': gb_proba[1]
        }
    
    def analyze_feature_importance(self, feature_names: List[str]) -> pd.DataFrame:
        """
        Analyze and return feature importances.
        
        Returns:
            DataFrame with feature importances
        """
        if self.rf_model is None:
            raise ValueError("Model not trained!")
        
        importances = self.rf_model.feature_importances_
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        self.logger.info("=" * 60)
        self.logger.info("TOP 10 MOST IMPORTANT FEATURES")
        self.logger.info("=" * 60)
        for idx, row in importance_df.head(10).iterrows():
            self.logger.info(f"{row['feature']:30s} {row['importance']:.4f}")
        
        return importance_df


def main():
    """Train and evaluate prediction models."""
    from root.logger import init_logging
    
    init_logging()
    logger = AviatorLogger.get_logger("Main")
    
    logger.info("=" * 60)
    logger.info("AVIATOR PREDICTION SYSTEM - TRAINING")
    logger.info("=" * 60)
    
    try:
        # Initialize analyzer
        analyzer = PredictionAnalyzer()
        
        # Load data
        df = analyzer.load_data(limit=50000)
        
        # Engineer features
        df_features = analyzer.engineer_features(df)
        
        # Prepare training data
        X, y, feature_names = analyzer.prepare_training_data(df_features)
        analyzer.feature_names = feature_names
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train models
        results = analyzer.train_models(X_train, y_train, X_test, y_test)
        
        # Analyze feature importance
        importance_df = analyzer.analyze_feature_importance(feature_names)
        
        # Save models
        analyzer.save_models()
        
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Random Forest Accuracy: {results['rf_accuracy']:.4f}")
        logger.info(f"Gradient Boosting Accuracy: {results['gb_accuracy']:.4f}")
        
    except Exception as e:
        logger.critical(f"Training failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
