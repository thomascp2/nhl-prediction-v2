"""
MLB Prediction System V1 - Configuration Module
================================================

Central configuration for MLB prediction system.
Based on proven NHL V2 methodology.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

# Project root - UPDATE THIS PATH for your local machine
# For Windows: Use raw string (r"...") or forward slashes
MLB_ROOT = Path(r"C:\Users\thoma\MLB Prediciton Model")

# Database path
DB_PATH = str(MLB_ROOT / "database" / "mlb_predictions.db")

# Logs directory
LOGS_DIR = str(MLB_ROOT / "logs")

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# =============================================================================
# LEARNING MODE SETTINGS (Year 1: Data Collection)
# =============================================================================
LEARNING_MODE = True  # Conservative probabilities during data collection
PROBABILITY_CAP = (0.35, 0.65)  # More conservative than NHL (sharper MLB market)
MODEL_TYPE = "statistical_only"  # No ML until October 2025

# =============================================================================
# PLAYER SELECTION CRITERIA
# =============================================================================
MIN_GAMES_REQUIRED = 10  # Need more games (162-game season)

# Pitcher criteria
MIN_PITCHER_K_RATE = 7.0  # K/9 innings (strikeout rate)
MIN_PITCHER_GAMES_STARTED = 5  # Established starter
MIN_PITCHER_PITCH_COUNT = 85  # Goes deep in games
MAX_PITCHER_ERA = 5.00  # Not getting shelled

# Batter criteria
MIN_BATTER_AVG = 0.230  # Not terrible
MIN_BATTER_GAMES = 20  # Regular player
MAX_LINEUP_POSITION = 6  # Top 6 in batting order
MIN_AT_BATS_PER_GAME = 3.5  # Gets enough plate appearances

MAX_PLAYERS_PER_DAY = 100  # Total predictions (pitchers + batters)

# =============================================================================
# PROP TYPES CONFIGURATION
# =============================================================================
PROP_TYPES = {
    # Pitcher props
    'pitcher_strikeouts': {
        'enabled': True,
        'distribution': 'poisson',  # Discrete count data
        'player_type': 'pitcher',
        'priority': 1,  # Highest priority (most popular)
    },
    'pitcher_earned_runs': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'poisson',
        'player_type': 'pitcher',
        'priority': 4,
    },
    'pitcher_walks': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'poisson',
        'player_type': 'pitcher',
        'priority': 5,
    },

    # Batter props
    'batter_hits': {
        'enabled': True,
        'distribution': 'binary',  # 0+ hits vs 1+ hits
        'player_type': 'batter',
        'priority': 2,
    },
    'batter_total_bases': {
        'enabled': True,
        'distribution': 'poisson',  # 1B + 2×2B + 3×3B + 4×HR
        'player_type': 'batter',
        'priority': 3,
    },
    'batter_home_runs': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'binary',
        'player_type': 'batter',
        'priority': 6,
    },
    'batter_rbis': {
        'enabled': False,  # Add later (Phase 2)
        'distribution': 'poisson',
        'player_type': 'batter',
        'priority': 7,
    },
}

# =============================================================================
# PARK FACTORS (CRITICAL FOR MLB!)
# =============================================================================
# 1.0 = neutral, >1.0 = offense-friendly, <1.0 = pitcher-friendly
PARK_FACTORS = {
    # Extreme hitter's parks
    'Coors Field': {  # Colorado Rockies
        'team': 'COL',
        'runs_factor': 1.25,  # 25% more runs!
        'home_runs_factor': 1.30,
        'hits_factor': 1.20,
        'strikeouts_factor': 0.95,  # Slightly fewer Ks (ball flies)
    },
    'Great American Ball Park': {  # Cincinnati Reds
        'team': 'CIN',
        'runs_factor': 1.15,
        'home_runs_factor': 1.25,
        'hits_factor': 1.10,
        'strikeouts_factor': 0.98,
    },

    # Extreme pitcher's parks
    'Oracle Park': {  # San Francisco Giants
        'team': 'SF',
        'runs_factor': 0.85,  # 15% fewer runs
        'home_runs_factor': 0.70,  # Very hard to hit HRs
        'hits_factor': 0.95,
        'strikeouts_factor': 1.05,
    },
    'T-Mobile Park': {  # Seattle Mariners
        'team': 'SEA',
        'runs_factor': 0.92,
        'home_runs_factor': 0.85,
        'hits_factor': 0.96,
        'strikeouts_factor': 1.03,
    },

    # Neutral parks (default)
    'Default': {
        'team': 'NEUTRAL',
        'runs_factor': 1.00,
        'home_runs_factor': 1.00,
        'hits_factor': 1.00,
        'strikeouts_factor': 1.00,
    },
}

# =============================================================================
# PLATOON SPLITS (LEFTY VS RIGHTY - CRITICAL!)
# =============================================================================
PLATOON_ADJUSTMENTS = {
    # Batter handedness vs Pitcher handedness
    'R_vs_R': 0.95,  # Right batter vs Right pitcher (slight disadvantage)
    'R_vs_L': 1.08,  # Right batter vs Left pitcher (advantage!)
    'L_vs_R': 1.05,  # Left batter vs Right pitcher (advantage)
    'L_vs_L': 0.92,  # Left batter vs Left pitcher (disadvantage)

    # Switch hitters (neutral)
    'S_vs_R': 1.00,
    'S_vs_L': 1.00,
}

# =============================================================================
# WEATHER ADJUSTMENTS (AFFECTS BALL FLIGHT!)
# =============================================================================
WEATHER_ADJUSTMENTS = {
    'temperature': {
        # Hot weather = ball flies farther
        'hot': {  # 85°F+
            'threshold': 85,
            'runs_boost': 1.08,
            'home_runs_boost': 1.12,
            'hits_boost': 1.05,
            'strikeouts_penalty': 0.97,
        },
        'cold': {  # <55°F
            'threshold': 55,
            'runs_penalty': 0.93,
            'home_runs_penalty': 0.88,
            'hits_penalty': 0.96,
            'strikeouts_boost': 1.04,  # Harder to see ball
        },
    },
    'wind': {
        # Wind direction relative to batter
        'out_to_cf': {  # Blowing out to center field
            'runs_boost': 1.10,
            'home_runs_boost': 1.15,
            'hits_boost': 1.05,
        },
        'in_from_cf': {  # Blowing in from center field
            'runs_penalty': 0.90,
            'home_runs_penalty': 0.85,
            'hits_penalty': 0.97,
        },
        'cross': {  # Cross wind
            'runs_factor': 1.00,  # Neutral
            'home_runs_factor': 0.98,
            'hits_factor': 1.00,
        },
    },
}

# =============================================================================
# HOME FIELD ADVANTAGE
# =============================================================================
HOME_FIELD_BOOST = {
    'general': 1.03,  # +3% across the board (similar to NHL)
    'batting': 1.04,  # +4% for batting stats
    'pitching': 0.97,  # -3% for opponent (pitchers benefit)
}

# =============================================================================
# SEASON INFORMATION
# =============================================================================
SEASON = "2025"
SEASON_START = datetime(2025, 3, 27)  # Opening Day (approximate)
SEASON_END = datetime(2025, 9, 28)  # Regular season end
PLAYOFFS_END = datetime(2025, 11, 1)  # World Series
TOTAL_GAMES = 162  # Per team regular season

# Spring Training
SPRING_TRAINING_START = datetime(2025, 2, 15)
SPRING_TRAINING_END = datetime(2025, 3, 25)

# =============================================================================
# API SETTINGS
# =============================================================================
# Primary: MLB Stats API (free)
MLB_STATS_API = "https://statsapi.mlb.com/api/v1"

# Backup: Baseball Reference, FanGraphs
BASEBALL_REFERENCE = "https://www.baseball-reference.com"
FANGRAPHS_API = "https://www.fangraphs.com"

# Weather API
WEATHER_API = "https://api.openweathermap.org/data/2.5"
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')  # Get from environment

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
TIMEZONE = "America/New_York"  # Eastern Time (MLB standard)

# =============================================================================
# DISCORD NOTIFICATIONS (Optional)
# =============================================================================
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL_MLB', '')
SEND_DISCORD_NOTIFICATIONS = False  # Enable when ready

# =============================================================================
# DATA COLLECTION TARGETS
# =============================================================================
DATA_COLLECTION_START = "2025-03-27"  # Opening Day 2025
DATA_COLLECTION_END = "2025-09-28"  # Regular season end
TARGET_PREDICTIONS_PER_DAY = 450  # Average (12-15 games × 30-40 players/game)
TARGET_TOTAL_PREDICTIONS = 75000  # For ML training (180 days × 450)

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
# MLB TEAM ABBREVIATIONS
# =============================================================================
MLB_TEAMS = {
    # American League East
    'BAL': 'Baltimore Orioles',
    'BOS': 'Boston Red Sox',
    'NYY': 'New York Yankees',
    'TB': 'Tampa Bay Rays',
    'TOR': 'Toronto Blue Jays',

    # American League Central
    'CWS': 'Chicago White Sox',
    'CLE': 'Cleveland Guardians',
    'DET': 'Detroit Tigers',
    'KC': 'Kansas City Royals',
    'MIN': 'Minnesota Twins',

    # American League West
    'HOU': 'Houston Astros',
    'LAA': 'Los Angeles Angels',
    'OAK': 'Oakland Athletics',
    'SEA': 'Seattle Mariners',
    'TEX': 'Texas Rangers',

    # National League East
    'ATL': 'Atlanta Braves',
    'MIA': 'Miami Marlins',
    'NYM': 'New York Mets',
    'PHI': 'Philadelphia Phillies',
    'WAS': 'Washington Nationals',

    # National League Central
    'CHC': 'Chicago Cubs',
    'CIN': 'Cincinnati Reds',
    'MIL': 'Milwaukee Brewers',
    'PIT': 'Pittsburgh Pirates',
    'STL': 'St. Louis Cardinals',

    # National League West
    'ARI': 'Arizona Diamondbacks',
    'COL': 'Colorado Rockies',
    'LAD': 'Los Angeles Dodgers',
    'SD': 'San Diego Padres',
    'SF': 'San Francisco Giants',
}

# =============================================================================
# HANDEDNESS CODES
# =============================================================================
HANDEDNESS = {
    'R': 'Right',
    'L': 'Left',
    'S': 'Switch',  # Switch hitter
}

# =============================================================================
# PITCHER TYPES
# =============================================================================
PITCHER_TYPES = {
    'starter': 'Starting Pitcher',
    'reliever': 'Relief Pitcher',
    'closer': 'Closer',
}

# =============================================================================
# PRINT CONFIG CONFIRMATION
# =============================================================================
print(f"MLB Config Loaded Successfully!")
print(f"  Database: {DB_PATH}")
print(f"  Learning Mode: {LEARNING_MODE}")
print(f"  Probability Cap: {PROBABILITY_CAP}")
print(f"  Season: {SEASON}")
print(f"  Enabled Props: {[k for k, v in PROP_TYPES.items() if v['enabled']]}")
print(f"  Target Predictions/Day: {TARGET_PREDICTIONS_PER_DAY}")
print(f"  Opening Day: {SEASON_START.strftime('%B %d, %Y')}")
