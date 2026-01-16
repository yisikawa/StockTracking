# リファクタリング完了報告

## 実施したリファクタリング

### 1. モジュール分割

#### `config.py` - 設定管理
- すべての定数と設定値を一元管理
- マジックナンバーを定数化
- 設定の変更が容易に

#### `database.py` - データベース操作
- データベース操作をクラス化
- 接続管理の統一
- 型ヒントの追加

#### `stock_api.py` - 株価API操作
- API呼び出しロジックの分離
- フォールバック機能の実装
- レスポンス構築の統一

#### `stock_analyzer.py` - 分析機能
- 分析ロジックの分離
- 各指標計算の関数化
- スコア計算の明確化

### 2. コードの改善

#### 重複コードの削減
- キャッシュレスポンス構築の統一（3箇所 → 1関数）
- エラーハンドリングの統一
- データ整形ロジックの共通化

#### 関数の分割
- 大きな関数を小さな関数に分割
- 単一責任の原則に従った設計
- テストしやすい構造

#### 型ヒントの追加
- すべての関数に型ヒントを追加
- コードの可読性向上
- IDEの補完機能の改善

### 3. 構造の改善

#### アーキテクチャ
```
app.py (メインアプリケーション)
├── config.py (設定)
├── database.py (データベース操作)
├── stock_api.py (API操作)
└── stock_analyzer.py (分析機能)
```

#### 責任の分離
- **app.py**: ルーティングとHTTPリクエスト処理
- **database.py**: データ永続化
- **stock_api.py**: 外部APIとの通信
- **stock_analyzer.py**: ビジネスロジック（分析）

### 4. 改善された点

#### 可読性
- コードがより読みやすく、理解しやすくなった
- 関数名が明確で、目的が分かりやすい
- コメントとdocstringの追加

#### 保守性
- モジュール化により、変更の影響範囲が明確
- 設定の変更が容易
- テストの追加が容易

#### 拡張性
- 新しい機能の追加が容易
- 新しい分析指標の追加が簡単
- APIの変更に対応しやすい

### 5. パフォーマンス

- 変更なし（機能は同じ）
- コードの実行速度は同等
- メモリ使用量も同等

### 6. テスト容易性

- 各モジュールが独立してテスト可能
- モックの作成が容易
- 単体テストの追加が簡単

## ファイル構成

```
StockTracking/
├── app.py              # メインアプリケーション（リファクタリング済み）
├── config.py           # 設定管理（新規）
├── database.py         # データベース操作（新規）
├── stock_api.py        # 株価API操作（新規）
├── stock_analyzer.py   # 分析機能（新規）
├── static/
│   ├── app.js
│   └── style.css
├── index.html
├── requirements.txt
└── README.md
```

## 互換性

- 既存のAPIエンドポイントはすべて維持
- フロントエンドコードの変更不要
- データベーススキーマの変更なし

## 次のステップ

1. 単体テストの追加
2. ロギング機能の追加
3. エラーハンドリングのさらなる改善
4. APIドキュメントの生成

---

# リファクタリング計画（2026-01-15）

## 概要

コードレビューにより、以下の改善点が特定されました。優先度順に対応を計画します。

## 1. 緊急修正（バグ）

### 1.1 ダッシュボード順序バグ [優先度: 高]

**ファイル**: `app.py` L335

**問題**: `ordered_data` を計算しているが、`dashboard_data` を返している

```python
# 現在（バグ）
return jsonify(dashboard_data)

# 修正
return jsonify(ordered_data)
```

**影響**: ダッシュボードの銘柄表示順序が正しくない

---

### 1.2 暗黙的な event 参照 [優先度: 高]

**ファイル**: `static/app.js` L720

**問題**: `changePeriod` 関数が `event` を引数で受け取らず、グローバル参照している

```javascript
// 現在（問題あり）
function changePeriod(period) {
    currentPeriod = period;
    document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');  // ← 暗黙的なevent参照
    if (currentStock) showStockDetail(currentStock);
}

// 修正: eventを明示的に引数として渡す
function changePeriod(period, event) {
    currentPeriod = period;
    document.querySelectorAll('.period-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    if (currentStock) showStockDetail(currentStock);
}
```

**HTML側の修正も必要**:
```javascript
// L387: ボタン生成部分
onclick="changePeriod('${period}', event)"
```

**影響**: 一部のブラウザ（特にStrict Mode）で動作しない可能性

---

## 2. セキュリティ改善

### 2.1 CORS設定の厳格化 [優先度: 中]

**ファイル**: `app.py` L15

**問題**: 全オリジンからのアクセスを許可している

```python
# 現在
CORS(app)

# 改善: 本番環境では特定オリジンのみ許可
from config import ALLOWED_ORIGINS, IS_PRODUCTION

if IS_PRODUCTION:
    CORS(app, origins=ALLOWED_ORIGINS)
else:
    CORS(app)  # 開発環境は全許可
```

**config.py に追加**:
```python
# 本番環境設定
IS_PRODUCTION: Final[bool] = os.getenv('FLASK_ENV') == 'production'
ALLOWED_ORIGINS: Final[List[str]] = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
```

---

### 2.2 SECRET_KEY の設定 [優先度: 中]

**ファイル**: `app.py`

**追加内容**:
```python
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
```

---

## 3. コード構造の改善

### 3.1 ロギング設定の分離 [優先度: 低]

**新規ファイル**: `logging_config.py`

```python
"""ロギング設定モジュール"""
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """アプリケーションのロギングを設定"""
    if app.debug:
        return
    
    try:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        app.logger.info('Logging configured successfully')
        
    except PermissionError:
        print("警告: ログファイルへの書き込み権限がありません")
    except Exception as e:
        print(f"警告: ログ設定中にエラー: {e}")
```

**app.py の修正**:
```python
from logging_config import setup_logging
setup_logging(app)
```

---

### 3.2 サービス層の導入 [優先度: 低]

**新規ディレクトリ/ファイル**: `services/stock_service.py`

```python
"""株価サービス層 - ビジネスロジックを集約"""
from typing import Dict, List, Optional, Tuple
from database import db
from stock_api import StockAPI, get_stock_price_with_fallback
from symbol_utils import normalize_symbol
from config import MAX_RETRIES, RETRY_DELAY, DASHBOARD_REQUEST_DELAY
import time

class StockService:
    """株価関連のビジネスロジック"""
    
    @staticmethod
    def add_stock(raw_symbol: str, force_add: bool = False) -> Tuple[Dict, int]:
        """
        銘柄を追加
        
        Returns:
            Tuple[Dict, int]: (レスポンスデータ, HTTPステータスコード)
        """
        symbol = normalize_symbol(raw_symbol)
        
        for attempt in range(MAX_RETRIES):
            try:
                info = StockAPI.get_ticker_info(symbol)
                name = info.get('name') if info else symbol
                
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
                # エラーハンドリングロジック...
                pass
        
        return {'error': '銘柄の追加に失敗しました'}, 500
    
    @staticmethod
    def get_dashboard_data() -> List[Dict]:
        """ダッシュボードデータを取得"""
        stocks = db.get_tracked_stocks()
        symbols = [stock['symbol'] for stock in stocks]
        
        dashboard_data = StockAPI.fetch_stocks_data_parallel(
            symbols, 
            delay=DASHBOARD_REQUEST_DELAY
        )
        
        # データ補完とエラーハンドリング...
        
        return dashboard_data
```

---

## 4. データベース層の改善

### 4.1 ハードコードされた日数の修正 [優先度: 中]

**ファイル**: `database.py` L114

```python
# 現在
def save_price_history(self, symbol: str, price_data: List[Dict], days: int = 30):

# 修正: 設定値を使用
def save_price_history(self, symbol: str, price_data: List[Dict], days: int = HISTORY_DAYS):
```

---

### 4.2 履歴取得の日付ベース化 [優先度: 中]

**ファイル**: `database.py` L102-112

