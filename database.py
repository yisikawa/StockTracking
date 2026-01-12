"""データベース操作モジュール"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from config import DB_NAME, CACHE_MINUTES, HISTORY_DAYS


class Database:
    """データベース操作クラス"""
    
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # 株価データテーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 追跡銘柄テーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS tracked_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # キャッシュテーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS price_cache (
                symbol TEXT PRIMARY KEY,
                current_price REAL,
                previous_close REAL,
                change REAL,
                change_percent REAL,
                volume INTEGER,
                market_cap INTEGER,
                pe_ratio REAL,
                dividend_yield REAL,
                week_52_high REAL,
                week_52_low REAL,
                cached_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_tracked_stocks(self) -> List[Dict]:
        """追跡中の銘柄一覧を取得"""
        conn = self.get_connection()
        stocks = conn.execute(
            'SELECT * FROM tracked_stocks ORDER BY added_at DESC'
        ).fetchall()
        conn.close()
        return [dict(stock) for stock in stocks]
    
    def add_stock(self, symbol: str, name: str) -> bool:
        """銘柄を追加"""
        conn = self.get_connection()
        try:
            conn.execute(
                'INSERT INTO tracked_stocks (symbol, name) VALUES (?, ?)',
                (symbol.upper(), name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def remove_stock(self, symbol: str):
        """銘柄を削除"""
        conn = self.get_connection()
        conn.execute('DELETE FROM tracked_stocks WHERE symbol = ?', (symbol.upper(),))
        conn.commit()
        conn.close()
    
    def get_cached_price(self, symbol: str, cache_minutes: int = CACHE_MINUTES) -> Optional[Dict]:
        """キャッシュされた価格情報を取得"""
        conn = self.get_connection()
        cache = conn.execute(
            'SELECT * FROM price_cache WHERE symbol = ?',
            (symbol.upper(),)
        ).fetchone()
        conn.close()
        
        if cache:
            cached_at = datetime.fromisoformat(cache['cached_at'])
            if (datetime.now() - cached_at).total_seconds() < cache_minutes * 60:
                return dict(cache)
        return None
    
    def save_price_cache(self, symbol: str, price_data: Dict):
        """価格情報をキャッシュに保存"""
        conn = self.get_connection()
        conn.execute('''
            INSERT OR REPLACE INTO price_cache 
            (symbol, current_price, previous_close, change, change_percent, volume,
             market_cap, pe_ratio, dividend_yield, week_52_high, week_52_low, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol.upper(),
            price_data.get('current_price'),
            price_data.get('previous_close'),
            price_data.get('change'),
            price_data.get('change_percent'),
            price_data.get('volume'),
            price_data.get('market_cap'),
            price_data.get('pe_ratio'),
            price_data.get('dividend_yield'),
            price_data.get('52_week_high'),
            price_data.get('52_week_low'),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def get_cached_history(self, symbol: str, days: int = HISTORY_DAYS) -> List[Dict]:
        """データベースから履歴データを取得"""
        conn = self.get_connection()
        history = conn.execute('''
            SELECT date, open, high, low, close, volume
            FROM stock_prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (symbol.upper(), days)).fetchall()
        conn.close()
        
        return [{
            'date': row['date'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        } for row in history]
    
    def save_price_history(self, symbol: str, price_data: List[Dict], days: int = 30):
        """価格履歴を保存"""
        conn = self.get_connection()
        for item in price_data[-days:]:
            conn.execute('''
                INSERT OR REPLACE INTO stock_prices 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol.upper(),
                item['date'],
                item['open'],
                item['high'],
                item['low'],
                item['close'],
                item['volume']
            ))
        conn.commit()
        conn.close()


# グローバルインスタンス
db = Database()
