"""Yahoo認証モジュール"""
import requests
import os
from typing import Optional, Dict
from config import USE_YAHOO_AUTH, YAHOO_COOKIE


class YahooAuthenticator:
    """Yahoo認証クラス"""
    
    def __init__(self):
        self.session = None
        self.cookies = None
        self._authenticated = False
        self._initialize_session()
    
    def _initialize_session(self):
        """セッションを初期化"""
        if not USE_YAHOO_AUTH:
            return
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Cookieが設定されている場合
        if YAHOO_COOKIE:
            # Cookie文字列をパースして設定
            self._set_cookies_from_string(YAHOO_COOKIE)
            self._authenticated = True
    
    def _set_cookies_from_string(self, cookie_string: str):
        """Cookie文字列をセッションに設定"""
        try:
            # Cookie文字列をパース
            cookies_dict = {}
            for item in cookie_string.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookies_dict[key] = value
            
            # セッションにCookieを設定
            for key, value in cookies_dict.items():
                self.session.cookies.set(key, value)
            
            # yfinanceが使用する可能性のある環境変数にも設定
            # 注意: yfinanceは直接Cookieをサポートしていないため、
            # 環境変数やグローバル設定で共有する必要があります
            os.environ['YAHOO_COOKIE'] = cookie_string
            
        except Exception as e:
            print(f"Cookie設定エラー: {e}")
    
    def get_session(self) -> Optional[requests.Session]:
        """認証済みセッションを取得"""
        return self.session if self._authenticated else None
    
    def get_cookies(self) -> Optional[Dict]:
        """認証済みCookieを取得"""
        return dict(self.session.cookies) if self.session and self._authenticated else None
    
    def is_authenticated(self) -> bool:
        """認証状態を確認"""
        return self._authenticated
    
    def verify_authentication(self) -> bool:
        """認証状態を検証"""
        if not self._authenticated:
            return False
        
        try:
            # Yahoo Financeにアクセスして認証状態を確認
            response = self.session.get('https://finance.yahoo.com', timeout=10)
            if response.status_code == 200:
                # 認証が有効かどうかを確認（ログインページにリダイレクトされていないか）
                if 'login' not in response.url.lower():
                    return True
            return False
        except Exception:
            return False


# グローバル認証インスタンス
yahoo_auth = YahooAuthenticator()
