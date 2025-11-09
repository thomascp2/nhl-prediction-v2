# 🏈 NFL PREDICTION SYSTEM - IMPLEMENTATION PLAN
**Based on Proven NHL System V2 Methodology**

---

## 🎯 EXECUTIVE SUMMARY

Build an NFL player prop prediction system using the **proven NHL V2 framework** (71% backtest, 68% live). NFL season is in Week 10 - still plenty of time for data collection through playoffs!

**Timeline:** 4 weeks to live deployment (Mid-November 2024)
**Target Accuracy:** 55-65% (realistic for NFL market - sharper than NBA/NHL)
**Data Collection:** Backtest on 2023 season, go live Week 11 (Nov 2024)
**ML Training:** August 2025 (after collecting 10,000+ predictions through playoffs)

---

## 📋 PROJECT CONTEXT

### **Current Timing 🔥**

```
✅ NFL Season: Week 10 of 18 (regular season)
✅ Games Played: 9 games per team
✅ Regular Season Ends: January 5, 2025
✅ Playoffs: January 11 - February 9, 2025 (Super Bowl)
✅ Total Weeks Left: 8 regular + 4 playoff = 12 weeks

Perfect for data collection this year, predictions next year!
```

### **NHL System Success (Proven Template)**

Your NHL V2 system validates this methodology:
- ✅ 71% backtest accuracy → 68% live accuracy
- ✅ Binary classification (points O0.5)
- ✅ Continuous regression (shots O2.5+)
- ✅ Statistical models (Poisson/Normal)
- ✅ Daily automation with grading
- ✅ Feature-rich modeling (50+ features)
- ✅ Learning mode (probability capping)

**NFL has MORE structure than NHL/NBA - perfect for statistical modeling!**

### **NHL → NFL Translation**

```
NHL Points O0.5 (Binary)        → NFL Anytime TD (Binary)
NHL Shots O2.5+ (Continuous)    → NFL Rec Yards O59.5+ (Normal dist)
NHL Ice Time                    → NFL Snap Count % / Target Share
NHL Goalie vs Team              → NFL Player vs Defense Rank
NHL Home Ice (+3%)              → NFL Home Field (+3%)
NHL Back-to-backs (-10%)        → NFL Short Week (-8%)
```

---

## 🏗️ SYSTEM ARCHITECTURE

### **Directory Structure**

```
NFL-Prediction-System-V1/
├── database/
│   └── nfl_predictions.db
├── features/
│   ├── __init__.py
│   ├── receiving_yards_extractor.py (continuous)
│   ├── receptions_extractor.py (continuous - Poisson)
│   ├── rushing_yards_extractor.py (continuous)
│   ├── passing_yards_extractor.py (continuous)
│   ├── anytime_td_extractor.py (binary)
│   └── matchup_analyzer.py
├── models/
│   ├── statistical_predictions.py
│   └── (ml_predictions.py - August 2025)
├── automation/
│   ├── generate_predictions_weekly.py
│   ├── auto_grade_tuesday.py
│   └── weekly_review.py
├── fetchers/
│   ├── fetch_game_schedule.py
│   ├── fetch_player_stats.py
│   ├── fetch_team_stats.py
│   ├── fetch_injury_reports.py
│   └── fetch_weather.py
├── utils/
│   ├── db_utils.py
│   └── validation.py
├── nfl_config.py
└── README.md
```

---

## 💾 DATABASE SCHEMA

### **SQLite Database: `nfl_predictions.db`**

#### **Table: predictions**
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_batch_id TEXT NOT NULL,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,  -- 1-18 (regular), 19-22 (playoffs)
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    position TEXT NOT NULL,  -- 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'
    prop_type TEXT NOT NULL,  -- 'rec_yards', 'receptions', 'rush_yards', 'pass_yards', 'pass_tds', 'anytime_td'
    line REAL NOT NULL,
    prediction TEXT NOT NULL,  -- 'OVER' or 'UNDER' (or 'YES'/'NO' for binary)
    probability REAL NOT NULL,

    -- Model metadata
    model_version TEXT DEFAULT 'statistical_v1',
    confidence_tier TEXT,

    -- Features (JSON for ML training)
    features_json TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_game_date ON predictions(game_date);
