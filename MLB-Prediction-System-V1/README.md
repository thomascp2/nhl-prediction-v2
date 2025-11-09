# ⚾ MLB PREDICTION SYSTEM V1
**Based on Proven NHL V2 Methodology (71% backtest → 68% live)**

---

## 🎯 PROJECT OVERVIEW

A statistical prediction system for MLB player props built on the proven NHL V2 framework. **Backtest on 2024 season**, **go live Opening Day 2025 (April)**, collect data all season, **train ML models October 2025**.

**Current Status:** ✅ **Foundation Complete** (Database, Features, Statistical Model)

**Target Accuracy:** 58-62% (realistic for sharp MLB market)

**Opening Day:** March 27, 2025 🎊

---

## 📦 WHAT'S BEEN BUILT

### ✅ Phase 1: Foundation (COMPLETE)

```
✅ Database Schema (5 tables + 4 views)
   - predictions
   - prediction_outcomes
   - player_game_logs (batters + pitchers combined)
   - game_schedule (with weather!)
   - park_factors (pre-loaded with 9 ballparks)

✅ Configuration System
   - mlb_config.py (learning mode, probability caps, prop types)
   - Park factors (Coors Field = 1.25 runs factor!)
   - Platoon adjustments (L/R splits)
   - Weather adjustments (temp, wind direction)

✅ Database Utilities
   - db_utils.py (save/retrieve predictions, game logs)
   - validation.py (temporal safety, feature validation)

✅ Feature Extractors (15+ features each)
   - pitcher_strikeouts_extractor.py (Poisson distribution)
   - batter_hits_extractor.py (Binary classification)
   - batter_total_bases_extractor.py (Poisson distribution)

✅ Statistical Prediction Model
   - statistical_predictions.py (Poisson/Binary distributions)
   - Probability capping (35-65% learning mode)
   - Feature storage for ML training
```

---

## 🎯 ENABLED PROP TYPES

### Priority 1: Pitcher Strikeouts (O5.5+)
- **Distribution:** Poisson
- **Most Popular MLB Prop!**
- **Features:** 15+ (K/9, opponent K rate, park factor, weather)

### Priority 2: Batter Hits (O0.5)
- **Distribution:** Binary (Yes/No)
- **Like NHL Points O0.5**
- **Features:** 15+ (batting avg, platoon splits, park factor)

### Priority 3: Batter Total Bases (O1.5+)
- **Distribution:** Poisson
- **Total Bases = 1B + 2×2B + 3×3B + 4×HR**
- **Features:** 15+ (power stats, park factor, weather)

### Coming Soon (Phase 2):
- Pitcher Earned Runs
- Batter Home Runs
- Batter RBIs
- Pitcher Walks

---

## 🏗️ SYSTEM ARCHITECTURE

```
MLB-Prediction-System-V1/
├── database/
│   ├── mlb_predictions.db (SQLite)
│   ├── schema.sql
│   └── create_database.py
│
├── features/
│   ├── pitcher_strikeouts_extractor.py
│   ├── batter_hits_extractor.py
│   └── batter_total_bases_extractor.py
│
├── models/
│   └── statistical_predictions.py
│
├── automation/ (TODO: Week 2-4)
│   ├── generate_predictions_daily.py
│   └── auto_grade_yesterday.py
│
├── fetchers/ (TODO: Week 2)
│   ├── fetch_game_schedule.py
│   ├── fetch_player_stats.py
│   └── fetch_weather.py
│
├── utils/
│   ├── db_utils.py
│   └── validation.py
│
├── mlb_config.py
└── README.md (this file)
```

---

## 🚀 QUICK START

### 1. Create Database

```bash
cd MLB-Prediction-System-V1
python database/create_database.py
```

**Output:**
```
✅ Database created successfully!
📊 Tables created (7)
👁️  Views created (4)
⚾ Park factors loaded: 9 ballparks
```

### 2. Test Feature Extraction

```python
from features.pitcher_strikeouts_extractor import extract_pitcher_strikeouts_features

# Example: Extract features for a starting pitcher
features = extract_pitcher_strikeouts_features(
    pitcher_name="Gerrit Cole",
    team="NYY",
    opponent="BOS",
    game_date="2025-04-15",
    pitcher_hand="R",
    line=6.5,
    game_context={
        'park_name': 'Yankee Stadium',
        'total': 8.5,
        'team_implied_runs': 4.5,
        'home_away': 'home',
        'weather': {'temperature': 68, 'wind_speed': 6, 'conditions': 'clear'}
    }
)

print(f"Features extracted: {len(features)} features")
print(f"  K/9 (season): {features['k_per_9_season']}")
print(f"  K/9 (last 5): {features['k_per_9_last_5']}")
print(f"  Park K factor: {features['park_k_factor']}")
```

