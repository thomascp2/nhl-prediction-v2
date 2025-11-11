"""
NFL Prediction System V1 - Configuration Module
================================================

Central configuration for NFL prediction system.
Based on proven NHL V2 methodology.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

# Project root - UPDATE THIS PATH for your local machine
# For Windows: Use raw string (r"...") or forward slashes
NFL_ROOT = Path(r"C:\Users\thoma\NFL-Model-v1")

# Database path
DB_PATH = str(NFL_ROOT / "database" / "nfl_predictions.db")

# Logs directory
LOGS_DIR = str(NFL_ROOT / "logs")

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# =============================================================================
# LEARNING MODE SETTINGS (Year 1: Data Collection)
# =============================================================================
LEARNING_MODE = True  # Conservative probabilities during data collection
PROBABILITY_CAP = (0.30, 0.70)  # Tighter than NHL (sharper NFL market)
MODEL_TYPE = "statistical_only"  # No ML until August 2025

# =============================================================================
# PLAYER SELECTION CRITERIA
# =============================================================================
MIN_GAMES_PLAYED = 5  # Player must have 5+ games (Week 6+)
MIN_SNAP_COUNT_PCT = 0.50  # Must play 50%+ of offensive snaps
MIN_TARGET_SHARE = 0.10  # Must get 10%+ of team targets (for receivers)
MAX_PLAYERS_PER_WEEK = 150  # Total predictions per week

# =============================================================================
# PROP TYPES CONFIGURATION
# =============================================================================
PROP_TYPES = {
    'rec_yards': {
        'enabled': True,
        'distribution': 'normal',
        'min_yards_per_game': 30.0,  # Only predict for 30+ yards/game receivers
        'positions': ['WR', 'TE'],
        'priority': 1,  # Highest priority (most popular prop)
    },
    'receptions': {
        'enabled': True,
        'distribution': 'poisson',
        'min_rec_per_game': 3.0,
        'positions': ['WR', 'TE', 'RB'],
        'priority': 2,
    },
    'rush_yards': {
        'enabled': True,
        'distribution': 'normal',
        'min_yards_per_game': 40.0,
        'positions': ['RB', 'QB'],
        'priority': 3,
    },
    'pass_yards': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'normal',
        'min_yards_per_game': 200.0,
        'positions': ['QB'],
        'priority': 4,
    },
    'pass_tds': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'poisson',
        'positions': ['QB'],
        'priority': 5,
    },
    'anytime_td': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'binary',
        'positions': ['WR', 'TE', 'RB', 'QB'],
        'priority': 6,
    },
}

# =============================================================================
# REST & FATIGUE SETTINGS
# =============================================================================
SHORT_WEEK_PENALTY = 0.92  # -8% performance on Thursday games
COMING_OFF_BYE_BOOST = 1.05  # +5% performance after bye week
DAYS_REST_NORMAL = 6  # Normal week (Sunday to Sunday)
DAYS_REST_SHORT = 3  # Short week (Thursday)

# =============================================================================
# WEATHER THRESHOLDS (CRITICAL FOR NFL!)
# =============================================================================
WEATHER_THRESHOLDS = {
    'wind': {
        'moderate': 15,  # MPH - significant impact on passing
        'high': 20,  # MPH - severe impact
        'moderate_penalty': 0.92,  # -8%
        'high_penalty': 0.80,  # -20%
    },
    'temperature': {
        'cold': 32,  # Fahrenheit - freezing
        'extreme_cold': 20,  # Fahrenheit
        'cold_penalty': 0.93,  # -7%
        'extreme_penalty': 0.85,  # -15%
    },
    'precipitation': {
        'rain_penalty': 0.90,  # -10%
        'snow_penalty': 0.85,  # -15%
    },
    'dome': {
        'is_dome': 1.00,  # No weather impact
    },
}

# =============================================================================
# GAME SCRIPT ADJUSTMENTS (BIGGEST NFL FACTOR!)
# =============================================================================
GAME_SCRIPT_ADJUSTMENTS = {
    'passing': {
        'trailing_7_plus': 1.15,  # +15% when trailing by 7+
        'leading_7_plus': 0.90,  # -10% when leading by 7+
        'close_game': 1.00,  # No adjustment (within 6 points)
    },
    'rushing': {
        'trailing_7_plus': 0.85,  # -15% when trailing (abandon run)
        'leading_7_plus': 1.20,  # +20% when leading (run clock)
        'close_game': 1.00,  # No adjustment
    },
}

# =============================================================================
# HOME FIELD ADVANTAGE
# =============================================================================
HOME_FIELD_BOOST = {
    'general': 1.03,  # +3% across the board
    'passing': 1.03,  # +3% for passing stats
    'rushing': 1.03,  # +3% for rushing stats
}

# Dome team adjustments (playing outdoors)
DOME_TEAM_OUTDOOR_PENALTY = 0.93  # -7% (Saints, Falcons, etc. on road)

# Cold weather team adjustments (playing at home in winter)
COLD_WEATHER_BOOST = 1.08  # +8% (Packers, Bills in December)
COLD_WEATHER_TEAMS = ['GB', 'BUF', 'CHI', 'DEN', 'NE', 'PIT']

# =============================================================================
# SEASON INFORMATION
# =============================================================================
SEASON = "2024"
SEASON_START = datetime(2024, 9, 5)  # Week 1
REGULAR_SEASON_END = datetime(2025, 1, 5)  # Week 18
PLAYOFFS_END = datetime(2025, 2, 9)  # Super Bowl LIX
TOTAL_REGULAR_WEEKS = 18
TOTAL_PLAYOFF_WEEKS = 4

# =============================================================================
# API SETTINGS
# =============================================================================
# Primary: ESPN API (free)
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

# Backup: NFL.com, Pro Football Reference
NFL_API_BASE = "https://api.nfl.com/v3"
PFR_BASE = "https://www.pro-football-reference.com"

# Weather API (free)
WEATHER_API = "https://api.weather.gov"

# Rate limiting
API_RATE_LIMIT = 60  # Requests per minute
API_TIMEOUT = 30  # Seconds

# =============================================================================
# MODEL SETTINGS
# =============================================================================
MODEL_VERSION = "statistical_v1"
RANDOM_SEED = 42

# Feature importance (for ML training later)
MIN_FEATURE_IMPORTANCE = 0.01

# =============================================================================
# TIMEZONE SETTINGS
# =============================================================================
TIMEZONE = "America/New_York"  # Eastern Time (NFL standard)

# =============================================================================
# DISCORD NOTIFICATIONS (Optional)
# =============================================================================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL_NFL', '')
SEND_DISCORD_NOTIFICATIONS = False  # Enable when ready

# =============================================================================
# DATA COLLECTION TARGETS
# =============================================================================
DATA_COLLECTION_START = "2024-11-10"  # Week 10 (now!)
DATA_COLLECTION_END = "2025-02-09"  # Super Bowl
TARGET_PREDICTIONS_PER_WEEK = 250  # Average
TARGET_TOTAL_PREDICTIONS = 3000  # For ML training (12 weeks × 250)

# =============================================================================
# VALIDATION SETTINGS
# =============================================================================
ENABLE_FEATURE_VALIDATION = True  # Check features before prediction
ENABLE_TEMPORAL_SAFETY_CHECK = True  # Ensure no future data leakage
ENABLE_PROBABILITY_VALIDATION = True  # Check probability caps

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# NFL TEAM ABBREVIATIONS
# =============================================================================
NFL_TEAMS = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE',
    'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
    'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
    'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
]

# Dome teams (no weather impact)
DOME_TEAMS = ['ARI', 'ATL', 'DAL', 'DET', 'HOU', 'IND', 'LAR', 'LV', 'MIN', 'NO']

# =============================================================================
# POSITION GROUPS
# =============================================================================
POSITIONS = {
    'QB': 'Quarterback',
    'RB': 'Running Back',
    'WR': 'Wide Receiver',
    'TE': 'Tight End',
    'K': 'Kicker',
    'DEF': 'Defense/Special Teams',
}

# =============================================================================
# INJURY STATUS CODES
# =============================================================================
INJURY_STATUS = {
    'out': 'Out (will not play)',
    'doubtful': 'Doubtful (<25% chance)',
    'questionable': 'Questionable (50% chance)',
    'probable': 'Probable (>75% chance)',
    'healthy': 'Healthy',
}

# Players with these statuses should NOT be predicted on
EXCLUDE_INJURY_STATUS = ['out', 'doubtful']

# =============================================================================
# PRINT CONFIG CONFIRMATION
# =============================================================================
print(f"NFL Config Loaded Successfully!")
print(f"  Database: {DB_PATH}")
print(f"  Learning Mode: {LEARNING_MODE}")
print(f"  Probability Cap: {PROBABILITY_CAP}")
print(f"  Season: {SEASON}")
print(f"  Enabled Props: {[k for k, v in PROP_TYPES.items() if v['enabled']]}")
print(f"  Target Predictions/Week: {TARGET_PREDICTIONS_PER_WEEK}")
