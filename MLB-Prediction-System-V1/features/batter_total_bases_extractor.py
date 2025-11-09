"""
Batter Total Bases Feature Extractor
====================================
Total bases = 1B + 2×2B + 3×3B + 4×HR (Poisson distribution)
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))
import mlb_config
from utils.db_utils import get_player_game_logs, get_park_factor


def extract_total_bases_features(
    batter_name: str,
    team: str,
    opponent: str,
    game_date: str,
    batter_hand: str,
    opposing_pitcher_hand: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Dict:
    """Extract 15+ features for total bases prediction"""

    features = {
        'player_name': batter_name,
        'player_type': 'batter',
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'prop_type': 'batter_total_bases',
        'line': line,
        'batter_hand': batter_hand,
        'opposing_pitcher_hand': opposing_pitcher_hand,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    game_logs = get_player_game_logs(batter_name, 'batter', limit=20)
    if not game_logs:
        return None

    # Season total bases
    season_tb = [g['total_bases'] for g in game_logs if g['total_bases'] is not None]
    if season_tb:
        features['total_bases_per_game_season'] = statistics.mean(season_tb)
        features['std_total_bases'] = statistics.stdev(season_tb) if len(season_tb) > 1 else 0
    else:
        features['total_bases_per_game_season'] = 0
        features['std_total_bases'] = 0

    # Last 10 games
    recent_games = game_logs[:10]
    recent_tb = [g['total_bases'] for g in recent_games if g['total_bases'] is not None]
    if recent_tb:
        features['total_bases_per_game_last_10'] = statistics.mean(recent_tb)
    else:
        features['total_bases_per_game_last_10'] = features['total_bases_per_game_season']

    # Power stats
    season_hr = [g['home_runs'] for g in game_logs if g['home_runs'] is not None]
    if season_hr:
        features['home_runs_per_game'] = statistics.mean(season_hr)
    else:
        features['home_runs_per_game'] = 0

    # Platoon splits
    platoon_key = f"{batter_hand}_vs_{opposing_pitcher_hand}"
    features['platoon_adjustment'] = mlb_config.PLATOON_ADJUSTMENTS.get(platoon_key, 1.00)

    # Park factor (HUGE for total bases/power!)
    park_name = game_context.get('park_name') if game_context else None
    if park_name:
        park_factor = get_park_factor(park_name)
        if park_factor:
            features['park_tb_factor'] = (park_factor.get('hits_factor', 1.00) + park_factor.get('home_runs_factor', 1.00)) / 2
        else:
            features['park_tb_factor'] = 1.00
    else:
        features['park_tb_factor'] = 1.00

    # Game context
    if game_context:
        features['home_away'] = game_context.get('home_away', 'away')
        features['game_total'] = game_context.get('total', 8.5)
    else:
        features['home_away'] = 'away'
        features['game_total'] = 8.5

    # Weather (affects power!)
    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['temperature'] = weather.get('temperature', 72)
        features['wind_direction'] = weather.get('wind_direction', 'calm')
    else:
        features['temperature'] = 72
        features['wind_direction'] = 'calm'

    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    return features


def calculate_total_bases_lambda(features: Dict) -> float:
    """Calculate Poisson lambda for total bases"""

    lambda_base = features['total_bases_per_game_last_10'] * 0.6 + features['total_bases_per_game_season'] * 0.4

    # Platoon advantage
    lambda_base *= features['platoon_adjustment']

    # Park factor (HUGE for power!)
    lambda_base *= features['park_tb_factor']

    # Weather
    if features['temperature'] > 85:
        lambda_base *= 1.08  # Hot = ball flies farther

    if features['wind_direction'] == 'out':
        lambda_base *= 1.12  # Wind blowing out = more power!

    # Home field
    if features['is_home']:
        lambda_base *= 1.04

    return lambda_base
