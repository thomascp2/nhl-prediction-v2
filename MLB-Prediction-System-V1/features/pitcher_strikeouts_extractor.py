"""
Pitcher Strikeouts Feature Extractor
====================================
Most popular MLB prop! (Poisson distribution)
Based on proven NHL continuous_feature_extractor.py methodology
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))
import mlb_config
from utils.db_utils import get_player_game_logs, get_park_factor


def extract_pitcher_strikeouts_features(
    pitcher_name: str,
    team: str,
    opponent: str,
    game_date: str,
    pitcher_hand: str,  # 'L' or 'R'
    line: float,
    game_context: Optional[Dict] = None
) -> Dict:
    """
    Extract 15+ features for pitcher strikeouts prediction

    Args:
        pitcher_name: Pitcher's name
        team: Pitcher's team
        opponent: Opponent team
        game_date: Game date (YYYY-MM-DD)
        pitcher_hand: Pitcher handedness ('L' or 'R')
        line: Prop line (e.g., 5.5 strikeouts)
        game_context: Optional game context (Vegas lines, weather, park, etc.)

    Returns:
        Dictionary of features
    """
    features = {
        'player_name': pitcher_name,
        'player_type': 'pitcher',
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'prop_type': 'pitcher_strikeouts',
        'line': line,
        'pitcher_hand': pitcher_hand,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    # Get pitcher game logs (last 20 starts)
    game_logs = get_player_game_logs(pitcher_name, 'pitcher', limit=20)

    if not game_logs:
        print(f"Warning: No game logs found for {pitcher_name}")
        return None

    # ========== PITCHER ABILITY (Season + Recent) ==========
    season_strikeouts = [g['pitcher_strikeouts'] for g in game_logs if g['pitcher_strikeouts'] is not None]
    season_innings = [g['innings_pitched'] for g in game_logs if g['innings_pitched'] is not None and g['innings_pitched'] > 0]

    if season_strikeouts and season_innings:
        # K/9 (strikeouts per 9 innings) - KEY METRIC
        total_k = sum(season_strikeouts)
        total_ip = sum(season_innings)
        features['k_per_9_season'] = (total_k * 9.0) / total_ip if total_ip > 0 else 0

        # Average strikeouts per start
        features['strikeouts_per_start_season'] = statistics.mean(season_strikeouts)
        features['std_strikeouts_season'] = statistics.stdev(season_strikeouts) if len(season_strikeouts) > 1 else 0
    else:
        features['k_per_9_season'] = 0
        features['strikeouts_per_start_season'] = 0
        features['std_strikeouts_season'] = 0

    # Last 5 starts (recent form - CRITICAL!)
    recent_starts = game_logs[:5]
    recent_k = [g['pitcher_strikeouts'] for g in recent_starts if g['pitcher_strikeouts'] is not None]
    recent_ip = [g['innings_pitched'] for g in recent_starts if g['innings_pitched'] is not None and g['innings_pitched'] > 0]

    if recent_k and recent_ip:
        features['strikeouts_per_start_last_5'] = statistics.mean(recent_k)
        total_recent_k = sum(recent_k)
        total_recent_ip = sum(recent_ip)
        features['k_per_9_last_5'] = (total_recent_k * 9.0) / total_recent_ip if total_recent_ip > 0 else 0

        # Hot/cold streak
        if features['k_per_9_last_5'] > features['k_per_9_season'] * 1.10:
            features['is_hot_streak'] = 1
        elif features['k_per_9_last_5'] < features['k_per_9_season'] * 0.90:
            features['is_cold_streak'] = 1
        else:
            features['is_hot_streak'] = 0
            features['is_cold_streak'] = 0
    else:
        features['strikeouts_per_start_last_5'] = features['strikeouts_per_start_season']
        features['k_per_9_last_5'] = features['k_per_9_season']
        features['is_hot_streak'] = 0
        features['is_cold_streak'] = 0

    # Innings pitched (predicts opportunity)
    if season_innings:
        features['innings_per_start'] = statistics.mean(season_innings)
    else:
        features['innings_per_start'] = 5.5  # Default

    # Pitch count (stamina)
    season_pitch_counts = [g['pitch_count'] for g in game_logs if g['pitch_count'] is not None]
    if season_pitch_counts:
        features['pitch_count_avg'] = statistics.mean(season_pitch_counts)
    else:
        features['pitch_count_avg'] = 95  # Default

    # ========== MATCHUP (Opponent Strikeout Rate) ==========
    # Would need opponent team stats - placeholder for now
    features['opponent_k_rate'] = 0.235  # TODO: Get from team_stats table (23.5% league average)
    features['opponent_contact_rate'] = 0.765  # TODO: Get from team_stats (76.5% = 100 - 23.5)

    # Platoon advantage (pitcher hand vs opponent)
    # vs LHB or vs RHB
    features['platoon_advantage'] = 1.00  # TODO: Calculate based on opponent's L/R splits

    # ========== PARK FACTOR (CRITICAL for baseball!) ==========
    park_name = game_context.get('park_name') if game_context else None
    if park_name:
        park_factor = get_park_factor(park_name)
        if park_factor:
            features['park_k_factor'] = park_factor.get('strikeouts_factor', 1.00)
            features['is_dome'] = park_factor.get('is_dome', False)
        else:
            features['park_k_factor'] = 1.00
            features['is_dome'] = False
    else:
        features['park_k_factor'] = 1.00
        features['is_dome'] = False

    # ========== GAME CONTEXT ==========
    if game_context:
        features['game_total'] = game_context.get('total', 8.5)  # O/U runs
        features['team_implied_runs'] = game_context.get('team_implied_runs', 4.25)
        features['home_away'] = game_context.get('home_away', 'away')
    else:
        features['game_total'] = 8.5
        features['team_implied_runs'] = 4.25
        features['home_away'] = 'away'

    # ========== WEATHER (HUGE for strikeouts!) ==========
    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['temperature'] = weather.get('temperature', 72)
        features['wind_speed'] = weather.get('wind_speed', 5)
        features['conditions'] = weather.get('conditions', 'clear')
    else:
        features['temperature'] = 72
        features['wind_speed'] = 5
        features['conditions'] = 'clear'

    # ========== REST ==========
    if game_context and 'rest' in game_context:
        features['days_rest'] = game_context['rest'].get('days_rest', 4)  # Pitchers usually on 5-day rotation
    else:
        features['days_rest'] = 4

    # ========== HOME FIELD ==========
    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    return features


def calculate_strikeouts_lambda(features: Dict) -> float:
    """
    Calculate Poisson lambda for strikeouts prediction

    Args:
        features: Extracted features

    Returns:
        Adjusted lambda (expected strikeouts)
    """
    # Start with recent form (weighted average)
    lambda_base = features['strikeouts_per_start_last_5'] * 0.6 + features['strikeouts_per_start_season'] * 0.4

    # Adjust for hot/cold streak
    if features['is_hot_streak']:
        lambda_base *= 1.10  # +10% for hot streak
    elif features['is_cold_streak']:
        lambda_base *= 0.90  # -10% for cold streak

    # Adjust for opponent K rate
    if features['opponent_k_rate'] > 0.25:  # High strikeout opponent
        lambda_base *= 1.10
    elif features['opponent_k_rate'] < 0.20:  # Low strikeout opponent
        lambda_base *= 0.90

    # Adjust for park factor (CRITICAL!)
    lambda_base *= features['park_k_factor']

    # Adjust for game total (high scoring = more innings = more Ks potentially)
    if features['game_total'] > 9.0:  # High-scoring game
        lambda_base *= 1.05
    elif features['game_total'] < 7.5:  # Low-scoring game (pitcher may get pulled early)
        lambda_base *= 0.95

    # Adjust for weather
    # Cold weather = harder to see ball = more Ks
    if not features['is_dome']:
        if features['temperature'] < 55:  # Cold
            lambda_base *= 1.05
        elif features['temperature'] > 85:  # Hot
            lambda_base *= 0.97

    # Adjust for home field
    if features['is_home']:
        lambda_base *= 1.03  # +3% at home

    return lambda_base
