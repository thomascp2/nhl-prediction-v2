"""
Database Utilities for NFL Prediction System
===========================================
Based on proven NHL V2 methodology
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(nfl_config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_prediction(prediction: Dict) -> int:
    """
    Save a single prediction to database

    Args:
        prediction: Dictionary with prediction details

    Returns:
        prediction_id: ID of inserted prediction
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO predictions (
                prediction_batch_id,
                game_date,
                week_number,
                player_name,
                team,
                opponent,
                position,
                prop_type,
                line,
                prediction,
                probability,
                model_version,
                confidence_tier,
                features_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction['prediction_batch_id'],
            prediction['game_date'],
            prediction['week_number'],
            prediction['player_name'],
            prediction['team'],
            prediction['opponent'],
            prediction['position'],
            prediction['prop_type'],
            prediction['line'],
            prediction['prediction'],
            prediction['probability'],
            prediction.get('model_version', nfl_config.MODEL_VERSION),
            prediction.get('confidence_tier'),
            json.dumps(prediction.get('features', {})),
        ))

        conn.commit()
        prediction_id = cursor.lastrowid

        return prediction_id

    except sqlite3.Error as e:
        print(f"Error saving prediction: {e}")
        conn.rollback()
        return -1

    finally:
        conn.close()


def save_predictions_batch(predictions: List[Dict]) -> Tuple[int, int]:
    """
    Save multiple predictions in a single transaction

    Args:
        predictions: List of prediction dictionaries

    Returns:
        (success_count, error_count)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    success_count = 0
    error_count = 0

    try:
        for prediction in predictions:
            try:
                cursor.execute("""
                    INSERT INTO predictions (
                        prediction_batch_id,
                        game_date,
                        week_number,
                        player_name,
                        team,
                        opponent,
                        position,
                        prop_type,
                        line,
                        prediction,
                        probability,
                        model_version,
                        confidence_tier,
                        features_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction['prediction_batch_id'],
                    prediction['game_date'],
                    prediction['week_number'],
                    prediction['player_name'],
                    prediction['team'],
                    prediction['opponent'],
                    prediction['position'],
                    prediction['prop_type'],
                    prediction['line'],
                    prediction['prediction'],
                    prediction['probability'],
                    prediction.get('model_version', nfl_config.MODEL_VERSION),
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


def get_predictions_for_week(week_number: int, ungraded_only: bool = True) -> List[Dict]:
    """
    Retrieve predictions for a specific week

    Args:
        week_number: Week number (1-22)
        ungraded_only: If True, only return predictions without outcomes

    Returns:
        List of prediction dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if ungraded_only:
            query = """
                SELECT p.*
                FROM predictions p
                LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id
                WHERE p.week_number = ?
                AND po.id IS NULL
                ORDER BY p.game_date, p.player_name
            """
        else:
            query = """
                SELECT * FROM predictions
                WHERE week_number = ?
                ORDER BY game_date, player_name
            """

        cursor.execute(query, (week_number,))
        rows = cursor.fetchall()

        predictions = []
        for row in rows:
            pred = dict(row)
            # Parse features JSON
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
    """
    Save the outcome of a prediction after game completes

    Args:
        prediction_id: ID of the prediction
        actual_value: Actual stat value from game
        outcome: 'HIT' or 'MISS'
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get prediction details
        cursor.execute("""
            SELECT game_date, week_number, player_name, prop_type, line, probability
            FROM predictions
            WHERE id = ?
        """, (prediction_id,))

        pred = cursor.fetchone()
        if not pred:
            print(f"Prediction {prediction_id} not found")
            return False

        # Insert outcome
        cursor.execute("""
            INSERT INTO prediction_outcomes (
                prediction_id,
                game_date,
                week_number,
                player_name,
                prop_type,
                line,
                predicted_probability,
                actual_stat_value,
                outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id,
            pred['game_date'],
            pred['week_number'],
            pred['player_name'],
            pred['prop_type'],
            pred['line'],
            pred['probability'],
            actual_value,
            outcome
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving outcome: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def get_player_game_logs(player_name: str, limit: int = 20) -> List[Dict]:
    """
    Get recent game logs for a player

    Args:
        player_name: Player's name
        limit: Number of recent games to return

    Returns:
        List of game log dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM player_game_logs
            WHERE player_name = ?
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_name, limit))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        print(f"Error fetching game logs: {e}")
        return []

    finally:
        conn.close()


