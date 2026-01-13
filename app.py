"""株価トラッキング & 分析アプリ - メインアプリケーションファイル"""
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from datetime import datetime
import time
from typing import Dict, Optional

from config import MAX_RETRIES, RETRY_DELAY, DASHBOARD_REQUEST_DELAY, CACHE_MINUTES
from database import db
from stock_api import StockAPI, get_stock_price_with_fallback
from stock_analyzer import StockAnalyzer
from symbol_utils import normalize_symbol, get_currency, SymbolUtils

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Logging configuration
import logging
from logging.handlers import RotatingFileHandler
import os

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Configure root logger to capture logs from all modules
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    
    app.logger.info('StockTracking startup')



@app.route('/api/stocks', methods=['GET'])
def get_tracked_stocks():
    """追跡中の銘柄一覧を取得"""
    stocks = db.get_tracked_stocks()
    return jsonify(stocks)


@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """新しい銘柄を追加"""
    data = request.json
    raw_symbol = data.get('symbol', '').upper() if data else ''
    force_add = data.get('force', False) if data else False
    
    if not raw_symbol:
        return jsonify({'error': '銘柄コードが必要です'}), 400
    
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


@app.route('/api/stocks/<path:symbol>', methods=['DELETE'])
def remove_stock(symbol: str):
    """銘柄を削除"""
    symbol = symbol.upper()
    db.remove_stock(symbol)
    return jsonify({'message': '銘柄を削除しました'})


@app.route('/api/stocks/<path:symbol>', methods=['PUT'])
def update_stock_portfolio(symbol: str):
    """ポートフォリオ情報（数量・平均取得単価）を更新"""
    symbol = symbol.upper()
    data = request.json
    
    quantity = data.get('quantity')
    avg_price = data.get('avg_price')
    
    if quantity is None or avg_price is None:
        return jsonify({'error': '数量と平均取得単価が必要です'}), 400
        
    try:
        quantity = float(quantity)
        avg_price = float(avg_price)
    except ValueError:
        return jsonify({'error': '数値形式が無効です'}), 400
        
    if db.update_portfolio(symbol, quantity, avg_price):
        return jsonify({'message': 'ポートフォリオ情報を更新しました', 'symbol': symbol})
    else:
        return jsonify({'error': '銘柄が見つかりません'}), 404


@app.route('/api/stocks/<path:symbol>/price', methods=['GET'])
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


@app.route('/api/stocks/<path:symbol>/analysis', methods=['GET'])
def analyze_stock(symbol: str):
    """株価の分析評価を実行"""
    symbol = normalize_symbol(symbol)
    period = request.args.get('period', '1y')
    
    try:
        hist = StockAPI.get_history(symbol, period)
        if hist is None or hist.empty:
            return jsonify({'error': 'データが見つかりません'}), 404
        
        analysis = StockAnalyzer.analyze(hist)
        currency = get_currency(symbol)
        
        return jsonify({
            'symbol': symbol,
            'currency': currency,
            'currency_symbol': SymbolUtils.get_currency_symbol(currency),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **analysis
        })
    except Exception as e:
        return jsonify({'error': f'分析の実行に失敗しました: {str(e)}'}), 500


@app.route('/api/stocks/<path:symbol>/dividends', methods=['GET'])
def get_dividends(symbol: str):
    """配当履歴を取得"""
    symbol = normalize_symbol(symbol)
    
    try:
        result = StockAPI.get_dividends(symbol)
        if result is None:
            return jsonify({'error': '配当データの取得に失敗しました'}), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'配当データの取得に失敗しました: {str(e)}'}), 500


@app.route('/api/stocks/<path:symbol>/financials', methods=['GET'])
def get_financials(symbol: str):
    """財務情報を取得"""
    symbol = normalize_symbol(symbol)
    
    try:
        result = StockAPI.get_financials(symbol)
        if result is None:
            return jsonify({'error': '財務データの取得に失敗しました'}), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'財務データの取得に失敗しました: {str(e)}'}), 500


@app.route('/api/stocks/search', methods=['GET'])
def search_stocks():
    """銘柄検索"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': '検索クエリが必要です'}), 400
    
    try:
        # シンボルを正規化して検索
        normalized = normalize_symbol(query)
        info = StockAPI.get_ticker_info(normalized)
        
        if info:
            symbol_info = SymbolUtils.get_stock_info(query)
            return jsonify({
                'results': [{
                    'symbol': normalized,
                    'name': info.get('name', normalized),
                    'market': symbol_info.get('market'),
                    'currency': symbol_info.get('currency'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                }]
            })
        return jsonify({'results': []})
    except Exception as e:
        return jsonify({'results': [], 'error': str(e)})


@app.route('/api/symbol/normalize', methods=['GET'])
def normalize_stock_symbol():
    """銘柄コードを正規化"""
    symbol = request.args.get('symbol', '')
    if not symbol:
        return jsonify({'error': 'シンボルが必要です'}), 400
    
    info = SymbolUtils.get_stock_info(symbol)
    return jsonify(info)


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """ダッシュボード用の全銘柄データを取得 - キャッシュ優先"""
    stocks = db.get_tracked_stocks()
    dashboard_data = []
    
    symbols = [stock['symbol'] for stock in stocks]
    
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
    
    return jsonify(dashboard_data)


@app.route('/')
def index():
    """メインページを返す"""
    return render_template('index.html')


if __name__ == '__main__':
    from config import USE_YAHOO_AUTH, SERVER_HOST, SERVER_PORT, SERVER_DEBUG
    from yahoo_auth import yahoo_auth
    
    print('データベースを初期化しました')
    db.init_app()
    
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