CREATE INDEX idx_predictions_week ON predictions(week_number);
CREATE INDEX idx_predictions_player ON predictions(player_name);
CREATE INDEX idx_predictions_prop ON predictions(prop_type);
```

#### **Table: prediction_outcomes**
```sql
CREATE TABLE prediction_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    prop_type TEXT NOT NULL,
    line REAL NOT NULL,
    predicted_probability REAL NOT NULL,

    -- Actual results
    actual_stat_value REAL,
    outcome TEXT,  -- 'HIT' or 'MISS'

    -- Grading metadata
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

CREATE INDEX idx_outcomes_game_date ON prediction_outcomes(game_date);
CREATE INDEX idx_outcomes_week ON prediction_outcomes(week_number);
CREATE INDEX idx_outcomes_outcome ON prediction_outcomes(outcome);
```

#### **Table: player_game_logs**
```sql
CREATE TABLE player_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    home_away TEXT,  -- 'home' or 'away'
    position TEXT NOT NULL,

    -- Core stats (position-dependent)
    -- Passing (QB)
    pass_attempts INTEGER,
    pass_completions INTEGER,
    pass_yards INTEGER,
    pass_tds INTEGER,
    interceptions INTEGER,

    -- Rushing (RB, QB)
    rush_attempts INTEGER,
    rush_yards INTEGER,
    rush_tds INTEGER,

    -- Receiving (WR, TE, RB)
    targets INTEGER,
    receptions INTEGER,
    rec_yards INTEGER,
    rec_tds INTEGER,

    -- Opportunity metrics
    snap_count INTEGER,
    snap_pct REAL,  -- % of offensive snaps
    target_share REAL,  -- % of team targets

    -- Game context
    game_script REAL,  -- Team lead/deficit (avg across game)
    team_score INTEGER,
    opp_score INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, player_name)
);

CREATE INDEX idx_logs_player ON player_game_logs(player_name);
CREATE INDEX idx_logs_date ON player_game_logs(game_date);
CREATE INDEX idx_logs_week ON player_game_logs(week_number);
```

#### **Table: game_schedule**
```sql
CREATE TABLE game_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_time TEXT,

    -- Vegas lines
    total REAL,  -- O/U points
    spread REAL,  -- Home team spread
    home_ml INTEGER,  -- Moneyline
    away_ml INTEGER,

    -- Derived (from total + spread)
    home_implied_points REAL,
    away_implied_points REAL,

    -- Pace context
    expected_pace REAL,  -- Plays per game (derived from team averages)

    -- Weather (CRITICAL for NFL!)
    weather_temp REAL,  -- Fahrenheit
    weather_wind REAL,  -- MPH
    weather_precip TEXT,  -- 'clear', 'rain', 'snow'
    is_dome BOOLEAN,  -- Indoor game

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, home_team, away_team)
);

CREATE INDEX idx_schedule_week ON game_schedule(week_number);
```

#### **Table: team_context**
```sql
CREATE TABLE team_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT NOT NULL,
    season TEXT NOT NULL,  -- '2024'
    week_number INTEGER NOT NULL,  -- Updated weekly

    -- Pace (plays per game)
    offensive_pace REAL,  -- Plays per game
    defensive_pace REAL,  -- Opponent plays per game allowed

    -- Defensive rankings (by position/stat)
    def_rank_pass_yards INTEGER,  -- 1-32
    def_rank_rush_yards INTEGER,  -- 1-32
    pass_yards_allowed_per_game REAL,
    rush_yards_allowed_per_game REAL,

    -- Advanced defense
    def_dvoa_pass REAL,  -- Defense-adjusted value over average (if available)
    def_dvoa_rush REAL,

    -- Positional defense (yards allowed to position)
    yards_allowed_to_wr1 REAL,  -- Top WR on opponent
    yards_allowed_to_wr2 REAL,
    yards_allowed_to_te REAL,
    yards_allowed_to_rb REAL,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team, season, week_number)
);

CREATE INDEX idx_team_context_week ON team_context(week_number);
```

#### **Table: short_week_tracker**
```sql
CREATE TABLE short_week_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    team TEXT NOT NULL,

    -- Rest days
    days_since_last_game INTEGER,  -- 3 (Thursday), 6 (normal), 7+ (bye week)
    is_short_week BOOLEAN,  -- Thursday game
    had_bye_week_last BOOLEAN,  -- Coming off bye

    -- Travel
    travel_distance REAL,  -- Miles
    timezone_change INTEGER,  -- Hours (-3 to +3)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, team)
);

