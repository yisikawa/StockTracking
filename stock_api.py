"""株価API操作モジュール"""
import logging
import yfinance as yf
import pandas as pd
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from database import db
from config import CACHE_MINUTES, HISTORY_DAYS, USE_YAHOO_AUTH
from yahoo_auth import yahoo_auth
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class StockAPI:
    """株価API操作クラス"""
    
    @staticmethod
    def _get_ticker(symbol: str):
        """認証情報付きTickerオブジェクトを取得"""
        # Yahoo認証が有効な場合、セッションを設定
        if USE_YAHOO_AUTH:
            session = yahoo_auth.get_session()
            if session:
                # yfinanceは内部的にrequestsを使用しますが、
                # 直接セッションを渡すことはできません
                # 代わりに、環境変数やグローバル設定でCookieを共有します
                cookies = yahoo_auth.get_cookies()
                if cookies:
                    # Cookieを環境変数に設定（yfinanceが使用する可能性がある）
                    import os
                    cookie_string = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                    os.environ['YAHOO_COOKIE'] = cookie_string
        
        ticker = yf.Ticker(symbol)
        return ticker
    
    @staticmethod
    def get_ticker_info(symbol: str) -> Optional[Dict]:
        """銘柄情報を取得"""
        try:
            ticker = StockAPI._get_ticker(symbol)
            info = ticker.info
            if info and ('longName' in info or 'shortName' in info):
                return {
                    'name': info.get('longName') or info.get('shortName') or symbol,
                    'market_cap': info.get('marketCap'),
                    'pe_ratio': info.get('trailingPE'),
                    'dividend_yield': info.get('dividendYield'),
                    '52_week_high': info.get('fiftyTwoWeekHigh'),
                    '52_week_low': info.get('fiftyTwoWeekLow')
                }
        except Exception as e:
            logger.warning(f"Error getting ticker info for {symbol}: {e}")
        return None
    
    @staticmethod
    def get_history(symbol: str, period: str = '1mo') -> Optional[pd.DataFrame]:
        """株価履歴を取得"""
        try:
            ticker = StockAPI._get_ticker(symbol)
            hist = ticker.history(period=period)
            return hist if not hist.empty else None
        except Exception as e:
            logger.error(f"Error getting history for {symbol}: {e}")
            return None
    
    @staticmethod
    def format_history_data(hist: pd.DataFrame) -> List[Dict]:
        """履歴データを整形"""
        data = []
        for date, row in hist.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        return data
    
    @staticmethod
    def calculate_price_change(hist: pd.DataFrame) -> Tuple[float, float, float, float]:
        """価格変動を計算"""
        if len(hist) == 0:
            return 0.0, 0.0, 0.0, 0.0
        
        current_price = float(hist['Close'].iloc[-1])
        previous_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close > 0 else 0.0
        
        return current_price, previous_close, change, change_percent
    
    @staticmethod
    def build_price_response(
        symbol: str,
        hist: Optional[pd.DataFrame],
        info: Optional[Dict],
        cached: bool = False,
        message: Optional[str] = None
    ) -> Dict:
        """価格レスポンスを構築"""
        if hist is None or hist.empty:
            return None
        
        current_price, previous_close, change, change_percent = StockAPI.calculate_price_change(hist)
        history_data = StockAPI.format_history_data(hist)
        
        response = {
            'symbol': symbol.upper(),
            'name': (info.get('name') if info else symbol) if info else symbol,
            'current_price': current_price,
            'previous_close': previous_close,
            'change': change,
            'change_percent': change_percent,
            'volume': int(hist['Volume'].iloc[-1]),
            'market_cap': info.get('market_cap') if info else None,
            'pe_ratio': info.get('pe_ratio') if info else None,
            'dividend_yield': info.get('dividend_yield') if info else None,
            '52_week_high': info.get('52_week_high') if info else None,
            '52_week_low': info.get('52_week_low') if info else None,
            'history': history_data,
            'cached': cached
        }
        
        if message:
            response['message'] = message
        
        return response
    
    @staticmethod
    def build_cached_response(symbol: str, cached_price: Dict, cached_history: List[Dict], message: str) -> Dict:
        """キャッシュデータからレスポンスを構築"""
        return {
            'symbol': symbol.upper(),
            'name': cached_price.get('name', symbol),
            'current_price': cached_price.get('current_price', 0),
            'previous_close': cached_price.get('previous_close', 0),
            'change': cached_price.get('change', 0),
            'change_percent': cached_price.get('change_percent', 0),
            'volume': cached_price.get('volume', 0),
            'market_cap': cached_price.get('market_cap'),
            'pe_ratio': cached_price.get('pe_ratio'),
            'dividend_yield': cached_price.get('dividend_yield'),
            '52_week_high': cached_price.get('week_52_high'),
            '52_week_low': cached_price.get('week_52_low'),
            'history': cached_history,
            'cached': True,
            'message': message
        }
    
    @staticmethod
    def build_history_response(symbol: str, cached_history: List[Dict], message: str) -> Dict:
        """履歴データからレスポンスを構築"""
        if not cached_history:
            return None
        
        latest = cached_history[0]
        previous = cached_history[1] if len(cached_history) > 1 else latest
        
        return {
            'symbol': symbol.upper(),
            'name': symbol,
            'current_price': latest.get('close', 0),
            'previous_close': previous.get('close', latest.get('close', 0)),
            'change': 0,
            'change_percent': 0,
            'volume': latest.get('volume', 0),
            'market_cap': None,
            'pe_ratio': None,
            'dividend_yield': None,
            '52_week_high': None,
            '52_week_low': None,
            'history': cached_history,
            'cached': True,
            'message': message
        }

    @staticmethod
    def fetch_stocks_data_parallel(symbols: List[str], delay: float = 0.5) -> List[Dict]:
        """複数銘柄のデータを並列で取得"""
        results = []
        
        # まずキャッシュをチェックして、有効なキャッシュがある銘柄はAPIリクエストしない
        symbols_to_fetch = []
        for symbol in symbols:
            cached_price = db.get_cached_price(symbol, CACHE_MINUTES)
            if cached_price:
                # キャッシュから結果を構築
                cached_history = db.get_cached_history(symbol)
                result = StockAPI.build_cached_response(
                    symbol, cached_price, cached_history,
                    'キャッシュされたデータを使用しています'
                )
                results.append(result)
            else:
                symbols_to_fetch.append(symbol)
        
        if not symbols_to_fetch:
            return results
            
        # 残りの銘柄を並列で取得
        # リクエスト間に遅延を入れるために、各スレッドで呼び出すラッパー関数
        def fetch_wrapper(symbol):
            try:
                # ランダムな遅延を入れる（レート制限回避のため）
                # 並列実行のため、開始タイミングを少しずらす
                if delay > 0:
                    time.sleep(delay) 
                result = get_stock_price_with_fallback(symbol, use_cache=False)
                if result is None:
                    return {
                        'symbol': symbol,
                        'name': symbol,
                        'error': 'Failed to fetch data (None returned)'
                    }
                return result
            except Exception as e:
                logger.error(f"Error fetching parallel data for {symbol}: {e}")
                return {
                    'symbol': symbol,
                    'error': str(e)
                }

        with ThreadPoolExecutor(max_workers=min(10, len(symbols_to_fetch))) as executor:
            future_to_symbol = {executor.submit(fetch_wrapper, sym): sym for sym in symbols_to_fetch}
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except Exception as e:
                    logger.error(f"Exception in parallel execution for {symbol}: {e}")
        
        return results


