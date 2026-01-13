
import sqlite3
import os

DB_NAME = "stock_tracking.db"

def migrate():
    print(f"Migrating database: {DB_NAME}")
    
    if not os.path.exists(DB_NAME):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(tracked_stocks)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'quantity' not in columns:
            print("Adding 'quantity' column...")
            cursor.execute("ALTER TABLE tracked_stocks ADD COLUMN quantity REAL DEFAULT 0.0")
        else:
            print("'quantity' column already exists.")

        if 'avg_price' not in columns:
            print("Adding 'avg_price' column...")
            cursor.execute("ALTER TABLE tracked_stocks ADD COLUMN avg_price REAL DEFAULT 0.0")
        else:
            print("'avg_price' column already exists.")
            
        conn.commit()
        print("Migration successful.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
