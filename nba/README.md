# NBA Prediction System V1

Professional-grade NBA player prop prediction system. Built alongside the successful NHL prediction system with proven architecture.

**Status:** ✅ Ready for initialization
**Season:** 2024-2025
**Target:** 55%+ accuracy on player props

---

## 🎯 System Overview

### Core Features (10 Props)

**Binary Props:**
- Points O15.5, O20.5, O25.5
- Rebounds O7.5, O10.5
- Assists O5.5, O7.5
- Threes O2.5
- Stocks (STL+BLK) O2.5

**Continuous Props:**
- PRA (Points + Rebounds + Assists) O30.5, O35.5, O40.5
- Minutes O28.5, O32.5

### Architecture

```
nba/
├── nba_config.py                  # Central configuration
├── setup_database.py              # Database schema setup
├── initialize_nba_system.py       # One-time initialization
│
├── data_fetchers/
│   └── nba_stats_api.py          # NBA Stats API client
│
├── features/
│   ├── binary_feature_extractor.py    # 11 binary features
│   └── continuous_feature_extractor.py # 10 continuous features
│
├── statistical_predictions.py     # Prediction engine
├── auto_grade_yesterday.py        # Daily grading (8 AM)
├── generate_predictions_daily.py  # Daily predictions (10 AM)
├── load_historical_data.py        # Historical data loader
└── run_backtest.py               # Backtest validation
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install requests scipy fuzzywuzzy python-Levenshtein
```

### 2. Initialize System

```bash
cd nba/
python initialize_nba_system.py
```

This will:
- Create database schema
- Load 2024-2025 season data (to date)
- Run backtest validation
- Verify accuracy >= 55%

**Note:** Initialization takes 10-15 minutes due to API rate limiting.

### 3. Daily Operations

**Morning (8 AM) - Grade yesterday's games:**
```bash
python auto_grade_yesterday.py
```

**Morning (10 AM) - Generate tomorrow's predictions:**
```bash
python generate_predictions_daily.py
```

---

## 📊 Data Sources

### 1. NBA Stats API (stats.nba.com)
- Game schedules
- Box scores
- Player game logs
- **Rate limit:** ~100 requests/minute

### 2. Covers.com (Future)
- Betting lines
- Odds movement
- Market data

---

## 🧪 Feature Engineering

### Binary Features (11 total)

For props like Points O15.5, Rebounds O7.5, etc.

1. **Season success rate** - % of games over line
2. **L20 success rate** - Last 20 games
3. **L10 success rate** - Last 10 games
4. **L5 success rate** - Last 5 games
5. **L3 success rate** - Last 3 games
6. **Current streak** - Consecutive overs/unders
7. **Max streak** - Longest streak this season
8. **Trend slope** - Improving or declining
9. **Home/Away split** - Performance difference
10. **Games played** - Sample size
11. **Insufficient data flag** - < 5 games

### Continuous Features (10 total)

For props like PRA, Minutes, etc.

1. **Season average**
2. **L10 average**
3. **L5 average**
4. **Season std deviation**
5. **L10 std deviation**
6. **Trend slope** - Linear regression
7. **Trend acceleration** - 2nd derivative
8. **Average minutes** - Playing time
9. **Home/Away split**
10. **Consistency score** - Inverse of CV

---

## 🎲 Prediction Methodology

### Learning Phase (Weeks 1-7)

**Statistical Models:**
- **Binary:** Poisson-based with feature adjustments
- **Continuous:** Normal distribution with trend adjustments
- **Probability cap:** 30-70% (conservative during data collection)

### ML Phase (Week 8+)

**XGBoost Models:**
- Binary classifier for Over/Under props
- Regressor for continuous props
- Weekly retraining
- Feature importance tracking

---

## 📈 Timeline & Phases

### Week 1 (Today)
**Backtest Validation**
- Load historical data (Oct 22 - today)
- Run backtest on 2+ weeks of data
- Target: 55%+ accuracy
- Decision: GO/NO-GO

### Weeks 2-7 (Live Data Collection)
**Exploration Phase**
- Players: Starters (5) + Significant bench (3) = 8 per team
- Daily predictions: 400-600
- Daily grading: Auto-grade yesterday
- Target: 5,000+ graded predictions

### Week 8+ (ML Training)
**Production Phase**
- Train XGBoost models
- Deploy if accuracy > statistical baseline
- Expand probability range to 20-80%
- Weekly retraining

---

## 🗄️ Database Schema

### Tables

**games**
- game_id, game_date, home_team, away_team
- home_score, away_score, status

**player_game_logs** (V3 continuous learning!)
- game_id, game_date, player_name, team
- minutes, points, rebounds, assists, steals, blocks
- pra, stocks (derived stats)

