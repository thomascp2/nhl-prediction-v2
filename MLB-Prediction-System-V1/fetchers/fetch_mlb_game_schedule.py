"""
MLB Game Schedule Fetcher
=========================
Fetches MLB game schedules from official MLB Stats API
- Game dates, times, teams
- Starting pitchers (with handedness!)
- Vegas lines (if available)
- Weather data
- Park information

For backtesting: Fetch 2025 season (April-October)
For live: Fetch current day's games
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import mlb_config
from utils.db_utils import get_db_connection

# MLB Stats API endpoints (Official MLB API - Free!)
MLB_STATS_API = "https://statsapi.mlb.com/api/v1"
MLB_SCHEDULE_ENDPOINT = f"{MLB_STATS_API}/schedule"

def fetch_games_for_date(game_date: str) -> List[Dict]:
    """
    Fetch all MLB games for a specific date

    Args:
        game_date: Date in YYYY-MM-DD format

    Returns:
        List of game dictionaries
    """
    print(f"\n⚾ Fetching MLB games for {game_date}...")

    url = MLB_SCHEDULE_ENDPOINT
    params = {
        'sportId': 1,  # MLB
        'date': game_date,
        'hydrate': 'probablePitcher,weather,venue'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        games = []

        if 'dates' not in data or not data['dates']:
            print(f"  No games found for {game_date}")
            return games

        for date_entry in data['dates']:
            for game in date_entry.get('games', []):
                game_data = parse_mlb_game(game)
                if game_data:
                    games.append(game_data)

        print(f"✅ Found {len(games)} games for {game_date}")
        return games

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching games: {e}")
        return []


def parse_mlb_game(game: Dict) -> Optional[Dict]:
    """Parse MLB Stats API game data into our database format"""
    try:
        # Get game date/time
        game_datetime_str = game.get('gameDate', '')
        if game_datetime_str:
            game_datetime = datetime.strptime(game_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
            game_date = game_datetime.strftime("%Y-%m-%d")
            game_time = game_datetime.strftime("%H:%M")
        else:
            return None

        # Get teams
        teams = game.get('teams', {})
        home_team_data = teams.get('home', {}).get('team', {})
        away_team_data = teams.get('away', {}).get('team', {})

        home_team = home_team_data.get('abbreviation', home_team_data.get('teamCode', ''))
        away_team = away_team_data.get('abbreviation', away_team_data.get('teamCode', ''))

        if not home_team or not away_team:
            return None

        # Get starting pitchers
        home_pitcher = None
        away_pitcher = None
        home_pitcher_hand = None
        away_pitcher_hand = None

        # Probable pitchers
        home_probable = teams.get('home', {}).get('probablePitcher', {})
        away_probable = teams.get('away', {}).get('probablePitcher', {})

        if home_probable:
            home_pitcher = home_probable.get('fullName')
            home_pitcher_hand = home_probable.get('pitchHand', {}).get('code')  # 'L' or 'R'

        if away_probable:
            away_pitcher = away_probable.get('fullName')
            away_pitcher_hand = away_probable.get('pitchHand', {}).get('code')

        # Get venue (park)
        venue = game.get('venue', {})
        park_name = venue.get('name', '')

        # Check if dome
        # We can look this up from our park_factors table later
        is_dome = False  # Will be updated from database

        # Get weather
        weather = game.get('weather', {})
        temperature = weather.get('temp')
        wind_speed = weather.get('wind')
        conditions = weather.get('condition', '')

        # Parse wind direction if available
        wind_direction = None
        if wind_speed:
            wind_str = str(wind_speed).lower()
            if 'out' in wind_str:
                wind_direction = 'out'
            elif 'in' in wind_str:
                wind_direction = 'in'
            elif 'cross' in wind_str or 'left' in wind_str or 'right' in wind_str:
                wind_direction = 'cross'
            else:
                wind_direction = 'calm'

            # Extract numeric wind speed
            import re
            wind_match = re.search(r'(\d+)', str(wind_speed))
            if wind_match:
                wind_speed = int(wind_match.group(1))
            else:
                wind_speed = None

        # Get scores (if game completed)
        home_score = teams.get('home', {}).get('score')
        away_score = teams.get('away', {}).get('score')

        # Check if game completed
        status = game.get('status', {})
        status_code = status.get('statusCode', '')
        game_completed = status_code in ['F', 'FR', 'FT']  # Final, Final (Rain), Final (Tied)

        # Note: MLB Stats API doesn't provide Vegas lines
        # We'd need to fetch these from a sports betting API
        # For now, set to None
        total = None
        home_ml = None
        away_ml = None
        spread = None  # MLB uses "run line" (-1.5/+1.5)
        home_implied_runs = None
        away_implied_runs = None

        game_data = {
            'game_date': game_date,
            'game_time': game_time,
            'home_team': home_team,
            'away_team': away_team,
            'home_pitcher': home_pitcher,
            'away_pitcher': away_pitcher,
            'home_pitcher_hand': home_pitcher_hand,
            'away_pitcher_hand': away_pitcher_hand,
            'total': total,
            'home_ml': home_ml,
            'away_ml': away_ml,
            'spread': spread,
            'home_implied_runs': home_implied_runs,
            'away_implied_runs': away_implied_runs,
            'temperature': temperature,
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'conditions': conditions if conditions else None,
            'park_name': park_name,
            'is_dome': 1 if is_dome else 0,
            'home_score': home_score,
            'away_score': away_score,
            'game_completed': 1 if game_completed else 0,
        }

        return game_data

    except Exception as e:
        print(f"⚠️  Error parsing game: {e}")
        return None


def save_games_to_db(games: List[Dict]) -> int:
    """Save games to database"""
    if not games:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    saved_count = 0

    for game in games:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO game_schedule (
                    game_date, game_time,
                    home_team, away_team,
                    home_pitcher, away_pitcher,
                    home_pitcher_hand, away_pitcher_hand,
                    total, home_ml, away_ml, spread,
                    home_implied_runs, away_implied_runs,
                    temperature, wind_speed, wind_direction, conditions,
                    park_name, is_dome,
                    home_score, away_score, game_completed,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                game['game_date'], game['game_time'],
                game['home_team'], game['away_team'],
                game['home_pitcher'], game['away_pitcher'],
                game['home_pitcher_hand'], game['away_pitcher_hand'],
                game['total'], game['home_ml'], game['away_ml'], game['spread'],
                game['home_implied_runs'], game['away_implied_runs'],
                game['temperature'], game['wind_speed'], game['wind_direction'], game['conditions'],
                game['park_name'], game['is_dome'],
                game['home_score'], game['away_score'], game['game_completed']
            ))
            saved_count += 1
        except Exception as e:
            print(f"⚠️  Error saving game {game['home_team']} vs {game['away_team']}: {e}")

    conn.commit()
    conn.close()

    return saved_count


def fetch_date_range(start_date: str, end_date: str) -> int:
    """
    Fetch games for a date range

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Total number of games saved
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"⚾ FETCHING MLB GAMES")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"{'='*60}")

    total_saved = 0
    current_dt = start_dt

    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        games = fetch_games_for_date(date_str)
        saved = save_games_to_db(games)
        total_saved += saved

        if saved > 0:
            print(f"  {date_str}: {saved} games saved")

        current_dt += timedelta(days=1)

    print(f"\n✅ Total games saved: {total_saved}")
    return total_saved


