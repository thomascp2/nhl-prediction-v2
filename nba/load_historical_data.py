"""
NBA Historical Data Loader
===========================

Loads historical NBA data for the 2024-2025 season.

Data loaded:
1. Games (schedule and results)
2. Player game logs (box scores)

This data is used for:
- Backtesting the prediction system
- Feature extraction for live predictions
- Continuous learning

Run once at setup, then update daily with auto_grade_yesterday.py
"""

import sqlite3
from datetime import datetime, timedelta
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from nba_config import DB_PATH, SEASON
from data_fetchers.nba_stats_api import NBAStatsAPI


class HistoricalDataLoader:
    """Load historical NBA data."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.api = NBAStatsAPI()

    def load_season_data(self, start_date, end_date):
        """
        Load all games and player stats between start_date and end_date.

        Args:
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
        """
        print(f"\n🏀 NBA HISTORICAL DATA LOADER")
        print(f"📅 Loading data from {start_date} to {end_date}")
        print(f"🏆 Season: {SEASON}")
        print("=" * 60)

        conn = sqlite3.connect(self.db_path)

        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        total_games = 0
        total_logs = 0
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            print(f"\n📅 Loading {date_str}...")

            # Fetch scoreboard
            games = self.api.get_scoreboard(date_str)

            if len(games) == 0:
                print(f"   No games on {date_str}")
                current += timedelta(days=1)
                continue

            print(f"   Found {len(games)} games")

            # Save games
            for game in games:
                self._save_game(conn, game, date_str)
                total_games += 1

                # Fetch boxscore if game is final
                if game['status'] == 'Final':
                    print(f"   Loading boxscore: {game['away_team']} @ {game['home_team']}")
                    boxscore = self.api.get_boxscore_traditional(game['game_id'])

                    # Save player stats
                    for player_stats in boxscore:
                        self._save_player_log(conn, player_stats, game, date_str)
                        total_logs += 1

                    # Update game scores
                    self._update_game_scores(conn, game['game_id'], boxscore)

                    time.sleep(0.6)  # Rate limiting

            conn.commit()
            current += timedelta(days=1)

        print("\n" + "=" * 60)
        print(f"✅ DATA LOAD COMPLETE")
        print(f"📊 Games loaded: {total_games}")
        print(f"📈 Player logs loaded: {total_logs}")

        conn.close()

        return {
            'games': total_games,
            'logs': total_logs
        }

    def _save_game(self, conn, game, game_date):
        """Save game to database."""
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO games
            (game_id, game_date, season, home_team, away_team, home_score, away_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game['game_id'], game_date, SEASON,
            game['home_team'], game['away_team'],
            game.get('home_score'), game.get('away_score'),
            game['status']
        ))

    def _save_player_log(self, conn, stats, game, game_date):
        """Save player game log to database."""
        cursor = conn.cursor()

        # Determine home/away and opponent
        if stats['team'] == game['home_team']:
            home_away = 'H'
            opponent = game['away_team']
        else:
            home_away = 'A'
            opponent = game['home_team']

        # Calculate derived stats
        pra = stats['points'] + stats['rebounds'] + stats['assists']
        stocks = stats['steals'] + stats['blocks']

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_game_logs
                (game_id, game_date, player_name, team, opponent, home_away,
                 minutes, points, rebounds, assists, steals, blocks, turnovers,
                 threes_made, fga, fgm, fta, ftm, plus_minus, pra, stocks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game['game_id'], game_date, stats['player_name'], stats['team'],
                opponent, home_away,
                stats['minutes'], stats['points'], stats['rebounds'], stats['assists'],
                stats['steals'], stats['blocks'], stats['turnovers'],
                stats['threes_made'], stats['fga'], stats['fgm'],
                stats['fta'], stats['ftm'], stats['plus_minus'],
                pra, stocks
            ))
        except sqlite3.IntegrityError:
            pass  # Already exists

    def _update_game_scores(self, conn, game_id, boxscore):
        """Update game scores from boxscore."""
        cursor = conn.cursor()

        # Calculate team totals
        teams = {}
        for player in boxscore:
            team = player['team']
            if team not in teams:
                teams[team] = 0
            teams[team] += player['points']

        if len(teams) == 2:
            team_list = list(teams.keys())
            cursor.execute("""
                UPDATE games
                SET home_score = ?,
                    away_score = ?,
                    status = 'Final'
                WHERE game_id = ?
            """, (teams.get(team_list[0], 0), teams.get(team_list[1], 0), game_id))

    def load_recent_weeks(self, weeks=2):
        """
        Load recent N weeks of data.

        Args:
            weeks (int): Number of weeks to load
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        return self.load_season_data(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

    def load_full_season(self):
        """Load full 2024-2025 NBA season."""
        # NBA 2024-2025 season: October 22, 2024 - April 13, 2025
        return self.load_season_data("2024-10-22", "2025-04-13")


# CLI interface
if __name__ == "__main__":
    loader = HistoricalDataLoader()

    if len(sys.argv) > 2:
        # Custom date range
        start = sys.argv[1]
        end = sys.argv[2]
        loader.load_season_data(start, end)
    elif len(sys.argv) > 1:
        # Number of weeks
        weeks = int(sys.argv[1])
        loader.load_recent_weeks(weeks)
    else:
        # Default: Load season to date
        today = datetime.now().strftime("%Y-%m-%d")
        loader.load_season_data("2024-10-22", today)
