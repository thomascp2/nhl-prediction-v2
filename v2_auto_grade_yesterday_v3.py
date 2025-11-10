"""
V2 Auto-Grade Yesterday's Predictions - VERSION 3
================================================

VERSION HISTORY:
- v1 (v2_auto_grade_yesterday.py): Original basic grading
- v2 (v2_auto_grade_yesterday_FIXED.py): Fixed fuzzy name matching + Discord 
- v3 (THIS FILE): Adds player_game_logs updates for continuous learning

WHAT'S NEW IN V3:
[OK] Saves all player stats to player_game_logs table after grading
[OK] Captures TOI, plus/minus, PIM in addition to points/shots
[OK] Enables feature extractors to use current data (not stale)
[OK] Creates complete feedback loop: predict -> grade -> update -> improve

This script:
1. Finds all predictions for target date
2. Fetches actual results from NHL API
3. Saves player stats to player_game_logs (NEW IN V3!)
4. Grades predictions (HIT/MISS) with fuzzy name matching
5. Stores results in prediction_outcomes table
6. Reports accuracy by tier
7. Sends Discord notification
"""

import sqlite3
import urllib.request
import urllib.error
import json as json_lib
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from v2_config import DB_PATH, LEARNING_MODE
from v2_discord_notifications import send_discord_notification


