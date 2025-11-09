"""
Statistical Predictions Model
=============================
Core prediction engine using Poisson/Normal distributions
Based on proven NHL statistical_predictions_v2.py methodology

NO ML until August 2025 - Pure statistical modeling for Year 1
"""

import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np
from scipy.stats import norm, poisson

sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from features.receiving_yards_extractor import (
    extract_receiving_yards_features,
    calculate_rec_yards_baseline,
    get_standard_deviation as get_rec_yards_std
)
from features.receptions_extractor import (
    extract_receptions_features,
    calculate_receptions_lambda
)
from features.rushing_yards_extractor import (
    extract_rushing_yards_features,
    calculate_rush_yards_baseline,
    get_standard_deviation as get_rush_yards_std
)


def predict_receiving_yards(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict receiving yards prop using Normal distribution

    Args:
        player_name: Player's name
        team: Player's team
        opponent: Opponent team
        game_date: Game date (YYYY-MM-DD)
        week_number: Week number (1-22)
        position: Player position (WR, TE)
        line: Prop line (e.g., 59.5 yards)
        game_context: Optional game context (Vegas lines, weather, etc.)

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_receiving_yards_features(
        player_name, team, opponent, game_date, week_number, position, line, game_context
    )

    if not features:
        print(f"Failed to extract features for {player_name}")
        return None, None, None

    # Calculate baseline (adjusted mean)
    baseline_yards = calculate_rec_yards_baseline(features)

    # Get standard deviation
    std_yards = get_rec_yards_std(features)

    # Calculate probability using Normal distribution
    prob_over = 1 - norm.cdf(line, loc=baseline_yards, scale=std_yards)

    # Apply probability cap (learning mode)
    if nfl_config.LEARNING_MODE:
        min_cap, max_cap = nfl_config.PROBABILITY_CAP
        prob_over = np.clip(prob_over, min_cap, max_cap)

    # Make prediction
    prediction = 'OVER' if prob_over >= 0.50 else 'UNDER'
    probability = prob_over if prediction == 'OVER' else (1 - prob_over)

    # Store model metadata in features
    features['model_type'] = 'normal_distribution'
    features['baseline_yards'] = baseline_yards
    features['std_yards'] = std_yards
    features['raw_probability'] = float(prob_over)  # Before capping
    features['capped_probability'] = float(probability)  # After capping

    return prediction, probability, features


def predict_receptions(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict receptions prop using Poisson distribution

    Args:
        Similar to predict_receiving_yards

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_receptions_features(
        player_name, team, opponent, game_date, week_number, position, line, game_context
    )

    if not features:
        print(f"Failed to extract features for {player_name}")
        return None, None, None

    # Calculate lambda (expected receptions)
    lambda_receptions = calculate_receptions_lambda(features)

    # Calculate probability using Poisson distribution
    # P(X > line) = 1 - P(X <= line) = 1 - CDF(line)
    prob_over = 1 - poisson.cdf(line, mu=lambda_receptions)

    # Apply probability cap (learning mode)
    if nfl_config.LEARNING_MODE:
        min_cap, max_cap = nfl_config.PROBABILITY_CAP
        prob_over = np.clip(prob_over, min_cap, max_cap)

    # Make prediction
    prediction = 'OVER' if prob_over >= 0.50 else 'UNDER'
    probability = prob_over if prediction == 'OVER' else (1 - prob_over)

    # Store model metadata in features
    features['model_type'] = 'poisson_distribution'
    features['lambda_receptions'] = lambda_receptions
    features['raw_probability'] = float(prob_over)
    features['capped_probability'] = float(probability)

    return prediction, probability, features


def predict_rushing_yards(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
    """
    Predict rushing yards prop using Normal distribution

    Args:
        Similar to predict_receiving_yards

    Returns:
        (prediction, probability, features) or (None, None, None) if error
    """
    # Extract features
    features = extract_rushing_yards_features(
        player_name, team, opponent, game_date, week_number, position, line, game_context
    )

    if not features:
        print(f"Failed to extract features for {player_name}")
        return None, None, None

    # Calculate baseline (adjusted mean)
    baseline_yards = calculate_rush_yards_baseline(features)

    # Get standard deviation
    std_yards = get_rush_yards_std(features)

    # Calculate probability using Normal distribution
    prob_over = 1 - norm.cdf(line, loc=baseline_yards, scale=std_yards)

    # Apply probability cap (learning mode)
    if nfl_config.LEARNING_MODE:
        min_cap, max_cap = nfl_config.PROBABILITY_CAP
        prob_over = np.clip(prob_over, min_cap, max_cap)

    # Make prediction
    prediction = 'OVER' if prob_over >= 0.50 else 'UNDER'
    probability = prob_over if prediction == 'OVER' else (1 - prob_over)

    # Store model metadata in features
    features['model_type'] = 'normal_distribution'
    features['baseline_yards'] = baseline_yards
    features['std_yards'] = std_yards
    features['raw_probability'] = float(prob_over)
    features['capped_probability'] = float(probability)

    return prediction, probability, features


def generate_prediction(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    prop_type: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Generate prediction for any prop type (router function)

    Args:
        player_name: Player's name
        team: Player's team
        opponent: Opponent team
        game_date: Game date (YYYY-MM-DD)
        week_number: Week number (1-22)
        position: Player position
        prop_type: Type of prop ('rec_yards', 'receptions', 'rush_yards')
        line: Prop line
        game_context: Optional game context

    Returns:
        Complete prediction dictionary or None if error
    """
    # Route to appropriate prediction function
    if prop_type == 'rec_yards':
        prediction, probability, features = predict_receiving_yards(
            player_name, team, opponent, game_date, week_number, position, line, game_context
        )
    elif prop_type == 'receptions':
        prediction, probability, features = predict_receptions(
            player_name, team, opponent, game_date, week_number, position, line, game_context
        )
    elif prop_type == 'rush_yards':
        prediction, probability, features = predict_rushing_yards(
            player_name, team, opponent, game_date, week_number, position, line, game_context
        )
    else:
        print(f"Unknown prop type: {prop_type}")
        return None

    if prediction is None or probability is None or features is None:
        return None

    # Build complete prediction object
    prediction_obj = {
        'prediction_batch_id': f"{game_date}_{week_number}",
        'game_date': game_date,
        'week_number': week_number,
        'player_name': player_name,
        'team': team,
        'opponent': opponent,
        'position': position,
        'prop_type': prop_type,
        'line': line,
        'prediction': prediction,
        'probability': probability,
        'model_version': nfl_config.MODEL_VERSION,
        'confidence_tier': get_confidence_tier(probability),
        'features': features,
    }

    return prediction_obj


def get_confidence_tier(probability: float) -> str:
    """
    Classify prediction confidence

    Args:
        probability: Predicted probability

    Returns:
        Confidence tier string
    """
    if probability >= 0.65:
        return 'high'
    elif probability >= 0.55:
        return 'medium'
    else:
        return 'low'


def calculate_expected_value(line: float, prob_over: float, odds_over: int, odds_under: int) -> Dict:
    """
    Calculate expected value for betting (optional)

    Args:
        line: Prop line
        prob_over: Probability of going over
        odds_over: American odds for over
        odds_under: American odds for under

    Returns:
        EV dictionary
    """
    # Convert American odds to decimal
    if odds_over > 0:
        decimal_over = 1 + (odds_over / 100)
    else:
        decimal_over = 1 + (100 / abs(odds_over))

    if odds_under > 0:
        decimal_under = 1 + (odds_under / 100)
    else:
        decimal_under = 1 + (100 / abs(odds_under))

    # Calculate EV
    prob_under = 1 - prob_over

    ev_over = (prob_over * decimal_over) - 1
    ev_under = (prob_under * decimal_under) - 1

    return {
        'ev_over': ev_over,
        'ev_under': ev_under,
        'best_bet': 'OVER' if ev_over > ev_under else 'UNDER',
        'best_ev': max(ev_over, ev_under)
    }


def batch_generate_predictions(
    players: list,
    game_date: str,
    week_number: int,
    game_contexts: Optional[Dict] = None
) -> list:
    """
    Generate predictions for multiple players

    Args:
        players: List of player dictionaries with required fields
        game_date: Game date
        week_number: Week number
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

        # Generate predictions for each enabled prop type
        for prop_config in player.get('props', []):
            prop_type = prop_config['prop_type']
            line = prop_config['line']

            # Check if prop type is enabled
            if prop_type not in nfl_config.PROP_TYPES:
                continue

            if not nfl_config.PROP_TYPES[prop_type].get('enabled', False):
                continue

            # Generate prediction
            prediction = generate_prediction(
                player_name=player['player_name'],
                team=player['team'],
                opponent=player['opponent'],
                game_date=game_date,
                week_number=week_number,
                position=player['position'],
                prop_type=prop_type,
                line=line,
                game_context=game_context
            )

            if prediction:
                predictions.append(prediction)

    return predictions


# =============================================================================
# MODEL DIAGNOSTICS (For monitoring)
# =============================================================================

def get_model_stats() -> Dict:
    """Get model statistics and performance metrics"""
    return {
        'model_version': nfl_config.MODEL_VERSION,
        'model_type': nfl_config.MODEL_TYPE,
        'learning_mode': nfl_config.LEARNING_MODE,
        'probability_cap': nfl_config.PROBABILITY_CAP,
        'enabled_prop_types': [k for k, v in nfl_config.PROP_TYPES.items() if v.get('enabled', False)],
    }


def validate_model_output(prediction: Dict) -> bool:
    """Validate model prediction output"""
    required_fields = [
        'prediction', 'probability', 'features', 'player_name',
        'team', 'opponent', 'prop_type', 'line', 'week_number'
    ]

    for field in required_fields:
        if field not in prediction:
            print(f"Missing required field: {field}")
            return False

    # Validate probability
    if not (0.0 <= prediction['probability'] <= 1.0):
        print(f"Invalid probability: {prediction['probability']}")
        return False

    # Validate prediction is OVER or UNDER
    if prediction['prediction'] not in ['OVER', 'UNDER']:
        print(f"Invalid prediction: {prediction['prediction']}")
        return False

    return True
