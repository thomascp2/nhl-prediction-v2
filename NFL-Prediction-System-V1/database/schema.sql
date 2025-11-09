-- ============================================================================
-- NFL PREDICTION SYSTEM V1 - DATABASE SCHEMA
-- ============================================================================
-- Based on proven NHL V2 methodology
-- Created: November 2024
-- Purpose: Track NFL player prop predictions for ML training
-- ============================================================================

-- ============================================================================
-- TABLE 1: predictions
-- Stores all predictions before games are played
-- ============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_batch_id TEXT NOT NULL,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,

    -- Player information
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    position TEXT NOT NULL,

    -- Prop details
    prop_type TEXT NOT NULL,
    line REAL NOT NULL,
    prediction TEXT NOT NULL,
    probability REAL NOT NULL,

    -- Model metadata
    model_version TEXT DEFAULT 'statistical_v1',
    confidence_tier TEXT,

    -- Features (JSON - CRITICAL for ML training!)
    features_json TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_game_date ON predictions(game_date);
CREATE INDEX IF NOT EXISTS idx_predictions_week ON predictions(week_number);
CREATE INDEX IF NOT EXISTS idx_predictions_player ON predictions(player_name);
CREATE INDEX IF NOT EXISTS idx_predictions_prop ON predictions(prop_type);
CREATE INDEX IF NOT EXISTS idx_predictions_batch ON predictions(prediction_batch_id);

-- ============================================================================
-- TABLE 2: prediction_outcomes
-- Stores graded predictions after games complete
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,

    -- Context
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    prop_type TEXT NOT NULL,
    line REAL NOT NULL,
    predicted_probability REAL NOT NULL,

    -- Actual results
    actual_stat_value REAL,
    outcome TEXT,

    -- Grading metadata
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

CREATE INDEX IF NOT EXISTS idx_outcomes_game_date ON prediction_outcomes(game_date);
CREATE INDEX IF NOT EXISTS idx_outcomes_week ON prediction_outcomes(week_number);
CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON prediction_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_outcomes_player ON prediction_outcomes(player_name);

-- ============================================================================
-- TABLE 3: player_game_logs
-- Stores actual game statistics (updated weekly after grading)
-- CRITICAL: Enables continuous learning as season progresses!
-- ============================================================================
CREATE TABLE IF NOT EXISTS player_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,

    -- Player/team context
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    home_away TEXT,
    position TEXT NOT NULL,

    -- Passing stats (QB)
    pass_attempts INTEGER,
    pass_completions INTEGER,
    pass_yards INTEGER,
    pass_tds INTEGER,
    interceptions INTEGER,
    sacks INTEGER,
    qb_rating REAL,

    -- Rushing stats (RB, QB)
    rush_attempts INTEGER,
    rush_yards INTEGER,
    rush_tds INTEGER,
    yards_per_carry REAL,

    -- Receiving stats (WR, TE, RB)
    targets INTEGER,
    receptions INTEGER,
    rec_yards INTEGER,
    rec_tds INTEGER,
    yards_per_reception REAL,

    -- Opportunity metrics (CRITICAL for NFL!)
    snap_count INTEGER,
    snap_pct REAL,
    target_share REAL,
    air_yards_share REAL,
    red_zone_targets INTEGER,
    red_zone_carries INTEGER,

    -- Game context
    game_script REAL,
    team_score INTEGER,
    opp_score INTEGER,
    game_total INTEGER,

    -- Special stats
    two_point_conversions INTEGER,
    fumbles INTEGER,
    fumbles_lost INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, player_name)
);

CREATE INDEX IF NOT EXISTS idx_logs_player ON player_game_logs(player_name);
CREATE INDEX IF NOT EXISTS idx_logs_date ON player_game_logs(game_date);
CREATE INDEX IF NOT EXISTS idx_logs_week ON player_game_logs(week_number);
CREATE INDEX IF NOT EXISTS idx_logs_team ON player_game_logs(team);

-- ============================================================================
-- TABLE 4: game_schedule
-- Stores upcoming and completed games with Vegas lines
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    game_time TEXT,

    -- Teams
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,

    -- Vegas lines
    total REAL,
    spread REAL,
    home_ml INTEGER,
    away_ml INTEGER,

    -- Derived metrics
    home_implied_points REAL,
    away_implied_points REAL,
    expected_pace REAL,

    -- Weather (CRITICAL for NFL!)
    weather_temp REAL,
    weather_wind REAL,
    weather_precip TEXT,
    weather_description TEXT,
    is_dome BOOLEAN DEFAULT 0,

    -- Game result (filled after completion)
    home_score INTEGER,
    away_score INTEGER,
    game_completed BOOLEAN DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, home_team, away_team)
);

