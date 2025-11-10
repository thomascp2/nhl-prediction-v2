"""
NBA Binary Feature Extractor
=============================

Extracts features for binary classification problems:
- Points O15.5, O20.5, O25.5
- Rebounds O7.5, O10.5
- Assists O5.5, O7.5
- Threes O2.5
- Stocks (STL+BLK) O2.5

Features (11 total):
1. Season success rate (% of games over line)
2. L20 success rate
3. L10 success rate
4. L5 success rate
5. L3 success rate
6. Current streak (consecutive overs/unders)
7. Max streak (longest streak this season)
8. Trend slope (improving or declining)
9. Home/Away split (performance difference)
10. Games played (sample size)
11. Insufficient data flag (< 5 games)
"""

import sqlite3
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nba_config import DB_PATH, MIN_GAMES_REQUIRED


class BinaryFeatureExtractor:
    """Extract binary features from player game logs."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def extract_features(self, player_name, stat_type, line, game_date, home_away='H'):
        """
        Extract binary features for a player-stat-line combination.

        Args:
            player_name (str): Player name
            stat_type (str): 'points', 'rebounds', 'assists', 'threes', 'stocks', 'pra'
            line (float): Over/Under line (e.g., 15.5)
            game_date (str): Game date (YYYY-MM-DD) - for temporal safety
            home_away (str): 'H' or 'A'

        Returns:
            dict: 11 binary features
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get historical games BEFORE game_date (temporal safety)
        query = """
            SELECT game_date, {stat_column}, home_away
            FROM player_game_logs
            WHERE player_name = ?
              AND game_date < ?
            ORDER BY game_date DESC
        """.format(stat_column=self._get_stat_column(stat_type))

        cursor.execute(query, (player_name, game_date))
        games = cursor.fetchall()

        conn.close()

        # Initialize features
        features = {
            'f_season_success_rate': 0.0,
            'f_l20_success_rate': 0.0,
            'f_l10_success_rate': 0.0,
            'f_l5_success_rate': 0.0,
            'f_l3_success_rate': 0.0,
            'f_current_streak': 0,
            'f_max_streak': 0,
            'f_trend_slope': 0.0,
            'f_home_away_split': 0.0,
            'f_games_played': len(games),
            'f_insufficient_data': 1 if len(games) < MIN_GAMES_REQUIRED else 0,
        }

        if len(games) == 0:
            return features

        # Extract stat values
        stat_values = [game[1] for game in games if game[1] is not None]
        if not stat_values:
            return features

        # 1-5: Success rates (season, L20, L10, L5, L3)
        features['f_season_success_rate'] = self._success_rate(stat_values, line)
        features['f_l20_success_rate'] = self._success_rate(stat_values[:20], line)
        features['f_l10_success_rate'] = self._success_rate(stat_values[:10], line)
        features['f_l5_success_rate'] = self._success_rate(stat_values[:5], line)
        features['f_l3_success_rate'] = self._success_rate(stat_values[:3], line)

        # 6-7: Streaks
        streak_data = self._calculate_streaks(stat_values, line)
        features['f_current_streak'] = streak_data['current']
        features['f_max_streak'] = streak_data['max']

        # 8: Trend slope (recent improving or declining)
        features['f_trend_slope'] = self._calculate_trend(stat_values[:10])

        # 9: Home/Away split
        home_games = [game[1] for game in games if game[2] == 'H' and game[1] is not None]
        away_games = [game[1] for game in games if game[2] == 'A' and game[1] is not None]
        features['f_home_away_split'] = self._home_away_split(
            home_games, away_games, line, home_away
        )

        return features

    @staticmethod
    def _get_stat_column(stat_type):
        """Map stat type to database column."""
        stat_map = {
            'points': 'points',
            'rebounds': 'rebounds',
            'assists': 'assists',
            'threes': 'threes_made',
            'stocks': '(steals + blocks)',  # Derived stat
            'pra': '(points + rebounds + assists)',  # Derived stat
        }
        return stat_map.get(stat_type, 'points')

    @staticmethod
    def _success_rate(values, line):
        """Calculate success rate (% of games over line)."""
        if not values:
            return 0.0
        overs = sum(1 for v in values if v > line)
        return overs / len(values)

    @staticmethod
    def _calculate_streaks(values, line):
        """Calculate current streak and max streak."""
        if not values:
            return {'current': 0, 'max': 0}

        current_streak = 0
        max_streak = 0
        temp_streak = 0
        last_result = None

        for value in values:
            result = 1 if value > line else -1

            if result == last_result:
                temp_streak += 1
            else:
                temp_streak = 1
                last_result = result

            max_streak = max(max_streak, abs(temp_streak))

            if temp_streak == 1 and len(values) > 0:
                current_streak = temp_streak * result

        # Current streak is the most recent
        if values:
            current_streak = 1 if values[0] > line else -1
            count = 1
            for i in range(1, len(values)):
                if (values[i] > line) == (values[0] > line):
                    count += 1
                else:
                    break
            current_streak *= count

        return {'current': current_streak, 'max': max_streak}

    @staticmethod
    def _calculate_trend(values):
        """Calculate trend slope using linear regression."""
        if len(values) < 3:
            return 0.0

        n = len(values)
        x = list(range(n))
        y = values

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        return slope

    @staticmethod
    def _home_away_split(home_games, away_games, line, current_home_away):
        """Calculate home/away split advantage."""
        if not home_games or not away_games:
            return 0.0

        home_rate = sum(1 for v in home_games if v > line) / len(home_games)
        away_rate = sum(1 for v in away_games if v > line) / len(away_games)

        split = home_rate - away_rate

        # Return split relative to current game
        return split if current_home_away == 'H' else -split


# Example usage
if __name__ == "__main__":
    extractor = BinaryFeatureExtractor()

    # Test feature extraction
    features = extractor.extract_features(
        player_name="LeBron James",
        stat_type="points",
        line=25.5,
        game_date="2024-11-09",
        home_away='H'
    )

    print("🏀 Binary Feature Extraction Test")
    print(f"Player: LeBron James")
    print(f"Prop: Points O25.5")
    print(f"\nFeatures:")
    for key, value in features.items():
        print(f"  {key}: {value}")
