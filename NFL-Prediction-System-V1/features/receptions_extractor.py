"""
Receptions Feature Extractor
============================
Extracts features for receptions props (count data - Poisson distribution)
Based on proven NHL binary_feature_extractor.py methodology
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from utils.db_utils import get_player_game_logs, get_team_context


def extract_receptions_features(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Dict:
    """Extract 20+ features for receptions prediction"""

    features = {
        'player_name': player_name,
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'week_number': week_number,
        'position': position,
        'prop_type': 'receptions',
        'line': line,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    game_logs = get_player_game_logs(player_name, limit=20)
    if not game_logs:
        return None

    # ========== PLAYER RECEPTION VOLUME ==========
    season_receptions = [g['receptions'] for g in game_logs if g['receptions'] is not None]
    if season_receptions:
        features['rec_per_game_season'] = statistics.mean(season_receptions)
        features['std_receptions_season'] = statistics.stdev(season_receptions) if len(season_receptions) > 1 else 0
        features['max_receptions'] = max(season_receptions)
    else:
        features['rec_per_game_season'] = 0
        features['std_receptions_season'] = 0
        features['max_receptions'] = 0

    # Last 4 games
    recent_games = game_logs[:4]
    recent_recs = [g['receptions'] for g in recent_games if g['receptions'] is not None]
    if recent_recs:
        features['rec_per_game_last_4'] = statistics.mean(recent_recs)
    else:
        features['rec_per_game_last_4'] = features['rec_per_game_season']

    # Catch rate (receptions / targets)
    season_targets = [g['targets'] for g in game_logs if g['targets'] is not None and g['targets'] > 0]
    if season_targets and season_receptions:
        total_targets = sum([g['targets'] or 0 for g in game_logs])
        total_recs = sum([g['receptions'] or 0 for g in game_logs])
        features['catch_rate'] = total_recs / total_targets if total_targets > 0 else 0.65
    else:
        features['catch_rate'] = 0.65  # Default

    # ========== OPPORTUNITY METRICS ==========
    if season_targets:
        features['targets_per_game'] = statistics.mean(season_targets)
        recent_targets = [g['targets'] for g in recent_games if g['targets'] is not None]
        features['targets_last_4'] = statistics.mean(recent_targets) if recent_targets else features['targets_per_game']
    else:
        features['targets_per_game'] = 0
        features['targets_last_4'] = 0

    # Target share
    target_shares = [g['target_share'] for g in game_logs if g['target_share'] is not None]
    features['target_share'] = statistics.mean(target_shares) if target_shares else 0

    # Snap count
    snap_pcts = [g['snap_pct'] for g in game_logs if g['snap_pct'] is not None]
    features['snap_count_pct'] = statistics.mean(snap_pcts) if snap_pcts else 0

    # ========== ROLE ==========
    features['is_slot_receiver'] = 1 if position == 'WR' and features['catch_rate'] > 0.70 else 0
    features['is_ppr_specialist'] = 1 if features['rec_per_game_season'] > 6.0 else 0

    # Average depth of target (short routes = more catches)
    total_yards = sum([g['rec_yards'] or 0 for g in game_logs])
    total_recs = sum([g['receptions'] or 0 for g in game_logs])
    features['avg_depth_of_target'] = total_yards / total_recs if total_recs > 0 else 10.0

    # ========== OPPONENT DEFENSE ==========
    opp_ctx = get_team_context(opponent, week_number)
    if opp_ctx:
        features['opp_pass_def_rank'] = opp_ctx.get('pass_def_rank', 16)
        if position == 'WR':
            features['opp_receptions_allowed_to_position'] = opp_ctx.get('yards_allowed_to_wr1', 65.0) / 12.0  # Estimate
        elif position == 'TE':
            features['opp_receptions_allowed_to_position'] = opp_ctx.get('yards_allowed_to_te', 55.0) / 11.0
        else:
            features['opp_receptions_allowed_to_position'] = 5.0
    else:
        features['opp_pass_def_rank'] = 16
        features['opp_receptions_allowed_to_position'] = 5.0

    # ========== GAME CONTEXT ==========
    if game_context:
        features['game_total'] = game_context.get('total', 45.0)
        features['spread'] = game_context.get('spread', 0.0)
        features['team_implied_points'] = game_context.get('team_implied_points', 22.5)
        features['home_away'] = game_context.get('home_away', 'away')
        features['expected_pace'] = game_context.get('expected_pace', 65.0)
    else:
        features['game_total'] = 45.0
        features['spread'] = 0.0
        features['team_implied_points'] = 22.5
        features['home_away'] = 'away'
        features['expected_pace'] = 65.0

    # ========== WEATHER ==========
    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['weather_wind'] = weather.get('wind', 5)
        features['is_dome'] = weather.get('is_dome', False)
    else:
        features['weather_wind'] = 5
        features['is_dome'] = False

    # ========== REST ==========
    if game_context and 'rest' in game_context:
        rest = game_context['rest']
        features['is_short_week'] = rest.get('is_short_week', False)
        features['coming_off_bye'] = rest.get('coming_off_bye', False)
    else:
        features['is_short_week'] = False
        features['coming_off_bye'] = False

    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    # Game script
    if features['spread'] > 7:
        features['expected_game_script'] = 'trailing'
    elif features['spread'] < -7:
        features['expected_game_script'] = 'leading'
    else:
        features['expected_game_script'] = 'close'

    return features


def calculate_receptions_lambda(features: Dict) -> float:
    """Calculate Poisson lambda for receptions"""

    # Weighted average (recent > season)
    lambda_base = features['rec_per_game_last_4'] * 0.6 + features['rec_per_game_season'] * 0.4

    # Adjust for target share
    if features['target_share'] > 0.25:
        lambda_base *= 1.10
    elif features['target_share'] < 0.15:
        lambda_base *= 0.90

    # Adjust for opponent
    if features['opp_pass_def_rank'] > 24:
        lambda_base *= 1.08
    elif features['opp_pass_def_rank'] < 8:
        lambda_base *= 0.92

    # Adjust for game total
    if features['game_total'] > 48.0:
        lambda_base *= 1.05
    elif features['game_total'] < 42.0:
        lambda_base *= 0.95

    # Adjust for game script (more important for receptions)
    if features['expected_game_script'] == 'trailing':
        lambda_base *= 1.10  # +10% when trailing (more targets)
    elif features['expected_game_script'] == 'leading':
        lambda_base *= 0.93  # -7% when leading

    # Weather (less impact on receptions than yards)
    if not features['is_dome'] and features['weather_wind'] >= 20:
        lambda_base *= 0.90

    # Rest
    if features['is_short_week']:
        lambda_base *= 0.92
    elif features['coming_off_bye']:
        lambda_base *= 1.05

    # Home field
    if features['is_home']:
        lambda_base *= 1.03

    return lambda_base
