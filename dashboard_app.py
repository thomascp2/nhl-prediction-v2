#!/usr/bin/env python3
"""
NHL Prediction System V2 - Dashboard Application
=================================================

Flask web dashboard for monitoring and managing the NHL prediction system.

Features:
- System health monitoring
- Command center (run scripts via buttons)
- Prediction browser
- ML feature importance tracking
- ESPN scoreboard integration
- Performance analytics

Usage:
    python dashboard_app.py

    Then open browser to: http://localhost:5000
"""

import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import json
import requests

# Configuration
PROJECT_ROOT = Path(__file__).parent
DB_PATH = Path(r"C:\Users\thoma\NHL-Model-Rebuild-V2\database\nhl_predictions_v2.db")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nhl-prediction-v2-dashboard'
app.config['TEMPLATES_AUTO_RELOAD'] = True


# ============================================================================
# DATABASE QUERIES
# ============================================================================

def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_system_health():
    """Get system health metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total predictions
    cursor.execute("SELECT COUNT(*) as count FROM predictions")
    total_predictions = cursor.fetchone()['count']

    # Graded predictions
    cursor.execute("SELECT COUNT(*) as count FROM prediction_outcomes")
    graded_predictions = cursor.fetchone()['count']

    # Player game logs
    cursor.execute("SELECT COUNT(*) as count FROM player_game_logs")
    player_logs = cursor.fetchone()['count']

    # Unique players
    cursor.execute("SELECT COUNT(DISTINCT player_name) as count FROM predictions")
    unique_players = cursor.fetchone()['count']

    # Feature variety (unique probabilities)
    cursor.execute("""
        SELECT COUNT(DISTINCT probability) as count
        FROM predictions
        WHERE probability IS NOT NULL
    """)
    feature_variety = cursor.fetchone()['count']

    # Predictions with features
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM predictions
        WHERE features_json IS NOT NULL AND features_json != ''
    """)
    predictions_with_features = cursor.fetchone()['count']

    # Database size
    db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

    conn.close()

    grading_rate = (graded_predictions / total_predictions * 100) if total_predictions > 0 else 0
    feature_capture_rate = (predictions_with_features / total_predictions * 100) if total_predictions > 0 else 0

    return {
        'total_predictions': total_predictions,
        'graded_predictions': graded_predictions,
        'grading_rate': round(grading_rate, 1),
        'player_logs': player_logs,
        'unique_players': unique_players,
        'feature_variety': feature_variety,
        'predictions_with_features': predictions_with_features,
        'feature_capture_rate': round(feature_capture_rate, 1),
        'db_size_mb': round(db_size_mb, 2)
    }


def get_performance_metrics():
    """Get accuracy and performance metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Overall accuracy
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits
        FROM prediction_outcomes
    """)
    result = cursor.fetchone()
    total = result['total']
    hits = result['hits']
    overall_accuracy = (hits / total * 100) if total > 0 else 0

    # Points accuracy (binary)
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits
        FROM prediction_outcomes
        WHERE prop_type = 'points'
    """)
    result = cursor.fetchone()
    points_total = result['total']
    points_hits = result['hits']
    points_accuracy = (points_hits / points_total * 100) if points_total > 0 else 0

    # Shots accuracy (continuous)
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits
        FROM prediction_outcomes
        WHERE prop_type = 'shots'
    """)
    result = cursor.fetchone()
    shots_total = result['total']
    shots_hits = result['hits']
    shots_accuracy = (shots_hits / shots_total * 100) if shots_total > 0 else 0

    # Brier score (calibration metric)
    cursor.execute("""
        SELECT
            AVG(
                CASE
                    WHEN outcome = 'HIT' THEN (1 - predicted_probability) * (1 - predicted_probability)
                    ELSE predicted_probability * predicted_probability
                END
            ) as brier_score
        FROM prediction_outcomes
        WHERE predicted_probability IS NOT NULL
    """)
    result = cursor.fetchone()
    brier_score = result['brier_score'] if result['brier_score'] else 0

    conn.close()

    return {
        'overall_accuracy': round(overall_accuracy, 1),
        'points_accuracy': round(points_accuracy, 1),
        'shots_accuracy': round(shots_accuracy, 1),
        'brier_score': round(brier_score, 3),
        'total_graded': total,
        'points_graded': points_total,
        'shots_graded': shots_total
    }


def get_recent_predictions(limit=20):
    """Get recent predictions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id,
            p.game_date,
            p.player_name,
            p.team,
            p.opponent,
            p.prop_type,
            p.line,
            p.prediction,
            p.probability,
            p.created_at,
            po.outcome,
            po.actual_stat_value
        FROM predictions p
        LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
        ORDER BY p.created_at DESC
        LIMIT ?
    """, (limit,))

    predictions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return predictions


def get_accuracy_trend(days=7):
    """Get daily accuracy trend."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            game_date,
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
            ROUND(SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as accuracy
        FROM prediction_outcomes
        WHERE game_date >= date('now', '-' || ? || ' days')
        GROUP BY game_date
        ORDER BY game_date ASC
    """, (days,))

    trend = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return trend


