# NHL Prediction System V2 - Dashboard

## Overview

A comprehensive web dashboard for monitoring and managing the NHL Prediction System V2. The dashboard provides real-time system health metrics, prediction browsing, ML feature tracking, and live sports scores.

## Features

### 📊 Dashboard Tab
- **System Health Monitoring**
  - Total predictions and grading rate
  - Feature capture statistics
  - Player game log counts
  - Database health metrics

- **Performance Analytics**
  - Overall accuracy tracking
  - Points vs Shots accuracy breakdown
  - Brier score (calibration metric)
  - Accuracy trend charts

- **Command Center**
  - One-click script execution
  - Grade yesterday's predictions
  - Generate tomorrow's predictions
  - Run diagnostics and system tests

- **Recent Predictions Table**
  - Last 10 predictions with outcomes
  - Real-time status updates

### 📝 Predictions Tab
- **Advanced Search & Filtering**
  - Filter by player name
  - Filter by prop type (points, shots, goals)
  - Filter by outcome (HIT/MISS)
  - Date range filtering
  - Search up to 100 predictions

- **Detailed Results Table**
  - All prediction details
  - Actual outcomes
  - Probability values

### 🧠 ML & Features Tab
- **Feature Statistics** (Pre-ML Phase)
  - Feature extraction statistics
  - Feature value distributions
  - Min/Max/Mean/StdDev for each feature

- **ML Feature Importance** (Week 10+)
  - Feature importance tracking over time
  - Model version comparison
  - Feature performance analysis

### 🏆 Live Scores Tab
- **ESPN Scoreboard Integration**
  - NHL scores (primary)
  - NBA scores
  - NFL scores
  - MLB scores
  - Real-time game status
  - Live score updates

## Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements_dashboard.txt
   ```

2. **Verify Database Location**
   The dashboard expects the database at:
   ```
   /home/user/nhl-prediction-v2/nhl_predictions_v2.db
   ```

## Usage

### Starting the Dashboard

```bash
python dashboard_app.py
```

The dashboard will start on: **http://localhost:5000**

### Access from Browser

1. Open your web browser
2. Navigate to: `http://localhost:5000`
3. The dashboard will load automatically

### Remote Access (Optional)

If you want to access the dashboard from another device on your network:

1. Find your machine's IP address:
   ```bash
   hostname -I
   ```

2. Access from another device:
   ```
   http://YOUR_IP_ADDRESS:5000
   ```

## Features Guide

### Command Center Buttons

| Button | Script | Purpose |
|--------|--------|---------|
| **Grade Yesterday** | `v2_auto_grade_yesterday_v3.py` | Grades yesterday's predictions against NHL results |
| **Generate Tomorrow** | `generate_predictions_daily.py` | Generates predictions for tomorrow's games |
| **Check Features** | `check_feature_storage.py` | Verifies features are being saved correctly |
| **Diagnose Features** | `diagnose_features.py` | Comprehensive feature diagnostics |
| **Run System Tests** | `test_fixed_system.py` | Runs all system validation tests |
| **Refresh Data** | - | Refreshes all dashboard metrics |

### Script Output

When you run a script via the Command Center:
- Output appears in the terminal-style box below the buttons
- Success (✓) or failure (✗) is indicated
- Dashboard automatically refreshes after successful script execution

### Auto-Refresh

The dashboard automatically refreshes metrics every 5 minutes to show the latest data.

## API Endpoints

The dashboard exposes the following API endpoints:

### System Metrics
- `GET /api/system-health` - System health metrics
- `GET /api/performance-metrics` - Accuracy and performance stats
- `GET /api/accuracy-trend?days=7` - Daily accuracy trend

### Predictions
- `GET /api/recent-predictions?limit=20` - Recent predictions
- `GET /api/predictions/search?...` - Search predictions with filters

### Features & ML
- `GET /api/feature-stats` - Feature extraction statistics
- `GET /api/feature-importance` - ML feature importance (Week 10+)

### Scoreboard
- `GET /api/scoreboard/hockey/nhl` - NHL scores
- `GET /api/scoreboard/basketball/nba` - NBA scores
- `GET /api/scoreboard/football/nfl` - NFL scores
- `GET /api/scoreboard/baseball/mlb` - MLB scores

### Commands
- `POST /api/run-script` - Execute allowed scripts

## Troubleshooting

### Dashboard won't start
```bash
# Check if port 5000 is already in use
lsof -i :5000

# Kill the process if needed
kill -9 <PID>

# Or use a different port in dashboard_app.py:
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Database not found
```bash
# Verify database location
ls -lh /home/user/nhl-prediction-v2/nhl_predictions_v2.db

# Update DB_PATH in dashboard_app.py if needed
```

### Scripts not executing
- Check that scripts exist in the project root
- Verify Python 3 is available: `python3 --version`
- Check script permissions: `chmod +x *.py`

### Scoreboard not loading
- Check internet connection
- ESPN API may be temporarily unavailable
- Try refreshing after a few seconds

## Development

### Debug Mode

The dashboard runs in debug mode by default, which:
- Auto-reloads on code changes
- Shows detailed error messages
- Enables Flask debugger

To disable debug mode (for production):
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

### Adding Custom Metrics

To add new metrics to the dashboard:

1. Add query function to `dashboard_app.py`:
   ```python
   def get_my_metric():
       conn = get_db_connection()
       # ... your query
       return data
   ```

2. Add API endpoint:
   ```python
   @app.route('/api/my-metric')
   def api_my_metric():
       return jsonify(get_my_metric())
   ```

3. Update frontend in `templates/index.html`:
   ```javascript
   function loadMyMetric() {
       fetch('/api/my-metric')
           .then(response => response.json())
           .then(data => {
               // Update UI
           });
   }
   ```

## Security Notes

- Dashboard is accessible to anyone who can reach the network/port
- Script execution is limited to a whitelist of safe scripts
- No authentication is currently implemented (local use only)
- For production use, consider adding:
  - Login authentication
  - HTTPS
  - Rate limiting
  - CSRF protection

## Tech Stack

- **Backend**: Flask (Python 3)
- **Frontend**: Bootstrap 5, Chart.js
- **Database**: SQLite
- **External APIs**: ESPN Scoreboard API

## Support

For issues or questions:
1. Check the main project documentation
2. Review the system status files
3. Run diagnostic scripts via the dashboard

---

**Version**: 1.0
**Last Updated**: November 2025
**Status**: Operational ✅