### 3. Generate Prediction

```python
from models.statistical_predictions import generate_prediction

prediction = generate_prediction(
    player_name="Gerrit Cole",
    player_type="pitcher",
    team="NYY",
    opponent="BOS",
    game_date="2025-04-15",
    prop_type="pitcher_strikeouts",
    line=6.5,
    player_hand="R",
    game_context={}  # Same as above
)

print(f"Prediction: {prediction['prediction']}")
print(f"Probability: {prediction['probability']:.2%}")
print(f"Confidence: {prediction['confidence_tier']}")
```

---

## 🔍 CRITICAL MLB-SPECIFIC FEATURES

### 1. Park Factors (HUGE in Baseball!)

```python
park_factors = {
    'Coors Field': {  # Colorado Rockies
        'runs_factor': 1.25,  # 25% more runs!
        'home_runs_factor': 1.30,
        'hits_factor': 1.20,
        'strikeouts_factor': 0.95,
    },
    'Oracle Park': {  # San Francisco Giants
        'runs_factor': 0.85,  # 15% fewer runs
        'home_runs_factor': 0.70,  # Very hard to hit HRs
        'hits_factor': 0.95,
        'strikeouts_factor': 1.05,
    },
}
```

**Why:** Coors Field can turn a 5.5 K pitcher into a 4.5 K pitcher!

### 2. Platoon Splits (Lefty vs Righty - CRITICAL!)

```python
platoon_adjustments = {
    'R_vs_R': 0.95,  # Right batter vs Right pitcher (slight disadvantage)
    'R_vs_L': 1.08,  # Right batter vs Left pitcher (ADVANTAGE!)
    'L_vs_R': 1.05,  # Left batter vs Right pitcher (advantage)
    'L_vs_L': 0.92,  # Left batter vs Left pitcher (disadvantage)
}
```

**Why:** Can swing hit probability by 15-20%!

### 3. Weather (Affects Ball Flight!)

```python
weather_adjustments = {
    'hot_weather': {  # 85°F+
        'runs_boost': 1.08,
        'home_runs_boost': 1.12,  # Ball flies farther!
    },
    'cold_weather': {  # <55°F
        'strikeouts_boost': 1.04,  # Harder to see ball
    },
    'wind_out_to_cf': {
        'home_runs_boost': 1.15,  # +15% to HRs!
    },
}
```

**Why:** Wind blowing out can boost home runs by 15%!

---

## 🧮 STATISTICAL MODELS

### Poisson Distribution (Pitcher Strikeouts, Total Bases)

```python
prob_over = 1 - poisson.cdf(line, mu=adjusted_lambda)

# Example:
# Pitcher: 6.2 K/start avg
# Line: 5.5 strikeouts
# Adjusted lambda: 6.5 (after opponent/park adjustments)
# P(K > 5.5) = 1 - poisson.cdf(5.5, 6.5) = 0.62
# Capped: 0.62 (within learning mode 35-65%)
```

### Binary Classification (Batter Hits)

```python
prob_hit = calculate_hit_probability(features)
# Includes: batting avg, platoon splits, park factor, weather

# Example:
# Batter: .285 avg, hot streak (last 10: .310)
# vs LHP (platoon advantage): +8%
# Park factor (Coors): +20%
# Final probability: 0.72 → capped to 0.65
```

---

## 📈 DATA COLLECTION TARGETS

### Year 1 (2025 Season)

```
Games per day: 12-15 (162-game season)
Predictions per day: 400-600 (pitchers + batters)
Season length: 180 days (Mar 27 - Sep 28)
Total predictions: 72,000-108,000
Graded predictions: 68,000+ (95% grading rate)
Time investment: 15-20 min per day
```

### Daily Workflow

**Morning (9:00 AM):**
```bash
# 1. Grade yesterday's games
python automation/auto_grade_yesterday.py

# 2. Generate today's predictions
python automation/generate_predictions_daily.py

# Done! (15-20 minutes)
```

---

## ⚙️ CONFIGURATION

### Learning Mode (Year 1)

```python
LEARNING_MODE = True
PROBABILITY_CAP = (0.35, 0.65)  # More conservative than NHL (sharper market)

# Why? MLB betting market is VERY efficient
# Need diverse training data for ML
# Don't want all 95% predictions
```

### Player Selection Criteria

```python
# Pitchers
MIN_PITCHER_K_RATE = 7.0  # K/9 innings
MIN_PITCHER_GAMES_STARTED = 5
MIN_PITCHER_PITCH_COUNT = 85
MAX_PITCHER_ERA = 5.00

# Batters
MIN_BATTER_AVG = 0.230
MIN_BATTER_GAMES = 20
MAX_LINEUP_POSITION = 6  # Top 6 in order
MIN_AT_BATS_PER_GAME = 3.5
```

---

