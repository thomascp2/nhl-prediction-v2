"""
NBA Database Schema Setup
=========================

Creates database schema for NBA prediction system.
Mirrors NHL V2 architecture.

Tables:
- games: NBA schedule
- player_game_logs: Historical player stats
- predictions: Model predictions + features
- prediction_outcomes: Graded results for ML training
"""

import sqlite3
from nba_config import DB_PATH

def setup_database():
    """Create all tables for NBA prediction system."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            game_date TEXT NOT NULL,
            season TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT DEFAULT 'scheduled'
        )
    """)

    # 2. Player game logs (for feature extraction)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_game_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            opponent TEXT NOT NULL,
            home_away TEXT NOT NULL,
            minutes REAL,
            points INTEGER,
            rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            threes_made INTEGER,
            fga INTEGER,
            fgm INTEGER,
            fta INTEGER,
            ftm INTEGER,
            plus_minus INTEGER,

            -- Derived stats
            pra INTEGER,  -- Points + Rebounds + Assists
            stocks INTEGER,  -- Steals + Blocks

            -- Metadata
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(game_id, player_name)
        )
    """)

    # 3. Predictions table (with features)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            opponent TEXT NOT NULL,
            home_away TEXT NOT NULL,

            -- Prop bet details
            prop_type TEXT NOT NULL,  -- points, rebounds, assists, pra, etc.
            line REAL NOT NULL,  -- 15.5, 7.5, etc.
            prediction TEXT NOT NULL,  -- OVER or UNDER
            probability REAL NOT NULL,  -- 0.30 to 0.70 (learning mode)

            -- Model features (11 binary features)
            f_season_success_rate REAL,
            f_l20_success_rate REAL,
            f_l10_success_rate REAL,
            f_l5_success_rate REAL,
            f_l3_success_rate REAL,
            f_current_streak INTEGER,
            f_max_streak INTEGER,
            f_trend_slope REAL,
            f_home_away_split REAL,
            f_games_played INTEGER,
            f_insufficient_data INTEGER,

            -- Model features (10 continuous features)
            f_season_avg REAL,
            f_l10_avg REAL,
            f_l5_avg REAL,
            f_season_std REAL,
            f_l10_std REAL,
            f_trend_acceleration REAL,
            f_avg_minutes REAL,
            f_consistency_score REAL,

            -- Metadata
            model_version TEXT DEFAULT 'statistical_v1',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(game_date, player_name, prop_type, line)
        )
    """)

    # 4. Prediction outcomes (for grading and ML training)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_name TEXT NOT NULL,

            -- Prop details
            prop_type TEXT NOT NULL,
            line REAL NOT NULL,
            prediction TEXT NOT NULL,

            -- Actual results
            actual_value REAL NOT NULL,  -- Actual points, rebounds, etc.
            outcome TEXT NOT NULL,  -- HIT or MISS

            -- Match quality
            match_tier INTEGER,  -- 1 (exact) to 5 (fuzzy)
            match_score REAL,  -- Fuzzy match confidence

            -- Metadata
            graded_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (prediction_id) REFERENCES predictions(id),
            UNIQUE(prediction_id)
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_player ON player_game_logs(player_name, game_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(game_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_date ON prediction_outcomes(game_date)")

    conn.commit()

    # Verify tables created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("✅ Database setup complete!")
    print(f"📁 Database: {DB_PATH}")
    print(f"📊 Tables created: {len(tables)}")
    for table in tables:
        print(f"   - {table[0]}")

    conn.close()

if __name__ == "__main__":
    setup_database()
