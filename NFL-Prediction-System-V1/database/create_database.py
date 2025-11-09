"""
Create NFL Predictions Database
================================
Initializes the database with the schema
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import nfl_config

def create_database():
    """Create database and execute schema"""
    print(f"Creating database at: {nfl_config.DB_PATH}")

    # Read schema
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Create database and execute schema
    conn = sqlite3.connect(nfl_config.DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("✅ Database created successfully!")

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"\n📊 Tables created ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")

        # Verify views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()

        if views:
            print(f"\n👁️  Views created ({len(views)}):")
            for view in views:
                print(f"  - {view[0]}")

        # Check schema version
        cursor.execute("SELECT version, applied_at FROM schema_version")
        version = cursor.fetchone()
        print(f"\n📌 Schema version: {version[0]} (applied {version[1]})")

        return True

    except sqlite3.Error as e:
        print(f"❌ Error creating database: {e}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)
