"""
Check if features_json is being saved in predictions table
"""

import sqlite3
import json

def check_feature_storage():
    """Check if features are being stored"""
    conn = sqlite3.connect('database/nhl_predictions_v2.db')
    cursor = conn.cursor()
    
    # Get sample predictions
    cursor.execute('''
        SELECT player_name, prop_type, features_json 
        FROM predictions 
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    
    rows = cursor.fetchall()
    
    print('=' * 80)
    print('FEATURE STORAGE CHECK')
    print('=' * 80)
    print()
    
    if not rows:
        print('No predictions found in database!')
        conn.close()
        return
    
    has_features = False
    missing_features = False
    
    for i, (player, prop, features_json) in enumerate(rows, 1):
        print(f'{i}. {player} ({prop}):')
        
        if features_json:
            try:
                features = json.loads(features_json)
                feature_count = len(features)
                print(f'   [OK] HAS {feature_count} FEATURES STORED')
                print(f'   Sample features: {list(features.keys())[:5]}')
                has_features = True
            except json.JSONDecodeError:
                print(f'   [WARNING] Has data but invalid JSON: {features_json[:50]}')
        else:
            print(f'   [ERROR] NULL - NO FEATURES STORED')
            missing_features = True
        
        print()
    
    # Summary
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print()
    
    if has_features and not missing_features:
        print('[OK] FEATURES ARE BEING SAVED!')
        print('   Your system is ready for ML training in Week 10.')
        print()
    elif missing_features and not has_features:
        print('[ERROR] FEATURES ARE NOT BEING SAVED!')
        print('   CRITICAL: You need to fix this before continuing.')
        print('   Without features, you cannot train ML models in Week 10.')
        print()
        print('   Next steps:')
        print('   1. Read FEATURE_STORAGE_FIX_GUIDE.md')
        print('   2. Update statistical_predictions_v2.py to save features')
        print('   3. Regenerate predictions with --force flag')
        print()
    else:
        print('[WARNING] MIXED RESULTS - Some predictions have features, some don\'t')
        print('   This suggests you recently added feature storage.')
        print('   Older predictions won\'t have features, but new ones will.')
        print()
    
    # Check total count
    cursor.execute('SELECT COUNT(*) FROM predictions')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE features_json IS NOT NULL')
    with_features = cursor.fetchone()[0]
    
    print(f'Total predictions: {total}')
    print(f'With features: {with_features} ({with_features/total*100:.1f}%)')
    print(f'Without features: {total - with_features} ({(total-with_features)/total*100:.1f}%)')
    print()
    
    conn.close()


if __name__ == '__main__':
    check_feature_storage()
