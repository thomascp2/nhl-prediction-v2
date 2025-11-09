"""
Batter Hits Feature Extractor
=============================
Binary classification (like NHL Points O0.5)
Will batter get 1+ hits?
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))
import mlb_config
from utils.db_utils import get_player_game_logs, get_park_factor


def extract_batter_hits_features(
    batter_name: str,
    team: str,
    opponent: str,
    game_date: str,
    batter_hand: str,  # 'L', 'R', or 'S' (switch)
    opposing_pitcher_hand: str,  # 'L' or 'R'
    line: float,  # Usually 0.5 (yes/no hits)
    game_context: Optional[Dict] = None
) -> Dict:
    """Extract 15+ features for batter hits prediction"""

    features = {
        'player_name': batter_name,
        'player_type': 'batter',
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'prop_type': 'batter_hits',
        'line': line,
        'batter_hand': batter_hand,
        'opposing_pitcher_hand': opposing_pitcher_hand,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    # Get batter game logs
    game_logs = get_player_game_logs(batter_name, 'batter', limit=20)
    if not game_logs:
        return None

    # Season batting average
    season_hits = [g['hits'] for g in game_logs if g['hits'] is not None]
    season_at_bats = [g['at_bats'] for g in game_logs if g['at_bats'] is not None and g['at_bats'] > 0]

    if season_hits and season_at_bats:
        total_hits = sum(season_hits)
        total_ab = sum(season_at_bats)
        features['batting_avg_season'] = total_hits / total_ab if total_ab > 0 else 0.250

        # Hit rate (% of games with 1+ hits)
        games_with_hits = sum([1 for h in season_hits if h >= 1])
        features['hit_rate_season'] = games_with_hits / len(season_hits) if season_hits else 0.65
    else:
        features['batting_avg_season'] = 0.250
        features['hit_rate_season'] = 0.65

    # Last 10 games
    recent_games = game_logs[:10]
    recent_hits = [g['hits'] for g in recent_games if g['hits'] is not None]
    recent_ab = [g['at_bats'] for g in recent_games if g['at_bats'] is not None and g['at_bats'] > 0]

    if recent_hits and recent_ab:
        features['batting_avg_last_10'] = sum(recent_hits) / sum(recent_ab) if sum(recent_ab) > 0 else features['batting_avg_season']
        games_with_hits_recent = sum([1 for h in recent_hits if h >= 1])
        features['hit_rate_last_10'] = games_with_hits_recent / len(recent_hits)

        # Hot/cold streak
        if features['batting_avg_last_10'] > features['batting_avg_season'] * 1.15:
            features['is_hot_streak'] = 1
        elif features['batting_avg_last_10'] < features['batting_avg_season'] * 0.85:
            features['is_cold_streak'] = 1
        else:
            features['is_hot_streak'] = 0
            features['is_cold_streak'] = 0
    else:
        features['batting_avg_last_10'] = features['batting_avg_season']
        features['hit_rate_last_10'] = features['hit_rate_season']
        features['is_hot_streak'] = 0
        features['is_cold_streak'] = 0

    # Platoon splits (CRITICAL for MLB!)
    platoon_key = f"{batter_hand}_vs_{opposing_pitcher_hand}"
    features['platoon_adjustment'] = mlb_config.PLATOON_ADJUSTMENTS.get(platoon_key, 1.00)

    # Park factor
    park_name = game_context.get('park_name') if game_context else None
    if park_name:
        park_factor = get_park_factor(park_name)
        features['park_hits_factor'] = park_factor.get('hits_factor', 1.00) if park_factor else 1.00
    else:
        features['park_hits_factor'] = 1.00

    # Game context
    if game_context:
        features['lineup_position'] = game_context.get('lineup_position', 5)
        features['home_away'] = game_context.get('home_away', 'away')
        features['game_total'] = game_context.get('total', 8.5)
    else:
        features['lineup_position'] = 5
        features['home_away'] = 'away'
        features['game_total'] = 8.5

    # Weather
    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['temperature'] = weather.get('temperature', 72)
        features['wind_direction'] = weather.get('wind_direction', 'calm')
    else:
        features['temperature'] = 72
        features['wind_direction'] = 'calm'

    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    return features


def calculate_hit_probability(features: Dict) -> float:
    """Calculate probability of getting 1+ hits"""

    # Start with recent hit rate
    prob_base = features['hit_rate_last_10'] * 0.6 + features['hit_rate_season'] * 0.4

    # Adjust for hot/cold streak
    if features['is_hot_streak']:
        prob_base *= 1.12
    elif features['is_cold_streak']:
        prob_base *= 0.88

    # Platoon advantage (CRITICAL!)
    prob_base *= features['platoon_adjustment']

    # Park factor
    prob_base *= features['park_hits_factor']

    # Lineup position (top of order = more at-bats)
    if features['lineup_position'] <= 3:
        prob_base *= 1.05

    # Weather
    if features['temperature'] > 85:  # Hot = ball flies
        prob_base *= 1.03

    if features['wind_direction'] == 'out':
        prob_base *= 1.05

    # Home field
    if features['is_home']:
        prob_base *= 1.04

    return prob_base
