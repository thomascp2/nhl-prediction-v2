"""
Comprehensive Database Diagnostic
Checks what's actually happening with features_json
"""

import sqlite3
import json
from datetime import datetime

def diagnose_database():
    """Run comprehensive database diagnostics"""
    
    print("="*80)
    print("DATABASE DIAGNOSTIC - FEATURE STORAGE")
    print("="*80)
    print()
    
    try:
        conn = sqlite3.connect('database/nhl_predictions_v2.db')
        cursor = conn.cursor()
        
        # Check 1: Schema
        print("[CHECK 1] Database Schema")
        print("-"*80)
        cursor.execute("PRAGMA table_info(predictions)")
        columns = cursor.fetchall()
        
        features_json_exists = False
        for col in columns:
            col_id, name, type_, notnull, default, pk = col
            if name == 'features_json':
                features_json_exists = True
                print(f"âœ… features_json column EXISTS")
                print(f"   Type: {type_}")
                print(f"   Nullable: {'No' if notnull else 'Yes'}")
                print(f"   Default: {default}")
                break
        
        if not features_json_exists:
            print("âŒ features_json column DOES NOT EXIST!")
            print("   This is the problem - the column is missing from your database!")
            return
        
        print()
        
        # Check 2: Recent predictions
        print("[CHECK 2] Recent Predictions (Last 5)")
        print("-"*80)
        cursor.execute("""
            SELECT id, player_name, prop_type, 
                   LENGTH(features_json) as json_length,
                   features_json
            FROM predictions 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("âš ï¸  No predictions found in database")
            return
        
        has_features = 0
        no_features = 0
        
        for pred_id, player, prop_type, json_len, features_json in rows:
            print(f"\nPrediction #{pred_id}: {player} ({prop_type})")
            
            if features_json and json_len and json_len > 0:
                print(f"  âœ… HAS features_json ({json_len} characters)")
                
                # Try to parse
                try:
                    features = json.loads(features_json)
                    print(f"  âœ… Valid JSON ({len(features)} features)")
                    print(f"  Sample: {list(features.keys())[:5]}")
                    has_features += 1
                except json.JSONDecodeError:
                    print(f"  âš ï¸  Has data but INVALID JSON")
                    print(f"  First 100 chars: {features_json[:100]}")
            else:
                print(f"  âŒ NO features_json (NULL or empty)")
                no_features += 1
        
        print()
        print("-"*80)
        print(f"Summary: {has_features} with features, {no_features} without")
        print()
        
        # Check 3: Total stats
        print("[CHECK 3] Overall Statistics")
        print("-"*80)
        
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE features_json IS NOT NULL AND features_json != ''
        """)
        with_features = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT prediction_batch_id) 
            FROM predictions
        """)
        batch_count = cursor.fetchone()[0]
        
        print(f"Total predictions: {total}")
        print(f"With features_json: {with_features} ({with_features/total*100:.1f}%)")
        print(f"Without features_json: {total - with_features} ({(total-with_features)/total*100:.1f}%)")
        print(f"Unique batches: {batch_count}")
        print()
        
        # Check 4: Batch analysis
        print("[CHECK 4] By Batch ID")
        print("-"*80)
        cursor.execute("""
            SELECT 
                prediction_batch_id,
                COUNT(*) as total,
                SUM(CASE WHEN features_json IS NOT NULL AND features_json != '' THEN 1 ELSE 0 END) as with_features,
                MIN(created_at) as first_pred
            FROM predictions
            GROUP BY prediction_batch_id
            ORDER BY first_pred DESC
            LIMIT 5
        """)
        
        for batch_id, total, with_feats, first_pred in cursor.fetchall():
            pct = (with_feats/total*100) if total > 0 else 0
            print(f"\nBatch: {batch_id}")
            print(f"  Total: {total}")
            print(f"  With features: {with_feats} ({pct:.1f}%)")
            print(f"  First prediction: {first_pred}")
        
        print()
        
        # Check 5: Sample feature content
        print("[CHECK 5] Sample Feature Content")
        print("-"*80)
        cursor.execute("""
            SELECT player_name, prop_type, features_json
            FROM predictions
            WHERE features_json IS NOT NULL AND features_json != ''
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            player, prop_type, features_json = row
            print(f"Player: {player} ({prop_type})")
            print(f"\nFeatures JSON:")
            print(features_json)
            print()
            
            try:
                features = json.loads(features_json)
                print(f"Parsed features ({len(features)} total):")
                for key, value in features.items():
                    print(f"  {key}: {value}")
            except:
                print("âŒ Could not parse JSON")
        else:
            print("âŒ No predictions with features_json found")
            print("\nThis is the core problem - features are not being saved!")
        
        print()
        
        # Diagnosis
        print("="*80)
        print("DIAGNOSIS")
        print("="*80)
        print()
        
        if with_features == 0:
            print("âŒ CRITICAL PROBLEM: NO features_json being saved")
            print()
            print("Possible causes:")
            print("  1. Using old version of statistical_predictions_v2.py")
            print("  2. features_json column exists but script not writing to it")
            print("  3. Script has a bug in _save_prediction() method")
            print()
            print("Solution:")
            print("  1. Verify you replaced statistical_predictions_v2.py with FULLY_FIXED version")
            print("  2. Check that _save_prediction() includes features_json in INSERT")
            print("  3. Test with: python statistical_predictions_v2.py")
            print("  4. Check database after test: python check_feature_storage.py")
        elif with_features < total:
            print("âš ï¸  PARTIAL PROBLEM: Some predictions missing features_json")
            print()
            print(f"  {with_features} predictions have features ({with_features/total*100:.1f}%)")
            print(f"  {total - with_features} predictions missing features ({(total-with_features)/total*100:.1f}%)")
            print()
            print("This suggests:")
            print("  - Old predictions don't have features (created before fix)")
            print("  - New predictions should have features (created after fix)")
            print()
            print("Action:")
            print("  1. Check most recent batch - does it have features?")
            print("  2. If yes, system is working (old data is normal)")
            print("  3. If no, check script version and _save_prediction() method")
        else:
            print("âœ… SUCCESS: All predictions have features_json")
            print()
            print("Your system is working correctly!")
            print("Ready for ML training in Week 10")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"âŒ Database error: {e}")
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    diagnose_database()
