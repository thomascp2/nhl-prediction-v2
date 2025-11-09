"""
Receiving Yards Feature Extractor
=================================
Extracts features for receiving yards props (continuous - Normal distribution)
Based on proven NHL continuous_feature_extractor.py methodology

Most popular NFL prop!
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from utils.db_utils import get_player_game_logs, get_team_context


def extract_receiving_yards_features(
    player_name: str,
    team: str,
    opponent: str,
    game_date: str,
    week_number: int,
    position: str,
    line: float,
    game_context: Optional[Dict] = None
) -> Dict:
    """
    Extract 25+ features for receiving yards prediction

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
        Dictionary of features
    """
    features = {
        # Metadata
        'player_name': player_name,
        'team': team,
        'opponent': opponent,
        'game_date': game_date,
        'week_number': week_number,
        'position': position,
        'prop_type': 'rec_yards',
        'line': line,
        'feature_extraction_date': datetime.now().strftime('%Y-%m-%d'),
    }

    # Get player game logs (last 20 games)
    game_logs = get_player_game_logs(player_name, limit=20)

    if not game_logs:
        print(f"Warning: No game logs found for {player_name}")
        return None

    # =============================================================================
    # PLAYER RECEIVING ABILITY (Season + Recent)
    # =============================================================================

    # Season-long stats
    season_rec_yards = [g['rec_yards'] for g in game_logs if g['rec_yards'] is not None]
    if season_rec_yards:
        features['rec_yards_per_game_season'] = statistics.mean(season_rec_yards)
        features['std_rec_yards_season'] = statistics.stdev(season_rec_yards) if len(season_rec_yards) > 1 else 0
        features['max_rec_yards_season'] = max(season_rec_yards)
        features['min_rec_yards_season'] = min(season_rec_yards)
    else:
        features['rec_yards_per_game_season'] = 0
        features['std_rec_yards_season'] = 0
        features['max_rec_yards_season'] = 0
        features['min_rec_yards_season'] = 0

    # Last 4 games (recent form - CRITICAL!)
    recent_games = game_logs[:4]
    recent_rec_yards = [g['rec_yards'] for g in recent_games if g['rec_yards'] is not None]
    if recent_rec_yards:
        features['rec_yards_per_game_last_4'] = statistics.mean(recent_rec_yards)
        features['std_rec_yards_last_4'] = statistics.stdev(recent_rec_yards) if len(recent_rec_yards) > 1 else 0

        # Hot/cold streak
        if features['rec_yards_per_game_last_4'] > features['rec_yards_per_game_season'] * 1.15:
            features['is_hot_streak'] = 1
        elif features['rec_yards_per_game_last_4'] < features['rec_yards_per_game_season'] * 0.85:
            features['is_cold_streak'] = 1
        else:
            features['is_hot_streak'] = 0
            features['is_cold_streak'] = 0
    else:
        features['rec_yards_per_game_last_4'] = features['rec_yards_per_game_season']
        features['std_rec_yards_last_4'] = features['std_rec_yards_season']
        features['is_hot_streak'] = 0
        features['is_cold_streak'] = 0

    # Yards per reception (efficiency)
    season_receptions = [g['receptions'] for g in game_logs if g['receptions'] is not None and g['receptions'] > 0]
    if season_receptions:
        total_yards = sum([g['rec_yards'] or 0 for g in game_logs])
        total_receptions = sum(season_receptions)
        features['yards_per_reception'] = total_yards / total_receptions if total_receptions > 0 else 0
    else:
        features['yards_per_reception'] = 0

    # =============================================================================
    # OPPORTUNITY METRICS (CRITICAL FOR NFL!)
    # =============================================================================

    # Targets (opportunity)
    season_targets = [g['targets'] for g in game_logs if g['targets'] is not None]
    if season_targets:
        features['targets_per_game'] = statistics.mean(season_targets)
        recent_targets = [g['targets'] for g in recent_games if g['targets'] is not None]
        if recent_targets:
            features['targets_last_4'] = statistics.mean(recent_targets)
        else:
            features['targets_last_4'] = features['targets_per_game']
    else:
        features['targets_per_game'] = 0
        features['targets_last_4'] = 0

    # Target share (% of team targets)
    season_target_shares = [g['target_share'] for g in game_logs if g['target_share'] is not None]
    if season_target_shares:
        features['target_share'] = statistics.mean(season_target_shares)
    else:
        features['target_share'] = 0

    # Snap count %
    season_snap_pcts = [g['snap_pct'] for g in game_logs if g['snap_pct'] is not None]
    if season_snap_pcts:
        features['snap_count_pct'] = statistics.mean(season_snap_pcts)
    else:
        features['snap_count_pct'] = 0

    # Air yards share (% of team air yards)
    season_air_yards_shares = [g['air_yards_share'] for g in game_logs if g['air_yards_share'] is not None]
    if season_air_yards_shares:
        features['air_yards_share'] = statistics.mean(season_air_yards_shares)
    else:
        features['air_yards_share'] = 0

    # Red zone targets
    season_rz_targets = [g['red_zone_targets'] for g in game_logs if g['red_zone_targets'] is not None]
    if season_rz_targets:
        features['red_zone_targets_per_game'] = statistics.mean(season_rz_targets)
    else:
        features['red_zone_targets_per_game'] = 0

    # =============================================================================
    # ROLE CLASSIFICATION
    # =============================================================================

    # Is WR1 (top receiver on team)
    features['is_wr1'] = 1 if features['target_share'] >= 0.22 else 0  # 22%+ target share = WR1

    # Is slot receiver (typically more catches, fewer yards)
    features['is_slot_receiver'] = 1 if position == 'WR' and features['yards_per_reception'] < 11.0 else 0

    # =============================================================================
    # QB CONNECTION (Receiving depends on QB!)
    # =============================================================================

    # Get QB stats from game logs (would need team context)
    # For now, use team-level passing stats
    team_ctx = get_team_context(team, week_number)
    if team_ctx:
        # Placeholder - would need actual team passing yards
        features['team_pass_yards_per_game'] = 250.0  # TODO: Get from team_context
    else:
        features['team_pass_yards_per_game'] = 250.0

    # =============================================================================
    # MATCHUP (Opponent Defense)
    # =============================================================================

    opp_ctx = get_team_context(opponent, week_number)
    if opp_ctx:
        features['opp_pass_def_rank'] = opp_ctx.get('pass_def_rank', 16)  # 1-32
        features['opp_pass_yards_allowed'] = opp_ctx.get('pass_yards_allowed_per_game', 230.0)

        # Positional defense
        if position == 'WR':
            features['opp_yards_allowed_to_position'] = opp_ctx.get('yards_allowed_to_wr1', 65.0)
        elif position == 'TE':
            features['opp_yards_allowed_to_position'] = opp_ctx.get('yards_allowed_to_te', 55.0)
        else:
            features['opp_yards_allowed_to_position'] = 60.0
    else:
        # Defaults (assume average defense)
        features['opp_pass_def_rank'] = 16
        features['opp_pass_yards_allowed'] = 230.0
        features['opp_yards_allowed_to_position'] = 60.0

    # =============================================================================
    # GAME CONTEXT (Vegas lines, etc.)
    # =============================================================================

    if game_context:
        features['game_total'] = game_context.get('total', 45.0)
        features['spread'] = game_context.get('spread', 0.0)
        features['team_implied_points'] = game_context.get('team_implied_points', 22.5)
        features['home_away'] = game_context.get('home_away', 'away')
        features['expected_pace'] = game_context.get('expected_pace', 65.0)  # Plays per game
    else:
        features['game_total'] = 45.0
        features['spread'] = 0.0
        features['team_implied_points'] = 22.5
        features['home_away'] = 'away'
        features['expected_pace'] = 65.0

    # =============================================================================
    # WEATHER (CRITICAL FOR PASSING!)
    # =============================================================================

    if game_context and 'weather' in game_context:
        weather = game_context['weather']
        features['weather_temp'] = weather.get('temp', 70)
        features['weather_wind'] = weather.get('wind', 5)
        features['weather_precip'] = weather.get('precip', 'clear')
        features['is_dome'] = weather.get('is_dome', False)
    else:
        features['weather_temp'] = 70
        features['weather_wind'] = 5
        features['weather_precip'] = 'clear'
        features['is_dome'] = False

    # =============================================================================
    # REST & FATIGUE
    # =============================================================================

    if game_context and 'rest' in game_context:
        rest = game_context['rest']
        features['days_rest'] = rest.get('days_rest', 6)
        features['is_short_week'] = rest.get('is_short_week', False)
        features['coming_off_bye'] = rest.get('coming_off_bye', False)
    else:
        features['days_rest'] = 6  # Normal week
        features['is_short_week'] = False
        features['coming_off_bye'] = False

    # =============================================================================
    # HOME FIELD ADVANTAGE
    # =============================================================================

    features['is_home'] = 1 if features['home_away'] == 'home' else 0

    # =============================================================================
    # GAME SCRIPT EXPECTATION (from spread)
    # =============================================================================

    # Positive spread = underdog (likely trailing = more passing)
    # Negative spread = favorite (likely leading = maybe less passing)
    if features['spread'] > 7:
        features['expected_game_script'] = 'trailing'  # Underdog
    elif features['spread'] < -7:
        features['expected_game_script'] = 'leading'  # Heavy favorite
    else:
        features['expected_game_script'] = 'close'  # Competitive game

    return features


def calculate_rec_yards_baseline(features: Dict) -> float:
    """
    Calculate baseline receiving yards expectation

    Args:
        features: Extracted features

    Returns:
        Baseline receiving yards (adjusted mean)
    """
    # Start with recent form (weighted average)
    baseline = features['rec_yards_per_game_last_4'] * 0.6 + features['rec_yards_per_game_season'] * 0.4

    # Adjust for hot/cold streak
    if features['is_hot_streak']:
        baseline *= 1.10  # +10% for hot streak
    elif features['is_cold_streak']:
        baseline *= 0.90  # -10% for cold streak

    # Adjust for target share (opportunity)
    if features['target_share'] > 0.25:  # High target share
        baseline *= 1.08
    elif features['target_share'] < 0.15:  # Low target share
        baseline *= 0.92

    # Adjust for opponent defense
    if features['opp_pass_def_rank'] > 24:  # Weak pass defense (rank 25-32)
        baseline *= 1.10
    elif features['opp_pass_def_rank'] < 8:  # Strong pass defense (rank 1-7)
        baseline *= 0.90

    # Adjust for game total (pace)
    if features['game_total'] > 48.0:  # High-scoring game
        baseline *= 1.05
    elif features['game_total'] < 42.0:  # Low-scoring game
        baseline *= 0.95

    # Adjust for game script
    if features['expected_game_script'] == 'trailing':
        baseline *= 1.08  # +8% (more passing when trailing)
    elif features['expected_game_script'] == 'leading':
        baseline *= 0.95  # -5% (less passing when leading)

    # Adjust for weather (CRITICAL!)
    if not features['is_dome']:
        wind = features['weather_wind']
        if wind >= 20:
            baseline *= 0.80  # -20% for high wind
        elif wind >= 15:
            baseline *= 0.92  # -8% for moderate wind

        if features['weather_precip'] in ['rain', 'snow']:
            baseline *= 0.90  # -10% for precipitation

        temp = features['weather_temp']
        if temp < 20:
            baseline *= 0.85  # -15% for extreme cold
        elif temp < 32:
            baseline *= 0.93  # -7% for cold

    # Adjust for rest
    if features['is_short_week']:
        baseline *= 0.92  # -8% for Thursday game
    elif features['coming_off_bye']:
        baseline *= 1.05  # +5% for extra rest

    # Adjust for home field
    if features['is_home']:
        baseline *= 1.03  # +3% at home

    return baseline


def get_standard_deviation(features: Dict) -> float:
    """
    Get appropriate standard deviation for Normal distribution

    Args:
        features: Extracted features

    Returns:
        Standard deviation
    """
    # Use recent standard deviation if available, otherwise season
    if features['std_rec_yards_last_4'] > 0:
        std = features['std_rec_yards_last_4'] * 0.6 + features['std_rec_yards_season'] * 0.4
    else:
        std = features['std_rec_yards_season']

    # Minimum std of 10 yards (avoid division by zero)
    if std < 10.0:
        std = 10.0

    return std