def get_stock_price_with_fallback(symbol: str, period: str = '1mo', use_cache: bool = True) -> Optional[Dict]:
    """株価データを取得（フォールバック機能付き）"""
    symbol = symbol.upper()
    
    # キャッシュをチェック
    cached_price = None
    if use_cache:
        cached_price = db.get_cached_price(symbol, CACHE_MINUTES)
    
    # APIからデータを取得
    try:
        hist = StockAPI.get_history(symbol, period)
        if hist is None or hist.empty:
            # データが見つからない場合、キャッシュまたは履歴データを使用
            if cached_price:
                cached_history = db.get_cached_history(symbol)
                return StockAPI.build_cached_response(
                    symbol, cached_price, cached_history,
                    'キャッシュされたデータを使用しています'
                )
            return None
        
        # 情報を取得
        info = StockAPI.get_ticker_info(symbol)
        
        # 価格変動を計算
        current_price, previous_close, change, change_percent = StockAPI.calculate_price_change(hist)
        
        # キャッシュに保存
        price_data = {
            'current_price': current_price,
            'previous_close': previous_close,
            'change': change,
            'change_percent': change_percent,
            'volume': int(hist['Volume'].iloc[-1]),
            'market_cap': info.get('market_cap') if info else None,
            'pe_ratio': info.get('pe_ratio') if info else None,
            'dividend_yield': info.get('dividend_yield') if info else None,
            '52_week_high': info.get('52_week_high') if info else None,
            '52_week_low': info.get('52_week_low') if info else None
        }
        db.save_price_cache(symbol, price_data)
        
        # 履歴データを保存
        history_data = StockAPI.format_history_data(hist)
        db.save_price_history(symbol, history_data)
        
        # レスポンスを構築
        return StockAPI.build_price_response(symbol, hist, info, cached=False)
        
    except Exception as e:
        error_msg = str(e)
        # レート制限エラーの場合、キャッシュまたは履歴データを使用
        if 'rate limit' in error_msg.lower() or 'too many requests' in error_msg.lower():
            logger.warning(f"Rate limit hit for {symbol}: {e}")
            if cached_price:
                cached_history = db.get_cached_history(symbol)
                return StockAPI.build_cached_response(
                    symbol, cached_price, cached_history,
                    'APIレート制限のため、キャッシュされたデータを使用しています'
                )
            # キャッシュがない場合、履歴データを取得
            cached_history = db.get_cached_history(symbol, HISTORY_DAYS)
            if cached_history:
                return StockAPI.build_history_response(
                    symbol, cached_history,
                    'APIレート制限のため、保存された履歴データを使用しています'
                )
        logger.error(f"Failed to get price for {symbol}: {e}")
        raise
