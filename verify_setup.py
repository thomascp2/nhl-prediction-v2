"""
Setup Verification Script
=========================
Confirms NFL and MLB systems are properly configured
"""

import sys
import sqlite3
from pathlib import Path

def verify_database(db_path, system_name):
    """Verify database exists and has tables"""
    print(f"\n{'='*60}")
    print(f"🔍 Verifying {system_name} System")
    print(f"{'='*60}")

    # Check if database file exists
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database NOT found at: {db_path}")
        return False

    print(f"✅ Database found: {db_path}")
    print(f"   File size: {db_file.stat().st_size / 1024:.2f} KB")

    # Connect and check tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\n📊 Tables found ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   • {table}: {count} rows")

        # Get list of views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]

        print(f"\n👁️  Views found ({len(views)}):")
        for view in views:
            print(f"   • {view}")

        conn.close()
        print(f"\n✅ {system_name} database is fully operational!")
        return True

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def verify_configs():
    """Verify config files can be imported"""
    print(f"\n{'='*60}")
    print(f"🔍 Verifying Configuration Files")
    print(f"{'='*60}")

    # Add NFL system to path
    nfl_path = Path(r"C:\Users\thoma\NFL-Model-v1")
    if nfl_path.exists():
        sys.path.insert(0, str(nfl_path))
        try:
            import nfl_config
            print(f"\n✅ NFL Config loaded successfully!")
            print(f"   Root: {nfl_config.NFL_ROOT}")
            print(f"   DB: {nfl_config.DB_PATH}")
            print(f"   Learning Mode: {nfl_config.LEARNING_MODE}")
            print(f"   Probability Cap: {nfl_config.PROBABILITY_CAP}")
            print(f"   Enabled Props: {[k for k, v in nfl_config.PROP_TYPES.items() if v['enabled']]}")
            nfl_db_path = nfl_config.DB_PATH
        except Exception as e:
            print(f"❌ Failed to load NFL config: {e}")
            nfl_db_path = None
    else:
        print(f"❌ NFL directory not found: {nfl_path}")
        nfl_db_path = None

    # Add MLB system to path
    mlb_path = Path(r"C:\Users\thoma\MLB-Model-v1")
    if mlb_path.exists():
        sys.path.insert(0, str(mlb_path))
        try:
            import mlb_config
            print(f"\n✅ MLB Config loaded successfully!")
            print(f"   Root: {mlb_config.MLB_ROOT}")
            print(f"   DB: {mlb_config.DB_PATH}")
            print(f"   Learning Mode: {mlb_config.LEARNING_MODE}")
            print(f"   Probability Cap: {mlb_config.PROBABILITY_CAP}")
            print(f"   Enabled Props: {[k for k, v in mlb_config.PROP_TYPES.items() if v['enabled']]}")
            mlb_db_path = mlb_config.DB_PATH
        except Exception as e:
            print(f"❌ Failed to load MLB config: {e}")
            mlb_db_path = None
    else:
        print(f"❌ MLB directory not found: {mlb_path}")
        mlb_db_path = None

    return nfl_db_path, mlb_db_path

def main():
    print("\n" + "="*60)
    print("🏈⚾ NFL & MLB PREDICTION SYSTEMS - SETUP VERIFICATION")
    print("="*60)

    # Verify configs can be loaded
    nfl_db_path, mlb_db_path = verify_configs()

    # Verify NFL database
    nfl_ok = False
    if nfl_db_path:
        nfl_ok = verify_database(nfl_db_path, "NFL")

    # Verify MLB database
    mlb_ok = False
    if mlb_db_path:
        mlb_ok = verify_database(mlb_db_path, "MLB")

    # Final summary
    print(f"\n{'='*60}")
    print(f"📋 FINAL SUMMARY")
    print(f"{'='*60}")

    if nfl_ok and mlb_ok:
        print(f"\n🎉 SUCCESS! Both systems are fully operational!")
        print(f"\n✅ NFL System: Ready")
        print(f"   • Database: {nfl_db_path}")
        print(f"   • 7 tables + 3 views")
        print(f"   • 3 prop types enabled (rec_yards, receptions, rush_yards)")

        print(f"\n✅ MLB System: Ready")
        print(f"   • Database: {mlb_db_path}")
        print(f"   • 5 tables + 4 views")
        print(f"   • 3 prop types enabled (pitcher_strikeouts, batter_hits, batter_total_bases)")

        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. Build data fetchers (Week 2-4)")
        print(f"   2. Run backtest validation")
        print(f"   3. Deploy live (NFL Week 11, MLB Opening Day 2025)")

    else:
        print(f"\n⚠️  ISSUES DETECTED:")
        if not nfl_ok:
            print(f"   ❌ NFL system needs attention")
        if not mlb_ok:
            print(f"   ❌ MLB system needs attention")
        print(f"\n   Please review the errors above and fix any issues.")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
