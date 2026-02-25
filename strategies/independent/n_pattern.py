"""
N字反包策略
反包昨日阴线
"""

import pandas as pd
from .base import BaseStrategy, Signal


class NPatternStrategy(BaseStrategy):
    """N字反包策略"""
    
    def __init__(self):
        super().__init__("N字反包")
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        
        if len(df) < 3:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0,
                reason="数据不足"
            )
        
        # 昨天K线
        yesterday_close = close.iloc[-2]
        yesterday_open = open_price.iloc[-2]
        yesterday_high = high.iloc[-2]
        yesterday_low = low.iloc[-2]
        
        # 今天K线
        today_close = close.iloc[-1]
        today_open = open_price.iloc[-1]
        
        # 昨天是阴线
        yesterday_is_bearish = yesterday_close < yesterday_open
        
        # 昨天跌幅够大 (>3%)
        yesterday_change = (yesterday_close - yesterday_open) / yesterday_open * 100
        
        # 今天反包
        today_is_bullish = today_close > today_open
        today_cover = today_close > yesterday_open  # 收盘超过昨天开盘
        
        if (yesterday_is_bearish and yesterday_change < -3 and 
            today_is_bullish and today_cover):
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"N字反包 昨日{yesterday_change:.1f}%"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无反包信号"
        )
    
    def get_params(self) -> dict:
        return {}
