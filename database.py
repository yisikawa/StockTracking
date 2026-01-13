"""データベース操作モジュール (SQLAlchemy版)"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.exc import IntegrityError
from models.database import db_session, init_db
from models.stock import TrackedStock, StockPrice, PriceCache
from config import CACHE_MINUTES, HISTORY_DAYS

logger = logging.getLogger(__name__)


class Database:
    """データベース操作クラス"""
    
    def __init__(self):
        # データベース初期化は明示的に呼び出すか、アプリ起動時に行う
        pass

    def init_app(self):
        """データベース初期化"""
        init_db()
    
    def get_tracked_stocks(self) -> List[Dict]:
        """追跡中の銘柄一覧を取得"""
        stocks = db_session.query(TrackedStock).order_by(TrackedStock.added_at.desc()).all()
        return [stock.to_dict() for stock in stocks]
    
    def add_stock(self, symbol: str, name: str) -> bool:
        """銘柄を追加"""
        try:
            stock = TrackedStock(symbol=symbol.upper(), name=name)
            db_session.add(stock)
            db_session.commit()
            logger.info(f"Added stock: {symbol}")
            return True
        except IntegrityError:
            db_session.rollback()
            return False
        except Exception as e:
            logger.error(f"Error adding stock: {e}")
            db_session.rollback()
            return False
    
    def remove_stock(self, symbol: str):
        """銘柄を削除"""
        logger.info(f"Removing stock: {symbol}")
        db_session.query(TrackedStock).filter_by(symbol=symbol.upper()).delete()
        db_session.commit()
    
    def get_cached_price(self, symbol: str, cache_minutes: int = CACHE_MINUTES) -> Optional[Dict]:
        """キャッシュされた価格情報を取得"""
        try:
            cache = db_session.query(PriceCache).filter_by(symbol=symbol.upper()).first()
            if cache and cache.cached_at:
                if (datetime.now() - cache.cached_at).total_seconds() < cache_minutes * 60:
                    return cache.to_dict()
        except Exception as e:
            logger.error(f"Error getting cached price: {e}")
        return None
    
    def save_price_cache(self, symbol: str, price_data: Dict):
        """価格情報をキャッシュに保存"""
        try:
            # マージ（アップサート）
            cache = PriceCache(
                symbol=symbol.upper(),
                current_price=price_data.get('current_price'),
                previous_close=price_data.get('previous_close'),
                change=price_data.get('change'),
                change_percent=price_data.get('change_percent'),
                volume=price_data.get('volume'),
                market_cap=price_data.get('market_cap'),
                pe_ratio=price_data.get('pe_ratio'),
                dividend_yield=price_data.get('dividend_yield'),
                week_52_high=price_data.get('52_week_high'),
                week_52_low=price_data.get('52_week_low'),
                cached_at=datetime.now()
            )
            db_session.merge(cache)
            db_session.commit()
        except Exception as e:
            logger.error(f"Error saving price cache: {e}")
            db_session.rollback()
    
    def get_cached_history(self, symbol: str, days: int = HISTORY_DAYS) -> List[Dict]:
        """データベースから履歴データを取得"""
        try:
            prices = db_session.query(StockPrice)\
                .filter_by(symbol=symbol.upper())\
                .order_by(StockPrice.date.desc())\
                .limit(days).all()
            return [price.to_dict() for price in prices]
        except Exception as e:
            logger.error(f"Error getting cached history: {e}")
            return []
    
    def save_price_history(self, symbol: str, price_data: List[Dict], days: int = 30):
        """価格履歴を保存"""
        try:
            for item in price_data[-days:]:
                # 既存データをチェック
                existing = db_session.query(StockPrice).filter_by(
                    symbol=symbol.upper(), 
                    date=item['date']
                ).first()
                
                if existing:
                    existing.open = item['open']
                    existing.high = item['high']
                    existing.low = item['low']
                    existing.close = item['close']
                    existing.volume = item['volume']
                else:
                    price = StockPrice(
                        symbol=symbol.upper(),
                        date=item['date'],
                        open=item['open'],
                        high=item['high'],
                        low=item['low'],
                        close=item['close'],
                        volume=item['volume']
                    )
                    db_session.add(price)
            db_session.commit()
        except Exception as e:
            logger.error(f"Error saving price history: {e}")
            db_session.rollback()


# グローバルインスタンス
db = Database()