**predictions**
- game_id, game_date, player_name, team
- prop_type, line, prediction, probability
- All 21 features (11 binary + 10 continuous)

**prediction_outcomes**
- prediction_id, actual_value, outcome (HIT/MISS)
- match_tier, match_score (fuzzy matching)

---

## 🎯 Success Criteria

### Backtest (Week 1)
- Total predictions: 500+ ✅
- Overall accuracy: 55%+ ✅
- Points accuracy: 55%+ ✅
- Rebounds accuracy: 55%+ ✅
- Assists accuracy: 55%+ ✅

### Data Collection (Weeks 2-7)
- Grading rate: 85%+ (scratches/injuries unavoidable)
- Feature variety: 10+ unique probabilities
- Accuracy: 55-65% (learning mode)
- Total predictions: 5,000+

### ML Training (Week 8+)
- Beat statistical baseline by 3%+
- Feature importance validated
- Consistent 60%+ accuracy

---

## 🔧 Configuration

**nba_config.py:**
```python
# Database
DB_PATH = "nba_predictions.db"

# Learning mode
LEARNING_MODE = True
PROBABILITY_CAP = (0.30, 0.70)

# Season
SEASON = "2024-25"
DATA_COLLECTION_START = "2024-10-22"

# Player classification
STARTERS_COUNT = 5
SIGNIFICANT_BENCH_COUNT = 3
```

---

## 📚 Key Principles

### 1. Temporal Safety (SACRED)
- **Never use future data**
- All features computed from data BEFORE game_date
- Backtest validates no data leakage

### 2. Binary vs Continuous
- Points, Rebounds, Assists = Binary events
- PRA, Minutes = Continuous values
- Different features, different models

### 3. Continuous Learning (V3)
- Auto-grading updates player_game_logs
- Fresh data for next day's predictions
- Model learns from new games

### 4. Process > Outcomes
- System validation > individual predictions
- Grading rate > lucky hits
- Data quality > short-term accuracy

---

## 🔄 Daily Workflow

### Morning (8:00 AM)
```bash
python auto_grade_yesterday.py
```

**What it does:**
1. Fetches NBA Stats API results for yesterday
2. Matches predictions to actual stats (fuzzy matching)
3. Saves outcomes to prediction_outcomes
4. **Updates player_game_logs** (v3 continuous learning!)
5. Calculates accuracy metrics
6. Discord notification (optional)

### Morning (10:00 AM)
```bash
python generate_predictions_daily.py
```

**What it does:**
1. Auto-detects tomorrow's date
2. Determines phase (exploration or exploitation)
3. Gets games from NBA Stats API
4. For each team, queries players with history
5. Calls statistical prediction engine
6. Saves to predictions table
7. Verifies feature variety (>10 unique probs)
8. Discord notification (optional)

---

## 🧰 Utility Scripts

### Load Historical Data
```bash
# Load last 2 weeks
python load_historical_data.py 2

# Load custom range
python load_historical_data.py 2024-10-22 2024-11-09

# Load full season
python load_historical_data.py
```

### Run Backtest
```bash
# Backtest last 2 weeks
python run_backtest.py

# Backtest custom range
python run_backtest.py 2024-10-22 2024-11-09
```

### Database Check
```bash
sqlite3 nba_predictions.db "SELECT COUNT(*) FROM player_game_logs"
sqlite3 nba_predictions.db "SELECT COUNT(*) FROM predictions"
sqlite3 nba_predictions.db "SELECT COUNT(*) FROM prediction_outcomes"
```

---

## 🚨 Known Limitations

### Scratched Players
- 10-15% of predictions won't grade (players scratched/injured)
- This is EXPECTED NBA behavior
- Not a system problem

### API Rate Limiting
- NBA Stats API: ~100 requests/minute
- Historical data load takes 10-15 minutes
- Built-in sleep(0.6) for rate limiting

### Name Matching
- Fuzzy matching handles most variations
- 5-tier system (exact → partial)
- Requires 80%+ match confidence

---

## 📞 Support

**Documentation:**
- `/nba/README.md` - This file
- `/nba/nba_config.py` - Configuration reference

**Discord Notifications:**
Set environment variable:
```bash
export DISCORD_WEBHOOK_URL="your_webhook_url"
```

---

## 🎉 Final Notes

This NBA prediction system mirrors the proven NHL V2 architecture:

✅ **Temporal safety** (no data leakage)
✅ **V3 continuous learning** (player logs update)
✅ **Feature extraction** (binary + continuous)
✅ **Statistical baseline** (Weeks 1-7)
✅ **ML training path** (Week 8+)
✅ **Professional methodology** (backtest → collect → train → deploy)

**Built for systems thinkers who value process integrity over outcomes.**

---

**Last Updated:** 2025-11-09
**Version:** 1.0
**Status:** Ready for initialization 🚀