def get_feature_importance():
    """Get feature importance data (from feature_importance table if ML trained, else mock data)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we have ML models trained
    cursor.execute("SELECT COUNT(*) as count FROM feature_importance")
    has_ml_features = cursor.fetchone()['count'] > 0

    if has_ml_features:
        cursor.execute("""
            SELECT
                fi.feature_name,
                fi.importance_score,
                fi.rank,
                mv.version,
                mv.trained_at
            FROM feature_importance fi
            JOIN model_versions mv ON fi.model_version_id = mv.id
            ORDER BY mv.trained_at DESC, fi.rank ASC
            LIMIT 20
        """)
        features = [dict(row) for row in cursor.fetchall()]
    else:
        # During data collection phase, show feature extraction stats
        features = []

    conn.close()
    return features


def get_feature_stats():
    """Get statistics about features being extracted (for pre-ML phase)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get a sample of features_json to analyze
    cursor.execute("""
        SELECT features_json
        FROM predictions
        WHERE features_json IS NOT NULL AND features_json != ''
        LIMIT 100
    """)

    feature_counts = {}
    feature_values = {}

    for row in cursor.fetchall():
        try:
            features = json.loads(row['features_json'])
            for key, value in features.items():
                if key not in feature_counts:
                    feature_counts[key] = 0
                    feature_values[key] = []
                feature_counts[key] += 1
                if isinstance(value, (int, float)):
                    feature_values[key].append(value)
        except:
            continue

    # Calculate stats
    feature_stats = []
    for feature_name, count in feature_counts.items():
        values = feature_values.get(feature_name, [])
        if values:
            feature_stats.append({
                'name': feature_name,
                'count': count,
                'min': round(min(values), 3),
                'max': round(max(values), 3),
                'mean': round(sum(values) / len(values), 3),
                'std': round((sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5, 3) if len(values) > 1 else 0
            })

    feature_stats.sort(key=lambda x: x['count'], reverse=True)
    conn.close()

    return feature_stats


# ============================================================================
# ESPN SCOREBOARD API
# ============================================================================

def get_espn_scoreboard(sport='hockey', league='nhl'):
    """Fetch ESPN scoreboard data."""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

def run_script(script_name):
    """Run a Python script and return output."""
    script_path = PROJECT_ROOT / script_name

    if not script_path.exists():
        return {'success': False, 'error': f'Script not found: {script_name}'}

    try:
        result = subprocess.run(
            ['python3', str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Script timeout (5 minutes)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# ROUTES - Pages
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


# ============================================================================
# ROUTES - API Endpoints
# ============================================================================

@app.route('/api/system-health')
def api_system_health():
    """Get system health metrics."""
    return jsonify(get_system_health())


@app.route('/api/performance-metrics')
def api_performance_metrics():
    """Get performance metrics."""
    return jsonify(get_performance_metrics())


@app.route('/api/recent-predictions')
def api_recent_predictions():
    """Get recent predictions."""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(get_recent_predictions(limit))


@app.route('/api/accuracy-trend')
def api_accuracy_trend():
    """Get accuracy trend."""
    days = request.args.get('days', 7, type=int)
    return jsonify(get_accuracy_trend(days))


@app.route('/api/feature-importance')
def api_feature_importance():
    """Get feature importance data."""
    return jsonify(get_feature_importance())


@app.route('/api/feature-stats')
def api_feature_stats():
    """Get feature statistics (pre-ML phase)."""
    return jsonify(get_feature_stats())


@app.route('/api/scoreboard/<sport>/<league>')
def api_scoreboard(sport, league):
    """Get ESPN scoreboard."""
    return jsonify(get_espn_scoreboard(sport, league))


@app.route('/api/run-script', methods=['POST'])
def api_run_script():
    """Execute a script."""
    data = request.get_json()
    script_name = data.get('script')

    if not script_name:
        return jsonify({'success': False, 'error': 'No script specified'}), 400

    # Whitelist of allowed scripts
    allowed_scripts = [
        'v2_auto_grade_yesterday_v3.py',
        'generate_predictions_daily.py',
        'check_feature_storage.py',
        'diagnose_features.py',
        'test_fixed_system.py',
        'clean_database_simple.py'
    ]

    if script_name not in allowed_scripts:
        return jsonify({'success': False, 'error': 'Script not allowed'}), 403

    result = run_script(script_name)
    return jsonify(result)


@app.route('/api/predictions/search')
def api_predictions_search():
    """Search and filter predictions."""
    player = request.args.get('player', '')
    prop_type = request.args.get('prop_type', '')
    outcome = request.args.get('outcome', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    limit = request.args.get('limit', 100, type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            p.id,
            p.game_date,
            p.player_name,
            p.team,
            p.opponent,
            p.prop_type,
            p.line,
            p.prediction,
            p.probability,
            p.created_at,
            po.outcome,
            po.actual_stat_value
        FROM predictions p
        LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
        WHERE 1=1
    """
    params = []

    if player:
        query += " AND LOWER(p.player_name) LIKE ?"
        params.append(f'%{player.lower()}%')

    if prop_type:
        query += " AND p.prop_type = ?"
        params.append(prop_type)

    if outcome:
        query += " AND po.outcome = ?"
        params.append(outcome)

    if date_from:
        query += " AND p.game_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND p.game_date <= ?"
        params.append(date_to)

    query += " ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    predictions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(predictions)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NHL PREDICTION SYSTEM V2 - DASHBOARD")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"Database exists: {DB_PATH.exists()}")
    print(f"Dashboard starting at: http://localhost:5000")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0', port=5000)
