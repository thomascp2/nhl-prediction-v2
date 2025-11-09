"""
NBA Statistical Prediction Engine
==================================

Statistical models for data collection phase (Weeks 1-7).
Uses Poisson/Normal distributions with feature-based adjustments.

Binary Props (Poisson):
- Points, Rebounds, Assists, Threes, Stocks

Continuous Props (Normal):
- PRA, Minutes

Learning Mode: Caps probabilities at 30-70% during data collection.
"""

import sys
import os
from scipy.stats import poisson, norm
import math

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from nba_config import LEARNING_MODE, PROBABILITY_CAP
from features.binary_feature_extractor import BinaryFeatureExtractor
from features.continuous_feature_extractor import ContinuousFeatureExtractor


class NBAStatisticalPredictor:
    """Statistical prediction engine for NBA props."""

    def __init__(self, learning_mode=LEARNING_MODE):
        self.learning_mode = learning_mode
        self.prob_cap = PROBABILITY_CAP
        self.binary_extractor = BinaryFeatureExtractor()
        self.continuous_extractor = ContinuousFeatureExtractor()

    def predict_binary_prop(self, player_name, stat_type, line, game_date, home_away='H'):
        """
        Predict binary prop (Over/Under).

        Args:
            player_name (str): Player name
            stat_type (str): 'points', 'rebounds', 'assists', 'threes', 'stocks'
            line (float): Over/Under line (e.g., 15.5)
            game_date (str): Game date (YYYY-MM-DD)
            home_away (str): 'H' or 'A'

        Returns:
            dict: {
                'prediction': 'OVER' or 'UNDER',
                'probability': float (0.30-0.70 in learning mode),
                'features': dict
            }
        """
        # Extract features
        features = self.binary_extractor.extract_features(
            player_name, stat_type, line, game_date, home_away
        )

        # If insufficient data, return default
        if features['f_insufficient_data'] == 1 or features['f_games_played'] < 5:
            return {
                'prediction': 'UNDER',
                'probability': 0.50,
                'features': features,
                'method': 'insufficient_data'
            }

        # Base rate from season success rate
        base_prob = features['f_season_success_rate']

        # Adjustments based on other features
        adjustments = 0.0

        # Recent form (L5 vs season)
        if features['f_l5_success_rate'] > features['f_season_success_rate']:
            adjustments += 0.05
        elif features['f_l5_success_rate'] < features['f_season_success_rate']:
            adjustments -= 0.05

        # Streak momentum
        if features['f_current_streak'] > 3:
            adjustments += 0.03
        elif features['f_current_streak'] < -3:
            adjustments -= 0.03

        # Trend
        if features['f_trend_slope'] > 0.5:
            adjustments += 0.02
        elif features['f_trend_slope'] < -0.5:
            adjustments -= 0.02

        # Home/Away split
        adjustments += features['f_home_away_split'] * 0.1

        # Final probability
        probability = base_prob + adjustments
        probability = max(0.0, min(1.0, probability))  # Clip to [0, 1]

        # Apply learning mode cap
        if self.learning_mode:
            probability = self._apply_learning_cap(probability)

        # Determine prediction
        prediction = 'OVER' if probability > 0.5 else 'UNDER'

        return {
            'prediction': prediction,
            'probability': probability,
            'features': features,
            'method': 'statistical_binary'
        }

    def predict_continuous_prop(self, player_name, stat_type, line, game_date, home_away='H'):
        """
        Predict continuous prop (Over/Under based on normal distribution).

        Args:
            player_name (str): Player name
            stat_type (str): 'pra', 'minutes'
            line (float): Over/Under line (e.g., 30.5)
            game_date (str): Game date (YYYY-MM-DD)
            home_away (str): 'H' or 'A'

        Returns:
            dict: {
                'prediction': 'OVER' or 'UNDER',
                'probability': float (0.30-0.70 in learning mode),
                'features': dict,
                'expected_value': float
            }
        """
        # Extract features
        features = self.continuous_extractor.extract_features(
            player_name, stat_type, game_date, home_away
        )

        # If insufficient data, return default
        if features.get('f_games_played', 0) < 5:
            return {
                'prediction': 'UNDER',
                'probability': 0.50,
                'features': features,
                'expected_value': line,
                'method': 'insufficient_data'
            }

        # Base prediction from L10 average (more recent = more relevant)
        mu = features['f_l10_avg']
        sigma = features['f_l10_std'] if features['f_l10_std'] > 0 else features['f_season_std']

        # Adjustments based on trends
        trend_adjustment = features['f_trend_slope'] * 2
        mu += trend_adjustment

        # Home/Away adjustment
        mu += features['f_home_away_split']

        # If sigma is 0, use season std or default
        if sigma == 0:
            sigma = features['f_season_std'] if features['f_season_std'] > 0 else mu * 0.2

        # Calculate probability of OVER using normal distribution
        try:
            probability = 1 - norm.cdf(line, loc=mu, scale=sigma)
        except:
            probability = 0.50

        # Apply learning mode cap
        if self.learning_mode:
            probability = self._apply_learning_cap(probability)

        # Determine prediction
        prediction = 'OVER' if probability > 0.5 else 'UNDER'

        return {
            'prediction': prediction,
            'probability': probability,
            'features': features,
            'expected_value': mu,
            'method': 'statistical_continuous'
        }

    def predict_prop(self, player_name, stat_type, line, game_date, home_away='H'):
        """
        Unified prediction interface. Automatically determines binary vs continuous.

        Args:
            player_name (str): Player name
            stat_type (str): Prop type
            line (float): Over/Under line
            game_date (str): Game date (YYYY-MM-DD)
            home_away (str): 'H' or 'A'

        Returns:
            dict: Prediction results
        """
        continuous_stats = ['pra', 'minutes']

        if stat_type in continuous_stats:
            return self.predict_continuous_prop(
                player_name, stat_type, line, game_date, home_away
            )
        else:
            return self.predict_binary_prop(
                player_name, stat_type, line, game_date, home_away
            )

    def _apply_learning_cap(self, probability):
        """Apply learning mode probability cap (30-70%)."""
        min_prob, max_prob = self.prob_cap
        return max(min_prob, min(max_prob, probability))


# Example usage
if __name__ == "__main__":
    predictor = NBAStatisticalPredictor()

    # Test binary prediction
    print("🏀 NBA Statistical Prediction Engine Test\n")

    result = predictor.predict_prop(
        player_name="LeBron James",
        stat_type="points",
        line=25.5,
        game_date="2024-11-09",
        home_away='H'
    )

    print("Binary Prediction (Points O25.5):")
    print(f"  Prediction: {result['prediction']}")
    print(f"  Probability: {result['probability']:.2%}")
    print(f"  Method: {result['method']}")

    # Test continuous prediction
    result2 = predictor.predict_prop(
        player_name="LeBron James",
        stat_type="pra",
        line=35.5,
        game_date="2024-11-09",
        home_away='H'
    )

    print("\nContinuous Prediction (PRA O35.5):")
    print(f"  Prediction: {result2['prediction']}")
    print(f"  Probability: {result2['probability']:.2%}")
    print(f"  Expected Value: {result2.get('expected_value', 'N/A')}")
    print(f"  Method: {result2['method']}")
