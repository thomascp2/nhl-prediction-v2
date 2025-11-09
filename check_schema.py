"""
Database Schema Checker and Fixer
Identifies required columns and generates proper insert statements
"""

import sqlite3
import sys
from datetime import datetime

def check_schema():
    """Check predictions table schema"""
    try:
        conn = sqlite3.connect('database/nhl_predictions_v2.db')
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(predictions)")
        columns = cursor.fetchall()
        
        print("="*80)
        print("PREDICTIONS TABLE SCHEMA")
        print("="*80)
        print()
        print(f"{'Column':<30} {'Type':<15} {'NotNull':<8} {'Default':<15} {'PK':<4}")
        print("-"*80)
        
        required_columns = []
        optional_columns = []
        
        for col in columns:
            col_id, name, type_, notnull, default, pk = col
            print(f"{name:<30} {type_:<15} {notnull:<8} {str(default):<15} {pk:<4}")
            
            if notnull and default is None and not pk:
                required_columns.append((name, type_))
            else:
                optional_columns.append((name, type_))
        
        print()
        print("="*80)
        print("COLUMN REQUIREMENTS")
        print("="*80)
        print()
        
        print(f"REQUIRED (NOT NULL, no default): {len(required_columns)} columns")
        for name, type_ in required_columns:
            print(f"  âš ï¸  {name} ({type_}) - MUST provide value")
        print()
        
        print(f"OPTIONAL (nullable or has default): {len(optional_columns)} columns")
        for name, type_ in optional_columns:
            print(f"  âœ… {name} ({type_})")
        print()
        
        # Check existing predictions
        cursor.execute("SELECT COUNT(*) FROM predictions")
        count = cursor.fetchone()[0]
        print(f"Total predictions in database: {count}")
        
        if count > 0:
            # Get sample
            cursor.execute("SELECT * FROM predictions LIMIT 1")
            sample = cursor.fetchone()
            col_names = [desc[0] for desc in cursor.description]
            
            print()
            print("="*80)
            print("SAMPLE PREDICTION (what a valid row looks like)")
            print("="*80)
            print()
            
            for name, value in zip(col_names, sample):
                if value is None:
                    print(f"  {name}: NULL")
                elif isinstance(value, str) and len(str(value)) > 50:
                    print(f"  {name}: {str(value)[:47]}...")
                else:
                    print(f"  {name}: {value}")
        
        conn.close()
        
        # Generate proper INSERT statement
        print()
        print("="*80)
        print("PROPER INSERT STATEMENT TEMPLATE")
        print("="*80)
        print()
        
        all_cols = [col[1] for col in cursor.execute("PRAGMA table_info(predictions)").fetchall()]
        
        print("cursor.execute('''")
        print("    INSERT INTO predictions (")
        print("        " + ",\n        ".join(all_cols))
        print("    ) VALUES (" + ", ".join(["?"] * len(all_cols)) + ")")
        print("''', (")
        for col in all_cols:
            print(f"    {col},  # TODO: provide value")
        print("))")
        
        return required_columns
        
    except sqlite3.Error as e:
        print(f"âŒ Database error: {e}")
        return None
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    required = check_schema()
    
    if required:
        print()
        print("="*80)
        print("âœ… SCHEMA CHECK COMPLETE")
        print("="*80)
        print()
        print("Next step: Update statistical_predictions_v2.py to provide ALL required columns")
        print()
        print("Required columns that MUST be provided:")
        for name, type_ in required:
            print(f"  - {name}")
