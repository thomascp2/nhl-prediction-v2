"""
Statistical Prediction Engine V2 - FULLY FIXED VERSION

CRITICAL FIXES (2025-11-08):
1. Fixed method calls: extract() -> extract_features()
2. Fixed parameter names: as_of_date -> game_date  
3. Fixed feature name mappings to match actual extractor outputs
4. Fixed insufficient_data checks (0.0/1.0 instead of False/True)
5. **ADDED prediction_batch_id generation and saving (required by database)**

The prediction_batch_id is generated at engine initialization and groups all
predictions made in the same run. Format: YYYYMMDD_HHMMSS (e.g., 20251108_143022)

Original Changes:
1. predict_points() returns features dict
2. predict_shots() returns features dict  
3. _save_prediction() saves features as JSON
4. All features captured for ML training

Date: 2025-11-08 (FULLY FIXED)
Status: PRODUCTION READY
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import sys
import math

# Import feature extractors
sys.path.insert(0, '.')
from features.binary_feature_extractor import BinaryFeatureExtractor
from features.continuous_feature_extractor import ContinuousFeatureExtractor


class StatisticalPredictionEngine:
    """
    Statistical prediction engine using proper distributions
    
    Key differences from V1:
    - Points: Binary classification with Poisson distribution
    - Shots: Continuous prediction with Normal distribution
    - Learning mode: Conservative 30-70% probability cap
    - Feature storage: Saves all features as JSON for ML training
    """
    
    def __init__(self, db_path: str = 'database/nhl_predictions_v2.db', learning_mode: bool = True, batch_id: str = None):
        """Initialize prediction engine"""
        self.db_path = db_path
        self.learning_mode = learning_mode
        
        # Generate batch_id for this prediction run (required by database)
        if batch_id is None:
            self.batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        else:
            self.batch_id = batch_id
        
        # Initialize feature extractors
        self.binary_extractor = BinaryFeatureExtractor(db_path)
        self.continuous_extractor = ContinuousFeatureExtractor(db_path)
        
        # Learning mode caps probabilities at 30-70%
        self.min_prob = 0.30 if learning_mode else 0.10
        self.max_prob = 0.70 if learning_mode else 0.95
        
        # Database connection for saving predictions
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        print(f'INFO: Statistical Prediction Engine V2 Initialized')
        print(f'INFO: Batch ID: {self.batch_id}')
        print(f'INFO: Learning Mode: {learning_mode}')
        if learning_mode:
            print(f'INFO:   Probability Cap: {self.min_prob:.0%}-{self.max_prob:.0%} (conservative)')
    
    def __del__(self):
        """Clean up database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def predict_points(
        self, 
        player: str, 
        team: str, 
        game_date: str, 
        opponent: str, 
        is_home: bool
    ) -> Optional[Dict]:
        """
        Predict points O0.5 using binary classification
        
        Uses Poisson distribution based on recent performance
        
        Args:
            player: Player name
            team: Player's team abbreviation
            game_date: Game date (YYYY-MM-DD)
            opponent: Opponent team abbreviation
            is_home: True if home game
            
        Returns:
            Prediction dict with features, or None if insufficient data
        """
        # Temporal safety: Only use data from before game_date
        cutoff_date = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Extract binary features (FIXED: correct method name and parameter)
        features = self.binary_extractor.extract_features(
            player_name=player,
            team=team,
            game_date=cutoff_date,
            opponent=opponent,
            is_home=is_home
        )
        
        # Check if we have sufficient data
        if features.get('insufficient_data', 0.0) == 1.0:
            return None
        
        # Calculate probability using Poisson distribution
        # NOTE: Binary extractor doesn't return PPG, so we estimate from success rates
        success_rate_l5 = features.get('success_rate_l5', 0.425)
        success_rate_l10 = features.get('success_rate_l10', 0.425)
        
        # Estimate PPG from success rate (if 50% success rate, assume ~0.6 PPG)
        ppg_recent = success_rate_l5 * 1.2  # Rough conversion
        success_rate = success_rate_l10  # Historical success
        
        # Poisson parameter (lambda) = expected points
        lambda_param = ppg_recent
        
        # P(X > 0.5) = 1 - P(X = 0) = 1 - e^(-lambda)
        prob_over = 1 - math.exp(-lambda_param)
        
        # Adjust based on recent success rate
        prob_over = (prob_over * 0.7) + (success_rate * 0.3)
        
        # Apply learning mode caps
        prob_over = max(self.min_prob, min(self.max_prob, prob_over))
        
        # Determine prediction
        prediction = 'OVER' if prob_over > 0.5 else 'UNDER'
        
        # Assign confidence tier
        confidence = self._assign_confidence_tier(prob_over)
        
        # CRITICAL: Prepare features dict for ML training (using actual feature names)
        features_for_ml = {
            # Binary features (actual names from extractor)
            'success_rate_season': features.get('success_rate_season', 0.35),
            'success_rate_l20': features.get('success_rate_l20', 0.35),
            'success_rate_l10': features.get('success_rate_l10', 0.35),
            'success_rate_l5': features.get('success_rate_l5', 0.35),
            'success_rate_l3': features.get('success_rate_l3', 0.35),
            'current_streak': features.get('current_streak', 0),
            'max_hot_streak': features.get('max_hot_streak', 0),
            'recent_momentum': features.get('recent_momentum', 0.35),
            'games_played': features.get('games_played', 0),
            
            # Context features
            'is_home': int(is_home),
            
            # Calculated features
            'lambda_param': lambda_param,
            'poisson_prob': 1 - math.exp(-lambda_param),
        }
        
        # Build prediction dict
        prediction_data = {
            'game_date': game_date,
            'player_name': player,
            'team': team,
            'opponent': opponent,
            'prop_type': 'points',
            'line': 0.5,
            'prediction': prediction,
            'probability': prob_over,
            'confidence_tier': confidence,
            'model_version': 'statistical_v2',
            'prediction_batch_id': self.batch_id,  # ← REQUIRED by database
            'features': features_for_ml,  # ← CRITICAL: Features included
            'created_at': datetime.now().isoformat()
        }
        
        # Save to database
        self._save_prediction(prediction_data)
        
        return prediction_data
    
    def predict_shots(
        self,
        player: str,
        team: str,
        game_date: str,
        opponent: str,
        is_home: bool,
        line: float = 2.5
    ) -> Optional[Dict]:
        """
        Predict shots using continuous distribution
        
        Uses Normal distribution based on shot volume and consistency
        
        Args:
            player: Player name
            team: Player's team abbreviation
            game_date: Game date (YYYY-MM-DD)
            opponent: Opponent team abbreviation
            is_home: True if home game
            line: Shots line (default 2.5)
            
        Returns:
            Prediction dict with features, or None if insufficient data
        """
        # Temporal safety: Only use data from before game_date
        cutoff_date = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Extract continuous features (FIXED: correct method name and parameter)
        features = self.continuous_extractor.extract_features(
            player_name=player,
            team=team,
            game_date=cutoff_date,
            opponent=opponent,
            is_home=is_home
        )
        
        # Check if we have sufficient data
        if features.get('insufficient_data', 0.0) == 1.0:
            return None
        
        # Calculate probability using Normal distribution
        mean_shots = features.get('sog_l10', 2.5)  # Last 10 games average
        std_dev = features.get('sog_std_l10', 1.5)  # Standard deviation
        
        # P(X > line) using normal CDF
        # Z-score = (line - mean) / std_dev
        z_score = (line - mean_shots) / std_dev if std_dev > 0 else 0
        
        # P(X > line) = 1 - CDF(z_score)
        # Approximate CDF using error function
        prob_over = 0.5 * (1 - self._erf(z_score / math.sqrt(2)))
        
        # Apply learning mode caps
        prob_over = max(self.min_prob, min(self.max_prob, prob_over))
        
        # Determine prediction
        prediction = 'OVER' if prob_over > 0.5 else 'UNDER'
        
        # Assign confidence tier
        confidence = self._assign_confidence_tier(prob_over)
        
        # CRITICAL: Prepare features dict for ML training (using actual feature names)
        features_for_ml = {
            # Continuous features (actual names from extractor)
            'sog_season': features.get('sog_season', 2.5),
            'sog_l10': features.get('sog_l10', 2.5),
            'sog_l5': features.get('sog_l5', 2.5),
            'sog_std_season': features.get('sog_std_season', 1.2),
            'sog_std_l10': features.get('sog_std_l10', 1.2),
            'sog_trend': features.get('sog_trend', 0.0),
            'avg_toi_minutes': features.get('avg_toi_minutes', 15.0),
            'games_played': features.get('games_played', 0),
            
            # Context features
            'is_home': int(is_home),
            'line': line,
            
            # Calculated features
            'mean_shots': mean_shots,
            'std_dev': std_dev,
            'z_score': z_score,
        }
        
        # Build prediction dict
        prediction_data = {
            'game_date': game_date,
            'player_name': player,
            'team': team,
            'opponent': opponent,
            'prop_type': 'shots',
            'line': line,
            'prediction': prediction,
            'probability': prob_over,
            'confidence_tier': confidence,
            'model_version': 'statistical_v2',
            'prediction_batch_id': self.batch_id,  # ← REQUIRED by database
            'features': features_for_ml,  # ← CRITICAL: Features included
            'created_at': datetime.now().isoformat()
        }
        
        # Save to database
        self._save_prediction(prediction_data)
        
        return prediction_data
    
    def _assign_confidence_tier(self, probability: float) -> str:
        """
        Assign confidence tier based on probability
        
        Adjusts thresholds based on learning mode:
        - Learning mode (30-70% cap): Conservative tiers, no T1-ELITE
        - Production mode (10-95% range): Full tier range
        """
        if self.learning_mode:
            # LEARNING MODE TIERS (30-70% cap)
            # No T1-ELITE during learning - we're being conservative!
            if probability >= 0.65 or probability <= 0.35:
                return 'T2-STRONG'  # Best tier in learning mode
            elif probability >= 0.60 or probability <= 0.40:
                return 'T3-GOOD'
            elif probability >= 0.55 or probability <= 0.45:
                return 'T4-LEAN'
            else:
                return 'T5-FADE'  # 45-55% range (coin flips)
        else:
            # PRODUCTION MODE TIERS (10-95% range)
            # Full confidence after ML training
            if probability >= 0.75 or probability <= 0.25:
                return 'T1-ELITE'  # Truly confident (75%+ or 25%-)
            elif probability >= 0.65 or probability <= 0.35:
                return 'T2-STRONG'
            elif probability >= 0.60 or probability <= 0.40:
                return 'T3-GOOD'
            elif probability >= 0.55 or probability <= 0.45:
                return 'T4-LEAN'
            else:
                return 'T5-FADE'
    
    def _save_prediction(self, prediction_data: Dict):
        """
        Save prediction to database WITH FEATURES
        
        CRITICAL FIX: Now saves features_json for ML training
        
        Args:
            prediction_data: Prediction dict with features
        """
        try:
            # Extract features and convert to JSON
            features_dict = prediction_data.get('features', {})
            features_json = json.dumps(features_dict) if features_dict else None
            
            # Insert prediction with features
            self.cursor.execute("""
                INSERT INTO predictions (
                    game_date, player_name, team, opponent, 
                    prop_type, line, prediction, probability, 
                    confidence_tier, model_version, prediction_batch_id, 
                    features_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction_data['game_date'],
                prediction_data['player_name'],
                prediction_data['team'],
                prediction_data['opponent'],
                prediction_data['prop_type'],
                prediction_data['line'],
                prediction_data['prediction'],
                prediction_data['probability'],
                prediction_data['confidence_tier'],
                prediction_data['model_version'],
                prediction_data['prediction_batch_id'],  # ← REQUIRED by database
                features_json,  # ← CRITICAL: Features saved here
                prediction_data['created_at']
            ))
            
            self.conn.commit()
            
        except sqlite3.IntegrityError as e:
            # Duplicate prediction - skip silently
            print(f'WARNING: Failed to save prediction: {e}')
        except Exception as e:
            print(f'ERROR: Failed to save prediction: {e}')
    
    def _erf(self, x: float) -> float:
        """
        Approximation of error function for normal CDF
        
        Uses Abramowitz and Stegun approximation
        """
        # Constants
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911
        
        # Save the sign of x
        sign = 1 if x >= 0 else -1
        x = abs(x)
        
        # A&S formula
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return sign * y


# Test function
if __name__ == '__main__':
    print('Testing Statistical Prediction Engine V2 (PATCHED)')
    print()
    
    engine = StatisticalPredictionEngine(learning_mode=True)
    
    # Test points prediction
    print('Testing points prediction...')
    pred = engine.predict_points(
        player='Connor McDavid',
        team='EDM',
        game_date='2025-11-09',
        opponent='CGY',
        is_home=True
    )
    
    if pred:
        print(f'  Player: {pred["player_name"]}')
        print(f'  Prediction: {pred["prediction"]} ({pred["probability"]:.1%})')
        print(f'  Confidence: {pred["confidence_tier"]}')
        print(f'  Features stored: {len(pred["features"])} features')
        print(f'  Sample features: {list(pred["features"].keys())[:5]}')
    else:
        print('  Insufficient data')
    
    print()
    print('[OK] Test complete - check database for features_json!')
    print()
    print('Run this to verify:')
    print('  python check_feature_storage.py')
