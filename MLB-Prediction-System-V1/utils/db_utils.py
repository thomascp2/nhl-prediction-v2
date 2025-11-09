"""
Database Utilities for MLB Prediction System
===========================================
Based on proven NHL/NFL V2 methodology
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import mlb_config


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(mlb_config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_prediction(prediction: Dict) -> int:
    """Save a single prediction to database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO predictions (
                prediction_batch_id, game_date, player_name, player_type,
                team, opponent, prop_type, line, prediction, probability,
                model_version, confidence_tier, features_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction['prediction_batch_id'],
            prediction['game_date'],
            prediction['player_name'],
            prediction['player_type'],
            prediction['team'],
            prediction['opponent'],
            prediction['prop_type'],
            prediction['line'],
            prediction['prediction'],
            prediction['probability'],
            prediction.get('model_version', mlb_config.MODEL_VERSION),
            prediction.get('confidence_tier'),
            json.dumps(prediction.get('features', {})),
        ))

        conn.commit()
        return cursor.lastrowid

    except sqlite3.Error as e:
        print(f"Error saving prediction: {e}")
        conn.rollback()
        return -1
    finally:
        conn.close()


def save_predictions_batch(predictions: List[Dict]) -> Tuple[int, int]:
    """Save multiple predictions in a single transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()

    success_count = 0
    error_count = 0

    try:
        for prediction in predictions:
            try:
                cursor.execute("""
                    INSERT INTO predictions (
                        prediction_batch_id, game_date, player_name, player_type,
                        team, opponent, prop_type, line, prediction, probability,
                        model_version, confidence_tier, features_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction['prediction_batch_id'],
                    prediction['game_date'],
                    prediction['player_name'],
                    prediction['player_type'],
                    prediction['team'],
                    prediction['opponent'],
                    prediction['prop_type'],
                    prediction['line'],
                    prediction['prediction'],
                    prediction['probability'],
                    prediction.get('model_version', mlb_config.MODEL_VERSION),
                    prediction.get('confidence_tier'),
                    json.dumps(prediction.get('features', {})),
                ))
                success_count += 1
            except sqlite3.Error as e:
                print(f"Error saving prediction for {prediction.get('player_name')}: {e}")
                error_count += 1

        conn.commit()
        return (success_count, error_count)

    except sqlite3.Error as e:
        print(f"Batch save error: {e}")
        conn.rollback()
        return (success_count, error_count)
    finally:
        conn.close()


def get_predictions_for_date(game_date: str, ungraded_only: bool = True) -> List[Dict]:
    """Retrieve predictions for a specific date"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if ungraded_only:
            query = """
                SELECT p.*
                FROM predictions p
                LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
                WHERE p.game_date = ?
                AND po.id IS NULL
                ORDER BY p.player_type, p.player_name
            """
        else:
            query = """
                SELECT * FROM predictions
                WHERE game_date = ?
                ORDER BY player_type, player_name
            """

        cursor.execute(query, (game_date,))
        rows = cursor.fetchall()

        predictions = []
        for row in rows:
            pred = dict(row)
            if pred.get('features_json'):
                pred['features'] = json.loads(pred['features_json'])
            predictions.append(pred)

        return predictions

    except sqlite3.Error as e:
        print(f"Error fetching predictions: {e}")
        return []
    finally:
        conn.close()


def save_prediction_outcome(prediction_id: int, actual_value: float, outcome: str):
    """Save the outcome of a prediction after game completes"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT game_date, player_name, player_type, prop_type, line, probability
            FROM predictions WHERE id = ?
        """, (prediction_id,))

        pred = cursor.fetchone()
        if not pred:
            print(f"Prediction {prediction_id} not found")
            return False

        cursor.execute("""
            INSERT INTO prediction_outcomes (
                prediction_id, game_date, player_name, player_type,
                prop_type, line, predicted_probability,
                actual_stat_value, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id, pred['game_date'], pred['player_name'], pred['player_type'],
            pred['prop_type'], pred['line'], pred['probability'],
            actual_value, outcome
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving outcome: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_player_game_logs(player_name: str, player_type: str, limit: int = 20) -> List[Dict]:
    """Get recent game logs for a player"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM player_game_logs
            WHERE player_name = ? AND player_type = ?
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_name, player_type, limit))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        print(f"Error fetching game logs: {e}")
        return []
    finally:
        conn.close()


def save_player_game_log(game_log: Dict) -> bool:
    """Save or update player game log"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO player_game_logs (
                game_date, player_name, player_type, team, opponent, home_away,
                at_bats, hits, doubles, triples, home_runs, rbis, runs,
                walks, batter_strikeouts, stolen_bases, total_bases,
                batting_avg, on_base_pct, slugging_pct,
                innings_pitched, earned_runs, pitcher_strikeouts,
                walks_allowed, hits_allowed, home_runs_allowed,
                pitch_count, pitches_per_inning, win_loss, era, whip,
                opposing_pitcher, park_name, temperature, wind_speed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_log['game_date'],
            game_log['player_name'],
            game_log['player_type'],
            game_log['team'],
            game_log['opponent'],
            game_log.get('home_away'),
            game_log.get('at_bats'),
            game_log.get('hits'),
            game_log.get('doubles'),
            game_log.get('triples'),
            game_log.get('home_runs'),
            game_log.get('rbis'),
            game_log.get('runs'),
            game_log.get('walks'),
            game_log.get('batter_strikeouts'),
            game_log.get('stolen_bases'),
            game_log.get('total_bases'),
            game_log.get('batting_avg'),
            game_log.get('on_base_pct'),
            game_log.get('slugging_pct'),
            game_log.get('innings_pitched'),
            game_log.get('earned_runs'),
            game_log.get('pitcher_strikeouts'),
            game_log.get('walks_allowed'),
            game_log.get('hits_allowed'),
            game_log.get('home_runs_allowed'),
            game_log.get('pitch_count'),
            game_log.get('pitches_per_inning'),
            game_log.get('win_loss'),
            game_log.get('era'),
            game_log.get('whip'),
            game_log.get('opposing_pitcher'),
            game_log.get('park_name'),
            game_log.get('temperature'),
            game_log.get('wind_speed'),
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving game log: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_park_factor(park_name: str) -> Optional[Dict]:
    """Get park factor for a ballpark"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM park_factors
            WHERE park_name = ?
        """, (park_name,))

        row = cursor.fetchone()
        return dict(row) if row else None

    except sqlite3.Error as e:
        print(f"Error fetching park factor: {e}")
        return None
    finally:
        conn.close()


