"""
Statistical Predictions Model for MLB
=====================================
Core prediction engine using Poisson/Binary distributions
Based on proven NHL/NFL statistical_predictions_v2.py

NO ML until October 2025 - Pure statistical modeling for Year 1
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np
from scipy.stats import poisson

sys.path.insert(0, str(Path(__file__).parent.parent))

import mlb_config
from features.pitcher_strikeouts_extractor import (
    extract_pitcher_strikeouts_features,
    calculate_strikeouts_lambda
)
from features.batter_hits_extractor import (
    extract_batter_hits_features,
    calculate_hit_probability
)
from features.batter_total_bases_extractor import (
    extract_total_bases_features,
    calculate_total_bases_lambda
)


def predict_pitcher_strikeouts(
    pitcher_name: str,
    team: str,
    opponent: str,
    game_date: str,
    pitcher_hand: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict pitcher strikeouts using Poisson distribution

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_pitcher_strikeouts_features(
        pitcher_name, team, opponent, game_date, pitcher_hand, line, game_context
    )

    if not features:
        return None, None, None

    # Calculate lambda (expected strikeouts)
    lambda_k = calculate_strikeouts_lambda(features)

    # Calculate probability using Poisson
    prob_over = 1 - poisson.cdf(line, mu=lambda_k)

    # Apply probability cap (learning mode)
    if mlb_config.LEARNING_MODE:
        min_cap, max_cap = mlb_config.PROBABILITY_CAP
        prob_over = np.clip(prob_over, min_cap, max_cap)

    # Make prediction
    prediction = 'OVER' if prob_over >= 0.50 else 'UNDER'
    probability = prob_over if prediction == 'OVER' else (1 - prob_over)

    # Store model metadata
    features['model_type'] = 'poisson_distribution'
    features['lambda_strikeouts'] = lambda_k
    features['raw_probability'] = float(prob_over)
    features['capped_probability'] = float(probability)

    return prediction, probability, features


def predict_batter_hits(
    batter_name: str,
    team: str,
    opponent: str,
    game_date: str,
    batter_hand: str,
    opposing_pitcher_hand: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict batter hits using binary classification

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_batter_hits_features(
        batter_name, team, opponent, game_date, batter_hand, opposing_pitcher_hand, line, game_context
    )

    if not features:
        return None, None, None

    # Calculate hit probability
    prob_hit = calculate_hit_probability(features)

    # Apply probability cap (learning mode)
    if mlb_config.LEARNING_MODE:
        min_cap, max_cap = mlb_config.PROBABILITY_CAP
        prob_hit = np.clip(prob_hit, min_cap, max_cap)

    # Make prediction (usually line is 0.5 for yes/no)
    prediction = 'YES' if prob_hit >= 0.50 else 'NO'
    probability = prob_hit if prediction == 'YES' else (1 - prob_hit)

    # Store model metadata
    features['model_type'] = 'binary_classification'
    features['hit_probability'] = prob_hit
    features['raw_probability'] = float(prob_hit)
    features['capped_probability'] = float(probability)

    return prediction, probability, features


def predict_batter_total_bases(
    batter_name: str,
    team: str,
    opponent: str,
    game_date: str,
    batter_hand: str,
    opposing_pitcher_hand: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict batter total bases using Poisson distribution

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_total_bases_features(
        batter_name, team, opponent, game_date, batter_hand, opposing_pitcher_hand, line, game_context
    )

    if not features:
        return None, None, None

    # Calculate lambda (expected total bases)
    lambda_tb = calculate_total_bases_lambda(features)

    # Calculate probability using Poisson
    prob_over = 1 - poisson.cdf(line, mu=lambda_tb)

    # Apply probability cap (learning mode)
    if mlb_config.LEARNING_MODE:
        min_cap, max_cap = mlb_config.PROBABILITY_CAP
        prob_over = np.clip(prob_over, min_cap, max_cap)

    # Make prediction
    prediction = 'OVER' if prob_over >= 0.50 else 'UNDER'
    probability = prob_over if prediction == 'OVER' else (1 - prob_over)

    # Store model metadata
    features['model_type'] = 'poisson_distribution'
    features['lambda_total_bases'] = lambda_tb
    features['raw_probability'] = float(prob_over)
    features['capped_probability'] = float(probability)

    return prediction, probability, features


def generate_prediction(
    player_name: str,
    player_type: str,  # 'batter' or 'pitcher'
    team: str,
    opponent: str,
    game_date: str,
    prop_type: str,
    line: float,
    player_hand: str = None,
    opposing_hand: str = None,
    game_context: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Generate prediction for any prop type (router function)

    Returns:
        Complete prediction dictionary or None if error
    """
    # Route to appropriate prediction function
    if prop_type == 'pitcher_strikeouts':
        prediction, probability, features = predict_pitcher_strikeouts(
            player_name, team, opponent, game_date, player_hand, line, game_context
        )
    elif prop_type == 'batter_hits':
        prediction, probability, features = predict_batter_hits(
            player_name, team, opponent, game_date, player_hand, opposing_hand, line, game_context
        )
    elif prop_type == 'batter_total_bases':
        prediction, probability, features = predict_batter_total_bases(
            player_name, team, opponent, game_date, player_hand, opposing_hand, line, game_context
        )
    else:
        print(f"Unknown prop type: {prop_type}")
        return None

    if prediction is None or probability is None or features is None:
        return None

    # Build complete prediction object
    prediction_obj = {
        'prediction_batch_id': f"{game_date}",
        'game_date': game_date,
        'player_name': player_name,
        'player_type': player_type,
        'team': team,
        'opponent': opponent,
        'prop_type': prop_type,
        'line': line,
        'prediction': prediction,
        'probability': probability,
        'model_version': mlb_config.MODEL_VERSION,
        'confidence_tier': get_confidence_tier(probability),
        'features': features,
    }

    return prediction_obj


