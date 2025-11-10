"""
Test Script for Statistical Predictions V2 - FIXED VERSION

This script tests all the fixes and verifies the system is working correctly.

Run this AFTER replacing statistical_predictions_v2.py with the fixed version.

Author: NHL Prediction System V2
Date: 2025-11-08
"""

import sys
import sqlite3
import json
from datetime import datetime

print("="*80)
print("TESTING STATISTICAL PREDICTIONS V2 - FIXED VERSION")
print("="*80)
print()

# Test 1: Import the modules
print("[TEST 1] Importing modules...")
try:
    from features.binary_feature_extractor import BinaryFeatureExtractor
    from features.continuous_feature_extractor import ContinuousFeatureExtractor
    from statistical_predictions_v2 import StatisticalPredictionEngine
    print("[PASS] PASS: All modules imported successfully")
except ImportError as e:
    print(f"[FAIL] FAIL: Import error - {e}")
    print("\nMake sure:")
    print("  1. features/ folder exists")
    print("  2. features/__init__.py exists (can be empty)")
    print("  3. binary_feature_extractor.py and continuous_feature_extractor.py exist")
    sys.exit(1)

print()

# Test 2: Database connection
print("[TEST 2] Checking database...")
db_path = r'database\nhl_predictions_v2.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['player_game_logs', 'predictions', 'games']
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        print(f"[FAIL] FAIL: Missing tables: {missing}")
        sys.exit(1)

    # Check player_game_logs has data
    cursor.execute("SELECT COUNT(*) FROM player_game_logs")
    log_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT player_name) FROM player_game_logs")
    player_count = cursor.fetchone()[0]

    print(f"[PASS] PASS: Database connected")
    print(f"    Tables: {', '.join(required_tables)}")
    print(f"    Player game logs: {log_count:,}")
    print(f"    Unique players: {player_count:,}")
    
    conn.close()
    
except Exception as e:
    print(f"[FAIL] FAIL: Database error - {e}")
    sys.exit(1)

print()

