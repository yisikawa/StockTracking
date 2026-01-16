import pandas as pd
from prophet import Prophet
import logging

# ロギング設定
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

class StockPredictor:
    def __init__(self):
        pass

    def predict(self, hist_data: pd.DataFrame, periods: int = 30) -> dict:
        """
        株価データを元に将来の価格を予測する
        
        Args:
            hist_data (pd.DataFrame): yfinanceから取得した履歴データ (indexがDate)
            periods (int): 予測する日数
            
        Returns:
            dict: 予測結果 (dates, trend, yhat, yhat_lower, yhat_upper)
        """
        # データ準備
        df = hist_data.reset_index()[['Date', 'Close']].copy()
        df.columns = ['ds', 'y']
        
        # タイムゾーン情報の削除（Prophetの要件）
        if df['ds'].dt.tz is not None:
            df['ds'] = df['ds'].dt.tz_localize(None)

        # モデルの初期化と学習
        # 日次データ、株価なのでトレンドの変化に追従しやすい設定に
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05
        )
        
        model.fit(df)
        
        # 将来のデータフレーム作成（平日のみ）
        future = model.make_future_dataframe(periods=periods, freq='B')
        
        # 予測実行
        forecast = model.predict(future)
        
        # 結果の整形
        # 直近の実績 + 予測期間
        result_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend']].tail(periods + 30)
        
        return {
            'dates': result_df['ds'].dt.strftime('%Y-%m-%d').tolist(),
            'current_price': float(hist_data['Close'].iloc[-1]),
            'forecast': {
                'yhat': result_df['yhat'].tolist(),
                'lower': result_df['yhat_lower'].tolist(),
                'upper': result_df['yhat_upper'].tolist(),
                'trend': result_df['trend'].tolist()
            },
            'summary': self._generate_summary(forecast, hist_data)
        }

    def _generate_summary(self, forecast, hist_data):
        last_close = hist_data['Close'].iloc[-1]
        next_day_pred = forecast['yhat'].iloc[-1] # 注: tailで切り取る前の最後の値を見るべきだが、ここでは簡易化
        
        # 正確には直近の実績日以降の最初の予測値を取得する
        last_date = hist_data.index[-1].replace(tzinfo=None)
        future_pred = forecast[forecast['ds'] > last_date].iloc[0]
        
        pred_price = future_pred['yhat']
        lower = future_pred['yhat_lower']
        upper = future_pred['yhat_upper']
        
        diff = pred_price - last_close
        diff_percent = (diff / last_close) * 100
        
        trend = "上昇" if diff > 0 else "下落"
        
        return {
            'next_day': {
                'date': future_pred['ds'].strftime('%Y-%m-%d'),
                'price': round(pred_price, 2),
                'range_low': round(lower, 2),
                'range_high': round(upper, 2),
                'diff': round(diff, 2),
                'diff_percent': round(diff_percent, 2),
                'trend_direction': trend
            }
        }
