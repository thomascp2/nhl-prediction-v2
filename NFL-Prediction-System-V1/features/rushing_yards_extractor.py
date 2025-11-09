"""
Rushing Yards Feature Extractor
================================
Extracts features for rushing yards props (continuous - Normal distribution)
Game script is CRITICAL for rushing!
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from utils.db_utils import get_player_game_logs, get_team_context


def extract_rushing_yards_features(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Dict:
    """Extract 20+ features for rushing yards prediction"""

    features = {
        'player_name': player_name,
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'week_number': week_number,
        'position': position,
        'prop_type': 'rush_yards',
        'line': line,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    game_logs = get_player_game_logs(player_name, limit=20)
    if not game_logs:
        return None

    # ========== PLAYER RUSHING ABILITY ==========
    season_rush_yards = [g['rush_yards'] for g in game_logs if g['rush_yards'] is not None]
    if season_rush_yards:
        features['rush_yards_per_game_season'] = statistics.mean(season_rush_yards)
        features['std_rush_yards_season'] = statistics.stdev(season_rush_yards) if len(season_rush_yards) > 1 else 0
        features['max_rush_yards'] = max(season_rush_yards)
    else:
        features['rush_yards_per_game_season'] = 0
        features['std_rush_yards_season'] = 0
        features['max_rush_yards'] = 0

    # Last 4 games (recent form)
    recent_games = game_logs[:4]
    recent_rush = [g['rush_yards'] for g in recent_games if g['rush_yards'] is not None]
    if recent_rush:
        features['rush_yards_per_game_last_4'] = statistics.mean(recent_rush)
        features['std_rush_yards_last_4'] = statistics.stdev(recent_rush) if len(recent_rush) > 1 else 0

        # Hot/cold streak
        if features['rush_yards_per_game_last_4'] > features['rush_yards_per_game_season'] * 1.15:
            features['is_hot_streak'] = 1
        elif features['rush_yards_per_game_last_4'] < features['rush_yards_per_game_season'] * 0.85:
            features['is_cold_streak'] = 1
        else:
            features['is_hot_streak'] = 0
            features['is_cold_streak'] = 0
    else:
        features['rush_yards_per_game_last_4'] = features['rush_yards_per_game_season']
        features['std_rush_yards_last_4'] = features['std_rush_yards_season']
        features['is_hot_streak'] = 0
        features['is_cold_streak'] = 0

    # Yards per carry (efficiency)
    season_carries = [g['rush_attempts'] for g in game_logs if g['rush_attempts'] is not None and g['rush_attempts'] > 0]
    if season_carries:
        total_yards = sum([g['rush_yards'] or 0 for g in game_logs])
        total_carries = sum(season_carries)
        features['yards_per_carry'] = total_yards / total_carries if total_carries > 0 else 0
    else:
        features['yards_per_carry'] = 0

    # ========== OPPORTUNITY METRICS ==========
    if season_carries:
        features['carries_per_game'] = statistics.mean(season_carries)
        recent_carries = [g['rush_attempts'] for g in recent_games if g['rush_attempts'] is not None]
        features['carries_last_4'] = statistics.mean(recent_carries) if recent_carries else features['carries_per_game']
    else:
        features['carries_per_game'] = 0
        features['carries_last_4'] = 0

    # Snap count
    snap_pcts = [g['snap_pct'] for g in game_logs if g['snap_pct'] is not None]
    features['snap_count_pct'] = statistics.mean(snap_pcts) if snap_pcts else 0

    # Red zone carries
    rz_carries = [g['red_zone_carries'] for g in game_logs if g['red_zone_carries'] is not None]
    features['red_zone_carry_share'] = statistics.mean(rz_carries) if rz_carries else 0

    # ========== ROLE ==========
    features['is_bellcow'] = 1 if features['carries_per_game'] >= 15 and features['snap_count_pct'] >= 0.65 else 0
    features['is_committee_back'] = 1 if features['carries_per_game'] < 12 else 0

    # ========== OFFENSIVE LINE QUALITY ==========
    team_ctx = get_team_context(team, week_number)
    if team_ctx:
        features['oline_rank'] = team_ctx.get('oline_rank', 16)  # 1-32
    else:
        features['oline_rank'] = 16

    # ========== OPPONENT DEFENSE ==========
    opp_ctx = get_team_context(opponent, week_number)
    if opp_ctx:
        features['opp_rush_def_rank'] = opp_ctx.get('rush_def_rank', 16)
        features['opp_rush_yards_allowed'] = opp_ctx.get('rush_yards_allowed_per_game', 120.0)
        features['opp_yards_per_carry_allowed'] = opp_ctx.get('yards_per_carry_allowed', 4.3)
    else:
        features['opp_rush_def_rank'] = 16
        features['opp_rush_yards_allowed'] = 120.0
        features['opp_yards_per_carry_allowed'] = 4.3

    # ========== GAME CONTEXT (CRITICAL FOR RUSHING!) ==========
    if game_context:
        features['game_total'] = game_context.get('total', 45.0)
        features['spread'] = game_context.get('spread', 0.0)
        features['team_implied_points'] = game_context.get('team_implied_points', 22.5)
        features['home_away'] = game_context.get('home_away', 'away')
    else:
        features['game_total'] = 45.0
        features['spread'] = 0.0
        features['team_implied_points'] = 22.5
        features['home_away'] = 'away'

    # ========== WEATHER (less impact on rushing) ==========
    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['weather_temp'] = weather.get('temp', 70)
        features['weather_precip'] = weather.get('precip', 'clear')
    else:
        features['weather_temp'] = 70
        features['weather_precip'] = 'clear'

    # ========== REST ==========
    if game_context and 'rest' in game_context:
        rest = game_context['rest']
        features['is_short_week'] = rest.get('is_short_week', False)
        features['coming_off_bye'] = rest.get('coming_off_bye', False)
    else:
        features['is_short_week'] = False
        features['coming_off_bye'] = False

    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    # ========== GAME SCRIPT (BIGGEST FACTOR FOR RUSHING!) ==========
    if features['spread'] < -7:
        features['expected_game_script'] = 'leading'  # Favorite (more rushing!)
    elif features['spread'] > 7:
        features['expected_game_script'] = 'trailing'  # Underdog (less rushing)
    else:
        features['expected_game_script'] = 'close'

    return features


def calculate_rush_yards_baseline(features: Dict) -> float:
    """Calculate baseline rushing yards expectation (game script is CRITICAL!)"""

    # Weighted average
    baseline = features['rush_yards_per_game_last_4'] * 0.6 + features['rush_yards_per_game_season'] * 0.4

    # Adjust for hot/cold streak
    if features['is_hot_streak']:
        baseline *= 1.10
    elif features['is_cold_streak']:
        baseline *= 0.90

    # Adjust for bellcow role
    if features['is_bellcow']:
        baseline *= 1.08
    elif features['is_committee_back']:
        baseline *= 0.85

    # Adjust for opponent defense
    if features['opp_rush_def_rank'] > 24:  # Weak rush defense
        baseline *= 1.15  # +15% (bigger impact than passing)
    elif features['opp_rush_def_rank'] < 8:  # Strong rush defense
        baseline *= 0.85  # -15%

    # Adjust for O-line quality
    if features['oline_rank'] <= 10:  # Good O-line
        baseline *= 1.08
    elif features['oline_rank'] >= 24:  # Bad O-line
        baseline *= 0.92

    # Adjust for team implied points
    if features['team_implied_points'] > 26.0:  # High-scoring offense
        baseline *= 1.05
    elif features['team_implied_points'] < 18.0:  # Low-scoring offense
        baseline *= 0.92

    # Adjust for GAME SCRIPT (BIGGEST FACTOR!)
    if features['expected_game_script'] == 'leading':
        baseline *= 1.20  # +20% (run out clock!)
    elif features['expected_game_script'] == 'trailing':
        baseline *= 0.85  # -15% (abandon run)

    # Weather (rushing benefits from bad weather!)
    if features['weather_precip'] in ['rain', 'snow']:
        baseline *= 1.05  # +5% (more running in bad weather)

    if features['weather_temp'] < 32:
        baseline *= 1.03  # +3% (cold weather = more running)

    # Rest
    if features['is_short_week']:
        baseline *= 0.92
    elif features['coming_off_bye']:
        baseline *= 1.05

    # Home field
    if features['is_home']:
        baseline *= 1.03

    return baseline


def get_standard_deviation(features: Dict) -> float:
    """Get appropriate standard deviation for Normal distribution"""

    if features['std_rush_yards_last_4'] > 0:
        std = features['std_rush_yards_last_4'] * 0.6 + features['std_rush_yards_season'] * 0.4
    else:
        std = features['std_rush_yards_season']

    # Minimum std of 15 yards (rushing is more volatile)
    if std < 15.0:
        std = 15.0

    return std
