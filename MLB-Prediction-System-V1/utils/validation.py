"""
Validation Utilities for MLB Prediction System
=============================================
Ensures data quality and temporal safety
Based on proven NHL/NFL V2 methodology
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
import mlb_config


def validate_probability(probability: float) -> Tuple[bool, str]:
    """Validate probability is within acceptable range"""
    if not isinstance(probability, (int, float)):
        return False, f"Probability must be numeric, got {type(probability)}"

    if probability < 0.0 or probability > 1.0:
        return False, f"Probability {probability} out of range [0.0, 1.0]"

    if mlb_config.LEARNING_MODE:
        min_cap, max_cap = mlb_config.PROBABILITY_CAP
        if probability < min_cap or probability > max_cap:
            return False, f"Probability {probability} outside learning mode cap [{min_cap}, {max_cap}]"

    return True, ""


def validate_features(features: Dict) -> Tuple[bool, str]:
    """Validate features dictionary"""
    if not isinstance(features, dict):
        return False, f"Features must be dictionary, got {type(features)}"

    if len(features) == 0:
        return False, "Features dictionary is empty"

    required_categories = ['player_name', 'player_type', 'prop_type', 'game_date']
    for category in required_categories:
        if category not in features:
            return False, f"Missing required feature: {category}"

    return True, ""


def check_temporal_safety(features: Dict, game_date: str) -> Tuple[bool, str]:
    """CRITICAL: Ensure no future data leakage"""
    if not mlb_config.ENABLE_TEMPORAL_SAFETY_CHECK:
        return True, ""

    try:
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')

        suspicious_keys = ['future_', 'next_', 'upcoming_']
        for key in features.keys():
            for suspicious in suspicious_keys:
                if suspicious in key.lower():
                    return False, f"Feature '{key}' may contain future data"

        if 'feature_extraction_date' in features:
            extraction_dt = datetime.strptime(features['feature_extraction_date'], '%Y-%m-%d')
            if extraction_dt > game_dt:
                return False, f"Features extracted AFTER game date"

        return True, ""

    except Exception as e:
        return False, f"Temporal safety check error: {e}"


def validate_prediction(prediction: Dict) -> Tuple[bool, List[str]]:
    """Comprehensive validation of prediction before saving"""
    errors = []

    required_fields = [
        'prediction_batch_id', 'game_date', 'player_name', 'player_type',
        'team', 'opponent', 'prop_type', 'line', 'prediction', 'probability'
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

    # Validate prediction
    if prediction['prediction'] not in ['OVER', 'UNDER', 'YES', 'NO']:
        errors.append(f"Invalid prediction value: {prediction['prediction']}")

    # Validate player type
    if prediction['player_type'] not in ['batter', 'pitcher']:
        errors.append(f"Invalid player type: {prediction['player_type']}")

    # Validate prop type
    if prediction['prop_type'] not in mlb_config.PROP_TYPES:
        errors.append(f"Invalid prop type: {prediction['prop_type']}")

    # Validate features if present
    if 'features' in prediction:
        is_valid, error = validate_features(prediction['features'])
        if not is_valid:
            errors.append(error)

        is_valid, error = check_temporal_safety(prediction['features'], prediction['game_date'])
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors
