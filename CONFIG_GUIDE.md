# コンフィグファイル設定ガイド

## 概要

アプリケーションの設定は`config.json`ファイルで一元管理されます。環境変数の代わりに、JSON形式のコンフィグファイルを使用することで、設定の管理が容易になります。

## 設定ファイルの作成

### 1. サンプルファイルをコピー

```bash
cp config.json.example config.json
```

### 2. 設定ファイルの構造

`config.json`ファイルは以下の構造になっています：

```json
{
  "database": {
    "name": "stock_tracking.db"
  },
  "cache": {
    "minutes": 5,
    "history_days": 30
  },
  "api": {
    "max_retries": 2,
    "retry_delay": 1,
    "dashboard_request_delay": 0.5
  },
  "analysis": {
    "rsi_period": 14,
    "ma_short": 20,
    "ma_long": 50,
    "trading_days_per_year": 252,
    "score_excellent": 80,
    "score_good": 60,
    "score_fair": 40,
    "score_poor": 20,
    "volatility_low": 20.0,
    "volatility_high": 40.0,
    "rsi_oversold": 30.0,
    "rsi_overbought": 70.0,
    "price_position_low": 0.3,
    "price_position_high": 0.7
  },
  "yahoo_auth": {
    "enabled": false,
    "cookie": "",
    "username": "",
    "password": ""
  },
  "server": {
    "host": "localhost",
    "port": 5000,
    "debug": true
  }
}
```

## 設定項目の説明

### database（データベース設定）

- `name`: データベースファイル名（デフォルト: `stock_tracking.db`）

### cache（キャッシュ設定）

- `minutes`: キャッシュの有効期限（分）（デフォルト: 5）
- `history_days`: 履歴データの保存日数（デフォルト: 30）

### api（API設定）

- `max_retries`: 最大リトライ回数（デフォルト: 2）
- `retry_delay`: リトライ間隔（秒）（デフォルト: 1）
- `dashboard_request_delay`: ダッシュボードリクエスト間の待機時間（秒）（デフォルト: 0.5）

### analysis（分析設定）

- `rsi_period`: RSI計算期間（デフォルト: 14）
- `ma_short`: 短期移動平均期間（デフォルト: 20）
- `ma_long`: 長期移動平均期間（デフォルト: 50）
- `trading_days_per_year`: 年間取引日数（デフォルト: 252）
- `score_excellent`: 優秀スコアの閾値（デフォルト: 80）
- `score_good`: 良好スコアの閾値（デフォルト: 60）
- `score_fair`: 普通スコアの閾値（デフォルト: 40）
- `score_poor`: 注意スコアの閾値（デフォルト: 20）
- `volatility_low`: 低ボラティリティの閾値（デフォルト: 20.0）
- `volatility_high`: 高ボラティリティの閾値（デフォルト: 40.0）
- `rsi_oversold`: RSI売られすぎの閾値（デフォルト: 30.0）
- `rsi_overbought`: RSI買われすぎの閾値（デフォルト: 70.0）
- `price_position_low`: 価格位置の下限（デフォルト: 0.3）
- `price_position_high`: 価格位置の上限（デフォルト: 0.7）

### yahoo_auth（Yahoo認証設定）

- `enabled`: 認証を有効にするか（デフォルト: false）
- `cookie`: Yahoo FinanceのCookie文字列
- `username`: Yahooユーザー名（未使用、将来の拡張用）
- `password`: Yahooパスワード（未使用、将来の拡張用）

### server（サーバー設定）

- `host`: サーバーのホスト名（デフォルト: localhost）
- `port`: サーバーのポート番号（デフォルト: 5000）
- `debug`: デバッグモードを有効にするか（デフォルト: true）

## Yahoo認証の設定例

```json
{
  "yahoo_auth": {
    "enabled": true,
    "cookie": "A3=d=AQABBN...&b=2&c=...; A1=d=AQABBN...&b=3&c=...",
    "username": "",
    "password": ""
  }
}
```

## 設定の変更方法

1. `config.json`ファイルを編集
2. アプリケーションを再起動

設定ファイルの変更は、アプリケーション再起動後に反映されます。

## セキュリティに関する注意

- `config.json`ファイルは`.gitignore`に含まれているため、Gitにコミットされません
- Cookieなどの機密情報を含むため、ファイルの権限を適切に設定してください
- 本番環境では、`debug`を`false`に設定することを推奨します

## トラブルシューティング

### 設定ファイルが見つからない場合

- `config.json.example`を`config.json`にコピーしてください
- デフォルト設定が使用されます

### 設定が反映されない場合

- アプリケーションを再起動してください
- JSONの構文エラーがないか確認してください
- ファイルのエンコーディングがUTF-8であることを確認してください
