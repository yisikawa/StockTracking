"""株価分析モジュール"""
import pandas as pd
from typing import Dict
from config import (
    RSI_PERIOD, MA_SHORT, MA_LONG, TRADING_DAYS_PER_YEAR,
    SCORE_EXCELLENT, SCORE_GOOD, SCORE_FAIR, SCORE_POOR,
    VOLATILITY_LOW, VOLATILITY_HIGH,
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    PRICE_POSITION_LOW, PRICE_POSITION_HIGH,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL
)


class StockAnalyzer:
    """株価分析クラス"""
    
    @staticmethod
    def calculate_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> float:
        """RSIを計算"""
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0
    
    @staticmethod
    def calculate_volatility(closes: pd.Series) -> float:
        """ボラティリティを計算（年率換算）"""
        returns = closes.pct_change().dropna()
        volatility = float(returns.std() * (TRADING_DAYS_PER_YEAR ** 0.5)) * 100
        return volatility
    
    @staticmethod
    def calculate_macd(closes: pd.Series, fast: int = MACD_FAST, slow: int = MACD_SLOW, signal: int = MACD_SIGNAL) -> Dict[str, float]:
        """MACDを計算"""
        exp1 = closes.ewm(span=fast, adjust=False).mean()
        exp2 = closes.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return {
            'macd': float(macd.iloc[-1]) if not macd.empty else 0.0,
            'signal': float(signal_line.iloc[-1]) if not signal_line.empty else 0.0,
            'histogram': float(histogram.iloc[-1]) if not histogram.empty else 0.0
        }
    
    @staticmethod
    def calculate_moving_averages(closes: pd.Series, short: int = MA_SHORT, long: int = MA_LONG) -> Dict[str, float]:
        """移動平均を計算"""
        ma_short = float(closes.tail(short).mean()) if len(closes) >= short else float(closes.iloc[-1])
        ma_long = float(closes.tail(long).mean()) if len(closes) >= long else float(closes.iloc[-1])
        return {'ma_20': ma_short, 'ma_50': ma_long}
    
    @staticmethod
    def calculate_price_range(closes: pd.Series) -> Dict[str, float]:
        """価格範囲を計算"""
        price_max = float(closes.max())
        price_min = float(closes.min())
        current_price = float(closes.iloc[-1])
        price_position = (current_price - price_min) / (price_max - price_min) if price_max > price_min else 0.5
        return {
            'max': price_max,
            'min': price_min,
            'current_position': float(price_position * 100)
        }
    
    @staticmethod
    def calculate_score(
        current_price: float,
        ma_20: float,
        ma_50: float,
        rsi: float,
        volatility: float,
        price_position: float
    ) -> int:
        """評価スコアを計算（0-100）"""
        score = 50  # ベーススコア
        
        # 価格と移動平均の関係
        if current_price > ma_20:
            score += 10
        if current_price > ma_50:
            score += 10
        if ma_20 > ma_50:
            score += 5
        
        # RSI評価
        if RSI_OVERSOLD < rsi < RSI_OVERBOUGHT:
            score += 10
        elif rsi < RSI_OVERSOLD:
            score += 5  # 売られすぎ
        elif rsi > RSI_OVERBOUGHT:
            score -= 5  # 買われすぎ
        
        # ボラティリティ評価
        if volatility < VOLATILITY_LOW:
            score += 10
        elif volatility > VOLATILITY_HIGH:
            score -= 10
        
        # 価格位置評価
        price_pos = price_position / 100
        if PRICE_POSITION_LOW < price_pos < PRICE_POSITION_HIGH:
            score += 5
        
        return max(0, min(100, score))
    
    @staticmethod
    def get_score_level(score: int) -> Dict[str, str]:
        """スコアから評価レベルを取得"""
        if score >= SCORE_EXCELLENT:
            return {'level': '優秀', 'recommendation': '強気'}
        elif score >= SCORE_GOOD:
            return {'level': '良好', 'recommendation': 'やや強気'}
        elif score >= SCORE_FAIR:
            return {'level': '普通', 'recommendation': '中立'}
        elif score >= SCORE_POOR:
            return {'level': '注意', 'recommendation': 'やや弱気'}
        else:
            return {'level': '要警戒', 'recommendation': '弱気'}
    
    @staticmethod
    def get_summary(current_price: float, ma_20: float, ma_50: float, rsi: float, volatility: float) -> Dict[str, str]:
        """サマリー情報を取得"""
        trend = '上昇トレンド' if current_price > ma_20 and ma_20 > ma_50 else \
                '下降トレンド' if current_price < ma_20 and ma_20 < ma_50 else '横ばい'
        
        momentum = '強い' if rsi > 60 else '弱い' if rsi < 40 else '普通'
        
        risk = '低' if volatility < VOLATILITY_LOW else '高' if volatility > VOLATILITY_HIGH else '中'
        
        return {'trend': trend, 'momentum': momentum, 'risk': risk}
    
    @staticmethod
    def analyze(hist: pd.DataFrame) -> Dict:
        """株価を分析"""
        closes = hist['Close']
        current_price = float(closes.iloc[-1])
        
        # 移動平均
        ma = StockAnalyzer.calculate_moving_averages(closes)
        ma_20, ma_50 = ma['ma_20'], ma['ma_50']
        
        # 価格範囲
        price_range = StockAnalyzer.calculate_price_range(closes)
        
        # RSI
        rsi = StockAnalyzer.calculate_rsi(closes)
        
        # ボラティリティ
        volatility = StockAnalyzer.calculate_volatility(closes)
        
        # 標準偏差
        price_std = float(closes.std())

        # MACD
        macd = StockAnalyzer.calculate_macd(closes)
        
        # スコア計算
        score = StockAnalyzer.calculate_score(
            current_price, ma_20, ma_50, rsi, volatility, price_range['current_position']
        )
        
        # 評価レベル
        level_info = StockAnalyzer.get_score_level(score)
        
        # サマリー
        summary = StockAnalyzer.get_summary(current_price, ma_20, ma_50, rsi, volatility)
        
        return {
            'current_price': current_price,
            'moving_averages': ma,
            'price_range': price_range,
            'indicators': {
                'rsi': rsi,
                'volatility': volatility,
                'price_std': price_std,
                'macd': macd
            },
            'score': score,
            'level': level_info['level'],
            'recommendation': level_info['recommendation'],
            'summary': summary
        }
