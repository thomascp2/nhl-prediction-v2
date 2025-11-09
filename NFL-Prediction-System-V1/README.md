# 🏈 NFL PREDICTION SYSTEM V1
**Based on Proven NHL V2 Methodology (71% backtest → 68% live)**

---

## 🎯 PROJECT OVERVIEW

A statistical prediction system for NFL player props built on the proven NHL V2 framework. Focus on **data collection Year 1**, **ML training August 2025**, **profit Year 2**.

**Current Status:** ✅ **Foundation Complete** (Database, Features, Statistical Model)

**Target Accuracy:** 55-65% (realistic for sharp NFL market)

---

## 📦 WHAT'S BEEN BUILT

### ✅ Phase 1: Foundation (COMPLETE)

```
✅ Database Schema (7 tables + 3 views)
   - predictions
   - prediction_outcomes
   - player_game_logs
   - game_schedule
   - team_context
   - short_week_tracker
   - injury_reports

✅ Configuration System
   - nfl_config.py (learning mode, probability caps, prop types)

✅ Database Utilities
   - db_utils.py (save/retrieve predictions, game logs)
   - validation.py (temporal safety, feature validation)

✅ Feature Extractors (25+ features each)
   - receiving_yards_extractor.py (Normal distribution)
   - receptions_extractor.py (Poisson distribution)
   - rushing_yards_extractor.py (Normal distribution)

✅ Statistical Prediction Model
   - statistical_predictions.py (Poisson/Normal distributions)
   - Probability capping (30-70% learning mode)
   - Feature storage for ML training
```

---

## 🎯 ENABLED PROP TYPES

### Priority 1: Receiving Yards (O59.5+)
- **Distribution:** Normal
- **Position:** WR, TE
- **Features:** 25+ (target share, matchup, weather, game script)
- **Most Popular NFL Prop!**

### Priority 2: Receptions (O4.5+)
- **Distribution:** Poisson
- **Position:** WR, TE, RB
- **Features:** 20+ (catch rate, targets, game script)

### Priority 3: Rushing Yards (O79.5+)
- **Distribution:** Normal
- **Position:** RB, QB
- **Features:** 20+ (carries, O-line, game script - CRITICAL!)

### Coming Soon:
- Passing Yards (QB)
- Passing TDs (QB)
- Anytime TD (WR, TE, RB)

---

## 🏗️ SYSTEM ARCHITECTURE

```
NFL-Prediction-System-V1/
├── database/
│   ├── nfl_predictions.db (SQLite)
│   ├── schema.sql
│   └── create_database.py
│
├── features/
│   ├── receiving_yards_extractor.py
│   ├── receptions_extractor.py
│   └── rushing_yards_extractor.py
│
├── models/
│   └── statistical_predictions.py
│
├── automation/ (TODO: Week 2)
│   ├── generate_predictions_weekly.py
│   └── auto_grade_tuesday.py
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
├── nfl_config.py
└── README.md (this file)
```

---

## 🚀 QUICK START

### 1. Create Database

```bash
cd NFL-Prediction-System-V1
python database/create_database.py
```

**Output:**
```
✅ Database created successfully!
📊 Tables created (9): predictions, prediction_outcomes, player_game_logs, ...
👁️  Views created (3): v_predictions_with_outcomes, v_player_season_stats, ...
```

### 2. Test Feature Extraction

```python
from features.receiving_yards_extractor import extract_receiving_yards_features

# Example: Extract features for a WR
features = extract_receiving_yards_features(
    player_name="Justin Jefferson",
    team="MIN",
    opponent="GB",
    game_date="2024-11-17",
    week_number=11,
    position="WR",
    line=74.5,
    game_context={
        'total': 48.0,
        'spread': -3.5,
        'team_implied_points': 25.75,
        'home_away': 'home',
        'weather': {'temp': 65, 'wind': 8, 'precip': 'clear', 'is_dome': True}
    }
)

print(f"Features extracted: {len(features)} features")
print(f"  Rec yards/game (season): {features['rec_yards_per_game_season']}")
print(f"  Target share: {features['target_share']:.2%}")
print(f"  Opponent pass def rank: {features['opp_pass_def_rank']}")
```

### 3. Generate Prediction

