from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from datetime import datetime
from models.database import Base

class TrackedStock(Base):
    __tablename__ = 'tracked_stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    name = Column(String)
    added_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name': self.name,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }

class StockPrice(Base):
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    date = Column(String, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint('symbol', 'date', name='_symbol_date_uc'),)

    def to_dict(self):
        return {
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

class PriceCache(Base):
    __tablename__ = 'price_cache'
    
    symbol = Column(String, primary_key=True)
    current_price = Column(Float)
    previous_close = Column(Float)
    change = Column(Float)
    change_percent = Column(Float)
    volume = Column(Integer)
    market_cap = Column(Integer)
    pe_ratio = Column(Float)
    dividend_yield = Column(Float)
    week_52_high = Column(Float)
    week_52_low = Column(Float)
    cached_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'current_price': self.current_price,
            'previous_close': self.previous_close,
            'change': self.change,
            'change_percent': self.change_percent,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'pe_ratio': self.pe_ratio,
            'dividend_yield': self.dividend_yield,
            'week_52_high': self.week_52_high,
            'week_52_low': self.week_52_low,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None
        }