CREATE INDEX idx_short_week ON short_week_tracker(week_number);
```

#### **Table: injury_reports**
```sql
CREATE TABLE injury_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'out', 'doubtful', 'questionable', 'probable'
    injury_type TEXT,  -- 'knee', 'hamstring', etc.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(report_date, player_name)
);

CREATE INDEX idx_injury_player ON injury_reports(player_name);
CREATE INDEX idx_injury_week ON injury_reports(week_number);
```

---

## 🎯 PROP TYPES & MODELING APPROACH

### **Priority 1: Receiving Yards (Continuous - Normal Distribution)**

**Most popular NFL prop!**

```python
# Normal distribution (like NHL shots)
def predict_receiving_yards(player_avg_yards, player_std, matchup_factor, line):
    """
    WR/TE receiving yards with matchup adjustments
    """
    adjusted_mean = player_avg_yards * matchup_factor
    prob_over = 1 - norm.cdf(line, adjusted_mean, player_std)

    # Cap probabilities (learning mode)
    prob_over = np.clip(prob_over, 0.30, 0.70)

    return prob_over
```

**Features (25+ total):**
```python
rec_yards_features = {
    # Player receiving ability
    'rec_yards_per_game_season': 68.5,
    'rec_yards_per_game_last_4': 82.3,  # Hot streak
    'yards_per_reception': 12.8,
    'std_rec_yards': 22.5,  # High variance!

    # Opportunity metrics (CRITICAL for NFL!)
    'targets_per_game': 8.5,
    'target_share': 0.26,  # 26% of team targets
    'snap_count_pct': 0.88,  # On field 88% of snaps
    'red_zone_target_share': 0.20,

    # Role
    'is_wr1': True,  # Top receiver on team
    'is_slot_receiver': False,
    'air_yards_share': 0.32,  # % of team air yards

    # QB Connection
    'qb_rating': 98.5,  -- QB quality
    'qb_pass_yards_per_game': 265.0,
    'qb_completion_pct': 0.665,

    # Matchup
    'opp_pass_def_rank': 28,  # 1-32 (32 = worst pass D)
    'opp_pass_yards_allowed': 265.5,
    'opp_coverage_type': 'zone',  # 'zone' or 'man'
    'opp_cb_rating': 95.2,  # Cornerback quality

    # Game context
    'home_away': 'away',
    'team_implied_total': 24.5,  # From Vegas
    'game_total': 47.5,  # High total = more passing
    'spread': -3.5,  # Underdog (trailing = more passes)

    # Weather (HUGE for passing!)
    'weather_temp': 72,  # Fahrenheit
    'weather_wind': 8,  # MPH (>15 hurts passing)
    'weather_precip': 'clear',
    'is_dome': False,

    # Rest
    'days_rest': 6,  # Normal week
    'is_short_week': False,  # Not Thursday game
    'coming_off_bye': False,
}
```

### **Priority 2: Receptions (Continuous - Poisson Distribution)**

**Popular prop, especially for PPR fantasy**

```python
def predict_receptions(player_avg_rec, matchup_factor, line):
    """
    Receptions modeled as count data (Poisson)
    Similar to NHL points O0.5
    """
    adjusted_lambda = player_avg_rec * matchup_factor

    # Poisson for discrete counts
    prob_over = 1 - poisson.cdf(line, adjusted_lambda)

    prob_over = np.clip(prob_over, 0.30, 0.70)
    return prob_over