```python
from models.statistical_predictions import generate_prediction

prediction = generate_prediction(
    player_name="Justin Jefferson",
    team="MIN",
    opponent="GB",
    game_date="2024-11-17",
    week_number=11,
    position="WR",
    prop_type="rec_yards",
    line=74.5,
    game_context={}  # Same as above
)

print(f"Prediction: {prediction['prediction']}")
print(f"Probability: {prediction['probability']:.2%}")
print(f"Confidence: {prediction['confidence_tier']}")
```

---

## 📊 CRITICAL NFL-SPECIFIC FEATURES

### 1. Game Script (BIGGEST FACTOR!)

```python
# Trailing by 7+ points = +15% pass volume, -15% rush volume
# Leading by 7+ points = -10% pass volume, +20% rush volume
# Derived from Vegas spread + game total
```

**Why:** Teams abandon the run when trailing, run out the clock when leading

### 2. Weather (HUGE for Passing!)

```python
# Wind 15+ MPH: -8% pass yards
# Wind 20+ MPH: -20% pass yards!
# Rain/snow: -10-15% all stats
# Cold < 32°F: -7% all stats
```

**Why:** Wind kills passing accuracy, weather favors rushing

### 3. Target Share / Opportunity

```python
# 25%+ target share = +20% to baseline
# WR1 injured = opportunity shift
# Snap count 50%+ required for prediction
```

**Why:** Volume = opportunity = production

### 4. Short Week (Thursday Games)

```python
# Thursday game: -8% performance
# Normal week: 6 days rest
# Coming off bye: +5% performance
```

**Why:** Less prep time + fatigue

### 5. Home Field Advantage

```python
# General: +3% all stats
# Dome teams outdoors: -7%
# Cold weather teams at home (Dec): +8%
```

---

## 🧮 STATISTICAL MODELS

### Normal Distribution (Continuous Stats)

Used for: **Receiving Yards**, **Rushing Yards**

```python
prob_over = 1 - norm.cdf(line, loc=adjusted_mean, scale=std_dev)

# Example:
# Player: 68 yards/game avg, 22 std dev
# Line: 59.5 yards
# Adjusted mean: 72 yards (after matchup/weather adjustments)
# P(X > 59.5) = 1 - norm.cdf(59.5, 72, 22) = 0.71
# Capped: 0.70 (learning mode max)
```

### Poisson Distribution (Count Data)

Used for: **Receptions**

```python
prob_over = 1 - poisson.cdf(line, mu=adjusted_lambda)

# Example:
# Player: 5.8 receptions/game avg
# Line: 4.5 receptions
# Adjusted lambda: 6.2 (after matchup adjustments)
# P(X > 4.5) = 1 - poisson.cdf(4.5, 6.2) = 0.68
```

---

## 📈 DATA COLLECTION TARGETS

### Year 1 (2024 Season)

```
Weeks: 10-18 (regular) + 19-22 (playoffs) = 12 weeks
Predictions per week: 200-300
Total predictions: 2,400-3,600
Graded predictions: 2,200-3,400 (93%+ grading rate)
Time investment: 3-5 hours per week
```

### Weekly Workflow

**Sunday Morning (10:00 AM):**
```bash
# Generate this week's predictions
python automation/generate_predictions_weekly.py --week 11

# Output: 250 predictions across 16 games
# Time: 2-3 hours (includes injury checks)
```

**Tuesday Morning (9:00 AM):**
```bash
# Grade last week's predictions
python automation/auto_grade_tuesday.py --week 10

# Output: Weekly accuracy + season accuracy
# Time: 1-2 hours
```

---

## ⚙️ CONFIGURATION

### Learning Mode (Year 1)

```python
LEARNING_MODE = True
PROBABILITY_CAP = (0.30, 0.70)  # Conservative

# Why? Build diverse training data for ML
# Don't want all 95% predictions
# Want probability variety for learning
```

### Player Selection Criteria

```python
MIN_GAMES_PLAYED = 5  # Week 6+
MIN_SNAP_COUNT_PCT = 0.50  # 50%+ snaps
MIN_TARGET_SHARE = 0.10  # 10%+ targets (receivers)
EXCLUDE_INJURY_STATUS = ['out', 'doubtful']
```

---

## 🎓 LESSONS FROM NHL V2