def save_game_schedule(game: Dict) -> bool:
    """Save or update game schedule"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO game_schedule (
                game_date, game_time, home_team, away_team,
                home_pitcher, away_pitcher, home_pitcher_hand, away_pitcher_hand,
                total, home_ml, away_ml, spread,
                home_implied_runs, away_implied_runs,
                temperature, wind_speed, wind_direction, conditions,
                park_name, is_dome,
                home_score, away_score, game_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game['game_date'], game.get('game_time'),
            game['home_team'], game['away_team'],
            game.get('home_pitcher'), game.get('away_pitcher'),
            game.get('home_pitcher_hand'), game.get('away_pitcher_hand'),
            game.get('total'), game.get('home_ml'), game.get('away_ml'), game.get('spread'),
            game.get('home_implied_runs'), game.get('away_implied_runs'),
            game.get('temperature'), game.get('wind_speed'),
            game.get('wind_direction'), game.get('conditions'),
            game.get('park_name'), game.get('is_dome', False),
            game.get('home_score'), game.get('away_score'),
            game.get('game_completed', False),
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving game schedule: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_daily_accuracy(game_date: Optional[str] = None) -> Dict:
    """Calculate accuracy for a specific date or all dates"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if game_date:
            cursor.execute("""
                SELECT
                    player_type, prop_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
                    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
                FROM prediction_outcomes
                WHERE game_date = ?
                GROUP BY player_type, prop_type
            """, (game_date,))
        else:
            cursor.execute("""
                SELECT
                    'ALL' as player_type, 'ALL' as prop_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
                    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
                FROM prediction_outcomes
            """)

        rows = cursor.fetchall()
        results = {}
        for row in rows:
            key = f"{row['player_type']}_{row['prop_type']}"
            results[key] = {
                'total': row['total'],
                'hits': row['hits'],
                'accuracy': row['accuracy']
            }

        return results

    except sqlite3.Error as e:
        print(f"Error calculating accuracy: {e}")
        return {}
    finally:
        conn.close()


def get_database_stats() -> Dict:
    """Get overall database statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        stats = {}

        # Total predictions
        cursor.execute("SELECT COUNT(*) as count FROM predictions")
        stats['total_predictions'] = cursor.fetchone()['count']

        # Graded predictions
        cursor.execute("SELECT COUNT(*) as count FROM prediction_outcomes")
        stats['graded_predictions'] = cursor.fetchone()['count']

        # Player game logs
        cursor.execute("SELECT COUNT(*) as count FROM player_game_logs")
        stats['game_logs'] = cursor.fetchone()['count']

        # Overall accuracy
        cursor.execute("""
            SELECT
                ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
            FROM prediction_outcomes
        """)
        result = cursor.fetchone()
        stats['overall_accuracy'] = result['accuracy'] if result['accuracy'] else 0.0

        return stats

    except sqlite3.Error as e:
        print(f"Error getting database stats: {e}")
        return {}
    finally:
        conn.close()
