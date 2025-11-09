"""
NFL Prediction System - Utilities
==================================
"""

from .db_utils import (
    get_db_connection,
    save_prediction,
    save_predictions_batch,
    get_predictions_for_week,
    save_prediction_outcome,
    get_player_game_logs,
    save_player_game_log,
    get_team_context,
    save_game_schedule,
)

from .validation import (
    validate_features,
    validate_probability,
    check_temporal_safety,
    validate_prediction,
)

__all__ = [
    'get_db_connection',
    'save_prediction',
    'save_predictions_batch',
    'get_predictions_for_week',
    'save_prediction_outcome',
    'get_player_game_logs',
    'save_player_game_log',
    'get_team_context',
    'save_game_schedule',
    'validate_features',
    'validate_probability',
    'check_temporal_safety',
    'validate_prediction',
]
