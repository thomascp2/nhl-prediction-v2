"""
Validation Utilities for NFL Prediction System
=============================================
Ensures data quality and temporal safety
Based on proven NHL V2 methodology
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config


def validate_probability(probability: float) -> Tuple[bool, str]:
    """
    Validate probability is within acceptable range

    Args:
        probability: Predicted probability (0.0 to 1.0)

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(probability, (int, float)):
        return False, f"Probability must be numeric, got {type(probability)}"

    if probability < 0.0 or probability > 1.0:
        return False, f"Probability {probability} out of range [0.0, 1.0]"

    # Check learning mode caps
    if nfl_config.LEARNING_MODE:
        min_cap, max_cap = nfl_config.PROBABILITY_CAP
        if probability < min_cap or probability > max_cap:
            return False, f"Probability {probability} outside learning mode cap [{min_cap}, {max_cap}]"

    return True, ""


def validate_features(features: Dict) -> Tuple[bool, str]:
    """
    Validate features dictionary

    Args:
        features: Dictionary of extracted features

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(features, dict):
        return False, f"Features must be dictionary, got {type(features)}"

    if len(features) == 0:
        return False, "Features dictionary is empty"

    # Check for required feature categories
    required_categories = [
        'player_name',
        'prop_type',
        'game_date',
    ]

    for category in required_categories:
        if category not in features:
            return False, f"Missing required feature: {category}"

    # Check for None values in numeric features
    for key, value in features.items():
        if value is None and key not in ['injury_status', 'weather_precip', 'home_away']:
            # Some features can be None
            continue

        # Numeric features should not be None
        if isinstance(value, str) and key not in ['player_name', 'team', 'opponent', 'position',
                                                    'prop_type', 'game_date', 'home_away',
                                                    'weather_precip', 'injury_status']:
            try:
                float(value)
            except ValueError:
                return False, f"Feature '{key}' should be numeric but got '{value}'"

    return True, ""


def check_temporal_safety(features: Dict, game_date: str) -> Tuple[bool, str]:
    """
    CRITICAL: Ensure no future data leakage

    Args:
        features: Dictionary of extracted features
        game_date: Date of the game being predicted (YYYY-MM-DD)

    Returns:
        (is_valid, error_message)
    """
    if not nfl_config.ENABLE_TEMPORAL_SAFETY_CHECK:
        return True, ""

    try:
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')

        # Check if any feature references data from after game_date
        suspicious_keys = ['future_', 'next_', 'upcoming_']
        for key in features.keys():
            for suspicious in suspicious_keys:
                if suspicious in key.lower():
                    return False, f"Feature '{key}' may contain future data (game: {game_date})"

        # Check if feature extraction date is reasonable
        if 'feature_extraction_date' in features:
            extraction_dt = datetime.strptime(features['feature_extraction_date'], '%Y-%m-%d')
            if extraction_dt > game_dt:
                return False, f"Features extracted AFTER game date ({extraction_dt} > {game_dt})"

        return True, ""

    except Exception as e:
        return False, f"Temporal safety check error: {e}"


def validate_prediction(prediction: Dict) -> Tuple[bool, List[str]]:
    """
    Comprehensive validation of prediction before saving

    Args:
        prediction: Complete prediction dictionary

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    required_fields = [
        'prediction_batch_id',
        'game_date',
        'week_number',
        'player_name',
        'team',
        'opponent',
        'position',
        'prop_type',
        'line',
        'prediction',
        'probability',
    ]

    for field in required_fields:
        if field not in prediction:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Validate probability
    is_valid, error = validate_probability(prediction['probability'])
    if not is_valid:
        errors.append(error)

    # Validate prediction is OVER or UNDER
    if prediction['prediction'] not in ['OVER', 'UNDER', 'YES', 'NO']:
        errors.append(f"Invalid prediction value: {prediction['prediction']}")

    # Validate week number
    if not (1 <= prediction['week_number'] <= 22):
        errors.append(f"Invalid week number: {prediction['week_number']} (must be 1-22)")

    # Validate position
    if prediction['position'] not in nfl_config.POSITIONS:
        errors.append(f"Invalid position: {prediction['position']}")

    # Validate prop type
    if prediction['prop_type'] not in nfl_config.PROP_TYPES:
        errors.append(f"Invalid prop type: {prediction['prop_type']}")

    # Validate line
    if not isinstance(prediction['line'], (int, float)) or prediction['line'] < 0:
        errors.append(f"Invalid line: {prediction['line']}")

    # Validate features if present
    if 'features' in prediction:
        is_valid, error = validate_features(prediction['features'])
        if not is_valid:
            errors.append(error)

        # Check temporal safety
        is_valid, error = check_temporal_safety(prediction['features'], prediction['game_date'])
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def validate_game_log(game_log: Dict) -> Tuple[bool, List[str]]:
    """
    Validate player game log before saving

    Args:
        game_log: Player game statistics

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    required_fields = [
        'game_date',
        'week_number',
        'player_name',
        'team',
        'opponent',
        'position',
    ]

    for field in required_fields:
        if field not in game_log:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Validate week number
    if not (1 <= game_log['week_number'] <= 22):
        errors.append(f"Invalid week number: {game_log['week_number']}")

    # Validate position
    if game_log['position'] not in nfl_config.POSITIONS:
        errors.append(f"Invalid position: {game_log['position']}")

    # Validate stats are non-negative
    stat_fields = [
        'pass_yards', 'pass_tds', 'rush_yards', 'rush_tds',
        'targets', 'receptions', 'rec_yards', 'rec_tds',
        'snap_count',
    ]

    for field in stat_fields:
        if field in game_log and game_log[field] is not None:
            if game_log[field] < 0:
                errors.append(f"Negative value for {field}: {game_log[field]}")

    # Validate percentages
    pct_fields = ['snap_pct', 'target_share', 'air_yards_share']
    for field in pct_fields:
        if field in game_log and game_log[field] is not None:
            if not (0.0 <= game_log[field] <= 1.0):
                errors.append(f"Invalid percentage for {field}: {game_log[field]} (must be 0.0-1.0)")

    return len(errors) == 0, errors


def validate_player_selection(player_stats: Dict) -> Tuple[bool, str]:
    """
    Validate if player meets selection criteria for predictions

    Args:
        player_stats: Player statistics

    Returns:
        (is_valid, reason_if_invalid)
    """
    # Check games played
    if player_stats.get('games_played', 0) < nfl_config.MIN_GAMES_PLAYED:
        return False, f"Insufficient games played ({player_stats.get('games_played', 0)} < {nfl_config.MIN_GAMES_PLAYED})"

    # Check snap count percentage
    if player_stats.get('snap_pct', 0) < nfl_config.MIN_SNAP_COUNT_PCT:
        return False, f"Insufficient snap count ({player_stats.get('snap_pct', 0):.2%} < {nfl_config.MIN_SNAP_COUNT_PCT:.2%})"

    # Check target share for receivers
    position = player_stats.get('position')
    if position in ['WR', 'TE']:
        if player_stats.get('target_share', 0) < nfl_config.MIN_TARGET_SHARE:
            return False, f"Insufficient target share ({player_stats.get('target_share', 0):.2%} < {nfl_config.MIN_TARGET_SHARE:.2%})"

    # Check injury status
    injury_status = player_stats.get('injury_status', 'healthy')
    if injury_status in nfl_config.EXCLUDE_INJURY_STATUS:
        return False, f"Player injury status: {injury_status}"

    return True, ""


def validate_prop_for_player(player_stats: Dict, prop_type: str) -> Tuple[bool, str]:
    """
    Validate if prop type is appropriate for player

    Args:
        player_stats: Player statistics
        prop_type: Prop type to validate

    Returns:
        (is_valid, reason_if_invalid)
    """
    if prop_type not in nfl_config.PROP_TYPES:
        return False, f"Unknown prop type: {prop_type}"

    prop_config = nfl_config.PROP_TYPES[prop_type]

    # Check if prop is enabled
    if not prop_config.get('enabled', False):
        return False, f"Prop type {prop_type} is not enabled"

    # Check position eligibility
    position = player_stats.get('position')
    if position not in prop_config.get('positions', []):
        return False, f"Position {position} not eligible for {prop_type}"

    # Check minimum thresholds
    if prop_type == 'rec_yards':
        if player_stats.get('rec_yards_per_game', 0) < prop_config.get('min_yards_per_game', 0):
            return False, f"Below minimum rec yards/game threshold"

    elif prop_type == 'receptions':
        if player_stats.get('rec_per_game', 0) < prop_config.get('min_rec_per_game', 0):
            return False, f"Below minimum receptions/game threshold"

    elif prop_type == 'rush_yards':
        if player_stats.get('rush_yards_per_game', 0) < prop_config.get('min_yards_per_game', 0):
            return False, f"Below minimum rush yards/game threshold"

    elif prop_type == 'pass_yards':
        if player_stats.get('pass_yards_per_game', 0) < prop_config.get('min_yards_per_game', 0):
            return False, f"Below minimum pass yards/game threshold"

    return True, ""


def validate_weather_data(weather: Dict) -> Tuple[bool, str]:
    """
    Validate weather data

    Args:
        weather: Weather dictionary

    Returns:
        (is_valid, error_message)
    """
    # Temperature should be reasonable (-20 to 120 F)
    if 'temp' in weather and weather['temp'] is not None:
        if not (-20 <= weather['temp'] <= 120):
            return False, f"Unreasonable temperature: {weather['temp']}F"

    # Wind should be reasonable (0 to 60 MPH)
    if 'wind' in weather and weather['wind'] is not None:
        if not (0 <= weather['wind'] <= 60):
            return False, f"Unreasonable wind speed: {weather['wind']} MPH"

    # Precipitation should be valid
    if 'precip' in weather and weather['precip'] is not None:
        valid_precip = ['clear', 'rain', 'snow', 'mixed']
        if weather['precip'] not in valid_precip:
            return False, f"Invalid precipitation type: {weather['precip']}"

    return True, ""


def get_validation_summary(predictions: List[Dict]) -> Dict:
    """
    Get validation summary for a batch of predictions

    Args:
        predictions: List of predictions

    Returns:
        Summary dictionary
    """
    summary = {
        'total': len(predictions),
        'valid': 0,
        'invalid': 0,
        'errors': []
    }

    for prediction in predictions:
        is_valid, errors = validate_prediction(prediction)
        if is_valid:
            summary['valid'] += 1
        else:
            summary['invalid'] += 1
            summary['errors'].extend(errors)

    return summary