def fetch_full_season(season: int = 2025) -> int:
    """
    Fetch entire MLB season

    Args:
        season: Season year (e.g., 2025)

    Returns:
        Total number of games saved
    """
    # MLB season typically runs April through October
    if season == 2025:
        start_date = "2025-03-27"  # Opening Day
        end_date = "2025-09-28"  # Last day of regular season
    elif season == 2024:
        start_date = "2024-03-28"
        end_date = "2024-09-29"
    else:
        # Generic
        start_date = f"{season}-03-28"
        end_date = f"{season}-09-29"

    return fetch_date_range(start_date, end_date)


def test_fetcher():
    """Test the fetcher with a single day"""
    print("\n" + "="*60)
    print("🧪 TESTING MLB GAME SCHEDULE FETCHER")
    print("="*60)

    # Test with Opening Day 2025
    games = fetch_games_for_date("2025-03-27")

    if games:
        print(f"\n📊 Sample Game Data:")
        print(json.dumps(games[0], indent=2))

        # Save to database
        saved = save_games_to_db(games)
        print(f"\n✅ Saved {saved} games to database")

        # Verify in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM game_schedule WHERE game_date = '2025-03-27'")
        count = cursor.fetchone()[0]
        conn.close()

        print(f"✅ Verified: {count} games in database for 2025-03-27")
    else:
        print("⚠️  No games found (may not be scheduled yet)")


if __name__ == "__main__":
    # Run test
    test_fetcher()

    # Uncomment to fetch full 2025 season:
    # fetch_full_season(2025)

    # Or fetch specific date range:
    # fetch_date_range("2025-04-01", "2025-04-07")  # First week