```

**Features (20+ total):**
```python
receptions_features = {
    # Player volume
    'rec_per_game_season': 5.8,
    'rec_per_game_last_4': 6.5,
    'catch_rate': 0.72,  # Catches / targets

    # Opportunity
    'targets_per_game': 8.0,
    'target_share': 0.24,
    'snap_count_pct': 0.85,

    # Role (PPR-dependent players)
    'is_slot_receiver': True,  # Slot = more receptions, fewer yards
    'avg_depth_of_target': 8.5,  # Shorter routes = more catches

    # Matchup
    'opp_receptions_allowed_to_position': 6.2,
    'opp_pass_def_rank': 22,

    # Game context
    'game_total': 45.5,
    'spread': 7.5,  # Big underdog = more passing volume
    'team_implied_total': 19.0,
}
```

### **Priority 3: Rushing Yards (Continuous - Normal Distribution)**

**Popular for RBs**

```python
def predict_rushing_yards(player_avg_yards, matchup_factor, line):
    """
    RB rushing yards with game script adjustments
    """
    adjusted_mean = player_avg_yards * matchup_factor
    prob_over = 1 - norm.cdf(line, adjusted_mean, player_std)

    prob_over = np.clip(prob_over, 0.30, 0.70)
    return prob_over
```

**Features (20+ total):**
```python
rush_yards_features = {
    # Player rushing
    'rush_yards_per_game': 78.5,
    'rush_yards_last_4': 92.3,
    'yards_per_carry': 4.8,
    'std_rush_yards': 28.5,

    # Opportunity
    'carries_per_game': 16.5,
    'carry_share': 0.68,  # % of team carries
    'snap_count_pct': 0.72,

    # Role
    'is_bellcow': True,  # Feature back (70%+ snaps)
    'red_zone_carry_share': 0.55,

    # O-Line
    'oline_rank': 8,  # Team O-line rank
    'yards_before_contact': 2.8,

    # Matchup
    'opp_rush_def_rank': 25,  # Bad rush defense
    'opp_rush_yards_allowed': 135.2,
    'opp_yards_per_carry_allowed': 4.9,

    # Game script (CRITICAL!)
    'spread': -6.5,  # Favorite (more rushing if leading)
    'team_implied_total': 27.5,
    'game_total': 48.0,
}
```

### **Priority 4: Passing Yards/TDs (Continuous - Normal)**

**Popular QB props**

```python
def predict_passing_yards(qb_avg_yards, matchup_factor, line):
    """
    QB passing yards (Normal distribution)
    """
    adjusted_mean = qb_avg_yards * matchup_factor
    prob_over = 1 - norm.cdf(line, adjusted_mean, qb_std)

    prob_over = np.clip(prob_over, 0.30, 0.70)
    return prob_over
```

### **Priority 5: Anytime Touchdown (Binary Classification)**

**Like NHL Points O0.5!**

```python
def predict_anytime_td(player_features):
    """
    Binary classification: Will player score a TD?
    Use logistic regression or Poisson
    """
    # Historical TD rate
    td_rate = player_features['td_rate_season']  # TDs per game

    # Red zone usage (CRITICAL!)
    if player_features['red_zone_target_share'] > 0.20:
        td_rate *= 1.25

    # Matchup
    if player_features['opp_tds_allowed_to_position'] > 0.70:
        td_rate *= 1.15

    # Game script
    if player_features['team_implied_total'] > 26.0:
        td_rate *= 1.10

    # Convert to probability (Poisson)
    prob_td = 1 - poisson.cdf(0, td_rate)

    # Cap probability
    prob_td = np.clip(prob_td, 0.30, 0.70)

    return prob_td
```

---

## 🗓️ IMPLEMENTATION TIMELINE

### **Phase 1: Backtest Setup (Weeks 1-2) - Nov 10-23**

#### **Week 1 (Nov 10-16): Infrastructure**
```
✅ Database setup (7 tables)
✅ Config file
✅ Directory structure
✅ Basic utilities (db_utils, validation)

Time: 6-8 hours (spread across week)
```

#### **Week 2 (Nov 17-23): Backtest Validation**
```
✅ Fetch 2023 NFL season data (Sep 2023 - Feb 2024)
✅ Build receiving yards feature extractor
✅ Build statistical prediction model
✅ Backtest on 500+ player-game props
✅ Validate accuracy (target: 55-65%)
✅ Identify what works

Time: 10-12 hours (spread across week)
```

**Milestone:** Proven statistical model (like NHL 71% → 68%)

---

### **Phase 2: Live Deployment (Weeks 3-4) - Nov 24 - Dec 7**

#### **Week 3 (Nov 24-30): Weekly Automation**
```
✅ Build generate_predictions_weekly.py
✅ Build auto_grade_tuesday.py
✅ Test on Week 10 games (dry run)
✅ Go LIVE for Week 11 (Nov 17)

