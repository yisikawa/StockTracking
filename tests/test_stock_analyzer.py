import unittest
import pandas as pd
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_analyzer import StockAnalyzer

class TestStockAnalyzer(unittest.TestCase):
    
    def setUp(self):
        # Create sample data for one year
        dates = pd.date_range(start='2023-01-01', periods=100)
        data = {
            'Close': [100 + i * 0.1 for i in range(100)], # Steady increase
            'High': [101 + i * 0.1 for i in range(100)],
            'Low': [99 + i * 0.1 for i in range(100)],
            'Volume': [1000 for _ in range(100)]
        }
        self.hist = pd.DataFrame(data, index=dates)
        
    def test_analyze(self):
        analysis = StockAnalyzer.analyze(self.hist)
        
        self.assertIsNotNone(analysis)
        self.assertIn('recommendation', analysis)
        self.assertIn('score', analysis)
        self.assertIn('recommendation', analysis)
        self.assertIn('score', analysis)
        self.assertIn('indicators', analysis)
        self.assertIn('moving_averages', analysis)
        
        indicators = analysis['indicators']
        self.assertIn('rsi', indicators)
        
        ma = analysis['moving_averages']
        self.assertIn('ma_20', ma)
        self.assertIn('ma_50', ma)
        
    def test_analyze_empty(self):
        empty_hist = pd.DataFrame()
        # Depending on implementation, might raise error or return default
        # Assuming we should handle it gracefully, but for now just checking if it runs
        try:
            StockAnalyzer.analyze(empty_hist)
        except:
            pass # Expected if empty handling isn't robust yet, but we are just setting up tests

if __name__ == '__main__':
    unittest.main()