def save_player_game_log(game_log: Dict) -> bool:
    """
    Save or update player game log

    Args:
        game_log: Dictionary with game statistics

    Returns:
        Success boolean
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO player_game_logs (
                game_date,
                week_number,
                player_name,
                team,
                opponent,
                home_away,
                position,
                pass_attempts,
                pass_completions,
                pass_yards,
                pass_tds,
                interceptions,
                sacks,
                qb_rating,
                rush_attempts,
                rush_yards,
                rush_tds,
                yards_per_carry,
                targets,
                receptions,
                rec_yards,
                rec_tds,
                yards_per_reception,
                snap_count,
                snap_pct,
                target_share,
                air_yards_share,
                red_zone_targets,
                red_zone_carries,
                game_script,
                team_score,
                opp_score,
                game_total,
                two_point_conversions,
                fumbles,
                fumbles_lost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_log['game_date'],
            game_log['week_number'],
            game_log['player_name'],
            game_log['team'],
            game_log['opponent'],
            game_log.get('home_away'),
            game_log['position'],
            game_log.get('pass_attempts'),
            game_log.get('pass_completions'),
            game_log.get('pass_yards'),
            game_log.get('pass_tds'),
            game_log.get('interceptions'),
            game_log.get('sacks'),
            game_log.get('qb_rating'),
            game_log.get('rush_attempts'),
            game_log.get('rush_yards'),
            game_log.get('rush_tds'),
            game_log.get('yards_per_carry'),
            game_log.get('targets'),
            game_log.get('receptions'),
            game_log.get('rec_yards'),
            game_log.get('rec_tds'),
            game_log.get('yards_per_reception'),
            game_log.get('snap_count'),
            game_log.get('snap_pct'),
            game_log.get('target_share'),
            game_log.get('air_yards_share'),
            game_log.get('red_zone_targets'),
            game_log.get('red_zone_carries'),
            game_log.get('game_script'),
            game_log.get('team_score'),
            game_log.get('opp_score'),
            game_log.get('game_total'),
            game_log.get('two_point_conversions'),
            game_log.get('fumbles'),
            game_log.get('fumbles_lost'),
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving game log: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def get_team_context(team: str, week_number: int) -> Optional[Dict]:
    """
    Get team context for a specific week

    Args:
        team: Team abbreviation
        week_number: Week number

    Returns:
        Team context dictionary or None
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM team_context
            WHERE team = ? AND week_number <= ?
            ORDER BY week_number DESC
            LIMIT 1
        """, (team, week_number))

        row = cursor.fetchone()
        return dict(row) if row else None

    except sqlite3.Error as e:
        print(f"Error fetching team context: {e}")
        return None

    finally:
        conn.close()


def save_game_schedule(game: Dict) -> bool:
    """
    Save or update game schedule

    Args:
        game: Dictionary with game details

    Returns:
        Success boolean
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO game_schedule (
                game_date,
                week_number,
                game_time,
                home_team,
                away_team,
                total,
                spread,
                home_ml,
                away_ml,
                home_implied_points,
                away_implied_points,
                expected_pace,
                weather_temp,
                weather_wind,
                weather_precip,
                weather_description,
                is_dome,
                home_score,
                away_score,
                game_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game['game_date'],
            game['week_number'],
            game.get('game_time'),
            game['home_team'],
            game['away_team'],
            game.get('total'),
            game.get('spread'),
            game.get('home_ml'),
            game.get('away_ml'),
            game.get('home_implied_points'),
            game.get('away_implied_points'),
            game.get('expected_pace'),
            game.get('weather_temp'),
            game.get('weather_wind'),
            game.get('weather_precip'),
            game.get('weather_description'),
            game.get('is_dome', False),
            game.get('home_score'),
            game.get('away_score'),
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


def get_weekly_accuracy(week_number: Optional[int] = None) -> Dict:
    """
    Calculate accuracy for a specific week or all weeks

    Args:
        week_number: Week to calculate (None for all weeks)

    Returns:
        Accuracy statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if week_number:
            cursor.execute("""
                SELECT
                    prop_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
                    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
                FROM prediction_outcomes
                WHERE week_number = ?
                GROUP BY prop_type
            """, (week_number,))
        else:
            cursor.execute("""
                SELECT
                    'ALL' as prop_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
                    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy
                FROM prediction_outcomes
            """)

        rows = cursor.fetchall()
        results = {}
        for row in rows:
            results[row['prop_type']] = {
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

        # Weeks with predictions
        cursor.execute("SELECT COUNT(DISTINCT week_number) as count FROM predictions")
        stats['weeks_with_predictions'] = cursor.fetchone()['count']

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