def get_confidence_tier(probability: float) -> str:
    """Classify prediction confidence"""
    if probability >= 0.60:
        return 'high'
    elif probability >= 0.50:
        return 'medium'
    else:
        return 'low'


def batch_generate_predictions(
    players: list,
    game_date: str,
    game_contexts: Optional[Dict] = None
) -> list:
    """
    Generate predictions for multiple players

    Args:
        players: List of player dictionaries with required fields
        game_date: Game date
        game_contexts: Dictionary of game contexts by team

    Returns:
        List of prediction dictionaries
    """
    predictions = []

    for player in players:
        # Get game context for this player's team
        game_context = None
        if game_contexts and player['team'] in game_contexts:
            game_context = game_contexts[player['team']]

        # Generate predictions for each prop
        for prop_config in player.get('props', []):
            prop_type = prop_config['prop_type']
            line = prop_config['line']

            # Check if prop type is enabled
            if prop_type not in mlb_config.PROP_TYPES:
                continue

            if not mlb_config.PROP_TYPES[prop_type].get('enabled', False):
                continue

            # Generate prediction
            prediction = generate_prediction(
                player_name=player['player_name'],
                player_type=player['player_type'],
                team=player['team'],
                opponent=player['opponent'],
                game_date=game_date,
                prop_type=prop_type,
                line=line,
                player_hand=player.get('player_hand'),
                opposing_hand=player.get('opposing_hand'),
                game_context=game_context
            )

            if prediction:
                predictions.append(prediction)

    return predictions


def get_model_stats() -> Dict:
    """Get model statistics and performance metrics"""
    return {
        'model_version': mlb_config.MODEL_VERSION,
        'model_type': mlb_config.MODEL_TYPE,
        'learning_mode': mlb_config.LEARNING_MODE,
        'probability_cap': mlb_config.PROBABILITY_CAP,
        'enabled_prop_types': [k for k, v in mlb_config.PROP_TYPES.items() if v.get('enabled', False)],
    }