```python
# 現在: limit(days) はレコード数制限
def get_cached_history(self, symbol: str, days: int = HISTORY_DAYS) -> List[Dict]:
    prices = db_session.query(StockPrice)\
        .filter_by(symbol=symbol.upper())\
        .order_by(StockPrice.date.desc())\
        .limit(days).all()
    return [price.to_dict() for price in prices]

# 改善: 日付範囲でフィルタ
from datetime import datetime, timedelta

def get_cached_history(self, symbol: str, days: int = HISTORY_DAYS) -> List[Dict]:
    """データベースから履歴データを取得（日付ベース）"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        prices = db_session.query(StockPrice)\
            .filter_by(symbol=symbol.upper())\
            .filter(StockPrice.date >= cutoff_date)\
            .order_by(StockPrice.date.desc())\
            .all()
        return [price.to_dict() for price in prices]
    except Exception as e:
        logger.error(f"Error getting cached history: {e}")
        return []
```

---

## 5. API層の改善

### 5.1 レスポンス構築の共通化 [優先度: 低]

**ファイル**: `stock_api.py`

```python
class ResponseBuilder:
    """APIレスポンス構築ヘルパー"""
    
    @staticmethod
    def build_base_response(symbol: str) -> Dict:
        """基本レスポンスを構築"""
        normalized = normalize_symbol(symbol)
        currency = get_currency(normalized)
        return {
            'symbol': normalized,
            'currency': currency,
            'currency_symbol': SymbolUtils.get_currency_symbol(currency),
            'market': SymbolUtils.get_market_name(normalized),
        }
    
    @staticmethod
    def add_price_info(response: Dict, hist: pd.DataFrame) -> Dict:
        """価格情報を追加"""
        if hist is None or hist.empty:
            return response
        
        current_price, previous_close, change, change_percent = \
            StockAPI.calculate_price_change(hist)
        
        response.update({
            'current_price': current_price,
            'previous_close': previous_close,
            'change': change,
            'change_percent': change_percent,
            'volume': int(hist['Volume'].iloc[-1]),
        })
        return response
```

---

### 5.2 レート制限対策の強化 [優先度: 中]

**ファイル**: `stock_api.py` L377

```python
# 現在: 固定遅延
if delay > 0:
    time.sleep(delay)

# 改善: ジッターを追加（レート制限回避に効果的）
import random

if delay > 0:
    jitter = random.uniform(0, delay * 0.5)  # 0〜50%のランダム遅延を追加
    time.sleep(delay + jitter)
```

---

## 6. フロントエンド改善

### 6.1 アクティブ状態検出の改善 [優先度: 低]

**ファイル**: `static/app.js` L340

```javascript
// 現在: 脆弱な検出方法
if (item.onclick && item.onclick.toString().includes(symbol)) {
    item.classList.add('active');
}

// 改善: data属性を使用
```

**HTML側の修正** (renderStockList関数内):
```javascript
<div class="stock-item ${isActive}" data-symbol="${stock.symbol}" onclick="selectStock('${stock.symbol}')">
```

**JS側の修正** (selectStock関数内):
```javascript
document.querySelectorAll('.stock-item').forEach(item => {
    item.classList.toggle('active', item.dataset.symbol === symbol);
});
```

---

### 6.2 グローバル状態の整理 [優先度: 低]

**ファイル**: `static/app.js` L1-9

```javascript
// 現在: バラバラのグローバル変数
let currentStock = null;
let currentPeriod = '1mo';
let currentTab = 'chart';
let chart = null;
let autoRefreshInterval = null;
let stocksData = [];

// 改善: 状態オブジェクトにまとめる
const AppState = {
    currentStock: null,
    currentPeriod: '1mo',
    currentTab: 'chart',
    chart: null,
    autoRefreshInterval: null,
    stocksData: [],
    
    // 状態更新メソッド
    setCurrentStock(symbol) {
        this.currentStock = symbol;
    },
    
    setPeriod(period) {
        this.currentPeriod = period;
    }
};
```

---

## 7. エラーハンドリングの統一

### 7.1 カスタム例外クラス [優先度: 低]

**新規ファイル**: `exceptions.py`

```python
"""カスタム例外モジュール"""

class StockTrackingError(Exception):
    """基底例外クラス"""
    status_code = 500
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code

class RateLimitError(StockTrackingError):
    """レート制限エラー"""
    status_code = 429
    
    def __init__(self, message: str = "APIレート制限に達しました"):
        super().__init__(message)

class StockNotFoundError(StockTrackingError):
    """銘柄が見つからない"""
    status_code = 404
    
    def __init__(self, symbol: str):
        super().__init__(f"銘柄 '{symbol}' が見つかりません")

class DataFetchError(StockTrackingError):
    """データ取得失敗"""
    status_code = 500
    
    def __init__(self, message: str = "データの取得に失敗しました"):
        super().__init__(message)
```

