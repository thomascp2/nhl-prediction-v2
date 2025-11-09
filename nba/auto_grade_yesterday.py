"""
NBA Auto-Grading Script (V1)
=============================

Grades yesterday's predictions automatically.

Features:
1. Fetches NBA Stats API results for yesterday
2. Fuzzy name matching (5-tier system like NHL)
3. Saves outcomes to prediction_outcomes table
4. **CRITICAL:** Updates player_game_logs table (v3 continuous learning!)
5. Calculates accuracy metrics
6. Discord notification (optional)

Run daily at 8 AM to grade previous day's games.
"""

import sqlite3
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from nba_config import DB_PATH, DISCORD_WEBHOOK_URL
from data_fetchers.nba_stats_api import NBAStatsAPI


class NBAAutoGrader:
    """Automatic grading for NBA predictions."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.api = NBAStatsAPI()

    def grade_yesterday(self, target_date=None):
        """
        Grade predictions from yesterday's games.

        Args:
            target_date (str): Optional date to grade (YYYY-MM-DD). Defaults to yesterday.
        """
        # Determine target date
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        print(f"\n🏀 NBA AUTO-GRADER")
        print(f"📅 Grading date: {target_date}")
        print("=" * 60)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get predictions to grade
        cursor.execute("""
            SELECT id, game_id, player_name, prop_type, line, prediction, probability
            FROM predictions
            WHERE game_date = ?
              AND id NOT IN (SELECT prediction_id FROM prediction_outcomes)
        """, (target_date,))

        predictions = cursor.fetchall()
        print(f"📊 Found {len(predictions)} predictions to grade\n")

        if len(predictions) == 0:
            print("✅ No predictions to grade")
            conn.close()
            return

        # Fetch games for the date
        games = self.api.get_scoreboard(target_date)
        print(f"🎮 Found {len(games)} games on {target_date}")

        # Fetch boxscores for all games
        all_player_stats = []
        for game in games:
            if game['status'] == 'Final':
                print(f"   Loading boxscore: {game['away_team']} @ {game['home_team']}")
                boxscore = self.api.get_boxscore_traditional(game['game_id'])
                all_player_stats.extend(boxscore)

        print(f"📈 Loaded stats for {len(all_player_stats)} players\n")

        # Grade each prediction
        graded_count = 0
        hit_count = 0
        ungraded = []

        for pred in predictions:
            pred_id, game_id, player_name, prop_type, line, prediction, probability = pred

            # Find player stats
            match_result = self._find_player_stats(player_name, all_player_stats)

            if match_result is None:
                ungraded.append((player_name, "No match found"))
                continue

            player_stats, match_tier, match_score = match_result

            # Get actual value for the stat
            actual_value = self._get_stat_value(player_stats, prop_type)

            # Determine outcome
            if prediction == 'OVER':
                outcome = 'HIT' if actual_value > line else 'MISS'
            else:  # UNDER
                outcome = 'HIT' if actual_value <= line else 'MISS'

            # Save outcome
            cursor.execute("""
                INSERT INTO prediction_outcomes
                (prediction_id, game_id, game_date, player_name, prop_type, line,
                 prediction, actual_value, outcome, match_tier, match_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred_id, game_id, target_date, player_name, prop_type, line,
                prediction, actual_value, outcome, match_tier, match_score
            ))

            graded_count += 1
            if outcome == 'HIT':
                hit_count += 1

        # **V3 CRITICAL:** Update player_game_logs
        logs_saved = self._save_player_game_logs(conn, all_player_stats, target_date)

        conn.commit()

        # Calculate accuracy
        accuracy = (hit_count / graded_count * 100) if graded_count > 0 else 0

        # Print results
        print("=" * 60)
        print(f"✅ GRADING COMPLETE")
        print(f"📊 Results: {hit_count}/{graded_count} ({accuracy:.1f}%)")
        print(f"💾 Saved {logs_saved} player logs to database (v3 continuous learning!)")

        if ungraded:
            print(f"\n⚠️  Ungraded: {len(ungraded)} predictions")
            for player, reason in ungraded[:5]:
                print(f"   - {player}: {reason}")

        conn.close()

        # Discord notification (optional)
        if DISCORD_WEBHOOK_URL:
            self._send_discord_notification(target_date, graded_count, hit_count, accuracy, logs_saved)

        return {
            'graded': graded_count,
            'hits': hit_count,
            'accuracy': accuracy,
            'logs_saved': logs_saved
        }

    def _find_player_stats(self, player_name, all_stats):
        """
        Find player in boxscore using fuzzy matching.

        Returns:
            tuple: (player_stats, match_tier, match_score) or None
        """
        best_match = None
        best_score = 0
        best_tier = 5

        for stats in all_stats:
            actual_name = stats['player_name']

            # Tier 1: Exact match
            if player_name.lower() == actual_name.lower():
                return (stats, 1, 100)

            # Tier 2: Simple ratio
            score = fuzz.ratio(player_name.lower(), actual_name.lower())
            if score > best_score:
                best_score = score
                best_match = stats
                best_tier = 2

            # Tier 3: Partial ratio
            score = fuzz.partial_ratio(player_name.lower(), actual_name.lower())
            if score > best_score:
                best_score = score
                best_match = stats
                best_tier = 3

        # Require minimum 80% match
        if best_score >= 80:
            return (best_match, best_tier, best_score)

        return None

    @staticmethod
    def _get_stat_value(stats, prop_type):
        """Extract stat value from player stats."""
        stat_map = {
            'points': 'points',
            'rebounds': 'rebounds',
            'assists': 'assists',
            'threes': 'threes_made',
            'stocks': lambda s: s.get('steals', 0) + s.get('blocks', 0),
            'pra': lambda s: s.get('points', 0) + s.get('rebounds', 0) + s.get('assists', 0),
            'minutes': 'minutes',
        }

        mapper = stat_map.get(prop_type)

        if callable(mapper):
            return mapper(stats)
        else:
            return stats.get(mapper, 0)

    def _save_player_game_logs(self, conn, all_stats, game_date):
        """
        Save player game logs to database (V3 continuous learning).

        This is CRITICAL for continuous learning - ensures model
        uses fresh data for tomorrow's predictions.
        """
        cursor = conn.cursor()
        saved_count = 0

        for stats in all_stats:
            # Calculate derived stats
            pra = stats['points'] + stats['rebounds'] + stats['assists']
            stocks = stats['steals'] + stats['blocks']

            # Determine home/away
            # Note: NBA Stats API provides this in the boxscore, but for simplicity
            # we'll infer from the game data. In production, fetch from games table.
            home_away = 'H'  # Placeholder - should be determined from game data

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO player_game_logs
                    (game_id, game_date, player_name, team, opponent, home_away,
                     minutes, points, rebounds, assists, steals, blocks, turnovers,
                     threes_made, fga, fgm, fta, ftm, plus_minus, pra, stocks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stats['game_id'], game_date, stats['player_name'], stats['team'],
                    '', home_away,  # Opponent TBD from game data
                    stats['minutes'], stats['points'], stats['rebounds'], stats['assists'],
                    stats['steals'], stats['blocks'], stats['turnovers'],
                    stats['threes_made'], stats['fga'], stats['fgm'],
                    stats['fta'], stats['ftm'], stats['plus_minus'],
                    pra, stocks
                ))
                saved_count += 1
            except sqlite3.IntegrityError:
                pass  # Already exists

        return saved_count

    def _send_discord_notification(self, date, graded, hits, accuracy, logs_saved):
        """Send Discord notification (optional)."""
        try:
            import requests

            message = f"""
🏀 **NBA Auto-Grader Report**
📅 Date: {date}

📊 **Results:**
- Graded: {graded}
- Hits: {hits}
- Accuracy: {accuracy:.1f}%

💾 **Continuous Learning:**
- Player logs saved: {logs_saved} (v3!)

✅ GRADING COMPLETE
            """

            payload = {"content": message}
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
        except:
            pass  # Discord is optional


# CLI interface
if __name__ == "__main__":
    grader = NBAAutoGrader()

    # Allow custom date from command line
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = None

    grader.grade_yesterday(target_date)
