"""
MLB Player Stats Fetcher
========================
Fetches MLB player game logs from official MLB Stats API
- Pitcher stats (IP, K, ER, etc.)
- Batter stats (H, HR, RBI, etc.)
- Handedness (L/R)
- Opposing pitcher/team

For backtesting: Fetch 2025 season game logs
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

import mlb_config
from utils.db_utils import get_db_connection

# MLB Stats API endpoints
MLB_STATS_API = "https://statsapi.mlb.com/api/v1"
MLB_TEAM_ROSTER = f"{MLB_STATS_API}/teams/{{team_id}}/roster"
MLB_PLAYER_STATS = f"{MLB_STATS_API}/people/{{player_id}}/stats"

# MLB Team IDs
MLB_TEAM_IDS = {
    'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111,
    'CHC': 112, 'CWS': 145, 'CIN': 113, 'CLE': 114,
    'COL': 115, 'DET': 116, 'HOU': 117, 'KC': 118,
    'LAA': 108, 'LAD': 119, 'MIA': 146, 'MIL': 158,
    'MIN': 142, 'NYM': 121, 'NYY': 147, 'OAK': 133,
    'PHI': 143, 'PIT': 134, 'SD': 135, 'SF': 137,
    'SEA': 136, 'STL': 138, 'TB': 139, 'TEX': 140,
    'TOR': 141, 'WAS': 120
}


def fetch_team_roster(team_abbr: str, season: int = 2025) -> List[Dict]:
    """
    Fetch team roster with player IDs

    Args:
        team_abbr: Team abbreviation (e.g., 'NYY', 'LAD')
        season: Season year

    Returns:
        List of player dictionaries
    """
    team_id = MLB_TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"⚠️  Unknown team: {team_abbr}")
        return []

    print(f"  Fetching roster for {team_abbr}...")

    url = MLB_TEAM_ROSTER.format(team_id=team_id)
    params = {'season': season}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        players = []
        roster = data.get('roster', [])

        for entry in roster:
            person = entry.get('person', {})
            position = entry.get('position', {})

            player = {
                'player_id': person.get('id'),
                'player_name': person.get('fullName'),
                'team': team_abbr,
                'position': position.get('abbreviation'),
                'player_type': None  # Will determine from position
            }

            # Determine if pitcher or batter
            pos = player['position']
            if pos == 'P':
                player['player_type'] = 'pitcher'
            else:
                player['player_type'] = 'batter'

            players.append(player)

        print(f"    Found {len(players)} players")
        return players

    except Exception as e:
        print(f"❌ Error fetching roster for {team_abbr}: {e}")
        return []


def fetch_player_game_log(player_id: str, player_name: str, team: str, player_type: str, season: int = 2025) -> List[Dict]:
    """
    Fetch player's game log for the season

    Args:
        player_id: MLB player ID
        player_name: Player's name
        team: Team abbreviation
        player_type: 'pitcher' or 'batter'
        season: Season year

    Returns:
        List of game log dictionaries
    """
    url = MLB_PLAYER_STATS.format(player_id=player_id)

    # Different stat groups for pitchers vs batters
    if player_type == 'pitcher':
        group = 'pitching'
        stat_type = 'gameLog'
    else:
        group = 'hitting'
        stat_type = 'gameLog'

    params = {
        'stats': stat_type,
        'group': group,
        'season': season
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        game_logs = []

        stats_data = data.get('stats', [])
        if not stats_data:
            return game_logs

        for stat_group in stats_data:
            splits = stat_group.get('splits', [])

            for split in splits:
                game_log = parse_player_game_log(split, player_name, team, player_type)
                if game_log:
                    game_logs.append(game_log)

        return game_logs

    except Exception as e:
        print(f"    ⚠️  Error fetching stats for {player_name}: {e}")
        return []


def parse_player_game_log(split: Dict, player_name: str, team: str, player_type: str) -> Optional[Dict]:
    """Parse MLB Stats API game log data"""
    try:
        # Get game info
        game = split.get('game', {})
        game_date_str = split.get('date', '')

        if not game_date_str:
            return None

        game_date = game_date_str  # Already in YYYY-MM-DD format

        # Get opponent
        opponent = split.get('opponent', {}).get('abbreviation', '')

        # Home/away
        is_home = split.get('isHome', False)
        home_away = 'home' if is_home else 'away'

        # Get stats
        stat = split.get('stat', {})

        # Initialize game log
        game_log = {
            'game_date': game_date,
            'player_name': player_name,
            'player_type': player_type,
            'team': team,
            'opponent': opponent,
            'home_away': home_away,
        }

        if player_type == 'pitcher':
            # Pitcher stats
            game_log['at_bats'] = None
            game_log['hits'] = None
            game_log['doubles'] = None
            game_log['triples'] = None
            game_log['home_runs'] = None
            game_log['rbis'] = None
            game_log['runs'] = None
            game_log['walks'] = None
            game_log['batter_strikeouts'] = None
            game_log['stolen_bases'] = None
            game_log['total_bases'] = None
            game_log['batting_avg'] = None
            game_log['on_base_pct'] = None
            game_log['slugging_pct'] = None

            # Pitcher-specific stats
            game_log['innings_pitched'] = float(stat.get('inningsPitched', 0))
            game_log['earned_runs'] = stat.get('earnedRuns')
            game_log['pitcher_strikeouts'] = stat.get('strikeOuts')
            game_log['walks_allowed'] = stat.get('baseOnBalls')
            game_log['hits_allowed'] = stat.get('hits')
            game_log['home_runs_allowed'] = stat.get('homeRuns')
            game_log['pitch_count'] = stat.get('numberOfPitches')

            # Calculate pitches per inning
            if game_log['innings_pitched'] and game_log['pitch_count']:
                game_log['pitches_per_inning'] = game_log['pitch_count'] / game_log['innings_pitched']
            else:
                game_log['pitches_per_inning'] = None

            # Win/Loss
            decisions = stat.get('decisions', '')
            game_log['win_loss'] = decisions if decisions in ['W', 'L', 'S'] else 'ND'

            # ERA and WHIP
            game_log['era'] = stat.get('era')
            game_log['whip'] = stat.get('whip')

            game_log['opposing_pitcher'] = None  # N/A for pitchers

        else:
            # Batter stats
            game_log['at_bats'] = stat.get('atBats')
            game_log['hits'] = stat.get('hits')
            game_log['doubles'] = stat.get('doubles')
            game_log['triples'] = stat.get('triples')
            game_log['home_runs'] = stat.get('homeRuns')
            game_log['rbis'] = stat.get('rbi')
            game_log['runs'] = stat.get('runs')
            game_log['walks'] = stat.get('baseOnBalls')
            game_log['batter_strikeouts'] = stat.get('strikeOuts')
            game_log['stolen_bases'] = stat.get('stolenBases')

            # Calculate total bases (1B + 2×2B + 3×3B + 4×HR)
            singles = game_log['hits'] - game_log['doubles'] - game_log['triples'] - game_log['home_runs']
            game_log['total_bases'] = (singles +
                                       2 * game_log['doubles'] +
                                       3 * game_log['triples'] +
                                       4 * game_log['home_runs'])

            game_log['batting_avg'] = stat.get('avg')
            game_log['on_base_pct'] = stat.get('obp')
            game_log['slugging_pct'] = stat.get('slg')

            # Pitcher-specific (None for batters)
            game_log['innings_pitched'] = None
            game_log['earned_runs'] = None
            game_log['pitcher_strikeouts'] = None
            game_log['walks_allowed'] = None
            game_log['hits_allowed'] = None
            game_log['home_runs_allowed'] = None
            game_log['pitch_count'] = None
            game_log['pitches_per_inning'] = None
            game_log['win_loss'] = None
            game_log['era'] = None
            game_log['whip'] = None

            game_log['opposing_pitcher'] = None  # Would need to fetch from game_schedule

        # Get park name (would need to fetch from game data)
        game_log['park_name'] = None
        game_log['temperature'] = None
        game_log['wind_speed'] = None

        return game_log

    except Exception as e:
        print(f"    ⚠️  Error parsing game log: {e}")
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
                    game_date, player_name, player_type, team, opponent, home_away,
                    at_bats, hits, doubles, triples, home_runs, rbis, runs, walks,
                    batter_strikeouts, stolen_bases, total_bases,
                    batting_avg, on_base_pct, slugging_pct,
                    innings_pitched, earned_runs, pitcher_strikeouts,
                    walks_allowed, hits_allowed, home_runs_allowed,
                    pitch_count, pitches_per_inning, win_loss, era, whip,
                    opposing_pitcher, park_name, temperature, wind_speed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log['game_date'], log['player_name'], log['player_type'],
                log['team'], log['opponent'], log['home_away'],
                log['at_bats'], log['hits'], log['doubles'], log['triples'],
                log['home_runs'], log['rbis'], log['runs'], log['walks'],
                log['batter_strikeouts'], log['stolen_bases'], log['total_bases'],
                log['batting_avg'], log['on_base_pct'], log['slugging_pct'],
                log['innings_pitched'], log['earned_runs'], log['pitcher_strikeouts'],
                log['walks_allowed'], log['hits_allowed'], log['home_runs_allowed'],
                log['pitch_count'], log['pitches_per_inning'], log['win_loss'],
                log['era'], log['whip'],
                log['opposing_pitcher'], log['park_name'],
                log['temperature'], log['wind_speed']
            ))
            saved_count += 1
        except Exception as e:
            print(f"    ⚠️  Error saving game log: {e}")

    conn.commit()
    conn.close()

    return saved_count


def fetch_team_stats(team_abbr: str, season: int = 2025, player_types: List[str] = ['pitcher', 'batter']) -> int:
    """
    Fetch all game logs for a team's players

    Args:
        team_abbr: Team abbreviation
        season: Season year
        player_types: List of player types to fetch

    Returns:
        Total number of game logs saved
    """
    print(f"\n⚾ Fetching stats for {team_abbr} ({season} season)...")

    # Get roster
    roster = fetch_team_roster(team_abbr, season)

    if not roster:
        return 0

    # Filter to requested player types
    players = [p for p in roster if p['player_type'] in player_types]
    print(f"  Found {len(players)} players ({player_types})")

    total_saved = 0

    for player in players:
        print(f"  {player['player_name']} ({player['player_type']})...")

        game_logs = fetch_player_game_log(
            player['player_id'],
            player['player_name'],
            player['team'],
            player['player_type'],
            season
        )

        saved = save_game_logs_to_db(game_logs)
        total_saved += saved

        if saved > 0:
            print(f"    ✅ Saved {saved} game logs")

        # Rate limiting
        time.sleep(0.3)

    return total_saved


def fetch_full_league_stats(season: int = 2025, teams: Optional[List[str]] = None) -> int:
    """
    Fetch game logs for entire league

    Args:
        season: Season year
        teams: Optional list of team abbreviations

    Returns:
        Total number of game logs saved
    """
    if teams is None:
        teams = list(MLB_TEAM_IDS.keys())

    print(f"\n{'='*60}")
    print(f"⚾ FETCHING MLB {season} SEASON PLAYER STATS")
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
    print("🧪 TESTING MLB PLAYER STATS FETCHER")
    print("="*60)

    # Test with Los Angeles Dodgers
    saved = fetch_team_stats('LAD', 2025, player_types=['pitcher', 'batter'])

    print(f"\n✅ Test complete: {saved} game logs saved")

    # Verify in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_game_logs WHERE team = 'LAD'")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"✅ Verified: {count} game logs in database for LAD")


if __name__ == "__main__":
    # Run test
    test_fetcher()

    # Uncomment to fetch full league:
    # fetch_full_league_stats(2025)