### What Works (Proven at 68.4% accuracy)

```
✅ Statistical distributions (Poisson, Normal)
✅ Binary vs Continuous modeling
✅ Feature richness (25-50 features)
✅ Temporal safety (no future data!)
✅ Learning mode (probability capping)
✅ player_game_logs continuous updates
✅ Feature storage (critical for ML training!)
```

### NFL-Specific Adaptations

```
✅ Game script modeling (biggest NFL factor)
✅ Weather adjustments (outdoor sport)
✅ Target share / opportunity tracking
✅ Short week penalties (Thursday games)
✅ Smaller sample size (17 games vs 82)
✅ Weekly rhythm (not daily like NHL/NBA)
```

---

## 📋 NEXT STEPS (Week 2)

### TODO: Automation Scripts

```bash
# 1. Weekly prediction generator
automation/generate_predictions_weekly.py

# 2. Tuesday grading script
automation/auto_grade_tuesday.py

# 3. Data fetchers
fetchers/fetch_game_schedule.py
fetchers/fetch_player_stats.py
fetchers/fetch_weather.py
```

### TODO: Backtest Validation

```bash
# Test on 2023 season (Week 10-18)
# Target: 55-65% accuracy
# Validate features, probability range
```

### TODO: Live Deployment

```bash
# Go live Week 11 (Nov 17, 2024)
# Generate + grade weekly
# Monitor accuracy
```

---

## 📊 SUCCESS METRICS

### Phase 1: Foundation (COMPLETE ✅)
```
✅ Database created
✅ Config system ready
✅ Feature extractors built (3 prop types)
✅ Statistical model implemented
✅ Utilities ready (db, validation)
```

### Phase 2: Backtest (Week 2)
```
⏳ Fetch 2023 season data
⏳ Generate 500+ backtest predictions
⏳ Validate 55-65% accuracy
⏳ Verify feature storage
⏳ Check probability distribution
```

### Phase 3: Live Deployment (Week 3-4)
```
⏳ Automation scripts working
⏳ Weekly predictions generated
⏳ Tuesday grading automated
⏳ 55-65% accuracy sustained
⏳ Features stored properly
```

### Phase 4: Data Collection (Nov-Feb)
```
⏳ 2,200-3,400 graded predictions
⏳ 93%+ grading rate
⏳ Feature variety validated
⏳ Data quality confirmed
⏳ Ready for ML training (August 2025)
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
# Learning mode: 30-70% only
# After ML training: 20-80%
# Prevents overconfidence
```

### Feature Validation

```python
# 25+ features per prediction
# No None values in numeric features
# Weather validated (temp, wind reasonable)
```

---

## 💬 SUPPORT

**Questions?** See the implementation plans:
- `NFL_IMPLEMENTATION_PLAN.md` - Complete 4-phase plan
- `MULTI_SPORT_COMPARISON.md` - NHL/NBA/NFL comparison

**Issues?** Check configuration:
- `nfl_config.py` - All system settings
- Database schema: `database/schema.sql`

---

## 🏆 PROJECT GOALS

**Year 1 (2024-25 Season):**
- ✅ Build foundation (DONE!)
- ⏳ Validate backtest (55-65% accuracy)
- ⏳ Deploy live (Week 11+)
- ⏳ Collect 2,200+ graded predictions

**Year 2 (2025-26 Season):**
- ML training (August 2025)
- Deploy ML models (beat statistical baseline)
- Target 58-68% accuracy
- Begin profit phase (5-10% ROI)

**Year 3 (2026-27 Season):**
- Optimize models
- Scale bankroll
- Expand prop types
- 10%+ sustained ROI

---

## 📖 METHODOLOGY

Based on proven NHL V2 framework:
- **Statistical foundations** (not arbitrary rules)
- **Temporal safety** (no data leakage)
- **Binary vs Continuous** modeling
- **Feature richness** (25-50 features)
- **Learning mode** (diverse training data)
- **Process integrity** (data quality over quick wins)

**These principles work across ALL sports!**

---

**Built with ❤️ by the team that brought you 68.4% NHL accuracy** 🏒🏈

---

**Last Updated:** November 9, 2024
**System Version:** 1.0.0
**Status:** Foundation Complete ✅
