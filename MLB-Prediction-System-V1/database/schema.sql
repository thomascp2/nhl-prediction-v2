-- ============================================================================
-- MLB PREDICTION SYSTEM V1 - DATABASE SCHEMA
-- ============================================================================
-- Based on proven NHL V2 methodology
-- Created: November 2024
-- Purpose: Track MLB player prop predictions for ML training
-- ============================================================================

-- ============================================================================
-- TABLE 1: predictions
-- Stores all predictions before games are played
-- ============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_batch_id TEXT NOT NULL,
    game_date TEXT NOT NULL,

    -- Player information
    player_name TEXT NOT NULL,
    player_type TEXT NOT NULL,  -- 'batter' or 'pitcher'
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,

    -- Prop details
    prop_type TEXT NOT NULL,  -- 'pitcher_strikeouts', 'batter_hits', 'batter_total_bases'
    line REAL NOT NULL,
    prediction TEXT NOT NULL,  -- 'OVER' or 'UNDER' (or 'YES'/'NO' for binary)
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
CREATE INDEX IF NOT EXISTS idx_predictions_player ON predictions(player_name);
CREATE INDEX IF NOT EXISTS idx_predictions_prop ON predictions(prop_type);
CREATE INDEX IF NOT EXISTS idx_predictions_player_type ON predictions(player_type);
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
    player_name TEXT NOT NULL,
    player_type TEXT NOT NULL,
    prop_type TEXT NOT NULL,
    line REAL NOT NULL,
    predicted_probability REAL NOT NULL,

    -- Actual results
    actual_stat_value REAL,
    outcome TEXT,  -- 'HIT' or 'MISS'

    -- Grading metadata
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

CREATE INDEX IF NOT EXISTS idx_outcomes_game_date ON prediction_outcomes(game_date);
CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON prediction_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_outcomes_player ON prediction_outcomes(player_name);
CREATE INDEX IF NOT EXISTS idx_outcomes_player_type ON prediction_outcomes(player_type);

-- ============================================================================
-- TABLE 3: player_game_logs
-- Stores actual game statistics (updated daily after grading)
-- CRITICAL: Enables continuous learning as season progresses!
-- ============================================================================
CREATE TABLE IF NOT EXISTS player_game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,

    -- Player/team context
    player_name TEXT NOT NULL,
    player_type TEXT NOT NULL,  -- 'batter' or 'pitcher'
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    home_away TEXT,  -- 'home' or 'away'

    -- Batter stats
    at_bats INTEGER,
    hits INTEGER,
    doubles INTEGER,
    triples INTEGER,
    home_runs INTEGER,
    rbis INTEGER,
    runs INTEGER,
    walks INTEGER,
    batter_strikeouts INTEGER,  -- Different from pitcher strikeouts
    stolen_bases INTEGER,
    total_bases INTEGER,
    batting_avg REAL,
    on_base_pct REAL,
    slugging_pct REAL,

    -- Pitcher stats
    innings_pitched REAL,
    earned_runs INTEGER,
    pitcher_strikeouts INTEGER,
    walks_allowed INTEGER,
    hits_allowed INTEGER,
    home_runs_allowed INTEGER,
    pitch_count INTEGER,
    pitches_per_inning REAL,
    win_loss TEXT,  -- 'W', 'L', 'ND' (no decision)
    era REAL,
    whip REAL,  -- (Walks + Hits) / Innings Pitched

    -- Game context
    opposing_pitcher TEXT,  -- For batters
    park_name TEXT,
    temperature REAL,
    wind_speed REAL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(game_date, player_name)
);

CREATE INDEX IF NOT EXISTS idx_logs_player ON player_game_logs(player_name);
CREATE INDEX IF NOT EXISTS idx_logs_date ON player_game_logs(game_date);
CREATE INDEX IF NOT EXISTS idx_logs_player_type ON player_game_logs(player_type);
CREATE INDEX IF NOT EXISTS idx_logs_team ON player_game_logs(team);

-- ============================================================================
-- TABLE 4: game_schedule
-- Stores upcoming and completed games with Vegas lines and weather
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    game_time TEXT,

    -- Teams
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,

    -- Pitchers (starting)
    home_pitcher TEXT,
    away_pitcher TEXT,
    home_pitcher_hand TEXT,  -- 'L' or 'R'
    away_pitcher_hand TEXT,  -- 'L' or 'R'

    -- Vegas lines
    total REAL,  -- O/U runs
    home_ml INTEGER,  -- Moneyline
    away_ml INTEGER,
    spread REAL,  -- Run line (usually -1.5 / +1.5)

    -- Derived metrics
    home_implied_runs REAL,
    away_implied_runs REAL,

    -- Weather (CRITICAL for MLB!)
    temperature REAL,
    wind_speed REAL,
    wind_direction TEXT,  -- 'out', 'in', 'cross', 'calm'
    conditions TEXT,  -- 'clear', 'cloudy', 'rain', 'dome'

    -- Park information
    park_name TEXT,
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

CREATE INDEX IF NOT EXISTS idx_schedule_date ON game_schedule(game_date);
CREATE INDEX IF NOT EXISTS idx_schedule_completed ON game_schedule(game_completed);
CREATE INDEX IF NOT EXISTS idx_schedule_home_team ON game_schedule(home_team);
CREATE INDEX IF NOT EXISTS idx_schedule_home_pitcher ON game_schedule(home_pitcher);

