# stock/technical_analysis.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from .models import Stock, TechnicalIndicator

class TechnicalAnalyzer:
    """テクニカル分析クラス"""
    
    @staticmethod
    def calculate_moving_averages(prices, periods=[5, 25, 75, 200]):
        """移動平均線計算"""
        ma_data = {}
        for period in periods:
            if len(prices) >= period:
                ma_data[f'ma_{period}'] = prices.rolling(window=period).mean().iloc[-1]
            else:
                ma_data[f'ma_{period}'] = None
        return ma_data
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        """RSI計算"""
        if len(prices) < period:
            return None
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        """MACD計算"""
        if len(prices) < slow:
            return None, None, None
        
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return macd.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        """ボリンジャーバンド計算"""
        if len(prices) < period:
            return None, None, None
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band.iloc[-1], sma.iloc[-1], lower_band.iloc[-1]
    
    @staticmethod
    def calculate_volatility(prices, period=30):
        """ボラティリティ計算"""
        if len(prices) < period:
            return None
        
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(window=period).std() * np.sqrt(252)  # 年率換算
        return volatility.iloc[-1]
    
    @staticmethod
    def get_price_momentum(prices, periods=[1, 5, 10, 20]):
        """価格モメンタム計算"""
        momentum = {}
        current_price = prices.iloc[-1]
        
        for period in periods:
            if len(prices) > period:
                past_price = prices.iloc[-(period+1)]
                momentum[f'momentum_{period}d'] = ((current_price - past_price) / past_price) * 100
            else:
                momentum[f'momentum_{period}d'] = None
        
        return momentum
    
    @classmethod
    def analyze_stock(cls, stock_code, days=252):
        """株式のテクニカル分析実行"""
        try:
            # 価格データ取得
            symbol = f"{stock_code}.T"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days}d")
            
            if hist.empty:
                return None
            
            prices = hist['Close']
            volumes = hist['Volume']
            
            # 各種指標計算
            ma_data = cls.calculate_moving_averages(prices)
            rsi = cls.calculate_rsi(prices)
            macd, macd_signal, macd_histogram = cls.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower = cls.calculate_bollinger_bands(prices)
            volatility = cls.calculate_volatility(prices)
            momentum = cls.get_price_momentum(prices)
            
            # 出来高分析
            avg_volume = volumes.rolling(window=20).mean().iloc[-1] if len(volumes) >= 20 else None
            volume_ratio = volumes.iloc[-1] / avg_volume if avg_volume else None
            
            # トレンド判定
            trend = cls.determine_trend(ma_data, rsi, macd)
            
            return {
                'stock_code': stock_code,
                'analysis_date': datetime.now().date(),
                'current_price': prices.iloc[-1],
                'moving_averages': ma_data,
                'rsi': rsi,
                'macd': {
                    'macd': macd,
                    'signal': macd_signal,
                    'histogram': macd_histogram
                },
                'bollinger_bands': {
                    'upper': bb_upper,
                    'middle': bb_middle,
                    'lower': bb_lower
                },
                'volatility': volatility,
                'momentum': momentum,
                'volume_analysis': {
                    'current_volume': volumes.iloc[-1],
                    'avg_volume_20d': avg_volume,
                    'volume_ratio': volume_ratio
                },
                'trend': trend,
                'signals': cls.generate_signals(ma_data, rsi, macd, bb_upper, bb_lower, prices.iloc[-1])
            }
            
        except Exception as e:
            print(f"テクニカル分析エラー {stock_code}: {e}")
            return None
    
    @staticmethod
    def determine_trend(ma_data, rsi, macd):
        """トレンド判定"""
        ma_5 = ma_data.get('ma_5')
        ma_25 = ma_data.get('ma_25')
        ma_75 = ma_data.get('ma_75')
        
        if all([ma_5, ma_25, ma_75]):
            if ma_5 > ma_25 > ma_75 and rsi > 50:
                return "強い上昇トレンド"
            elif ma_5 > ma_25 and macd > 0:
                return "上昇トレンド"
            elif ma_5 < ma_25 < ma_75 and rsi < 50:
                return "強い下降トレンド"
            elif ma_5 < ma_25 and macd < 0:
                return "下降トレンド"
            else:
                return "レンジ・調整"
        else:
            return "判定不能"
    
    @staticmethod
    def generate_signals(ma_data, rsi, macd, bb_upper, bb_lower, current_price):
        """売買シグナル生成"""
        signals = []
        
        # RSIシグナル
        if rsi:
            if rsi > 70:
                signals.append({"type": "売り", "reason": "RSI過熱（70超）", "strength": "中"})
            elif rsi < 30:
                signals.append({"type": "買い", "reason": "RSI過売り（30以下）", "strength": "中"})
        
        # MACDシグナル
        if macd is not None:
            if macd > 0:
                signals.append({"type": "買い", "reason": "MACD上昇転換", "strength": "弱"})
            elif macd < 0:
                signals.append({"type": "売り", "reason": "MACD下降転換", "strength": "弱"})
        
        # ボリンジャーバンドシグナル
        if bb_upper and bb_lower:
            if current_price > bb_upper:
                signals.append({"type": "売り", "reason": "ボリンジャーバンド上限突破", "strength": "中"})
            elif current_price < bb_lower:
                signals.append({"type": "買い", "reason": "ボリンジャーバンド下限突破", "strength": "中"})
        
        # 移動平均シグナル
        ma_5 = ma_data.get('ma_5')
        ma_25 = ma_data.get('ma_25')
        
        if ma_5 and ma_25:
            if ma_5 > ma_25:
                signals.append({"type": "買い", "reason": "短期移動平均が長期を上抜け", "strength": "弱"})
            elif ma_5 < ma_25:
                signals.append({"type": "売り", "reason": "短期移動平均が長期を下抜け", "strength": "弱"})
        
        return signals

# モデル定義も追加
class TechnicalIndicator(models.Model):
    """テクニカル指標データ"""
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='technical_indicators')
    date = models.DateField(verbose_name="分析日")
    
    # 移動平均
    ma_5 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="5日移動平均")
    ma_25 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="25日移動平均")
    ma_75 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="75日移動平均")
    ma_200 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="200日移動平均")
    
    # オシレーター
    rsi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="RSI")
    macd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MACD")
    macd_signal = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="MACDシグナル")
    
    # ボリンジャーバンド
    bb_upper = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ボリンジャー上限")
    bb_lower = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ボリンジャー下限")
    
    # ボラティリティ・モメンタム
    volatility = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="ボラティリティ")
    momentum_1d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="1日モメンタム")
    momentum_5d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="5日モメンタム")
    momentum_20d = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="20日モメンタム")
    
    # トレンド判定
    trend = models.CharField(max_length=50, blank=True, verbose_name="トレンド")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['stock', 'date']
        ordering = ['-date']