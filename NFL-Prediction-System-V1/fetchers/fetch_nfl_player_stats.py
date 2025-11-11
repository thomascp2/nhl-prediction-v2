"""
NFL Player Stats Fetcher
========================
Fetches NFL player game logs from ESPN API
- Passing stats (QB)
- Rushing stats (RB, QB)
- Receiving stats (WR, TE, RB)
- Opportunity metrics (targets, snap count)

For backtesting: Fetch 2024-2025 season game logs
For live: Fetch current season stats
"""

import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from utils.db_utils import get_db_connection

# ESPN API endpoints
ESPN_PLAYER_STATS = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/athletes/{player_id}/gamelog"
ESPN_TEAM_ROSTER = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/roster"

# NFL Team IDs for ESPN API
NFL_TEAM_IDS = {
    'ARI': '22', 'ATL': '1', 'BAL': '33', 'BUF': '2',
    'CAR': '29', 'CHI': '3', 'CIN': '4', 'CLE': '5',
    'DAL': '6', 'DEN': '7', 'DET': '8', 'GB': '9',
    'HOU': '34', 'IND': '11', 'JAX': '30', 'KC': '12',
    'LV': '13', 'LAC': '24', 'LAR': '14', 'MIA': '15',
    'MIN': '16', 'NE': '17', 'NO': '18', 'NYG': '19',
    'NYJ': '20', 'PHI': '21', 'PIT': '23', 'SF': '25',
    'SEA': '26', 'TB': '27', 'TEN': '10', 'WAS': '28'
}


def fetch_team_roster(team_abbr: str, season: int = 2024) -> List[Dict]:
    """
    Fetch team roster with player IDs

    Args:
        team_abbr: Team abbreviation (e.g., 'KC', 'BUF')
        season: Season year

    Returns:
        List of player dictionaries with IDs
    """
    team_id = NFL_TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"⚠️  Unknown team: {team_abbr}")
        return []

    print(f"  Fetching roster for {team_abbr}...")

    url = ESPN_TEAM_ROSTER.format(team_id=team_id)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        players = []
        athletes = data.get('athletes', [])

        for athlete in athletes:
            player = {
                'player_id': athlete.get('id'),
                'player_name': athlete.get('displayName'),
                'team': team_abbr,
                'position': athlete.get('position', {}).get('abbreviation'),
            }
            players.append(player)

        print(f"    Found {len(players)} players")
        return players

    except Exception as e:
        print(f"❌ Error fetching roster for {team_abbr}: {e}")
        return []


def fetch_player_game_log(player_id: str, player_name: str, team: str, season: int = 2024) -> List[Dict]:
    """
    Fetch player's game log for the season

    Args:
        player_id: ESPN player ID
        player_name: Player's name
        team: Team abbreviation
        season: Season year

    Returns:
        List of game log dictionaries
    """
    url = ESPN_PLAYER_STATS.format(player_id=player_id)
    params = {'season': season, 'seasontype': 2}  # seasontype=2 is regular season

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        game_logs = []

        # ESPN returns game logs in different structures depending on the player
        if 'events' not in data:
            return game_logs

        for event in data['events']:
            game_log = parse_player_game_stats(event, player_name, team)
            if game_log:
                game_logs.append(game_log)

        return game_logs

    except Exception as e:
        print(f"    ⚠️  Error fetching stats for {player_name}: {e}")
        return []


def parse_player_game_stats(event: Dict, player_name: str, team: str) -> Optional[Dict]:
    """Parse ESPN game log data into our database format"""
    try:
        # Get game date and week
        game_date_str = event.get('gameDate', '')
        if game_date_str:
            game_datetime = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%MZ")
            game_date = game_datetime.strftime("%Y-%m-%d")
        else:
            return None

        # Get opponent
        opponent = event.get('opponent', {}).get('abbreviation', '')
        home_away = 'home' if event.get('homeAway') == 'home' else 'away'

        # Get stats
        stats = event.get('stats', {})

        # Initialize all stat fields
        game_log = {
            'game_date': game_date,
            'week_number': event.get('week', {}).get('number'),
            'player_name': player_name,
            'team': team,
            'opponent': opponent,
            'home_away': home_away,
            'position': None,  # Will be filled from roster
        }

        # Parse passing stats (QB)
        passing_stats = stats.get('passing', {})
        game_log['pass_attempts'] = passing_stats.get('completions-attempts', '0-0').split('-')[1] if passing_stats else None
        game_log['pass_completions'] = passing_stats.get('completions-attempts', '0-0').split('-')[0] if passing_stats else None
        game_log['pass_yards'] = passing_stats.get('yards')
        game_log['pass_tds'] = passing_stats.get('touchdowns')
        game_log['interceptions'] = passing_stats.get('interceptions')
        game_log['qb_rating'] = passing_stats.get('QBRating')

        # Parse rushing stats
        rushing_stats = stats.get('rushing', {})
        game_log['rush_attempts'] = rushing_stats.get('attempts')
        game_log['rush_yards'] = rushing_stats.get('yards')
        game_log['rush_tds'] = rushing_stats.get('touchdowns')
        game_log['yards_per_carry'] = rushing_stats.get('avg')

        # Parse receiving stats
        receiving_stats = stats.get('receiving', {})
        game_log['targets'] = receiving_stats.get('targets')
        game_log['receptions'] = receiving_stats.get('receptions')
        game_log['rec_yards'] = receiving_stats.get('yards')
        game_log['rec_tds'] = receiving_stats.get('touchdowns')
        game_log['yards_per_reception'] = receiving_stats.get('avg')

        # Note: ESPN API doesn't provide all advanced metrics
        # We'll need to set these as None and potentially fetch from another source
        game_log['snap_count'] = None
        game_log['snap_pct'] = None
        game_log['target_share'] = None
        game_log['air_yards_share'] = None
        game_log['red_zone_targets'] = None
        game_log['red_zone_carries'] = None
        game_log['game_script'] = None
        game_log['team_score'] = None
        game_log['opp_score'] = None
        game_log['game_total'] = None
        game_log['fumbles'] = None
        game_log['fumbles_lost'] = None

        return game_log

    except Exception as e:
        print(f"    ⚠️  Error parsing game stats: {e}")
        return None