-- ============================================================================
-- TABLE 5: park_factors
-- Stores ballpark characteristics (CRITICAL for MLB!)
-- ============================================================================
CREATE TABLE IF NOT EXISTS park_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_name TEXT UNIQUE NOT NULL,
    team TEXT NOT NULL,

    -- Scoring factors (relative to 1.0 = neutral)
    runs_factor REAL DEFAULT 1.0,
    home_runs_factor REAL DEFAULT 1.0,
    hits_factor REAL DEFAULT 1.0,
    strikeouts_factor REAL DEFAULT 1.0,

    -- Handedness splits
    lhb_hr_factor REAL DEFAULT 1.0,  -- Left-handed batter HR factor
    rhb_hr_factor REAL DEFAULT 1.0,  -- Right-handed batter HR factor
    lhp_k_factor REAL DEFAULT 1.0,   -- Left-handed pitcher K factor
    rhp_k_factor REAL DEFAULT 1.0,   -- Right-handed pitcher K factor

    -- Dimensions
    left_field_distance INTEGER,  -- Feet
    center_field_distance INTEGER,
    right_field_distance INTEGER,
    wall_height INTEGER,  -- Average wall height

    -- Characteristics
    altitude INTEGER,  -- Feet above sea level (Coors = 5,200!)
    is_dome BOOLEAN DEFAULT 0,
    has_retractable_roof BOOLEAN DEFAULT 0,

    -- Notes
    notes TEXT,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pre-populate some park factors
INSERT OR IGNORE INTO park_factors (park_name, team, runs_factor, home_runs_factor, hits_factor, strikeouts_factor, altitude, is_dome, notes)
VALUES
    ('Coors Field', 'COL', 1.25, 1.30, 1.20, 0.95, 5200, 0, 'Extreme hitters park - high altitude'),
    ('Great American Ball Park', 'CIN', 1.15, 1.25, 1.10, 0.98, 550, 0, 'Hitter-friendly, short dimensions'),
    ('Oracle Park', 'SF', 0.85, 0.70, 0.95, 1.05, 0, 0, 'Extreme pitchers park - large dimensions'),
    ('T-Mobile Park', 'SEA', 0.92, 0.85, 0.96, 1.03, 0, 0, 'Pitcher-friendly, marine layer'),
    ('Yankee Stadium', 'NYY', 1.08, 1.15, 1.05, 0.97, 55, 0, 'Hitter-friendly, short right field porch'),
    ('Fenway Park', 'BOS', 1.05, 1.10, 1.08, 0.98, 20, 0, 'Hitter-friendly, Green Monster'),
    ('Petco Park', 'SD', 0.90, 0.80, 0.93, 1.04, 20, 0, 'Pitcher-friendly, large dimensions'),
    ('Tropicana Field', 'TB', 0.96, 0.92, 1.00, 1.02, 0, 1, 'Dome - neutral with slight pitcher lean'),
    ('Rogers Centre', 'TOR', 1.02, 1.05, 1.03, 0.99, 300, 1, 'Dome - slightly hitter-friendly');

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- View: Current predictions with outcomes
CREATE VIEW IF NOT EXISTS v_predictions_with_outcomes AS
SELECT
    p.id,
    p.prediction_batch_id,
    p.game_date,
    p.player_name,
    p.player_type,
    p.team,
    p.opponent,
    p.prop_type,
    p.line,
    p.prediction,
    p.probability,
    po.actual_stat_value,
    po.outcome,
    po.graded_at
FROM predictions p
LEFT JOIN prediction_outcomes po ON p.id = po.prediction_id;

-- View: Player season statistics (batters)
CREATE VIEW IF NOT EXISTS v_batter_season_stats AS
SELECT
    player_name,
    team,
    COUNT(*) as games_played,
    AVG(batting_avg) as season_batting_avg,
    AVG(hits) as avg_hits_per_game,
    AVG(total_bases) as avg_total_bases,
    AVG(home_runs) as avg_home_runs,
    SUM(hits) as total_hits,
    SUM(at_bats) as total_at_bats,
    CAST(SUM(hits) AS REAL) / NULLIF(SUM(at_bats), 0) as calculated_avg
FROM player_game_logs
WHERE player_type = 'batter' AND at_bats > 0
GROUP BY player_name, team;

-- View: Player season statistics (pitchers)
CREATE VIEW IF NOT EXISTS v_pitcher_season_stats AS
SELECT
    player_name,
    team,
    COUNT(*) as games_started,
    AVG(innings_pitched) as avg_innings_pitched,
    AVG(pitcher_strikeouts) as avg_strikeouts,
    SUM(pitcher_strikeouts) as total_strikeouts,
    SUM(innings_pitched) as total_innings_pitched,
    (SUM(pitcher_strikeouts) * 9.0) / NULLIF(SUM(innings_pitched), 0) as k_per_9,
    AVG(pitch_count) as avg_pitch_count,
    AVG(era) as season_era
FROM player_game_logs
WHERE player_type = 'pitcher' AND innings_pitched > 0
GROUP BY player_name, team;

-- View: Daily accuracy summary
CREATE VIEW IF NOT EXISTS v_daily_accuracy AS
SELECT
    game_date,
    player_type,
    prop_type,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) as hits,
    ROUND(100.0 * SUM(CASE WHEN outcome = 'HIT' THEN 1 ELSE 0 END) / COUNT(*), 2) as accuracy_pct
FROM prediction_outcomes
GROUP BY game_date, player_type, prop_type
ORDER BY game_date DESC, player_type, prop_type;

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