**app.py に追加**:
```python
from exceptions import StockTrackingError

@app.errorhandler(StockTrackingError)
def handle_stock_error(error):
    return jsonify({'error': str(error)}), error.status_code
```

---

## 8. 推奨ファイル構成（将来）

```
StockTracking/
├── app.py                    # エントリーポイント（軽量化）
├── config.py                 # 設定
├── exceptions.py             # カスタム例外（新規）
├── logging_config.py         # ロギング設定（新規）
├── services/                 # サービス層（新規）
│   ├── __init__.py
│   └── stock_service.py
├── api/                      # APIルート分離（将来）
│   ├── __init__.py
│   ├── stocks.py
│   └── dashboard.py
├── models/
│   ├── __init__.py
│   ├── database.py
│   └── stock.py
├── database.py               # DB操作
├── stock_api.py              # 外部API
├── stock_analyzer.py         # 分析
├── symbol_utils.py           # ユーティリティ
├── yahoo_auth.py             # 認証
├── static/
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_stock_api.py
│   └── test_stock_analyzer.py
└── logs/
    └── app.log
```

---

## 実装優先度まとめ

| 優先度 | 項目 | 影響 | 工数 |
|--------|------|------|------|
| **高** | 1.1 ダッシュボードバグ | 機能不全 | 小 |
| **高** | 1.2 event参照 | 互換性問題 | 小 |
| **中** | 2.1 CORS設定 | セキュリティ | 小 |
| **中** | 2.2 SECRET_KEY | セキュリティ | 小 |
| **中** | 4.1 DB日数修正 | データ整合性 | 小 |
| **中** | 4.2 日付ベース履歴 | データ整合性 | 中 |
| **中** | 5.2 レート制限対策 | 安定性 | 小 |
| **低** | 3.1 ロギング分離 | 保守性 | 中 |
| **低** | 3.2 サービス層 | 保守性 | 大 |
| **低** | 5.1 レスポンス共通化 | 保守性 | 中 |
| **低** | 6.1 アクティブ検出 | 堅牢性 | 小 |
| **低** | 6.2 状態整理 | 保守性 | 中 |
| **低** | 7.1 例外クラス | 保守性 | 中 |

---

## 実施記録

| 日付 | 項目 | 担当 | 備考 |
|------|------|------|------|
| 2026-01-15 | 1.1 ダッシュボードバグ修正 | - | app.py L335: ordered_dataを返すように修正 |
| 2026-01-15 | 1.2 event参照修正 | - | app.js: changePeriod関数にevent引数を追加 |
| 2026-01-15 | 2.1 CORS設定 | - | 本番環境では特定オリジンのみ許可するように変更 |
| 2026-01-15 | 2.2 SECRET_KEY設定 | - | app.pyにSECRET_KEY設定を追加 |
| 2026-01-15 | 4.1 DB日数修正 | - | database.py: days=30をHISTORY_DAYSに変更 |
| 2026-01-15 | 4.2 日付ベース履歴 | - | get_cached_historyを日付範囲でフィルタするように変更 |
| 2026-01-15 | 5.2 レート制限対策 | - | stock_api.py: ジッターを追加してレート制限回避を強化 |
| 2026-01-16 | 3.1 ロギング分離 | - | logging_config.pyを新規作成、app.pyから分離 |
| 2026-01-16 | 6.1 アクティブ検出改善 | - | app.js: data属性を使用した堅牢な検出方法に変更 |
| 2026-01-16 | 7.1 例外クラス | - | exceptions.pyを新規作成、カスタム例外クラスを追加 |
| 2026-01-16 | 6.2 状態整理 | - | app.js: AppStateオブジェクトを追加（既存コードとの互換性維持） |
| 2026-01-16 | 5.1 レスポンス共通化 | - | stock_api.py: ResponseBuilderクラスを追加 |
| 2026-01-16 | 3.2 サービス層導入 | - | services/stock_service.pyを新規作成、app.pyのビジネスロジックを移行 |
| 2026-01-16 | Phase 1: チャート設定定数化 | - | CHART_CONFIGオブジェクトを追加、ハードコード値を定数化 |
| 2026-01-16 | Phase 2: AppState統合 | - | チャート関連状態をAppStateに統合、同期ヘルパー関数を追加 |
| 2026-01-16 | Phase 3: データ変換ユーティリティ | - | DataTransformerオブジェクトを追加、OHLC/Volume/MA変換を分離 |
| 2026-01-16 | Phase 4: ChartManager導入 | - | drawChart関数をChartManagerクラスに分割、責務を明確化 |
| 2026-01-16 | Phase 5: テンプレート・イベント整理 | - | Templatesオブジェクトを追加、イベント委譲パターンを導入 |

