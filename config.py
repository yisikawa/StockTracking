"""アプリケーション設定 - コンフィグファイルから読み込み"""
import json
import os
from typing import Final, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_file: str = 'config.json'):
        """コンフィグファイルを読み込む"""
        self.config_path = Path(config_file)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """コンフィグファイルを読み込む"""
        config = self._get_default_config()
        
        # JSONファイルから読み込み
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # 再帰的にマージするロジックが必要だが、簡易的にトップレベルのみマージ、または主要セクションのみマージ
                    # ここでは簡易実装として、デフォルトにファイル設定を重ねる
                    self._deep_update(config, file_config)
            except Exception as e:
                print(f"警告: コンフィグファイルの読み込みに失敗しました: {e}")
        
        # 環境変数で上書き
        self._override_from_env(config)
        
        return config

    def _deep_update(self, base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _override_from_env(self, config):
        # Server
        if os.getenv('SERVER_HOST'):
            config.setdefault('server', {})['host'] = os.getenv('SERVER_HOST')
        if os.getenv('SERVER_PORT'):
            config.setdefault('server', {})['port'] = int(os.getenv('SERVER_PORT'))
        if os.getenv('SERVER_DEBUG'):
            config.setdefault('server', {})['debug'] = os.getenv('SERVER_DEBUG').lower() == 'true'
            
        # Database
        if os.getenv('DB_NAME'):
            config.setdefault('database', {})['name'] = os.getenv('DB_NAME')
            
        # Yahoo Auth
        if os.getenv('USE_YAHOO_AUTH'):
            config.setdefault('yahoo_auth', {})['enabled'] = os.getenv('USE_YAHOO_AUTH').lower() == 'true'
        if os.getenv('YAHOO_COOKIE'):
            config.setdefault('yahoo_auth', {})['cookie'] = os.getenv('YAHOO_COOKIE')
        if os.getenv('YAHOO_USERNAME'):
            config.setdefault('yahoo_auth', {})['username'] = os.getenv('YAHOO_USERNAME')
        if os.getenv('YAHOO_PASSWORD'):
            config.setdefault('yahoo_auth', {})['password'] = os.getenv('YAHOO_PASSWORD')

    def _get_default_config(self) -> dict:
        """デフォルト設定を返す"""
        return {
            "database": {"name": "stock_tracking.db"},
            "cache": {"minutes": 5, "history_days": 30},
            "api": {"max_retries": 2, "retry_delay": 1, "dashboard_request_delay": 0.5},
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
                "price_position_high": 0.7,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9
            },
            "yahoo_auth": {"enabled": False, "cookie": "", "username": "", "password": ""},
            "server": {"host": "localhost", "port": 5000, "debug": True}
        }
    def get(self, *keys, default=None):
        """設定値を取得（ネストされたキーに対応）"""
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def save(self):
        """設定をファイルに保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"設定の保存に失敗しました: {e}")
            return False


# グローバル設定インスタンス
_config_instance = Config()

# データベース設定
DB_NAME: Final[str] = _config_instance.get('database', 'name', default='stock_tracking.db')

# キャッシュ設定
CACHE_MINUTES: Final[int] = _config_instance.get('cache', 'minutes', default=5)
HISTORY_DAYS: Final[int] = _config_instance.get('cache', 'history_days', default=30)

# API設定
MAX_RETRIES: Final[int] = _config_instance.get('api', 'max_retries', default=2)
RETRY_DELAY: Final[int] = _config_instance.get('api', 'retry_delay', default=1)
DASHBOARD_REQUEST_DELAY: Final[float] = _config_instance.get('api', 'dashboard_request_delay', default=0.5)

# 分析設定
RSI_PERIOD: Final[int] = _config_instance.get('analysis', 'rsi_period', default=14)
MA_SHORT: Final[int] = _config_instance.get('analysis', 'ma_short', default=20)
MA_LONG: Final[int] = _config_instance.get('analysis', 'ma_long', default=50)
TRADING_DAYS_PER_YEAR: Final[int] = _config_instance.get('analysis', 'trading_days_per_year', default=252)

# MACD設定
MACD_FAST: Final[int] = _config_instance.get('analysis', 'macd_fast', default=12)
MACD_SLOW: Final[int] = _config_instance.get('analysis', 'macd_slow', default=26)
MACD_SIGNAL: Final[int] = _config_instance.get('analysis', 'macd_signal', default=9)

# スコア評価の閾値
SCORE_EXCELLENT: Final[int] = _config_instance.get('analysis', 'score_excellent', default=80)
SCORE_GOOD: Final[int] = _config_instance.get('analysis', 'score_good', default=60)
SCORE_FAIR: Final[int] = _config_instance.get('analysis', 'score_fair', default=40)
SCORE_POOR: Final[int] = _config_instance.get('analysis', 'score_poor', default=20)

# ボラティリティ閾値
VOLATILITY_LOW: Final[float] = _config_instance.get('analysis', 'volatility_low', default=20.0)
VOLATILITY_HIGH: Final[float] = _config_instance.get('analysis', 'volatility_high', default=40.0)

# RSI閾値
RSI_OVERSOLD: Final[float] = _config_instance.get('analysis', 'rsi_oversold', default=30.0)
RSI_OVERBOUGHT: Final[float] = _config_instance.get('analysis', 'rsi_overbought', default=70.0)

# 価格位置閾値
PRICE_POSITION_LOW: Final[float] = _config_instance.get('analysis', 'price_position_low', default=0.3)
PRICE_POSITION_HIGH: Final[float] = _config_instance.get('analysis', 'price_position_high', default=0.7)

# Yahoo認証設定（コンフィグファイルから取得）
YAHOO_AUTH_ENABLED: Final[bool] = _config_instance.get('yahoo_auth', 'enabled', default=False)
YAHOO_COOKIE: Optional[str] = _config_instance.get('yahoo_auth', 'cookie', default='') or None
YAHOO_USERNAME: Optional[str] = _config_instance.get('yahoo_auth', 'username', default='') or None
YAHOO_PASSWORD: Optional[str] = _config_instance.get('yahoo_auth', 'password', default='') or None
USE_YAHOO_AUTH: Final[bool] = YAHOO_AUTH_ENABLED and bool(YAHOO_COOKIE or (YAHOO_USERNAME and YAHOO_PASSWORD))

# サーバー設定
SERVER_HOST: Final[str] = _config_instance.get('server', 'host', default='localhost')
SERVER_PORT: Final[int] = _config_instance.get('server', 'port', default=5000)
SERVER_DEBUG: Final[bool] = _config_instance.get('server', 'debug', default=True)

# 本番環境設定
IS_PRODUCTION: Final[bool] = os.getenv('FLASK_ENV') == 'production'
ALLOWED_ORIGINS: Final[List[str]] = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