Time: 8-10 hours
```

#### **Week 4 (Dec 1-7): Live Monitoring**
```
✅ Weekly predictions + grading
✅ Monitor accuracy (target: 55-65%)
✅ Verify features storing correctly
✅ Make adjustments if needed

Time: 2 hours/week (weekly operations)
```

**Milestone:** System live and running smoothly!

---

### **Phase 3: Data Collection (Nov 2024 - Feb 2025)**

#### **Weekly Operations (Every Week)**
```
Tuesday Morning (9 AM):
✅ Grade last week's games (16 games)
✅ Review week's performance
✅ 1-2 hours

Sunday Morning (10 AM):
✅ Generate this week's predictions (16 games)
✅ Check injury reports
✅ Monitor accuracy trends
✅ 2-3 hours

Total: 3-5 hours per week
```

**Target:** 200-300 predictions/week × 12 weeks = 2,400-3,600 predictions
**Including Playoffs:** 3,000-4,000 predictions total

---

### **Phase 4: ML Training (August 2025)**

```
✅ Export 3,000-4,000 graded predictions
✅ Train XGBoost models (rec yards, rush yards, TDs)
✅ Feature importance analysis
✅ Hyperparameter tuning
✅ Validate on holdout set
✅ Deploy for 2025-26 season
```

**Target:** ML beats statistical baseline by 2-5%

---

## ⚙️ CONFIGURATION

### **nfl_config.py**

```python
import os
from datetime import datetime, timedelta

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "nfl_predictions.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Learning Mode Settings
LEARNING_MODE = True  # Conservative probabilities during data collection
PROBABILITY_CAP = (0.30, 0.70)  # Tighter than NHL (sharper NFL market)
MIN_GAMES_PLAYED = 5  # Player must have 5+ games (Week 6+)

# Prop Types (Start Simple, Expand Gradually)
PROP_TYPES = {
    'rec_yards': {
        'enabled': True,
        'distribution': 'normal',
        'min_rec_yards_pg': 30.0,  # Only predict for 30+ yards/game receivers
        'positions': ['WR', 'TE'],
    },
    'receptions': {
        'enabled': True,
        'distribution': 'poisson',
        'min_rec_pg': 3.0,
        'positions': ['WR', 'TE', 'RB'],
    },
    'rush_yards': {
        'enabled': True,
        'distribution': 'normal',
        'min_rush_yards_pg': 40.0,
        'positions': ['RB', 'QB'],
    },
    'pass_yards': {
        'enabled': False,  # Add later
        'distribution': 'normal',
        'positions': ['QB'],
    },
    'anytime_td': {
        'enabled': False,  # Add later
        'distribution': 'binary',
        'positions': ['WR', 'TE', 'RB'],
    },
}

# Player Selection
MIN_SNAP_COUNT_PCT = 0.50  # Must play 50%+ of snaps
MIN_TARGET_SHARE = 0.10  # Must get 10%+ of targets (for receivers)
MAX_PLAYERS_PER_WEEK = 150  # Total predictions (16 games × 8-10 players/game)

# API Settings
NFL_API = "https://api.sportsdata.io/v3/nfl"  # Or ESPN API
# Backup: Pro Football Reference

# Short Week Settings
SHORT_WEEK_PENALTY = 0.92  # -8% performance on Thursday games
COMING_OFF_BYE_BOOST = 1.05  # +5% performance after bye week

# Weather Thresholds (CRITICAL for NFL!)
WIND_THRESHOLD = 15  # MPH - significant passing impact
COLD_THRESHOLD = 32  # Fahrenheit - freezing
PRECIP_PENALTY = 0.90  # -10% in rain/snow

# Model Settings
MODEL_VERSION = "statistical_v1"
RANDOM_SEED = 42

