"""
Generate Daily Predictions - V3 with Duplicate Detection
Checks for existing predictions before generating to prevent constraint errors
"""

import sys
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from v2_config import DB_PATH
from statistical_predictions_v2 import StatisticalPredictionEngine

def check_predictions_exist(target_date: str) -> tuple[bool, int]:
    """
    Check if predictions already exist for target date
    
    Args:
        target_date: Date in YYYY-MM-DD format
        
    Returns:
        Tuple of (predictions_exist, prediction_count)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE game_date = ?', (target_date,))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0, count


def delete_existing_predictions(target_date: str) -> int:
    """
    Delete existing predictions for target date
    
    Args:
        target_date: Date in YYYY-MM-DD format
        
    Returns:
        Number of predictions deleted
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count before deleting
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE game_date = ?', (target_date,))
    count = cursor.fetchone()[0]
    
    # Delete
    cursor.execute('DELETE FROM predictions WHERE game_date = ?', (target_date,))
    conn.commit()
    conn.close()
    
    return count


def check_games_exist(target_date: str) -> tuple[bool, int]:
    """
    Check if games exist in database for target date
    
    Args:
        target_date: Date in YYYY-MM-DD format
        
    Returns:
        Tuple of (games_exist, game_count)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM games WHERE game_date = ?', (target_date,))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0, count


def fetch_game_schedule(target_date: str) -> bool:
    """
    Call fetch_game_schedule_FINAL.py to populate games
    
    Args:
        target_date: Date in YYYY-MM-DD format
        
    Returns:
        True if successful, False otherwise
    """
    print()
    print("=" * 80)
    print(f"AUTO-FETCHING GAME SCHEDULE FOR {target_date}")
    print("=" * 80)
    print()
    
    try:
        # Run fetch_game_schedule_FINAL.py
        result = subprocess.run(
            [sys.executable, 'fetch_game_schedule_FINAL.py', target_date],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Game schedule fetched successfully!")
            print()
            return True
        else:
            print(f"⚠️  Warning: Game schedule fetch returned code {result.returncode}")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Last 500 chars
            if result.stderr:
                print("Errors:", result.stderr[-500:])
            print()
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Error: Game schedule fetch timed out")
        print()
        return False
    except FileNotFoundError:
        print("❌ Error: fetch_game_schedule_FINAL.py not found")
        print("   Make sure it's in the same directory")
        print()
        return False
    except Exception as e:
        print(f"❌ Error fetching game schedule: {e}")
        print()
        return False


def get_players_with_history_for_team(team: str, min_games: int = 5, top_n: int = 12) -> list[str]:
    """
    Get players who have game log history for a team
    
    Args:
        team: Team abbreviation
        min_games: Minimum games required in history
        top_n: Number of top players to return (12 for exploration, 8 for exploitation)
        
    Returns:
        List of player names with sufficient history
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT player_name, COUNT(*) as games, 
               SUM(points) * 1.0 / COUNT(*) as ppg
        FROM player_game_logs
        WHERE team = ?
        GROUP BY player_name
        HAVING games >= ?
        ORDER BY ppg DESC
        LIMIT ?
    ''', (team, min_games, top_n))
    
    players = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return players


def determine_phase(current_date: str) -> tuple[str, int]:
    """
    Determine which collection phase we're in
    
    Args:
        current_date: Current date string YYYY-MM-DD
        
    Returns:
        Tuple of (phase_name, players_per_team)
    """
    # Exploration: Nov 7 - Nov 19 (top 12 players per team)
    # Exploitation: Nov 20 - Jan 5 (top 8 players per team)
    
    exploration_end = datetime(2025, 11, 19)
    current = datetime.strptime(current_date, '%Y-%m-%d')
    
    if current <= exploration_end:
        return "EXPLORATION", 12
    else:
        return "EXPLOITATION", 8


def generate_predictions_for_date(target_date: str, force: bool = False) -> int:
    """
    Generate predictions for all games on target date
    
    Args:
        target_date: Date in YYYY-MM-DD format
        force: If True, delete existing predictions and regenerate
        
    Returns:
        Number of predictions generated
    """
    # Determine phase
    phase, players_per_team = determine_phase(target_date)
    
    print('=' * 80)
    print(f'GENERATING PREDICTIONS FOR {target_date}')
    print(f'Phase: {phase} (Top {players_per_team} players per team)') 
    print('=' * 80)
    print()
    
    # Check if predictions already exist
    preds_exist, pred_count = check_predictions_exist(target_date)
    
    if preds_exist and not force:
        print(f"⚠️  PREDICTIONS ALREADY EXIST FOR {target_date}")
        print(f"   Found {pred_count} existing predictions in database")
        print()
        print("   Options:")
        print("   1. Skip generation (predictions already done) ✅")
        print("   2. Regenerate with --force flag:")
        print(f"      python generate_predictions_daily.py {target_date} --force")
        print()
        print("⏭️  Skipping generation - predictions already exist")
        print()
        return 0
    
    if preds_exist and force:
        print(f"🔄 FORCE MODE: Deleting {pred_count} existing predictions...")
        deleted = delete_existing_predictions(target_date)
        print(f"   ✅ Deleted {deleted} predictions")
        print()
    
    # Check if games exist, fetch if not
    games_exist, game_count = check_games_exist(target_date)
    
    if not games_exist:
        print(f"⚠️  No games found in database for {target_date}")
        print("   Attempting to fetch game schedule...")
        print()
        
        if not fetch_game_schedule(target_date):
            print("❌ Failed to fetch game schedule")
            print("   Cannot generate predictions without games in database")
            print()
            return 0
        
        # Verify games now exist
        games_exist, game_count = check_games_exist(target_date)
        if not games_exist:
            print("❌ Still no games found after fetch attempt")
            print("   This likely means no NHL games scheduled for this date")
            print()
            return 0
    
    print(f"✅ Found {game_count} games in database for {target_date}")
    print()
    
    # Get games
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT game_date, away_team, home_team FROM games WHERE game_date = ?', (target_date,))
    games = cursor.fetchall()
    conn.close()
    
    print(f"Games on {target_date}:")
    for _, away, home in games:
        print(f"  {away} @ {home}")
    print()
    
    # Initialize prediction engine
    engine = StatisticalPredictionEngine(db_path=DB_PATH, learning_mode=True)
    
    total_predictions = 0
    total_players_found = 0
    total_players_skipped = 0
    
    for game_date, away_team, home_team in games:
        # Away team players
        away_players = get_players_with_history_for_team(away_team, min_games=5, top_n=players_per_team)
        
        if away_players:
            print(f"{away_team}: {len(away_players)} players with history")
            total_players_found += len(away_players)
            
            for player in away_players:
                # Points O0.5
                pred = engine.predict_points(player, away_team, game_date, home_team, is_home=False)
                if pred:
                    total_predictions += 1
                
                # Shots O2.5
                pred = engine.predict_shots(player, away_team, game_date, home_team, is_home=False)
                if pred:
                    total_predictions += 1
        else:
            print(f"{away_team}: No players with sufficient history (skipping)")
            total_players_skipped += 1
        
        # Home team players
        home_players = get_players_with_history_for_team(home_team, min_games=5, top_n=players_per_team)
        
        if home_players:
            print(f"{home_team}: {len(home_players)} players with history")
            total_players_found += len(home_players)
            
            for player in home_players:
                # Points O0.5
                pred = engine.predict_points(player, home_team, game_date, away_team, is_home=True)
                if pred:
                    total_predictions += 1
                
                # Shots O2.5
                pred = engine.predict_shots(player, home_team, game_date, away_team, is_home=True)
                if pred:
                    total_predictions += 1
        else:
            print(f"{home_team}: No players with sufficient history (skipping)")
            total_players_skipped += 1
        
        print()
    
    print()
    print('=' * 80)
    print(f'GENERATED {total_predictions} PREDICTIONS')
    print('=' * 80)
    print()
    print(f'Players found: {total_players_found}')
    print(f'Teams skipped: {total_players_skipped}')
    print(f'Phase: {phase}')
    print()
    
    return total_predictions


def verify_predictions(target_date: str) -> dict:
    """
    Verify predictions were saved correctly
    
    Args:
        target_date: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary with verification results
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count predictions
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE game_date = ?', (target_date,))
    count = cursor.fetchone()[0]
    
    # Get variety stats
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT player_name) as unique_players,
            COUNT(DISTINCT ROUND(probability, 2)) as unique_probs,
            AVG(probability) as avg_prob,
            MIN(probability) as min_prob,
            MAX(probability) as max_prob,
            SUM(CASE WHEN prediction = 'OVER' THEN 1 ELSE 0 END) as over_count,
            SUM(CASE WHEN prediction = 'UNDER' THEN 1 ELSE 0 END) as under_count
        FROM predictions 
        WHERE game_date = ?
    ''', (target_date,))
    
    stats = cursor.fetchone()
    conn.close()
    
    if stats:
        return {
            'count': count,
            'unique_players': stats[0],
            'unique_probs': stats[1],
            'avg_prob': stats[2],
            'min_prob': stats[3],
            'max_prob': stats[4],
            'over_count': stats[5],
            'under_count': stats[6]
        }
    else:
        return {'count': 0}