---

## 追加リファクタリング提案（2026-01-16）

### 1. チャート描画の責務分離 [優先度: 高]
- `drawChart`の責務が多いため、`createChart`/`renderCandles`/`renderVolume`/`renderMAs`に分割
- `static/app.js`内に`ChartRenderer`相当のモジュールを作成し可読性を向上

### 2. UI状態の一元管理 [優先度: 高]
- `currentPeriod`/`selectedMAPeriods`/`currentTab`を`AppState`に統合
- `window.currentPriceData`を`AppState.currentPriceData`へ移動しグローバル依存を削減

### 3. 移動平均設定の定数化 [優先度: 中]
- 5日刻みの期間リストや「最大2本」の制限を定数化
- UI生成とルールを分離（例: `MA_CONFIG = { allowed, max }`）

### 4. シリーズ管理の統一 [優先度: 中]
- MA以外（ローソク足/出来高）も含め、シリーズ破棄の統一ロジックを導入
- 再描画時のシリーズ参照切れを防止

### 5. データ変換ユーティリティ化 [優先度: 中]
- `history`からOHLC/出来高への変換処理をユーティリティとして分離
- 将来のデータ形式変更に強い構成にする

### 6. UIテンプレート分割 [優先度: 低]
- `renderChartTab`のHTML生成を関数分割（価格情報/MA選択/チャート）
- DOM生成とイベントバインドを分離して保守性を向上

### 7. 設定の外部化 [優先度: 低]
- 初期値（期間: 3mo、MA: 5/15）を設定ファイルに切り出し
- フロント設定の変更を容易にする

---

## 詳細リファクタリング計画（2026-01-16 チャート機能）

### 概要

ローソク足チャート・移動平均線・出来高表示の実装に伴い、フロントエンドコードの改善が必要。
以下に具体的な実装案を記載する。

---

### 1. AppStateとグローバル変数の二重管理解消 [優先度: 高]

**現状の問題:**
- `AppState`オブジェクトと`let`グローバル変数が並存
- `selectedMAPeriods`/`maSeries`/`lwChart`が`AppState`に含まれていない
- 状態更新が統一されていない

**提案コード:**
```javascript
const AppState = {
    // 既存
    currentStock: null,
    currentPeriod: '3mo',
    currentTab: 'chart',
    chart: null,
    autoRefreshInterval: null,
    stocksData: [],
    
    // 追加
    selectedMAPeriods: [5, 15],
    maSeries: [],
    lwChart: null,
    currentPriceData: null,
    currentAnalysisData: null,
    
    // 状態更新メソッド
    setCurrentStock(symbol) { this.currentStock = symbol; },
    setPeriod(period) { this.currentPeriod = period; },
    setTab(tab) { this.currentTab = tab; },
    setChart(chartInstance) { this.chart = chartInstance; },
    setLwChart(chartInstance) { this.lwChart = chartInstance; },
    setMASeries(series) { this.maSeries = series; },
    setSelectedMAPeriods(periods) { this.selectedMAPeriods = periods; },
    setPriceData(data) { this.currentPriceData = data; },
    setAnalysisData(data) { this.currentAnalysisData = data; }
};
```

**影響ファイル:** `static/app.js`
**工数:** 中

---

### 2. チャート設定の定数化 [優先度: 高]