# Season Info
SEASON = "2024"
SEASON_START = datetime(2024, 9, 5)  # Week 1
SEASON_END = datetime(2025, 1, 5)  # Week 18
PLAYOFFS_END = datetime(2025, 2, 9)  # Super Bowl
```

---

## 🎯 PLAYER SELECTION LOGIC

### **Weekly Player Selection**

```python
def select_players_for_predictions(week_number):
    """
    Select players to predict on for this week's games
    Focus on starters + high-snap players
    """
    games = fetch_games(week_number)
    selected_players = []

    for game in games:
        # Get both teams' rosters
        home_players = fetch_roster(game['home_team'])
        away_players = fetch_roster(game['away_team'])

        for player in (home_players + away_players):
            # Filter criteria
            if (player['snap_count_pct'] >= 0.50 and
                player['games_played'] >= 5 and
                player['is_starter']):

                # Check injury status
                if player['injury_status'] not in ['out', 'doubtful']:
                    selected_players.append(player)

    return selected_players  # Typically 120-150 players/week
```

### **Prop Selection Per Player**

```python
def select_props_for_player(player):
    """
    Determine which props to predict for this player
    Based on their position and role
    """
    props = []

    # Wide Receivers / Tight Ends
    if player['position'] in ['WR', 'TE']:
        if player['rec_yards_per_game'] >= 30.0:
            props.append('rec_yards')
        if player['rec_per_game'] >= 3.0:
            props.append('receptions')
        if player['red_zone_target_share'] >= 0.15:
            props.append('anytime_td')

    # Running Backs
    if player['position'] == 'RB':
        if player['rush_yards_per_game'] >= 40.0:
            props.append('rush_yards')
        if player['rec_per_game'] >= 3.0:
            props.append('receptions')
        if player['red_zone_touch_share'] >= 0.30:
            props.append('anytime_td')

    # Quarterbacks
    if player['position'] == 'QB':
        if player['is_starter']:
            props.append('pass_yards')
            props.append('pass_tds')

    return props  # Typically 2-3 props per player
```

---

## 🔥 CRITICAL NFL-SPECIFIC FEATURES

### **1. Game Script (MASSIVE Factor!)**

```python
game_script_adjustment = {
    # Receiving yards (more when trailing)
    'trailing_by_7+': 1.15,  # +15% to pass volume
    'leading_by_7+': 0.90,  # -10% (run out clock)

    # Rushing yards (more when leading)
    'trailing_by_7+': 0.85,  # -15% (abandon run)
    'leading_by_7+': 1.20,  # +20% (run out clock)

    # Derived from spread + game total
    # Example: -7 point favorite (likely leading) = more rushing
}

# Research shows:
# - Teams trailing by 2+ scores: 30% more pass attempts
# - Teams leading by 2+ scores: 40% more rush attempts
# - First half doesn't matter, second half is critical
```

**Why It Matters:** Can completely flip prop expectations!

### **2. Weather (HUGE for Passing!)**

```python
weather_adjustment = {
    # Wind (passing)
    'wind_15_20_mph': 0.92,  # -8% to pass yards
    'wind_20+_mph': 0.80,  # -20% to pass yards!

    # Cold (all stats)
    'temp_below_32': 0.93,  # -7% to all stats
    'temp_below_20': 0.85,  # -15% in extreme cold

    # Precipitation (all stats)
    'rain': 0.90,  # -10%
    'snow': 0.85,  # -15%

    # Dome (no weather impact)
    'is_dome': 1.00,
}
```

**Why It Matters:** 20 MPH wind can kill a passing prop!

### **3. Target Share / Snap Count (Opportunity)**

```python
opportunity_boost = {
    # WR1 with high target share
    'target_share_25+_pct': 1.20,  # +20% to baseline
    'target_share_20_25_pct': 1.10,  # +10%

    # Snap count changes (injury to teammate)
    'snap_increase_10+_pct': 1.15,  # More snaps = more opportunity

    # Example:
    # WR: 60 yards/game, 20% target share
    # Teammate WR1 injured: target share → 28%
    # Expected yards: 60 × 1.20 = 72 yards
}
```

**Why It Matters:** Find value when teammates are out!

### **4. Short Week (Thursday Games)**

```python
short_week_penalty = {
    'thursday_game': 0.92,  # -8% performance
    'sunday_after_monday': 0.95,  # -5% (short prep)
    'coming_off_bye': 1.05,  # +5% (extra rest)
}
```

**Why It Matters:** Thursday games = less prep + fatigue!

### **5. Home Field Advantage**

```python
home_field_boost = {
    'general': 1.03,  # +3% (similar to NHL)
    'dome_teams_outdoors': 0.93,  # -7% (Saints, Falcons on road)
    'cold_weather_teams': 1.08,  # +8% (GB, BUF in December)
}
```

---

## 🚀 WEEKLY WORKFLOW (Once Live)

### **Sunday Morning Routine (10:00 AM)**

```bash
cd NFL-Prediction-System-V1