def main():
    """Main execution"""
    # Parse arguments
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        print(f"Using provided date: {target_date}")
    else:
        # Auto-detect tomorrow
        target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Auto-detected tomorrow: {target_date}")
    
    # Check for force flag
    force = '--force' in sys.argv or '-f' in sys.argv
    
    print()
    
    # Generate predictions
    count = generate_predictions_for_date(target_date, force=force)
    
    if count == 0:
        # Check if predictions exist (skipped) vs error
        preds_exist, pred_count = check_predictions_exist(target_date)
        if preds_exist:
            print("ℹ️  Predictions already exist - use --force to regenerate")
            return 0  # Success - predictions exist
        else:
            print("⚠️  No predictions generated")
            print("   Check if:")
            print("   1. Games are scheduled for this date")
            print("   2. Players have sufficient game history (5+ games)")
            print()
            return 1  # Error - no predictions and none exist
    
    # Verify predictions
    print()
    print('=' * 80)
    print('VERIFICATION RESULTS')
    print('=' * 80)
    print()
    
    results = verify_predictions(target_date)
    
    print(f"Predictions in database: {results['count']}")
    
    if results['count'] > 0:
        print(f"Unique players: {results['unique_players']}")
        print(f"Unique probabilities: {results['unique_probs']}")
        print(f"Avg probability: {results['avg_prob']:.1%}")
        print(f"Range: {results['min_prob']:.1%} to {results['max_prob']:.1%}")
        print(f"OVER: {results['over_count']}, UNDER: {results['under_count']}")
        print()
        
        # Success criteria
        if results['unique_probs'] > 10:
            print("✅ SUCCESS - Predictions generated and verified!")
            print("   Feature variety looks good (not using defaults)")
        else:
            print("⚠️  WARNING - Low probability variety")
            print("   May be using default values - check player history")
    else:
        print("❌ ERROR - Predictions generated but not found in database")
    
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
