"""
NFL Game Schedule Fetcher
=========================
Fetches NFL game schedules from ESPN API
- Game dates, times, teams
- Vegas lines (spread, total, moneyline)
- Weather data (if available)
- Home/away teams

For backtesting: Fetch 2024-2025 season (Weeks 1-18 + playoffs)
For live: Fetch current week's games
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config
from utils.db_utils import get_db_connection

# ESPN API endpoints
ESPN_NFL_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ESPN_NFL_SCHEDULE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/schedule"


def fetch_games_for_week(season: int, week: int) -> List[Dict]:
    """
    Fetch all games for a specific week

    Args:
        season: NFL season year (e.g., 2024 for 2024-2025 season)
        week: Week number (1-18 for regular season, 19-22 for playoffs)

    Returns:
        List of game dictionaries
    """
    print(f"\n🏈 Fetching NFL games for {season} Season, Week {week}...")

    # ESPN API uses dates, so we need to estimate the week's date range
    # NFL typically starts first Thursday of September
    # Each week is roughly 7 days apart

    # Calculate approximate date for the week
    if season == 2024:
        season_start = datetime(2024, 9, 5)  # Week 1 started Sept 5, 2024
    elif season == 2025:
        season_start = datetime(2025, 9, 4)  # Week 1 starts Sept 4, 2025 (estimated)
    else:
        # Generic calculation
        season_start = datetime(season, 9, 7)  # First Thursday of September

    # Calculate the date for this week (subtract 1 because week 1 is the start date)
    week_date = season_start + timedelta(weeks=(week - 1))

    # Format date for API (YYYYMMDD)
    date_str = week_date.strftime("%Y%m%d")

    # Build URL
    url = f"{ESPN_NFL_SCOREBOARD}?dates={date_str}&seasontype=2&week={week}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        games = []

        if 'events' not in data:
            print(f"⚠️  No games found for Week {week}")
            return games

        for event in data['events']:
            game = parse_espn_game(event, season, week)
            if game:
                games.append(game)

        print(f"✅ Found {len(games)} games for Week {week}")
        return games

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching games: {e}")
        return []


def parse_espn_game(event: Dict, season: int, week: int) -> Optional[Dict]:
    """Parse ESPN API game data into our database format"""
    try:
        # Get game date/time
        game_date_str = event.get('date', '')
        if game_date_str:
            game_datetime = datetime.strptime(game_date_str, "%Y-%m-%dT%H:%MZ")
            game_date = game_datetime.strftime("%Y-%m-%d")
            game_time = game_datetime.strftime("%H:%M")
        else:
            return None

        # Get teams
        competitions = event.get('competitions', [])
        if not competitions:
            return None

        competition = competitions[0]
        competitors = competition.get('competitors', [])

        if len(competitors) != 2:
            return None

        # Figure out home/away
        home_team = None
        away_team = None
        home_score = None
        away_score = None

        for competitor in competitors:
            team_abbr = competitor.get('team', {}).get('abbreviation', '')
            is_home = competitor.get('homeAway', '') == 'home'
            score = competitor.get('score')

            if is_home:
                home_team = team_abbr
                home_score = int(score) if score else None
            else:
                away_team = team_abbr
                away_score = int(score) if score else None

        if not home_team or not away_team:
            return None

        # Get Vegas lines (if available)
        odds = competition.get('odds', [])
        spread = None
        total = None
        home_ml = None
        away_ml = None

        if odds:
            odd = odds[0]
            spread = odd.get('spread')
            total = odd.get('overUnder')

            # Moneylines
            if 'homeTeamOdds' in odd:
                home_ml = odd['homeTeamOdds'].get('moneyLine')
            if 'awayTeamOdds' in odd:
                away_ml = odd['awayTeamOdds'].get('moneyLine')

        # Calculate implied points from total and spread
        home_implied_points = None
        away_implied_points = None
        if total and spread:
            # Home team gets total/2 - spread/2
            # Away team gets total/2 + spread/2
            home_implied_points = (total / 2) - (spread / 2)
            away_implied_points = (total / 2) + (spread / 2)

        # Determine if dome
        venue = competition.get('venue', {})
        venue_name = venue.get('fullName', '')
        is_dome = venue.get('indoor', False)

        # Get weather (if available)
        weather = competition.get('weather', {})
        weather_temp = weather.get('temperature')
        weather_condition = weather.get('displayValue', '')

        # Parse wind from weather condition (if available)
        weather_wind = None
        if 'wind' in weather_condition.lower():
            # Try to extract wind speed from string like "Wind 15 MPH"
            import re
            wind_match = re.search(r'(\d+)\s*mph', weather_condition, re.IGNORECASE)
            if wind_match:
                weather_wind = int(wind_match.group(1))

        # Check if game is completed
        status = event.get('status', {})
        game_completed = status.get('type', {}).get('completed', False)

        game_data = {
            'game_date': game_date,
            'week_number': week,
            'game_time': game_time,
            'home_team': home_team,
            'away_team': away_team,
            'total': total,
            'spread': spread,
            'home_ml': home_ml,
            'away_ml': away_ml,
            'home_implied_points': home_implied_points,
            'away_implied_points': away_implied_points,
            'weather_temp': weather_temp,
            'weather_wind': weather_wind,
            'weather_description': weather_condition if weather_condition else None,
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
                    game_date, week_number, game_time,
                    home_team, away_team,
                    total, spread, home_ml, away_ml,
                    home_implied_points, away_implied_points,
                    weather_temp, weather_wind, weather_description, is_dome,
                    home_score, away_score, game_completed,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                game['game_date'], game['week_number'], game['game_time'],
                game['home_team'], game['away_team'],
                game['total'], game['spread'], game['home_ml'], game['away_ml'],
                game['home_implied_points'], game['away_implied_points'],
                game['weather_temp'], game['weather_wind'], game['weather_description'], game['is_dome'],
                game['home_score'], game['away_score'], game['game_completed']
            ))
            saved_count += 1
        except Exception as e:
            print(f"⚠️  Error saving game {game['home_team']} vs {game['away_team']}: {e}")

    conn.commit()
    conn.close()

    return saved_count


def fetch_full_season(season: int, weeks: range = range(1, 19)) -> int:
    """
    Fetch entire season schedule

    Args:
        season: NFL season year (e.g., 2024)
        weeks: Range of weeks to fetch (default 1-18 for regular season)

    Returns:
        Total number of games saved
    """
    print(f"\n{'='*60}")
    print(f"🏈 FETCHING NFL {season} SEASON SCHEDULE")
    print(f"{'='*60}")

    total_saved = 0

    for week in weeks:
        games = fetch_games_for_week(season, week)
        saved = save_games_to_db(games)
        total_saved += saved
        print(f"  Week {week}: {saved} games saved")

    print(f"\n✅ Total games saved: {total_saved}")
    return total_saved


def test_fetcher():
    """Test the fetcher with Week 1 of 2024 season"""
    print("\n" + "="*60)
    print("🧪 TESTING NFL GAME SCHEDULE FETCHER")
    print("="*60)

    # Test with Week 1 of 2024 season
    games = fetch_games_for_week(2024, 1)

    if games:
        print(f"\n📊 Sample Game Data:")
        print(json.dumps(games[0], indent=2))

        # Save to database
        saved = save_games_to_db(games)
        print(f"\n✅ Saved {saved} games to database")

        # Verify in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM game_schedule WHERE week_number = 1")
        count = cursor.fetchone()[0]
        conn.close()

        print(f"✅ Verified: {count} games in database for Week 1")
    else:
        print("❌ No games found")


if __name__ == "__main__":
    # Run test
    test_fetcher()

    # Uncomment to fetch full 2024 season:
    # fetch_full_season(2024, range(1, 19))  # Weeks 1-18