def save_player_game_logs_to_db(conn, game_id: str, game_date: str, player_stats_by_team: dict):
    """
    Save player stats to player_game_logs table
    
    NEW IN V3: This function ensures feature extractors get fresh data every day.
    Without this, predictions are based on stale data and model can't improve.
    
    Args:
        conn: Database connection
        game_id: NHL game ID
        game_date: Game date YYYY-MM-DD
        player_stats_by_team: Dict with 'away' and 'home' keys, each containing:
            {player_name: {stats}, ...}
    """
    cursor = conn.cursor()
    saved_count = 0
    
    for team_type in ['away', 'home']:
        is_home = 1 if team_type == 'home' else 0
        team_stats = player_stats_by_team.get(team_type, {})
        
        for player_name, stats in team_stats.items():
            try:
                # Calculate binary outcomes for feature extraction
                points = stats.get('points', 0)
                shots = stats.get('shots', 0)
                
                scored_1plus_points = 1 if points >= 1 else 0
                scored_2plus_shots = 1 if shots >= 2 else 0
                scored_3plus_shots = 1 if shots >= 3 else 0  
                scored_4plus_shots = 1 if shots >= 4 else 0
                
                cursor.execute("""
                    INSERT OR REPLACE INTO player_game_logs
                    (game_id, game_date, player_name, team, opponent, is_home,
                     goals, assists, points, shots_on_goal, toi_seconds, plus_minus, pim,
                     scored_1plus_points, scored_2plus_shots, scored_3plus_shots, scored_4plus_shots,
                     created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id,
                    game_date,
                    player_name,
                    stats.get('team'),
                    stats.get('opponent'),
                    is_home,
                    stats.get('goals', 0),
                    stats.get('assists', 0),
                    points,
                    shots,
                    stats.get('toi_seconds', 0),
                    stats.get('plus_minus', 0),
                    stats.get('pim', 0),
                    scored_1plus_points,
                    scored_2plus_shots,
                    scored_3plus_shots,
                    scored_4plus_shots,
                    datetime.now().isoformat()
                ))
                saved_count += 1
            except Exception as e:
                print(f'      [WARNING] Could not save {player_name} to player_game_logs: {e}')
    
    conn.commit()
    return saved_count

def fetch_actual_results(game_date: str) -> Dict[str, Dict]:
    """
    Fetch actual player stats from NHL API for all games on given date
    
    Args:
        game_date: Date in YYYY-MM-DD format
        
    Returns:
        Dict mapping player_name -> {points, shots, goals, assists, team, opponent}
    """
    print(f'Fetching actual results for {game_date}...')
    
    player_stats = {}
    
    try:
        # Get schedule for the date
        schedule_url = f'https://api-web.nhle.com/v1/schedule/{game_date}'
        req = urllib.request.Request(schedule_url)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                schedule_data = json_lib.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f'[ERROR] Schedule API returned status {e.code}')
            return player_stats
        
        # Find games for the target date
        games = []
        for day in schedule_data.get('gameWeek', []):
            if day.get('date') == game_date:
                games = day.get('games', [])
                break
        
        if not games:
            print(f'No games found for {game_date}')
            return player_stats
        
        print(f'Found {len(games)} games')
        
        # Fetch boxscore for each game
        for game in games:
            game_id = game.get('id')
            if not game_id:
                continue
            
            away_abbrev = game.get('awayTeam', {}).get('abbrev', 'UNK')
            home_abbrev = game.get('homeTeam', {}).get('abbrev', 'UNK')
            game_state = game.get('gameState', 'UNKNOWN')
            
            print(f'  Fetching: {away_abbrev} @ {home_abbrev} (ID: {game_id}, State: {game_state})')
            
            # Only process finished games
            if game_state not in ['OFF', 'FINAL']:
                print(f'    [WARNING] Game not finished yet (state: {game_state})')
                continue
            
            try:
                # Get boxscore
                boxscore_url = f'https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore'
                box_req = urllib.request.Request(boxscore_url)

                try:
                    with urllib.request.urlopen(box_req, timeout=10) as box_response:
                        boxscore = json_lib.loads(box_response.read().decode('utf-8'))
                except urllib.error.HTTPError as e:
                    print(f'    [ERROR] Boxscore API returned status {e.code}')
                    continue
                
                # Extract player stats from boxscore
                if 'playerByGameStats' not in boxscore:
                    print(f'    [WARNING] No player stats in boxscore')
                    continue
                
                player_by_game = boxscore['playerByGameStats']
                away_stats = player_by_game.get('awayTeam', {})
                home_stats = player_by_game.get('homeTeam', {})
                
                # Process away team
                away_players = {}
                for position in ['forwards', 'defense']:
                    for player in away_stats.get(position, []):
                        name_data = player.get('name', {})
                        player_name = name_data.get('default', '')
                        
                        if player_name:
                            points = player.get('points', 0)
                            shots = player.get('sog', 0)
                            goals = player.get('goals', 0)
                            assists = player.get('assists', 0)
                            toi = player.get('toi', '0:00')
                            plus_minus = player.get('plusMinus', 0)
                            pim = player.get('pim', 0)
                            
                            # Convert TOI to seconds
                            toi_seconds = 0
                            if toi and ':' in toi:
                                try:
                                    parts = toi.split(':')
                                    if len(parts) == 2:
                                        toi_seconds = int(parts[0]) * 60 + int(parts[1])
                                except:
                                    toi_seconds = 0
                            
                            player_stats[player_name] = {
                                'points': points,
                                'shots': shots,
                                'goals': goals,
                                'assists': assists,
                                'team': away_abbrev,
                                'opponent': home_abbrev,
                                'toi_seconds': toi_seconds,
                                'plus_minus': plus_minus,
                                'pim': pim
                            }
                            
                            away_players[player_name] = player_stats[player_name]
                
                # Process home team
                home_players = {}
                for position in ['forwards', 'defense']:
                    for player in home_stats.get(position, []):
                        name_data = player.get('name', {})
                        player_name = name_data.get('default', '')
                        
                        if player_name:
                            points = player.get('points', 0)
                            shots = player.get('sog', 0)
                            goals = player.get('goals', 0)
                            assists = player.get('assists', 0)
                            toi = player.get('toi', '0:00')
                            plus_minus = player.get('plusMinus', 0)
                            pim = player.get('pim', 0)
                            
                            # Convert TOI to seconds
                            toi_seconds = 0
                            if toi and ':' in toi:
                                try:
                                    parts = toi.split(':')
                                    if len(parts) == 2:
                                        toi_seconds = int(parts[0]) * 60 + int(parts[1])
                                except:
                                    toi_seconds = 0
                            
                            player_stats[player_name] = {
                                'points': points,
                                'shots': shots,
                                'goals': goals,
                                'assists': assists,
                                'team': home_abbrev,
                                'opponent': away_abbrev,
                                'toi_seconds': toi_seconds,
                                'plus_minus': plus_minus,
                                'pim': pim
                            }
                            
                            home_players[player_name] = player_stats[player_name]
                
                # NEW IN V3: Save player stats to player_game_logs table
                # This ensures feature extractors have fresh data for next predictions
                conn = sqlite3.connect(DB_PATH)
                saved = save_player_game_logs_to_db(
                    conn,
                    game_id=str(game_id),
                    game_date=game_date,
                    player_stats_by_team={'away': away_players, 'home': home_players}
                )
                conn.close()
                
                player_count = len(away_players) + len(home_players)
                print(f'    [OK] Fetched stats for {player_count} players ([SAVE] saved {saved} to player_game_logs)')
                
            except Exception as e:
                print(f'    [ERROR] Error fetching game {game_id}: {e}')
                continue
        
        print(f'Found stats for {len(player_stats)} players total')
        
    except Exception as e:
        print(f'[ERROR] Error fetching results: {e}')
    
    return player_stats


def find_player_stats(player_name: str, actual_stats: Dict) -> Optional[tuple]:
    """
    Find player stats with fuzzy matching to handle name variations
    
    Handles:
    - Exact match
    - Case-insensitive
    - Spacing differences (J.Kulich vs J. Kulich)
    - Dot variations (E.Lindholm vs E. Lindholm)
    - Nickname variations
    
    Args:
        player_name: Player name from prediction
        actual_stats: Dict of {player_name: stats}
        
    Returns:
        (player stats dict, match_type) or (None, None) if not found
    """
    # Strategy 1: Exact match
    if player_name in actual_stats:
        return actual_stats[player_name], 'exact'
    
    # Strategy 2: Case-insensitive exact match
    for name, stats in actual_stats.items():
        if name.lower() == player_name.lower():
            return stats, 'case_insensitive'
    
    # Strategy 3: Normalize spacing around dots and compare
    # Handles: "J.Kulich" vs "J. Kulich"
    def normalize_name(name):
        """Remove spaces after dots and lowercase"""
        import re
        # Add space after dots if missing: "J.Kulich" -> "J. Kulich"
        name = re.sub(r'\.(?=[A-Z])', '. ', name)
        # Remove extra spaces
        name = ' '.join(name.split())
        return name.lower()
    
    normalized_search = normalize_name(player_name)
    
    for name, stats in actual_stats.items():
        if normalize_name(name) == normalized_search:
            return stats, 'normalized'
    
    # Strategy 4: Remove all spaces/dots and compare
    # Handles: "E. Lindholm" vs "E.Lindholm" vs "ELindholm"
    def strip_all(name):
        return name.replace('.', '').replace(' ', '').replace('-', '').lower()
    
    stripped_search = strip_all(player_name)
    
    for name, stats in actual_stats.items():
        if strip_all(name) == stripped_search:
            return stats, 'stripped'
    
    # Strategy 5: Fuzzy matching (similar names)
    # Handles minor typos or variations
    try:
        from difflib import SequenceMatcher
        
        best_match = None
        best_match_name = None
        best_ratio = 0.85  # 85% similarity threshold
        
        for name, stats in actual_stats.items():
            ratio = SequenceMatcher(None, player_name.lower(), name.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = stats
                best_match_name = name
        
        if best_match:
            return best_match, f'fuzzy_{best_ratio:.0%}'
            
    except ImportError:
        pass
    
    # Not found
    return None, None


def grade_predictions(game_date: str) -> Dict:
    """
    Grade all predictions for given date
    
    Args:
        game_date: Date in YYYY-MM-DD format
        
    Returns:
        Dict with grading results and stats
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get predictions for date
    cursor.execute('''
        SELECT id, player_name, team, opponent, prop_type, line, 
               prediction, probability, confidence_tier
        FROM predictions
        WHERE game_date = ?
    ''', (game_date,))
    
    predictions = cursor.fetchall()
    
    if not predictions:
        print(f'No predictions found for {game_date}')
        conn.close()
        return {}
    
    print(f'Found {len(predictions)} predictions to grade')
    
    # Fetch actual results
    actual_stats = fetch_actual_results(game_date)
    
    if not actual_stats:
        print('Could not fetch actual results - cannot grade')
        conn.close()
        return {}
    
    # Grade each prediction
    results = {
        'total': 0,
        'hits': 0,
        'misses': 0,
        'by_tier': {},
        'by_prop': {},
        'graded': [],
        'match_stats': {
            'exact': 0,
            'case_insensitive': 0,
            'normalized': 0,
            'stripped': 0,
            'fuzzy': 0,
            'not_found': 0
        }
    }
    
    print()
    print('Grading predictions...')
    print()
    
    not_found_count = 0
    not_found_examples = []
    
    for pred in predictions:
        pred_id, player_name, team, opponent, prop_type, line, prediction, probability, tier = pred
        
        # Find player's actual stats using fuzzy matching
        actual, match_type = find_player_stats(player_name, actual_stats)
        
        if not actual:
            results['match_stats']['not_found'] += 1
            not_found_count += 1
            if len(not_found_examples) < 5:
                not_found_examples.append(f'{player_name} ({team})')
            continue
        
        # Track match type
        if match_type.startswith('fuzzy_'):
            results['match_stats']['fuzzy'] += 1
        elif match_type in results['match_stats']:
            results['match_stats'][match_type] += 1
        
        # Get actual stat value
        if prop_type == 'points':
            actual_value = actual['points']
        elif prop_type == 'shots':
            actual_value = actual['shots']
        elif prop_type == 'goals':
            actual_value = actual['goals']
        else:
            print(f'[WARNING] Unknown prop type: {prop_type}')
            continue
        
        # Determine outcome
        if prediction == 'OVER':
            hit = actual_value > line
        else:  # UNDER
            hit = actual_value < line
        
        outcome = 'HIT' if hit else 'MISS'
        
        # Determine what actually happened
        actual_outcome = 'OVER' if actual_value > line else 'UNDER'
        
        # Store in database
        cursor.execute('''
            INSERT INTO prediction_outcomes
            (prediction_id, game_date, player_name, prop_type, line,
             predicted_outcome, predicted_probability, 
             actual_stat_value, actual_outcome, outcome, graded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pred_id, game_date, player_name, prop_type, line,
              prediction, probability, actual_value, actual_outcome, outcome, 
              datetime.now().isoformat()))
        
        # Update stats
        results['total'] += 1
        if hit:
            results['hits'] += 1
        else:
            results['misses'] += 1
        
        # By tier
        if tier not in results['by_tier']:
            results['by_tier'][tier] = {'total': 0, 'hits': 0}
        results['by_tier'][tier]['total'] += 1
        if hit:
            results['by_tier'][tier]['hits'] += 1
        
        # By prop type
        if prop_type not in results['by_prop']:
            results['by_prop'][prop_type] = {'total': 0, 'hits': 0}
        results['by_prop'][prop_type]['total'] += 1
        if hit:
            results['by_prop'][prop_type]['hits'] += 1
        
        results['graded'].append({
            'player': player_name,
            'team': team,
            'prop': f'{prop_type} {prediction} {line}',
            'predicted': probability,
            'actual': actual_value,
            'outcome': outcome
        })
    
    conn.commit()
    conn.close()
    
    # Show not found examples if any
    if not_found_count > 0:
        print()
        print(f'[WARNING] {not_found_count} predictions could not be matched to player stats')
        if not_found_examples:
            print(f'Examples: {", ".join(not_found_examples[:5])}')
            if not_found_count > 5:
                print(f'... and {not_found_count - 5} more')
    
    return results


def print_grading_report(results: Dict, game_date: str):
    """Print detailed grading report"""
    
    if not results or results['total'] == 0:
        print('No predictions graded')
        return
    
    print('='*80)
    print(f'GRADING RESULTS - {game_date}')
    print('='*80)
    print()
    
    # Overall accuracy
    accuracy = results['hits'] / results['total']
    print(f'Overall: {results["hits"]}/{results["total"]} ({accuracy:.1%})')
    print()
    
    # Name matching stats
    if results.get('match_stats'):
        match_stats = results['match_stats']
        total_checked = sum(match_stats.values())
        matched = total_checked - match_stats['not_found']
        
        print('Name Matching:')
        print(f'  Total predictions: {total_checked}')
        print(f'  Successfully matched: {matched} ({matched/total_checked:.1%})')
        print(f'  Not found: {match_stats["not_found"]} ({match_stats["not_found"]/total_checked:.1%})')
        print()
        print('  Match types:')
        if match_stats['exact'] > 0:
            print(f'    Exact: {match_stats["exact"]}')
        if match_stats['case_insensitive'] > 0:
            print(f'    Case-insensitive: {match_stats["case_insensitive"]}')
        if match_stats['normalized'] > 0:
            print(f'    Normalized (spacing): {match_stats["normalized"]}')
        if match_stats['stripped'] > 0:
            print(f'    Stripped (dots/spaces): {match_stats["stripped"]}')
        if match_stats['fuzzy'] > 0:
            print(f'    Fuzzy (similarity): {match_stats["fuzzy"]}')
        print()
    
    # By tier
    if results['by_tier']:
        print('By Confidence Tier:')
        for tier in sorted(results['by_tier'].keys()):
            stats = results['by_tier'][tier]
            tier_acc = stats['hits'] / stats['total'] if stats['total'] > 0 else 0
            print(f'  {tier}: {stats["hits"]}/{stats["total"]} ({tier_acc:.1%})')
        print()
    
    # By prop type
    if results['by_prop']:
        print('By Prop Type:')
        for prop in sorted(results['by_prop'].keys()):
            stats = results['by_prop'][prop]
            prop_acc = stats['hits'] / stats['total'] if stats['total'] > 0 else 0
            print(f'  {prop}: {stats["hits"]}/{stats["total"]} ({prop_acc:.1%})')
        print()
    
    # Sample of results
    print('Sample Results (first 10):')
    for result in results['graded'][:10]:
        emoji = '[OK]' if result['outcome'] == 'HIT' else '[ERROR]'
        print(f'  {emoji} {result["player"]} ({result["team"]}): {result["prop"]} - '
              f'Predicted {result["predicted"]:.1%}, Actual {result["actual"]} - {result["outcome"]}')
    
    if len(results['graded']) > 10:
        print(f'  ... and {len(results["graded"]) - 10} more')
    
    print()
    print('='*80)


def main():
    """Main grading function"""
    
    print()
    print('='*80)
    print('AUTO-GRADING PREDICTIONS - V2 FIXED')
    print('='*80)
    print()
    
    # Determine target date
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        # Default to yesterday
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f'Grading target: {target_date}')
    print()
    
    # Grade predictions
    results = grade_predictions(target_date)
    
    if results and results['total'] > 0:
        # Print report
        print_grading_report(results, target_date)
        
        # Send Discord notification
        try:
            accuracy = results['hits'] / results['total']
            
            # Match stats
            match_stats = results.get('match_stats', {})
            total_checked = sum(match_stats.values())
            matched = total_checked - match_stats.get('not_found', 0)
            match_rate = matched / total_checked if total_checked > 0 else 0
            
            message = f"""**[OK] GRADING COMPLETE - {target_date}**

Overall: {results['hits']}/{results['total']} ({accuracy:.1%})
Name matching: {matched}/{total_checked} ({match_rate:.1%})

By Prop Type:
"""
            for prop in sorted(results['by_prop'].keys()):
                stats = results['by_prop'][prop]
                prop_acc = stats['hits'] / stats['total'] if stats['total'] > 0 else 0
                message += f"• {prop}: {stats['hits']}/{stats['total']} ({prop_acc:.1%})\n"
            
            # Try to send notification
            try:
                send_discord_notification(message)
            except TypeError:
                # If function signature requires title and message separately
                notify_workflow_success(f"Grading Complete - {target_date}", message)
        except Exception as e:
            print(f'Could not send Discord notification: {e}')
        
        return 0
    else:
        print('[ERROR] Grading failed or no predictions to grade')
        return 1


if __name__ == '__main__':
    sys.exit(main())
