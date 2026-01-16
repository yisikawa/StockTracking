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
