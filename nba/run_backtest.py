"""
NBA Backtest Validation
========================

Validates prediction system on historical data.

Process:
1. For each historical date with completed games
2. Generate predictions (using only data before that date)
3. Grade predictions against actual results
4. Calculate accuracy metrics

Success criteria (like NHL):
- Overall accuracy: 55%+
- Points accuracy: 55%+
- Rebounds accuracy: 55%+
- Assists accuracy: 55%+
- PRA accuracy: 55%+

If accuracy >= 55%, proceed to live data collection.
Otherwise, refine features and retest.
"""

import sqlite3
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from nba_config import DB_PATH
from statistical_predictions import NBAStatisticalPredictor


class NBABacktest:
    """Backtest NBA prediction system."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.predictor = NBAStatisticalPredictor(learning_mode=False)  # No cap for backtest

    def run_backtest(self, start_date, end_date, sample_players=8):
        """
        Run backtest on historical data.

        Args:
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
            sample_players (int): Players per team to test (like NHL's top 12)
        """
        print(f"\n🏀 NBA BACKTEST VALIDATION")
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"📊 Sample size: Top {sample_players} players per team")
        print("=" * 60)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all completed games in date range
        cursor.execute("""
            SELECT DISTINCT game_date
            FROM games
            WHERE game_date >= ?
              AND game_date <= ?
              AND status = 'Final'
            ORDER BY game_date
        """, (start_date, end_date))

        dates = [row[0] for row in cursor.fetchall()]
        print(f"📅 Testing {len(dates)} dates\n")

        # Results tracking
        results_by_prop = {}
        total_predictions = 0

        # Run backtest for each date
        for i, date in enumerate(dates, 1):
            print(f"[{i}/{len(dates)}] Testing {date}...", end=' ')

            # Get games for this date
            cursor.execute("""
                SELECT game_id, home_team, away_team
                FROM games
                WHERE game_date = ?
                  AND status = 'Final'
            """, (date,))

            games = cursor.fetchall()
            date_predictions = 0

            for game_id, home_team, away_team in games:
                # Test both teams
                for team, opponent, home_away in [
                    (home_team, away_team, 'H'),
                    (away_team, home_team, 'A')
                ]:
                    # Get top players for this team
                    players = self._get_team_players(cursor, team, sample_players, date)

                    for player_name in players:
                        # Test core props
                        test_props = [
                            ('points', 15.5),
                            ('points', 20.5),
                            ('rebounds', 7.5),
                            ('assists', 5.5),
                            ('pra', 30.5),
                        ]

                        for prop_type, line in test_props:
                            # Generate prediction
                            prediction = self.predictor.predict_prop(
                                player_name, prop_type, line, date, home_away
                            )

                            # Get actual result
                            actual = self._get_actual_result(
                                cursor, game_id, player_name, prop_type
                            )

                            if actual is None:
                                continue  # Player didn't play

                            # Grade prediction
                            if prediction['prediction'] == 'OVER':
                                hit = actual > line
                            else:  # UNDER
                                hit = actual <= line

                            # Track results
                            if prop_type not in results_by_prop:
                                results_by_prop[prop_type] = {'hits': 0, 'total': 0}

                            results_by_prop[prop_type]['total'] += 1
                            if hit:
                                results_by_prop[prop_type]['hits'] += 1

                            total_predictions += 1
                            date_predictions += 1

            print(f"{date_predictions} predictions")

        # Calculate final metrics
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)

        overall_hits = sum(r['hits'] for r in results_by_prop.values())
        overall_total = sum(r['total'] for r in results_by_prop.values())
        overall_accuracy = (overall_hits / overall_total * 100) if overall_total > 0 else 0

        print(f"\n🎯 OVERALL: {overall_hits}/{overall_total} ({overall_accuracy:.1f}%)")

        # By prop type
        print(f"\n📊 BY PROP TYPE:")
        for prop_type, results in sorted(results_by_prop.items()):
            accuracy = (results['hits'] / results['total'] * 100) if results['total'] > 0 else 0
            status = "✅" if accuracy >= 55 else "❌"
            print(f"   {status} {prop_type.upper()}: {results['hits']}/{results['total']} ({accuracy:.1f}%)")

        # Success criteria
        print(f"\n🎯 SUCCESS CRITERIA:")
        if overall_accuracy >= 55:
            print(f"   ✅ Overall accuracy: {overall_accuracy:.1f}% (target: 55%+)")
            print(f"\n🚀 BACKTEST PASSED - Ready for live data collection!")
        else:
            print(f"   ❌ Overall accuracy: {overall_accuracy:.1f}% (target: 55%+)")
            print(f"\n⚠️  BACKTEST FAILED - Refine features and retest")

        conn.close()

        return {
            'overall_accuracy': overall_accuracy,
            'total_predictions': total_predictions,
            'results_by_prop': results_by_prop
        }

    def _get_team_players(self, cursor, team, count, game_date):
        """Get top N players for a team (by minutes)."""
        cursor.execute("""
            SELECT player_name
            FROM player_game_logs
            WHERE team = ?
              AND game_date < ?
            GROUP BY player_name
            HAVING COUNT(*) >= 3
            ORDER BY AVG(minutes) DESC
            LIMIT ?
        """, (team, game_date, count))

        return [row[0] for row in cursor.fetchall()]

    def _get_actual_result(self, cursor, game_id, player_name, prop_type):
        """Get actual stat value for a player in a game."""
        stat_map = {
            'points': 'points',
            'rebounds': 'rebounds',
            'assists': 'assists',
            'pra': 'pra',
            'threes': 'threes_made',
            'stocks': 'stocks',
            'minutes': 'minutes',
        }

        column = stat_map.get(prop_type, 'points')

        cursor.execute(f"""
            SELECT {column}
            FROM player_game_logs
            WHERE game_id = ?
              AND player_name = ?
        """, (game_id, player_name))

        result = cursor.fetchone()
        return result[0] if result else None


# CLI interface
if __name__ == "__main__":
    backtest = NBABacktest()

    if len(sys.argv) > 2:
        # Custom date range
        start = sys.argv[1]
        end = sys.argv[2]
    else:
        # Default: Last 2 weeks
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    backtest.run_backtest(start, end)
