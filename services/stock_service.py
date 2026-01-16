"""株価サービス層 - ビジネスロジックを集約"""
from typing import Dict, List, Optional, Tuple
from database import db
from stock_api import StockAPI, get_stock_price_with_fallback
from symbol_utils import normalize_symbol
from config import MAX_RETRIES, RETRY_DELAY, DASHBOARD_REQUEST_DELAY
import time
import logging

logger = logging.getLogger(__name__)


class StockService:
    """株価関連のビジネスロジック"""
    
    @staticmethod
    def add_stock(raw_symbol: str, force_add: bool = False) -> Tuple[Dict, int]:
        """
        銘柄を追加
        
        Args:
            raw_symbol: 生の銘柄コード
            force_add: レート制限時でも強制的に追加するか
        
        Returns:
            Tuple[Dict, int]: (レスポンスデータ, HTTPステータスコード)
        """
        if not raw_symbol:
            return {'error': '銘柄コードが必要です'}, 400
        
        # シンボルを正規化（日本株対応）
        symbol = normalize_symbol(raw_symbol)
        
        # リトライループ
        for attempt in range(MAX_RETRIES):
            try:
                # 銘柄情報を取得
                info = StockAPI.get_ticker_info(symbol)
                name = info.get('name') if info else symbol
                
                # データベースに追加
                if db.add_stock(symbol, name):
                    return {
                        'message': '銘柄を追加しました',
                        'symbol': symbol,
                        'name': name,
                        'info_loaded': info is not None
                    }, 201
                else:
                    return {'error': 'この銘柄は既に追加されています'}, 400
                    
            except Exception as e:
                error_msg = str(e)
                # レート制限エラーの場合
                if 'rate limit' in error_msg.lower() or 'too many requests' in error_msg.lower():
                    if force_add or attempt >= MAX_RETRIES - 1:
                        # レート制限でも強制的に追加（シンボル名のみ）
                        if db.add_stock(symbol, symbol):
                            return {
                                'message': '銘柄を追加しました（レート制限のため、詳細情報は後で取得されます）',
                                'symbol': symbol,
                                'name': symbol,
                                'info_loaded': False,
                                'warning': 'APIレート制限のため、詳細情報は後で更新されます'
                            }, 201
                        else:
                            return {'error': 'この銘柄は既に追加されています'}, 400
                    else:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                else:
                    # その他のエラー
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        # エラーでもシンボル名で追加を試みる
                        if db.add_stock(symbol, symbol):
                            return {
                                'message': '銘柄を追加しました（詳細情報の取得に失敗しました）',
                                'symbol': symbol,
                                'name': symbol,
                                'info_loaded': False,
                                'warning': f'詳細情報の取得に失敗: {error_msg}'
                            }, 201
                        else:
                            return {'error': 'この銘柄は既に追加されています'}, 400
        
        return {'error': '銘柄の追加に失敗しました。しばらく待ってから再度お試しください。'}, 500
    
    @staticmethod
    def get_dashboard_data() -> List[Dict]:
        """
        ダッシュボードデータを取得
        
        Returns:
            List[Dict]: ダッシュボード用の銘柄データリスト（順序保持）
        """
        stocks = db.get_tracked_stocks()
        symbols = [stock['symbol'] for stock in stocks]
        
        if not symbols:
            return []
        
        # 並列処理で一括取得
        # ダッシュボード表示時は少し遅延を入れてレート制限を回避
        dashboard_data = StockAPI.fetch_stocks_data_parallel(symbols, delay=DASHBOARD_REQUEST_DELAY)
        
        # 取得結果には銘柄名が含まれていない場合があるため（エラー時など）、補完する
        stock_map = {stock['symbol']: stock['name'] for stock in stocks}
        for data in dashboard_data:
            if 'symbol' in data and data['symbol'] in stock_map:
                if 'name' not in data or data['name'] == data['symbol']:
                    data['name'] = stock_map[data['symbol']]
                    
            # エラー時のフォールバック: 履歴データがあればそれを使用
            if 'error' in data:
                symbol = data['symbol']
                cached_history = db.get_cached_history(symbol, days=1)
                if cached_history:
                    latest = cached_history[0]
                    # 辞書の内容を書き換え
                    data.clear()
                    data.update({
                        'symbol': symbol,
                        'name': stock_map.get(symbol, symbol),
                        'price': latest.get('close', 0),
                        'change': 0,
                        'change_percent': 0,
                        'cached': True,
                        'message': '履歴データを使用 (並列取得エラー)'
                    })
                else:
                    # 履歴データもない場合（新規追加直後のエラーなど）
                    # エラー情報を残しつつ、最低限の情報を設定
                    data['name'] = stock_map.get(symbol, symbol)
                    data['price'] = 0
                    data['change'] = 0
                    data['change_percent'] = 0
                    data['cached'] = False
                    data['message'] = f"データ取得エラー: {data.get('error', 'Unknown')}"
        
        # 順序を維持するために、元のリスト順に並べ替え
        ordered_data = []
        data_map = {d.get('symbol'): d for d in dashboard_data}
        
        for symbol in symbols:
            if symbol in data_map:
                entry = data_map[symbol]
                # UI表示用にキー名を調整（price -> current_priceの揺らぎ吸収など）
                if 'current_price' in entry and 'price' not in entry:
                    entry['price'] = entry['current_price']
                ordered_data.append(entry)
        
        return ordered_data
