import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_api import StockAPI

class TestStockAPI(unittest.TestCase):
    
    def setUp(self):
        self.symbol = "AAPL"
        
    @patch('stock_api.StockAPI._get_ticker')
    def test_get_ticker_info_success(self, mock_get_ticker):
        # Mock ticker info
        mock_ticker = MagicMock()
        mock_ticker.info = {
            'longName': 'Apple Inc.',
            'marketCap': 1000000,
            'trailingPE': 25.5,
            'dividendYield': 0.01
        }
        mock_get_ticker.return_value = mock_ticker
        
        info = StockAPI.get_ticker_info(self.symbol)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['name'], 'Apple Inc.')
        self.assertEqual(info['market_cap'], 1000000)
    
    @patch('stock_api.StockAPI._get_ticker')
    def test_get_ticker_info_none(self, mock_get_ticker):
        # Mock exception
        mock_ticker = MagicMock()
        type(mock_ticker).info = PropertyMock(side_effect=Exception("API Error"))
        mock_get_ticker.return_value = mock_ticker
        
        # Should return None on error
        info = StockAPI.get_ticker_info(self.symbol)
        self.assertIsNone(info)

    def test_calculate_price_change(self):
        # Create a sample DataFrame
        data = {
            'Close': [100.0, 102.0, 105.0]
        }
        hist = pd.DataFrame(data)
        
        current, prev, change, percent = StockAPI.calculate_price_change(hist)
        
        self.assertEqual(current, 105.0)
        self.assertEqual(prev, 102.0)
        self.assertEqual(change, 3.0)
        self.assertAlmostEqual(percent, 2.941, places=3) # 3/102 * 100

    def test_calculate_price_change_empty(self):
        hist = pd.DataFrame()
        current, prev, change, percent = StockAPI.calculate_price_change(hist)
        self.assertEqual(current, 0.0)

    @patch('stock_api.get_stock_price_with_fallback')
    @patch('stock_api.db')
    def test_fetch_stocks_data_parallel(self, mock_db, mock_get_price):
        # Mock DB cache miss
        mock_db.get_cached_price.return_value = None
        
        # Mock API response
        mock_get_price.side_effect = lambda symbol, use_cache: {
            'symbol': symbol, 'current_price': 150.0
        }
        
        symbols = ['AAPL', 'GOOGL']
        results = StockAPI.fetch_stocks_data_parallel(symbols, delay=0)
        
        self.assertEqual(len(results), 2)
        symbols_in_results = [r['symbol'] for r in results]
        self.assertIn('AAPL', symbols_in_results)
        self.assertIn('GOOGL', symbols_in_results)

if __name__ == '__main__':
    unittest.main()
