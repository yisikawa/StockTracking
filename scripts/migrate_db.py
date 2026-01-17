import sqlite3
import logging
import os
import sys

# Add the project root to sys.path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate():
    db_path = DB_NAME
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check tracked_stocks table for missing columns
        cursor.execute("PRAGMA table_info(tracked_stocks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'quantity' not in columns:
            logger.info("Adding 'quantity' column to 'tracked_stocks' table")
            cursor.execute("ALTER TABLE tracked_stocks ADD COLUMN quantity FLOAT DEFAULT 0.0")
            
        if 'avg_price' not in columns:
            logger.info("Adding 'avg_price' column to 'tracked_stocks' table")
            cursor.execute("ALTER TABLE tracked_stocks ADD COLUMN avg_price FLOAT DEFAULT 0.0")

        # Check for price_cache table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_cache'")
        if not cursor.fetchone():
            logger.info("Table 'price_cache' does not exist. It will be created by SQLAlchemy init_db.")
            # We can leave this to init_db, but for a clean migration we could create it here.
            # But since we use SQLAlchemy, let's just ensure columns in existing tables are correct.

        conn.commit()
        logger.info("Database migration completed successfully.")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
