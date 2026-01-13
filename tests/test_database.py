import unittest
import sys
import os
from sqlalchemy import create_engine
from typing import Dict

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import db_session, Base
from database import Database, db

class TestDatabase(unittest.TestCase):
    
    def setUp(self):
        # Create in-memory engine
        self.engine = create_engine('sqlite:///:memory:')
        
        # Configure the global session to use this engine
        db_session.configure(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Use the global db instance (it's stateless wrapper around db_session)
        self.db = db
        
    def tearDown(self):
        db_session.remove()
        Base.metadata.drop_all(self.engine)
        
    def test_add_get_remove_stock(self):
        # Add
        result = self.db.add_stock("AAPL", "Apple Inc.")
        self.assertTrue(result)
        
        # Get
        stocks = self.db.get_tracked_stocks()
        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0]['symbol'], "AAPL")
        
        # Add duplicate
        result = self.db.add_stock("AAPL", "Apple Inc.")
        self.assertFalse(result)
        
        # Remove
        self.db.remove_stock("AAPL")
        stocks = self.db.get_tracked_stocks()
        self.assertEqual(len(stocks), 0)
        
    def test_cache(self):
        symbol = "TEST"
        price_data = {"current_price": 100}
        
        # Save cache
        self.db.save_price_cache(symbol, price_data)
        
        # Get cache
        cached = self.db.get_cached_price(symbol, cache_minutes=5)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['current_price'], 100)
        
        # Expired cache (0 minutes valid)
        expired = self.db.get_cached_price(symbol, cache_minutes=0)
        self.assertIsNone(expired)

if __name__ == '__main__':
    unittest.main()
