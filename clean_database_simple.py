"""
Clean Database - Remove Predictions Without Features

Deletes all predictions that don't have features_json.
These predictions are useless for ML training anyway.
"""

import sqlite3

def clean_database():
    """Remove predictions without features_json"""
    
    print("="*80)
    print("CLEANING DATABASE - REMOVING PREDICTIONS WITHOUT FEATURES")
    print("="*80)
    print()
    
    try:
        conn = sqlite3.connect('database/nhl_predictions_v2.db')
        cursor = conn.cursor()
        
        # Count before
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_before = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE features_json IS NULL OR features_json = ''
        """)
        to_delete = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE features_json IS NOT NULL AND features_json != ''
        """)
        to_keep = cursor.fetchone()[0]
        
        print(f"Current state:")
        print(f"  Total predictions: {total_before}")
        print(f"  With features: {to_keep}")
        print(f"  Without features: {to_delete}")
        print()
        
        if to_delete == 0:
            print("SUCCESS: No predictions to delete - all have features!")
            conn.close()
            return
        
        # Confirm deletion
        print(f"WARNING: About to DELETE {to_delete} predictions without features")
        print(f"KEEP: Will keep {to_keep} predictions with features")
        print()
        
        response = input("Proceed with deletion? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("CANCELLED - no changes made")
            conn.close()
            return
        
        print()
        print("Deleting predictions without features...")
        
        # Delete predictions without features
        cursor.execute("""
            DELETE FROM predictions 
            WHERE features_json IS NULL OR features_json = ''
        """)
        deleted_predictions = cursor.rowcount
        
        # Also delete orphaned prediction outcomes
        cursor.execute("""
            DELETE FROM prediction_outcomes 
            WHERE prediction_id NOT IN (SELECT id FROM predictions)
        """)
        deleted_outcomes = cursor.rowcount
        
        conn.commit()
        
        # Count after
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_after = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE features_json IS NOT NULL AND features_json != ''
        """)
        with_features_after = cursor.fetchone()[0]
        
        print()
        print("="*80)
        print("CLEANUP COMPLETE")
        print("="*80)
        print()
        print(f"Deleted:")
        print(f"  {deleted_predictions} predictions without features")
        print(f"  {deleted_outcomes} orphaned prediction outcomes")
        print()
        print(f"Remaining:")
        print(f"  {total_after} predictions")
        if total_after > 0:
            pct = (with_features_after/total_after*100)
            print(f"  {with_features_after} with features ({pct:.1f}%)")
        print()
        
        if total_after == with_features_after and total_after > 0:
            print("SUCCESS: All remaining predictions have features!")
            print("Your database is now 100% ML-ready")
        else:
            print("WARNING: Some predictions still missing features")
            print("Run diagnostic again to investigate")
        
        print()
        print("Next steps:")
        print("  1. Generate fresh predictions: python generate_predictions_daily.py")
        print("  2. Verify features saved: python check_feature_storage.py")
        print("  3. Continue daily workflow")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"ERROR: Database error: {e}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    clean_database()