CREATE INDEX IF NOT EXISTS idx_schedule_week ON game_schedule(week_number);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON game_schedule(game_date);
CREATE INDEX IF NOT EXISTS idx_schedule_completed ON game_schedule(game_completed);

-- ============================================================================
-- TABLE 5: team_context
-- Stores team-level statistics updated weekly
-- ============================================================================
CREATE TABLE IF NOT EXISTS team_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team TEXT NOT NULL,
    season TEXT NOT NULL,
    week_number INTEGER NOT NULL,

    -- Pace (plays per game)
    offensive_pace REAL,
    defensive_pace REAL,

    -- Overall rankings (1-32)
    offensive_rank INTEGER,
    defensive_rank INTEGER,

    -- Passing defense
    pass_def_rank INTEGER,
    pass_yards_allowed_per_game REAL,
    pass_tds_allowed INTEGER,
    completion_pct_allowed REAL,

    -- Rushing defense
    rush_def_rank INTEGER,
    rush_yards_allowed_per_game REAL,
    rush_tds_allowed INTEGER,
    yards_per_carry_allowed REAL,

    -- Positional defense (yards allowed to position)
    yards_allowed_to_wr1 REAL,
    yards_allowed_to_wr2 REAL,
    yards_allowed_to_te REAL,
    yards_allowed_to_rb REAL,

    -- Offensive line quality
    oline_rank INTEGER,
    sacks_allowed INTEGER,

    -- Defensive line quality
    dline_rank INTEGER,
    sacks_generated INTEGER,

    -- Advanced metrics (if available)
    dvoa_offense REAL,
    dvoa_defense REAL,

    -- Timestamps
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team, season, week_number)
);

CREATE INDEX IF NOT EXISTS idx_team_context_week ON team_context(week_number);
CREATE INDEX IF NOT EXISTS idx_team_context_team ON team_context(team);

-- ============================================================================
-- TABLE 6: short_week_tracker
-- Tracks rest days and travel for fatigue analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS short_week_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    team TEXT NOT NULL,

    -- Rest information
    days_since_last_game INTEGER,
    is_short_week BOOLEAN DEFAULT 0,
    had_bye_week_last BOOLEAN DEFAULT 0,

    -- Travel context
    travel_distance REAL,
    timezone_change INTEGER,
    is_primetime BOOLEAN DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, team)
);

CREATE INDEX IF NOT EXISTS idx_short_week_date ON short_week_tracker(game_date);
CREATE INDEX IF NOT EXISTS idx_short_week_week ON short_week_tracker(week_number);
CREATE INDEX IF NOT EXISTS idx_short_week_team ON short_week_tracker(team);

-- ============================================================================
-- TABLE 7: injury_reports
-- Tracks player injury status (updated multiple times per week)
-- ============================================================================
CREATE TABLE IF NOT EXISTS injury_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    game_date TEXT NOT NULL,
    week_number INTEGER NOT NULL,

    -- Player information
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    position TEXT NOT NULL,

    -- Injury details
    status TEXT NOT NULL,
    injury_type TEXT,
    practice_status TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(report_date, player_name)
);

CREATE INDEX IF NOT EXISTS idx_injury_player ON injury_reports(player_name);
CREATE INDEX IF NOT EXISTS idx_injury_week ON injury_reports(week_number);
CREATE INDEX IF NOT EXISTS idx_injury_status ON injury_reports(status);
CREATE INDEX IF NOT EXISTS idx_injury_game_date ON injury_reports(game_date);

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- View: Current week predictions with outcomes
CREATE VIEW IF NOT EXISTS v_predictions_with_outcomes AS
SELECT
    p.id,
    p.prediction_batch_id,
    p.game_date,
    p.week_number,
    p.player_name,
    p.team,
    p.opponent,
    p.position,
    p.prop_type,
    p.line,
    p.prediction,
    p.probability,
    po.actual_stat_value,
    po.outcome,
    po.graded_at
FROM predictions p
LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id;

-- View: Player season statistics
CREATE VIEW IF NOT EXISTS v_player_season_stats AS
SELECT
    player_name,
    team,
    position,
    COUNT(*) as games_played,
    AVG(pass_yards) as avg_pass_yards,
    AVG(rush_yards) as avg_rush_yards,
    AVG(rec_yards) as avg_rec_yards,
    AVG(receptions) as avg_receptions,
    AVG(targets) as avg_targets,
    AVG(snap_pct) as avg_snap_pct
FROM player_game_logs
GROUP BY player_name, team, position;

-- View: Weekly accuracy summary
CREATE VIEW IF NOT EXISTS v_weekly_accuracy AS
SELECT
    week_number,
    prop_type,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy_pct
FROM prediction_outcomes
GROUP BY week_number, prop_type
ORDER BY week_number DESC, prop_type;

-- ============================================================================
-- SCHEMA VERSION
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version) VALUES ('1.0.0');

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
