"""銘柄シンボルユーティリティモジュール - 日本株対応・通貨処理"""
from typing import Dict, Tuple


class SymbolUtils:
    """銘柄シンボル処理ユーティリティクラス"""
    
    # 市場サフィックスと通貨のマッピング
    MARKET_CURRENCY_MAP = {
        '.T': 'JPY',      # 東京証券取引所
        '.JP': 'JPY',     # 日本
        '.HK': 'HKD',     # 香港
        '.L': 'GBP',      # ロンドン
        '.PA': 'EUR',     # パリ
        '.DE': 'EUR',     # ドイツ
        '.F': 'EUR',      # フランクフルト
        '.AS': 'EUR',     # アムステルダム
        '.MI': 'EUR',     # ミラノ
        '.SW': 'CHF',     # スイス
        '.TO': 'CAD',     # トロント
        '.AX': 'AUD',     # オーストラリア
        '.KS': 'KRW',     # 韓国
        '.TW': 'TWD',     # 台湾
        '.SS': 'CNY',     # 上海
        '.SZ': 'CNY',     # 深セン
    }
    
    # 通貨シンボル
    CURRENCY_SYMBOLS = {
        'JPY': '¥',
        'USD': '$',
        'HKD': 'HK$',
        'GBP': '£',
        'EUR': '€',
        'CHF': 'CHF ',
        'CAD': 'CA$',
        'AUD': 'A$',
        'KRW': '₩',
        'TWD': 'NT$',
        'CNY': '¥',
    }
    
    # 日本の主要企業マッピング（検索補助用）
    JAPANESE_COMPANIES = {
        '7203': 'トヨタ自動車',
        '6758': 'ソニーグループ',
        '9984': 'ソフトバンクグループ',
        '6861': 'キーエンス',
        '8306': '三菱UFJフィナンシャル・グループ',
        '7267': '本田技研工業',
        '9433': 'KDDI',
        '6501': '日立製作所',
        '7974': '任天堂',
        '4063': '信越化学工業',
        '8058': '三菱商事',
        '9432': '日本電信電話',
        '6902': 'デンソー',
        '6098': 'リクルートホールディングス',
        '4519': '中外製薬',
    }
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        銘柄コードを正規化（日本株対応）
        
        Args:
            symbol: 入力された銘柄コード
            
        Returns:
            正規化された銘柄コード
        """
        symbol = symbol.upper().strip()
        
        # すでに市場サフィックスが付いている場合はそのまま返す
        for suffix in SymbolUtils.MARKET_CURRENCY_MAP.keys():
            if symbol.endswith(suffix):
                return symbol
        
        # 数字4桁のみの場合は日本株とみなして.Tを付与
        if symbol.isdigit() and len(symbol) == 4:
            return f"{symbol}.T"
        
        return symbol
    
    @staticmethod
    def get_currency(symbol: str) -> str:
        """
        銘柄の通貨を判定
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            通貨コード（例: 'JPY', 'USD'）
        """
        symbol = symbol.upper()
        
        for suffix, currency in SymbolUtils.MARKET_CURRENCY_MAP.items():
            if symbol.endswith(suffix):
                return currency
        
        # デフォルトは米ドル
        return 'USD'
    
    @staticmethod
    def get_currency_symbol(currency: str) -> str:
        """
        通貨コードから通貨シンボルを取得
        
        Args:
            currency: 通貨コード
            
        Returns:
            通貨シンボル
        """
        return SymbolUtils.CURRENCY_SYMBOLS.get(currency, '$')
    
    @staticmethod
    def format_price(price: float, symbol: str) -> str:
        """
        価格を通貨に応じてフォーマット
        
        Args:
            price: 価格
            symbol: 銘柄コード
            
        Returns:
            フォーマットされた価格文字列
        """
        currency = SymbolUtils.get_currency(symbol)
        currency_symbol = SymbolUtils.get_currency_symbol(currency)
        
        # 日本円は小数点なし
        if currency == 'JPY':
            return f"{currency_symbol}{price:,.0f}"
        # 韓国ウォンも小数点なし
        elif currency == 'KRW':
            return f"{currency_symbol}{price:,.0f}"
        else:
            return f"{currency_symbol}{price:,.2f}"
    
    @staticmethod
    def format_change(change: float, change_percent: float, symbol: str) -> Tuple[str, str]:
        """
        変動額と変動率をフォーマット
        
        Args:
            change: 変動額
            change_percent: 変動率
            symbol: 銘柄コード
            
        Returns:
            (フォーマットされた変動額, フォーマットされた変動率)
        """
        currency = SymbolUtils.get_currency(symbol)
        currency_symbol = SymbolUtils.get_currency_symbol(currency)
        sign = '+' if change >= 0 else ''
        
        if currency in ('JPY', 'KRW'):
            change_str = f"{sign}{currency_symbol}{change:,.0f}"
        else:
            change_str = f"{sign}{currency_symbol}{change:,.2f}"
        
        percent_str = f"{sign}{change_percent:.2f}%"
        
        return change_str, percent_str
    
    @staticmethod
    def is_japanese_stock(symbol: str) -> bool:
        """
        日本株かどうかを判定
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            日本株の場合True
        """
        symbol = symbol.upper()
        return symbol.endswith('.T') or symbol.endswith('.JP') or (symbol.isdigit() and len(symbol) == 4)
    
    @staticmethod
    def get_market_name(symbol: str) -> str:
        """
        市場名を取得
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            市場名
        """
        symbol = symbol.upper()
        
        market_names = {
            '.T': '東京証券取引所',
            '.JP': '日本',
            '.HK': '香港証券取引所',
            '.L': 'ロンドン証券取引所',
            '.PA': 'ユーロネクスト・パリ',
            '.DE': 'ドイツ取引所',
            '.F': 'フランクフルト証券取引所',
            '.SS': '上海証券取引所',
            '.SZ': '深セン証券取引所',
            '.KS': '韓国取引所',
            '.TO': 'トロント証券取引所',
            '.AX': 'オーストラリア証券取引所',
        }
        
        for suffix, name in market_names.items():
            if symbol.endswith(suffix):
                return name
        
        return 'NASDAQ/NYSE'
    
    @staticmethod
    def get_stock_info(symbol: str) -> Dict:
        """
        銘柄の基本情報を取得（シンボルベース）
        
        Args:
            symbol: 銘柄コード
            
        Returns:
            銘柄情報辞書
        """
        normalized = SymbolUtils.normalize_symbol(symbol)
        currency = SymbolUtils.get_currency(normalized)
        
        # 日本株の場合、事前定義された企業名を取得
        base_symbol = normalized.replace('.T', '').replace('.JP', '')
        company_name = SymbolUtils.JAPANESE_COMPANIES.get(base_symbol)
        
        return {
            'original_symbol': symbol,
            'normalized_symbol': normalized,
            'currency': currency,
            'currency_symbol': SymbolUtils.get_currency_symbol(currency),
            'market': SymbolUtils.get_market_name(normalized),
            'is_japanese': SymbolUtils.is_japanese_stock(symbol),
            'known_name': company_name,
        }


# 便利な関数をモジュールレベルでエクスポート
normalize_symbol = SymbolUtils.normalize_symbol
get_currency = SymbolUtils.get_currency
format_price = SymbolUtils.format_price
format_change = SymbolUtils.format_change
is_japanese_stock = SymbolUtils.is_japanese_stock