# Generate this week's predictions (16 games)
python automation/generate_predictions_weekly.py --week 11

# Output:
# "Found 16 games for Week 11"
# "Selected 128 players for predictions"
# "Generated 312 predictions across receiving, rushing, TDs"
# "Predictions saved to database"

# Check injury reports (2 hours before games)
python fetchers/check_injury_updates.py

# Done! (2-3 hours total)
```

### **Tuesday Morning Routine (9:00 AM)**

```bash
cd NFL-Prediction-System-V1

# Grade last week's games (16 games)
python automation/auto_grade_tuesday.py --week 10

# Output:
# "Graded 298 predictions from Week 10"
# "Weekly accuracy: 61.4% (183/298)"
# "Season accuracy: 58.7% (1,245/2,122)"

# Done! (1-2 hours total)
```

---

## 📚 DATA SOURCES

### **Primary: NFL API / SportsData.io**

```
Endpoint: https://api.sportsdata.io/v3/nfl

✅ Player stats (traditional + advanced)
✅ Team stats (pace, defensive rankings)
✅ Game schedules
✅ Game results
✅ Snap counts, target share
✅ Injury reports

Note: Free tier available (500 requests/day)
```

### **Secondary: Pro Football Reference (Scraping)**

```
✅ Advanced metrics (air yards, yards after catch)
✅ Historical matchups
✅ Weather data
✅ Snap count %

Note: Respect robots.txt, rate limit
```

### **Vegas Lines: Covers.com or OddsAPI**

```
✅ Game totals (O/U)
✅ Spreads (for game script)
✅ Moneylines
✅ Player props (for comparison)

Free tier options available
```

### **Weather: Weather.gov API (Free)**

```
✅ Temperature
✅ Wind speed/direction
✅ Precipitation
✅ Updated hourly

