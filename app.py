"""株価トラッキング & 分析アプリ - メインアプリケーションファイル"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import time
from typing import Dict, Optional

from config import MAX_RETRIES, RETRY_DELAY, DASHBOARD_REQUEST_DELAY, CACHE_MINUTES
from database import db
from stock_api import StockAPI, get_stock_price_with_fallback
from stock_analyzer import StockAnalyzer

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)


@app.route('/api/stocks', methods=['GET'])
def get_tracked_stocks():
    """追跡中の銘柄一覧を取得"""
    stocks = db.get_tracked_stocks()
    return jsonify(stocks)


@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """新しい銘柄を追加"""
    data = request.json
    symbol = data.get('symbol', '').upper() if data else ''
    force_add = data.get('force', False) if data else False
    
    if not symbol:
        return jsonify({'error': '銘柄コードが必要です'}), 400
    
    # リトライループ
    for attempt in range(MAX_RETRIES):
        try:
            # 銘柄情報を取得
            info = StockAPI.get_ticker_info(symbol)
            name = info.get('name') if info else symbol
            
            # データベースに追加
            if db.add_stock(symbol, name):
                return jsonify({
                    'message': '銘柄を追加しました',
                    'symbol': symbol,
                    'name': name,
                    'info_loaded': info is not None
                }), 201
            else:
                return jsonify({'error': 'この銘柄は既に追加されています'}), 400
                
        except Exception as e:
            error_msg = str(e)
            # レート制限エラーの場合
            if 'rate limit' in error_msg.lower() or 'too many requests' in error_msg.lower():
                if force_add or attempt >= MAX_RETRIES - 1:
                    # レート制限でも強制的に追加（シンボル名のみ）
                    if db.add_stock(symbol, symbol):
                        return jsonify({
                            'message': '銘柄を追加しました（レート制限のため、詳細情報は後で取得されます）',
                            'symbol': symbol,
                            'name': symbol,
                            'info_loaded': False,
                            'warning': 'APIレート制限のため、詳細情報は後で更新されます'
                        }), 201
                    else:
                        return jsonify({'error': 'この銘柄は既に追加されています'}), 400
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
                        return jsonify({
                            'message': '銘柄を追加しました（詳細情報の取得に失敗しました）',
                            'symbol': symbol,
                            'name': symbol,
                            'info_loaded': False,
                            'warning': f'詳細情報の取得に失敗: {error_msg}'
                        }), 201
                    else:
                        return jsonify({'error': 'この銘柄は既に追加されています'}), 400
    
    return jsonify({'error': '銘柄の追加に失敗しました。しばらく待ってから再度お試しください。'}), 500


@app.route('/api/stocks/<symbol>', methods=['DELETE'])
def remove_stock(symbol: str):
    """銘柄を削除"""
    symbol = symbol.upper()
    db.remove_stock(symbol)
    return jsonify({'message': '銘柄を削除しました'})


@app.route('/api/stocks/<symbol>/price', methods=['GET'])
def get_stock_price(symbol: str):
    """株価データを取得（最新と履歴）- キャッシュ機能付き"""
    symbol = symbol.upper()
    period = request.args.get('period', '1mo')
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'
    
    try:
        response = get_stock_price_with_fallback(symbol, period, use_cache)
        if response:
            return jsonify(response)
        else:
            return jsonify({'error': 'データが見つかりません'}), 404
    except Exception as e:
        error_msg = str(e)
        # レート制限エラーの場合、履歴データを試す
        if 'rate limit' in error_msg.lower() or 'too many requests' in error_msg.lower():
            cached_history = db.get_cached_history(symbol)
            if cached_history:
                response = StockAPI.build_history_response(
                    symbol, cached_history,
                    'APIレート制限のため、保存された履歴データを使用しています'
                )
                if response:
                    return jsonify(response)
        return jsonify({'error': f'データの取得に失敗しました: {error_msg}'}), 500


@app.route('/api/stocks/<symbol>/analysis', methods=['GET'])
def analyze_stock(symbol: str):
    """株価の分析評価を実行"""
    symbol = symbol.upper()
    period = request.args.get('period', '1y')
    
    try:
        hist = StockAPI.get_history(symbol, period)
        if hist is None or hist.empty:
            return jsonify({'error': 'データが見つかりません'}), 404
        
        analysis = StockAnalyzer.analyze(hist)
        
        return jsonify({
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **analysis
        })
    except Exception as e:
        return jsonify({'error': f'分析の実行に失敗しました: {str(e)}'}), 500


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """ダッシュボード用の全銘柄データを取得 - キャッシュ優先"""
    stocks = db.get_tracked_stocks()
    dashboard_data = []
    
    for stock in stocks:
        symbol = stock['symbol']
        
        # まずキャッシュをチェック
        cached_price = db.get_cached_price(symbol, CACHE_MINUTES)
        
        if cached_price:
            # キャッシュから取得
            dashboard_data.append({
                'symbol': symbol,
                'name': stock['name'],
                'price': cached_price.get('current_price', 0),
                'change': cached_price.get('change', 0),
                'change_percent': cached_price.get('change_percent', 0),
                'cached': True
            })
        else:
            # APIから取得を試みる
            try:
                hist = StockAPI.get_history(symbol, '5d')
                if hist is not None and not hist.empty:
                    current_price, previous_close, change, change_percent = StockAPI.calculate_price_change(hist)
                    
                    # キャッシュに保存
                    price_data = {
                        'current_price': current_price,
                        'previous_close': previous_close,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': int(hist['Volume'].iloc[-1]) if len(hist) > 0 else 0
                    }
                    db.save_price_cache(symbol, price_data)
                    
                    dashboard_data.append({
                        'symbol': symbol,
                        'name': stock['name'],
                        'price': current_price,
                        'change': change,
                        'change_percent': change_percent,
                        'cached': False
                    })
                
                # レート制限を避けるため、リクエスト間に少し待機
                time.sleep(DASHBOARD_REQUEST_DELAY)
            except Exception:
                # エラーが発生しても、データベースから履歴データがあれば使用
                cached_history = db.get_cached_history(symbol, days=1)
                if cached_history:
                    latest = cached_history[0]
                    dashboard_data.append({
                        'symbol': symbol,
                        'name': stock['name'],
                        'price': latest.get('close', 0),
                        'change': 0,
                        'change_percent': 0,
                        'cached': True,
                        'message': '履歴データを使用'
                    })
    
    return jsonify(dashboard_data)


@app.route('/')
def index():
    """メインページを返す"""
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    from config import USE_YAHOO_AUTH, SERVER_HOST, SERVER_PORT, SERVER_DEBUG
    from yahoo_auth import yahoo_auth
    
    print('データベースを初期化しました')
    
    # Yahoo認証状態を表示
    if USE_YAHOO_AUTH:
        if yahoo_auth.is_authenticated():
            print('Yahoo認証: 有効')
        else:
            print('Yahoo認証: 無効（認証情報が設定されていません）')
    else:
        print('Yahoo認証: 無効（匿名アクセス）')
    
    print(f'サーバーを起動しています... http://{SERVER_HOST}:{SERVER_PORT}')
    app.run(debug=SERVER_DEBUG, host=SERVER_HOST, port=SERVER_PORT)