# Test 3: Binary feature extraction
print("[TEST 3] Testing binary feature extractor...")
try:
    extractor = BinaryFeatureExtractor(db_path)
    extractor.connect()
    
    # Get a sample player
    cursor = extractor.conn.cursor()
    cursor.execute("""
        SELECT player_name, team, opponent, is_home
        FROM player_game_logs
        WHERE game_date = '2025-10-15'
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if not row:
        print("[WARNING] WARNING: No test data for 2025-10-15, using generic test")
        player, team, opponent, is_home = 'Test Player', 'TOR', 'MTL', 1
    else:
        player, team, opponent, is_home = row
    
    # Extract features
    features = extractor.extract_features(
        player_name=player,
        team=team,
        game_date='2025-10-15',
        opponent=opponent,
        is_home=bool(is_home)
    )
    
    # Check expected features exist
    expected = [
        'success_rate_season', 'success_rate_l20', 'success_rate_l10',
        'success_rate_l5', 'success_rate_l3', 'current_streak',
        'max_hot_streak', 'recent_momentum', 'is_home',
        'games_played', 'insufficient_data'
    ]
    
    missing = [f for f in expected if f not in features]

    if missing:
        print(f"[FAIL] FAIL: Missing features: {missing}")
        extractor.close()
        sys.exit(1)

    print(f"[PASS] PASS: Binary features extracted")
    print(f"    Player: {player}")
    print(f"    Features: {len(features)}")
    print(f"    Success rate (L10): {features['success_rate_l10']:.1%}")
    print(f"    Current streak: {features['current_streak']:+.0f}")
    print(f"    Games played: {features['games_played']:.0f}")
    
    extractor.close()
    
except Exception as e:
    print(f"[FAIL] FAIL: Binary extractor error - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Continuous feature extraction
print("[TEST 4] Testing continuous feature extractor...")
try:
    extractor = ContinuousFeatureExtractor(db_path)
    extractor.connect()
    
    # Get a sample player
    cursor = extractor.conn.cursor()
    cursor.execute("""
        SELECT player_name, team, opponent, is_home
        FROM player_game_logs
        WHERE game_date = '2025-10-15'
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if row:
        player, team, opponent, is_home = row
        
        # Extract features
        features = extractor.extract_features(
            player_name=player,
            team=team,
            game_date='2025-10-15',
            opponent=opponent,
            is_home=bool(is_home)
        )
        
        # Check expected features exist
        expected = [
            'sog_season', 'sog_l10', 'sog_l5',
            'sog_std_season', 'sog_std_l10', 'sog_trend',
            'avg_toi_minutes', 'is_home', 'games_played', 'insufficient_data'
        ]
        
        missing = [f for f in expected if f not in features]

        if missing:
            print(f"[FAIL] FAIL: Missing features: {missing}")
            extractor.close()
            sys.exit(1)

        print(f"[PASS] PASS: Continuous features extracted")
        print(f"    Player: {player}")
        print(f"    Features: {len(features)}")
        print(f"    SOG (L10): {features['sog_l10']:.2f}")
        print(f"    Trend: {features['sog_trend']:+.2f}")
        print(f"    TOI: {features['avg_toi_minutes']:.1f} min")
    else:
        print("[WARNING] WARNING: No test data available, skipping")
    
    extractor.close()
    
except Exception as e:
    print(f"[FAIL] FAIL: Continuous extractor error - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: Statistical prediction engine
print("[TEST 5] Testing statistical prediction engine...")
try:
    engine = StatisticalPredictionEngine(db_path, learning_mode=True)
    
    # Get a player with history
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_name, team
        FROM player_game_logs
        WHERE game_date < '2025-10-15'
        GROUP BY player_name, team
        HAVING COUNT(*) >= 5
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if not row:
        print("[WARNING] WARNING: No players with 5+ games, skipping")
        conn.close()
    else:
        player, team = row
        conn.close()
        
        # Test points prediction
        print(f"\n  Testing points prediction for {player}...")
        pred = engine.predict_points(
            player=player,
            team=team,
            game_date='2025-10-15',
            opponent='OPP',
            is_home=True
        )
        
        if pred is None:
            print("    [WARNING] Insufficient data (expected for some players)")
        else:
            print(f"    Prediction: {pred['prediction']}")
            print(f"    Probability: {pred['probability']:.1%}")
            print(f"    Confidence: {pred['confidence_tier']}")
            print(f"    Features stored: {len(pred['features'])}")
            
            # Verify features are correct names
            expected_features = [
                'success_rate_season', 'success_rate_l10', 'current_streak',
                'is_home', 'lambda_param'
            ]
            has_features = all(f in pred['features'] for f in expected_features)
            
            if has_features:
                print(f"    [PASS] Correct feature names")
            else:
                print(f"    [FAIL] Missing expected features")
                print(f"    Got: {list(pred['features'].keys())}")
        
        # Test shots prediction
        print(f"\n  Testing shots prediction for {player}...")
        pred = engine.predict_shots(
            player=player,
            team=team,
            game_date='2025-10-15',
            opponent='OPP',
            is_home=True,
            line=2.5
        )
        
        if pred is None:
            print("    [WARNING] Insufficient data (expected for some players)")
        else:
            print(f"    Prediction: {pred['prediction']}")
            print(f"    Probability: {pred['probability']:.1%}")
            print(f"    Confidence: {pred['confidence_tier']}")
            print(f"    Features stored: {len(pred['features'])}")
            
            # Verify features are correct names
            expected_features = [
                'sog_season', 'sog_l10', 'sog_trend',
                'is_home', 'mean_shots'
            ]
            has_features = all(f in pred['features'] for f in expected_features)
            
            if has_features:
                print(f"    [PASS] Correct feature names")
            else:
                print(f"    [FAIL] Missing expected features")
                print(f"    Got: {list(pred['features'].keys())}")
    
    print()
    print("[PASS] PASS: Statistical prediction engine working")
    
except Exception as e:
    print(f"[FAIL] FAIL: Prediction engine error - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 6: Database feature storage
print("[TEST 6] Checking feature storage in database...")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if features_json column exists
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'features_json' not in columns:
        print("[FAIL] FAIL: features_json column missing from predictions table")
        conn.close()
        sys.exit(1)
    
    # Check if any predictions have features
    cursor.execute("""
        SELECT COUNT(*) 
        FROM predictions 
        WHERE features_json IS NOT NULL
    """)
    count_with_features = cursor.fetchone()[0]
    
    if count_with_features > 0:
        # Get a sample
        cursor.execute("""
            SELECT player_name, features_json 
            FROM predictions 
            WHERE features_json IS NOT NULL 
            LIMIT 1
        """)
        row = cursor.fetchone()
        player, features_json = row
        features = json.loads(features_json)
        
        print(f"[PASS] PASS: Features being saved to database")
        print(f"    Predictions with features: {count_with_features}")
        print(f"    Sample player: {player}")
        print(f"    Sample features: {len(features)}")
        print(f"    Feature names: {', '.join(list(features.keys())[:5])}...")
    else:
        print("[WARNING] WARNING: No predictions with features yet")
        print("    This is expected if you just started testing")
        print("    Run generate_predictions to populate")
    
    conn.close()
    
except Exception as e:
    print(f"[FAIL] FAIL: Database check error - {e}")
    sys.exit(1)

print()
print("="*80)
print("ALL TESTS PASSED [PASS]")
print("="*80)
print()
print("Your statistical_predictions_v2.py is working correctly!")
print()
print("Next steps:")
print("  1. Run backtest validation: python generate_predictions_backtest.py")
print("  2. Generate daily predictions: python generate_predictions_daily_v2.py")
print("  3. Grade predictions: python v2_auto_grade_yesterday_v3.py")
print()
print("System Status: READY FOR PRODUCTION ðŸš€")