Critical for NFL predictions!
```

---

## ⚠️ KNOWN CHALLENGES & SOLUTIONS

### **Challenge 1: Small Sample Size**

**Problem:** Only 17 games per season (vs 82 in NHL/NBA)

**Solution:**
```python
# Use multiple seasons for baseline (2022-2024)
# Weight recent games heavily (last 4 games = 50% weight)
# Focus on rate stats (yards/game, not totals)
```

### **Challenge 2: Game Script Volatility**

**Problem:** Blowouts change everything (abandon run/pass)

**Solution:**
```python
# Use spread as predictor (>7 = likely blowout)
# Model game script explicitly (trailing/leading)
# Be conservative on big spreads (>10 points)
```

### **Challenge 3: Injury Impact**

**Problem:** One injury can shift entire offense

**Solution:**
```python
# Check injury reports 2 hours before games
# Monitor practice participation (DNP, Limited, Full)
# Adjust target share when WR1/RB1 out
```

### **Challenge 4: Weather Unpredictability**

**Problem:** Weather changes game day morning

**Solution:**
```python
# Fetch weather 2 hours before kickoff
# Have "weather adjustment" model ready
# Be conservative in bad weather games
```

---

## 🎓 LEARNING FROM NHL/NBA SYSTEMS

### **What to Keep (Proven Winners)**

```
✅ Binary vs Continuous modeling approach
✅ Poisson/Normal distributions
✅ Feature storage (features_json)
✅ Temporal safety (no future data)
✅ Learning mode (probability capping)
✅ Weekly grading workflow
✅ player_game_logs continuous updates
✅ Validation scripts
✅ Database structure
```

### **What to Adapt (NFL-Specific)**

```
✅ Game script modeling (biggest NFL factor)
✅ Weather adjustments (doesn't exist in NBA/NHL much)
✅ Target share / opportunity shifts
✅ Short week tracking (Thursday games)
✅ Smaller sample size (17 games vs 82)
✅ Weekly rhythm (not daily like NHL/NBA)
```

---

## 📝 FILES TO CREATE (Priority Order)

### **Week 1: Foundation**
```
1. nfl_config.py
2. database/schema.sql
3. utils/db_utils.py
4. utils/validation.py
5. README.md
```

### **Week 2: Backtest**
```
6. fetchers/fetch_game_schedule.py
7. fetchers/fetch_player_stats.py
8. fetchers/fetch_team_stats.py
9. fetchers/fetch_weather.py
10. features/receiving_yards_extractor.py
11. models/statistical_predictions.py
12. automation/backtest_framework.py
```

### **Week 3: Live Deployment**
```
13. automation/generate_predictions_weekly.py
14. automation/auto_grade_tuesday.py
15. features/receptions_extractor.py
16. features/rushing_yards_extractor.py
17. fetchers/fetch_injury_reports.py
```

### **Week 4: Monitoring & Expansion**
```
18. automation/weekly_review.py
19. features/anytime_td_extractor.py (optional)
20. utils/discord_notifications.py (optional)
21. validation/calibration_monitor.py
```

---

## 📊 SUCCESS METRICS

### **Backtest Phase (Week 2)**
```
✅ Accuracy: 55-65% (realistic for NFL sharp market)
✅ Predictions: 500+ (2023 season sample)
✅ Grading Rate: 95%+ (fewer scratches than NHL/NBA)
✅ Feature Variety: 25+ unique probabilities
✅ Probability Range: Respects 30-70% cap
```

### **Live Collection Phase (Nov 2024 - Feb 2025)**
```
✅ Weekly Predictions: 200-300
✅ Grading Rate: 93%+ (injuries accounted for)
✅ Accuracy: 55-65% sustained
✅ Total Predictions: 3,000-4,000 generated
✅ Graded Predictions: 2,800+ for ML training
```

### **ML Training Phase (August 2025)**
```
✅ Training Samples: 2,800+ graded
✅ ML Accuracy: 58-68% (beat statistical baseline)
✅ Feature Importance: Game script, weather, target share validated
✅ Ready for 2025-26 season
```

---

## 🏁 SUCCESS DEFINITION

**System is successful if:**

1. **Backtest Validation (Week 2):** 55-65% accuracy on 2023 sample
2. **Live Launch (Week 4):** System running smoothly with weekly ops
3. **Data Collection (Nov-Feb):** 2,800+ graded predictions with features
4. **Sustained Accuracy:** 55-65% maintained through playoffs
5. **Data Quality:** 93%+ grading rate, features properly stored

**Long-term (2025-26 Season):**
- ML models deployed (beat statistical baseline)
- 58-68% accuracy sustained
- Finding 3-5% edges vs market
- Profitable at 5%+ ROI

---

## 💬 QUESTIONS FOR USER

Before implementing:

1. **Do you have NFL API access?** (SportsData.io or ESPN?)
2. **Which props to start with?** (Rec yards only, or add rushing/TDs?)
3. **Discord notifications?** (Want weekly accuracy alerts?)
4. **DraftKings/FanDuel account?** (To verify available props/lines)
5. **Start with backtest or go straight to live?** (Recommend backtest first)

---

## 🎯 HANDOFF TO IMPLEMENTATION

**Build this NFL system using the NHL V2 framework as the template.**

**Reference these NHL files for patterns:**
- `NHL_PREDICTION_SYSTEM_V2_BIBLE.md` - Overall methodology
- `statistical_predictions_v2.py` - Statistical modeling approach
- `binary_feature_extractor.py` - Feature extraction pattern (for anytime TD)
- `continuous_feature_extractor.py` - Feature extraction pattern (for yards/receptions)
- `v2_auto_grade_yesterday_v3.py` - Grading system pattern (adapt to weekly)
- `v2_config.py` - Configuration pattern

**NFL-Specific Emphasis:**
- Game script is CRITICAL (biggest NFL factor)
- Weather tracking is CRITICAL (unique to outdoor sports)
- Target share / opportunity metrics (more volatile than NHL/NBA)
- Weekly rhythm (not daily like NHL/NBA)
- Smaller sample size (careful with overfitting)

**TIMING: Week 10 of 18 - perfect for data collection through playoffs!** 🏈🚀

---

**END OF NFL IMPLEMENTATION PLAN**
