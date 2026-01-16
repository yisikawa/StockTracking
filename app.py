"""株価トラッキング & 分析アプリ - メインアプリケーションファイル"""
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from datetime import datetime
import os
from typing import Dict, Optional

from config import CACHE_MINUTES, IS_PRODUCTION, ALLOWED_ORIGINS
from database import db
from stock_api import StockAPI, get_stock_price_with_fallback
from stock_analyzer import StockAnalyzer
from symbol_utils import normalize_symbol, get_currency, SymbolUtils
from exceptions import StockTrackingError
from services.stock_service import StockService

app = Flask(__name__, static_folder='static', static_url_path='/static')

# SECRET_KEY設定
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# CORS設定（本番環境では特定オリジンのみ許可）
if IS_PRODUCTION:
    CORS(app, origins=ALLOWED_ORIGINS)
else:
    CORS(app)  # 開発環境は全許可

# Logging configuration
from logging_config import setup_logging
setup_logging(app)



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
    
    # サービス層に処理を委譲
    response_data, status_code = StockService.add_stock(raw_symbol, force_add)
    return jsonify(response_data), status_code


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
    # サービス層に処理を委譲
    dashboard_data = StockService.get_dashboard_data()
    return jsonify(dashboard_data)


@app.errorhandler(StockTrackingError)
def handle_stock_error(error):
    """カスタム例外のハンドラー"""
    return jsonify({'error': str(error)}), error.status_code


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