## 🎓 LESSONS FROM NHL V2

### What Works (Proven at 68.4% accuracy)

```
✅ Statistical distributions (Poisson, Binary)
✅ Feature richness (15-25 features per prop)
✅ Temporal safety (no future data!)
✅ Learning mode (probability capping)
✅ player_game_logs continuous updates
✅ Feature storage (critical for ML training!)
```

### MLB-Specific Adaptations

```
✅ Park factors (bigger impact than NHL home ice)
✅ Platoon splits (doesn't exist in NHL)
✅ Weather (affects ball flight)
✅ Pitcher vs batter matchups
✅ Sharper market (more conservative caps: 35-65%)
✅ Two player types (pitchers AND batters)
```

---

## 📋 NEXT STEPS (Week 2-4)

### TODO: Data Fetchers (Week 2)

```bash
fetchers/fetch_game_schedule.py  # MLB Stats API
fetchers/fetch_player_stats.py    # Batting/pitching stats
fetchers/fetch_weather.py         # OpenWeather API
```

### TODO: Backtest Validation (Week 3-4)

```bash
# Test on 2024 season (April-October)
# Target: 58-62% accuracy
# Validate features, probability range
# 2,000+ predictions on historical data
```

### TODO: Daily Automation (Week 5-8)

```bash
automation/generate_predictions_daily.py
automation/auto_grade_yesterday.py
automation/weekly_review.py
```

---

## 📊 SUCCESS METRICS

### Phase 1: Foundation (COMPLETE ✅)
```
✅ Database created (5 tables + 4 views)
✅ Config system ready
✅ Feature extractors built (3 prop types)
✅ Statistical model implemented
✅ Utilities ready (db, validation)
✅ Park factors pre-loaded (9 ballparks)
```

### Phase 2: Backtest (Week 3-4)
```
⏳ Fetch 2024 season data (April-October)
⏳ Generate 2,000+ backtest predictions
⏳ Validate 58-62% accuracy
⏳ Verify feature storage
⏳ Check probability distribution
```

### Phase 3: Live Deployment (Opening Day 2025)
```
⏳ Automation scripts working
⏳ Daily predictions generated
⏳ Daily grading automated
⏳ 58-62% accuracy sustained
⏳ Features stored properly
```

### Phase 4: Data Collection (April-Sept 2025)
```
⏳ 68,000+ graded predictions
⏳ 95%+ grading rate
⏳ Feature variety validated
⏳ Data quality confirmed
⏳ Ready for ML training (October 2025)
```

---

## 🔬 VALIDATION & SAFETY

### Temporal Safety (CRITICAL!)

```python
# NO FUTURE DATA LEAKAGE
# Feature extraction date < game date
# Only use data available before game
```

### Probability Validation

```python
# Learning mode: 35-65% only
# After ML training: 30-70%
# Prevents overconfidence in sharp market
```

### Park Factors Pre-Loaded

```python
# 9 ballparks already in database:
# - Coors Field (extreme hitter's park)
# - Oracle Park (extreme pitcher's park)
# - Yankee Stadium, Fenway Park, etc.
```

---

## 💬 SUPPORT

**Questions?** See the implementation plan:
- `MLB_IMPLEMENTATION_PLAN.md` (in parent directory)
- `MULTI_SPORT_COMPARISON.md` - NHL/NBA/NFL/MLB comparison

**Issues?** Check configuration:
- `mlb_config.py` - All system settings
- Database schema: `database/schema.sql`

---

## 🏆 PROJECT GOALS

**Year 1 (2024-25 Off-Season + 2025 Season):**
- ✅ Build foundation (DONE!)
- ⏳ Backtest on 2024 season (58-62% accuracy)
- ⏳ Deploy live Opening Day 2025
- ⏳ Collect 68,000+ graded predictions

**Year 2 (2025 Off-Season):**
- ML training (October 2025)
- Deploy ML models (beat statistical baseline)
- Target 60-65% accuracy
- Begin profit phase (3-5% ROI)

**Year 3 (2026 Season):**
- Optimize models
- Scale bankroll
- Expand prop types
- 8%+ sustained ROI

---

## 📖 METHODOLOGY

Based on proven NHL V2 framework:
- **Statistical foundations** (Poisson/Binary, not rules)
- **Temporal safety** (no data leakage)
- **Feature richness** (15-25 features per prop)
- **Learning mode** (diverse training data)
- **Sport-specific adaptations** (park factors, platoon splits, weather)
- **Process integrity** (data quality over quick wins)

**These principles work across ALL sports!**

---

**Built with ❤️ by the team that brought you 68.4% NHL accuracy** 🏒⚾

---

**Last Updated:** November 9, 2024
**System Version:** 1.0.0
**Status:** Foundation Complete ✅
**Opening Day:** March 27, 2025 🎊