def save_game_logs_to_db(game_logs: List[Dict]) -> int:
    """Save player game logs to database"""
    if not game_logs:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    saved_count = 0

    for log in game_logs:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_game_logs (
                    game_date, week_number, player_name, team, opponent, home_away, position,
                    pass_attempts, pass_completions, pass_yards, pass_tds, interceptions, qb_rating,
                    rush_attempts, rush_yards, rush_tds, yards_per_carry,
                    targets, receptions, rec_yards, rec_tds, yards_per_reception,
                    snap_count, snap_pct, target_share, air_yards_share,
                    red_zone_targets, red_zone_carries,
                    game_script, team_score, opp_score, game_total,
                    fumbles, fumbles_lost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log['game_date'], log['week_number'], log['player_name'], log['team'],
                log['opponent'], log['home_away'], log['position'],
                log['pass_attempts'], log['pass_completions'], log['pass_yards'],
                log['pass_tds'], log['interceptions'], log['qb_rating'],
                log['rush_attempts'], log['rush_yards'], log['rush_tds'], log['yards_per_carry'],
                log['targets'], log['receptions'], log['rec_yards'],
                log['rec_tds'], log['yards_per_reception'],
                log['snap_count'], log['snap_pct'], log['target_share'], log['air_yards_share'],
                log['red_zone_targets'], log['red_zone_carries'],
                log['game_script'], log['team_score'], log['opp_score'], log['game_total'],
                log['fumbles'], log['fumbles_lost']
            ))
            saved_count += 1
        except Exception as e:
            print(f"    ⚠️  Error saving game log: {e}")

    conn.commit()
    conn.close()

    return saved_count


def fetch_team_stats(team_abbr: str, season: int = 2024, positions: List[str] = ['QB', 'RB', 'WR', 'TE']) -> int:
    """
    Fetch all game logs for a team's key players

    Args:
        team_abbr: Team abbreviation
        season: Season year
        positions: List of positions to fetch

    Returns:
        Total number of game logs saved
    """
    print(f"\n🏈 Fetching stats for {team_abbr} ({season} season)...")

    # Get roster
    roster = fetch_team_roster(team_abbr, season)

    if not roster:
        return 0

    # Filter to key positions
    key_players = [p for p in roster if p['position'] in positions]
    print(f"  Found {len(key_players)} players at positions {positions}")

    total_saved = 0

    for player in key_players:
        print(f"  {player['player_name']} ({player['position']})...")

        game_logs = fetch_player_game_log(
            player['player_id'],
            player['player_name'],
            player['team'],
            season
        )

        # Add position to game logs
        for log in game_logs:
            log['position'] = player['position']

        saved = save_game_logs_to_db(game_logs)
        total_saved += saved

        if saved > 0:
            print(f"    ✅ Saved {saved} game logs")

        # Rate limiting
        time.sleep(0.5)

    return total_saved


def fetch_full_league_stats(season: int = 2024, teams: Optional[List[str]] = None) -> int:
    """
    Fetch game logs for entire league

    Args:
        season: Season year
        teams: Optional list of team abbreviations (fetches all if None)

    Returns:
        Total number of game logs saved
    """
    if teams is None:
        teams = list(NFL_TEAM_IDS.keys())

    print(f"\n{'='*60}")
    print(f"🏈 FETCHING NFL {season} SEASON PLAYER STATS")
    print(f"  Teams: {len(teams)}")
    print(f"{'='*60}")

    total_saved = 0

    for team in teams:
        saved = fetch_team_stats(team, season)
        total_saved += saved
        print(f"  {team}: {saved} game logs saved\n")

    print(f"\n✅ Total game logs saved: {total_saved}")
    return total_saved


def test_fetcher():
    """Test the fetcher with one team"""
    print("\n" + "="*60)
    print("🧪 TESTING NFL PLAYER STATS FETCHER")
    print("="*60)

    # Test with Kansas City Chiefs
    saved = fetch_team_stats('KC', 2024, positions=['QB', 'RB', 'WR', 'TE'])

    print(f"\n✅ Test complete: {saved} game logs saved")

    # Verify in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_game_logs WHERE team = 'KC'")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"✅ Verified: {count} game logs in database for KC")


if __name__ == "__main__":
    # Run test
    test_fetcher()

    # Uncomment to fetch full league:
    # fetch_full_league_stats(2024)