**現状の問題:**
- MA期間リスト`[5, 10, 15, ...]`がハードコード（L538）
- 最大選択数`2`がマジックナンバー（L868）
- チャート色設定が`drawChart`内に散在

**提案コード:**
```javascript
const CHART_CONFIG = {
    MA: {
        periods: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
        maxSelection: 2,
        defaultSelection: [5, 15],
        colors: [
            '#fbbf24',  // 黄色
            '#8b5cf6',  // 紫色
            '#3b82f6',  // 青色
            '#10b981',  // 緑色
            '#f59e0b',  // オレンジ
            '#ef4444',  // 赤色
            '#06b6d4',  // シアン
            '#a855f7',  // 紫
            '#ec4899',  // ピンク
            '#14b8a6'   // ティール
        ]
    },
    CANDLE: {
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444'
    },
    VOLUME: {
        upColor: 'rgba(34, 197, 94, 0.5)',
        downColor: 'rgba(239, 68, 68, 0.5)'
    },
    PERIOD: {
        default: '3mo',
        options: ['1mo', '3mo', '6mo', '1y', '2y'],
        labels: { '1mo': '1M', '3mo': '3M', '6mo': '6M', '1y': '1Y', '2y': '2Y' }
    }
};
```

**影響ファイル:** `static/app.js`
**工数:** 小

---

### 3. drawChart関数の分割 [優先度: 中]

**現状の問題:**
- 1関数で「チャート生成」「ローソク足」「出来高」「移動平均線」を処理
- 約120行の巨大関数（L726-850）
- テストが困難

**提案コード:**
```javascript
const ChartManager = {
    chart: null,
    series: {
        candle: null,
        volume: null,
        ma: []
    },

    // チャートインスタンス生成
    create(element) {
        this.chart = LightweightCharts.createChart(element, {
            layout: { background: { color: 'transparent' }, textColor: '#64748b' },
            grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
            rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } },
            leftPriceScale: { visible: true, borderVisible: false, scaleMargins: { top: 0.8, bottom: 0 } },
            timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false }
        });
        return this.chart;
    },

    // チャート破棄
    destroy() {
        this.series.ma = [];
        if (this.chart) {
            try { this.chart.remove(); } catch (e) { console.warn('チャート削除失敗:', e); }
            this.chart = null;
        }
    },

    // ローソク足描画
    renderCandles(history) {
        this.series.candle = this.chart.addCandlestickSeries(CHART_CONFIG.CANDLE);
        this.series.candle.setData(DataTransformer.toOHLC(history));
    },

    // 出来高描画
    renderVolume(history) {
        this.series.volume = this.chart.addHistogramSeries({
            priceFormat: { type: 'volume', precision: 0, minMove: 1 },
            priceScaleId: 'left',
            scaleMargins: { top: 0.8, bottom: 0 }
        });
        this.series.volume.setData(DataTransformer.toVolume(history));
    },

    // 移動平均線描画
    renderMA(history, periods) {
        periods.forEach((period, index) => {
            const maData = DataTransformer.toMA(history, period);
            if (maData.length > 0) {
                const maSeries = this.chart.addLineSeries({
                    color: CHART_CONFIG.MA.colors[index % CHART_CONFIG.MA.colors.length],
                    lineWidth: 2,
                    title: `MA${period}`,
                    priceLineVisible: false,
                    lastValueVisible: true
                });
                maSeries.setData(maData);
                this.series.ma.push(maSeries);
            }
        });
    },

    // メイン描画
    draw(element, history, periods) {
        this.destroy();
        this.create(element);
        this.renderCandles(history);
        this.renderVolume(history);
        this.renderMA(history, periods);
        this.chart.timeScale().fitContent();
        return this.chart;
    }
};
```

**影響ファイル:** `static/app.js`
**工数:** 大

---

### 4. データ変換ユーティリティの抽出 [優先度: 中]

**現状の問題:**
- `history.map(d => ({...}))`が複数箇所に存在
- 変換ロジックが分散

