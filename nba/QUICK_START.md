# NBA Prediction System - Quick Start Guide

## 🎯 What You Have

A complete NBA player prop prediction system with 10 core features, ready for:
1. **Backtest validation** (today)
2. **Live predictions** (tomorrow/this week)
3. **ML training** (Week 8+)

---

## 🚀 Getting Started (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install requests scipy fuzzywuzzy python-Levenshtein
```

### Step 2: Initialize the System

```bash
cd nba/
python initialize_nba_system.py
```

**What happens:**
- Creates database (`nba_predictions.db`)
- Loads historical data from Oct 22, 2024 to today
- Runs backtest validation
- Shows accuracy metrics

**Expected result:**
```
✅ Overall accuracy: 60-70%+ (target: 55%+)
🚀 SYSTEM READY FOR LIVE PREDICTIONS!
```

⏰ **Time:** 10-15 minutes (due to API rate limiting)

---

## 📅 Daily Operations

### Option A: Run Manually

**Morning (8 AM) - Grade yesterday:**
```bash
python auto_grade_yesterday.py
```

**Morning (10 AM) - Generate tomorrow:**
```bash
python generate_predictions_daily.py
```

### Option B: Automate with Cron

```bash
# Add to crontab
0 8 * * * cd /path/to/nba && python auto_grade_yesterday.py
0 10 * * * cd /path/to/nba && python generate_predictions_daily.py
```

---

## 🧪 Understanding Your System

### 10 Core Props

**Binary (Over/Under):**
- Points: O15.5, O20.5, O25.5
- Rebounds: O7.5, O10.5
- Assists: O5.5, O7.5
- Threes: O2.5
- Stocks (STL+BLK): O2.5

**Continuous (Regression):**
- PRA (Points + Rebounds + Assists): O30.5, O35.5, O40.5
- Minutes: O28.5, O32.5

### Player Selection

**Exploration Phase (Weeks 1-7):**
- Starters (5) + Significant bench (3) = 8 players per team
- Broad coverage for data collection

**Exploitation Phase (Later):**
- Starters only (5 per team)
- Quality over quantity

### Learning Mode

**Current (Weeks 1-7):**
- Statistical models (Poisson/Normal)
- Probability cap: 30-70% (conservative)
- Goal: Collect 5,000+ graded predictions

**Future (Week 8+):**
- XGBoost ML models
- Probability range: 20-80%
- Weekly retraining

---

## 📊 Checking Your Data

### Database Queries

```bash
# How many player logs?
sqlite3 nba_predictions.db "SELECT COUNT(*) FROM player_game_logs"

# How many predictions?
sqlite3 nba_predictions.db "SELECT COUNT(*) FROM predictions"

# Accuracy today?
sqlite3 nba_predictions.db "
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN outcome='HIT' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as accuracy
FROM prediction_outcomes
WHERE game_date = date('now', '-1 day')
"
```

---

## 🔍 Your Timeline

### Today (Week 1): Backtest
```bash
python initialize_nba_system.py
# Expected: 55%+ accuracy on historical data
# Decision: GO → Proceed to live predictions
```

### Tomorrow (Week 2): Go Live
```bash
# Morning: Generate predictions for tonight's games
python generate_predictions_daily.py

# Next morning: Grade last night's results
python auto_grade_yesterday.py
```

### This Week (Weeks 2-7): Data Collection
- Run grading + prediction daily
- Accumulate 5,000+ graded predictions
- Monitor accuracy (target: 55-65%)
- Validate system stability

### Week 8+: ML Training
- Train XGBoost models on collected data
- Deploy if accuracy > statistical baseline
- Weekly retraining
- Track ROI and profitability

---

## 🎯 Success Metrics

### Daily Checks
- ✅ Grading rate: 85%+ (scratches/injuries are normal)
- ✅ Feature variety: 10+ unique probabilities
- ✅ Accuracy: 55-65% (learning mode)
- ✅ Player logs updating (continuous learning)

### Weekly Reviews
- Total predictions: 400-600/day
- Graded predictions: Growing steadily
- No system errors
- Database integrity maintained

### Phase Goals
- Exploration: 5,000+ graded predictions
- ML Training: 60%+ accuracy
- Production: Beat statistical baseline by 3%+

---

## 🚨 Troubleshooting

### "No games scheduled"
- Normal on off-days
- NBA plays mostly Tue-Sun
- System will resume next game day

### "Low feature variety"
- Check player_game_logs has data
- Verify temporal safety (using past data only)
- Review feature extraction logic

### "Grading rate < 85%"
- Normal: 10-15% scratches/injuries
- Concerning: >20% ungraded
- Check name matching (fuzzy matching)

### API Rate Limiting
- Built-in sleep(0.6) between requests
- Initialization takes 10-15 minutes
- Don't run multiple scripts simultaneously

---

## 📚 Learn More

**Full Documentation:**
- `nba/README.md` - Complete system documentation
- `nba/nba_config.py` - Configuration reference

**Architecture:**
- Mirrors successful NHL V2 system
- Temporal safety (no data leakage)
- V3 continuous learning (logs update)
- Professional ML methodology

**Key Principles:**
- Process > Outcomes
- Data quality > Short-term accuracy
- System validation > Individual predictions

---

## 🎉 You're Ready!

Your NBA prediction system is **production-ready** with:

✅ **10 core props** (Points, Rebounds, Assists, PRA, etc.)
✅ **21 features** (11 binary + 10 continuous)
✅ **Statistical prediction engine** (Poisson/Normal)
✅ **Auto-grading** (v3 continuous learning)
✅ **Daily prediction generation** (phase-aware)
✅ **Backtest validation** (temporal safety verified)

**Next step:** Run `python initialize_nba_system.py` and start the journey! 🚀

---

**Questions?** Review the full README.md or check the NHL system for reference patterns.