**提案コード:**
```javascript
const DataTransformer = {
    // OHLC形式に変換
    toOHLC(history) {
        return history.map(d => ({
            time: d.date,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close
        }));
    },
    
    // 出来高形式に変換
    toVolume(history) {
        return history.map(d => ({
            time: d.date,
            value: d.volume,
            color: d.close >= d.open ? CHART_CONFIG.VOLUME.upColor : CHART_CONFIG.VOLUME.downColor
        }));
    },
    
    // 移動平均形式に変換
    toMA(history, period) {
        const maData = [];
        const closes = history.map(d => d.close);
        
        for (let i = 0; i < history.length; i++) {
            if (i >= period - 1) {
                const sum = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
                maData.push({ time: history[i].date, value: sum / period });
            }
        }
        return maData;
    }
};
```

**影響ファイル:** `static/app.js`
**工数:** 中

---

### 5. UIテンプレート分割 [優先度: 低]

**現状の問題:**
- `renderChartTab`のHTMLテンプレートが約35行
- 価格情報/MA選択/チャートコンテナが混在

**提案コード:**
```javascript
const Templates = {
    priceInfo(priceData, currencySymbol, currency) {
        return `
            <div class="price-info">
                <div class="info-box"><h4>現在価格</h4><div class="value">${formatPrice(priceData.current_price, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>前日終値</h4><div class="value">${formatPrice(priceData.previous_close, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>出来高</h4><div class="value">${formatNumber(priceData.volume)}</div></div>
                <div class="info-box"><h4>時価総額</h4><div class="value">${formatLargeNumber(priceData.market_cap, currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>52週高値</h4><div class="value">${formatPrice(priceData['52_week_high'], currencySymbol, currency)}</div></div>
                <div class="info-box"><h4>52週安値</h4><div class="value">${formatPrice(priceData['52_week_low'], currencySymbol, currency)}</div></div>
            </div>
        `;
    },
    
    maSelector(periods, selected) {
        const checkboxes = periods.map(period => `
            <label class="ma-checkbox-label">
                <input type="checkbox" class="ma-period-checkbox" value="${period}" 
                       ${selected.includes(period) ? 'checked' : ''} onchange="toggleMAPeriod(${period})">
                <span>MA${period}</span>
            </label>
        `).join('');
        
        return `
            <div class="ma-selector">
                <div class="ma-selector-label">移動平均線:</div>
                <div class="ma-checkbox-group">${checkboxes}</div>
            </div>
        `;
    },
    
    chartContainer() {
        return '<div class="chart-container"><div id="candlestickChart" style="height: 400px;"></div></div>';
    }
};
```

**影響ファイル:** `static/app.js`
**工数:** 中

---

### 6. イベントハンドラの整理 [優先度: 低]

**現状の問題:**
- `onclick="toggleMAPeriod(${period})"`がインラインで定義
- イベント登録が分散

**提案:**
- イベント委譲パターンの導入
- `data-*`属性を使用した統一的なイベント処理

```javascript
// イベント委譲による統一処理
document.addEventListener('change', (e) => {
    if (e.target.classList.contains('ma-period-checkbox')) {
        const period = parseInt(e.target.value);
        toggleMAPeriod(period);
    }
});
```

**影響ファイル:** `static/app.js`
**工数:** 中

---

### 実装優先度まとめ

| 優先度 | 項目 | 影響 | 工数 | 依存関係 |
|--------|------|------|------|----------|
| **高** | 1. AppState統合 | 状態管理の一貫性 | 中 | なし |
| **高** | 2. 定数化 | 保守性・可読性 | 小 | なし |
| **中** | 3. drawChart分割 | 可読性・テスト性 | 大 | 1, 2 |
| **中** | 4. データ変換抽出 | 再利用性 | 中 | 2 |
| **低** | 5. テンプレート分割 | 保守性 | 中 | 2 |
| **低** | 6. イベント整理 | 保守性 | 中 | なし |

---

### 推奨実装順序

1. **Phase 1**: 定数化（CHART_CONFIG）→ 影響範囲が小さく、他の変更の基盤となる
2. **Phase 2**: AppState統合 → グローバル状態を整理
3. **Phase 3**: データ変換ユーティリティ → 再利用可能なコードを分離
4. **Phase 4**: drawChart分割 → ChartManagerへの移行
5. **Phase 5**: テンプレート・イベント整理 → 保守性向上
