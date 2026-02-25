"""
布林带策略
价格突破布林带上下轨
"""

import pandas as pd
from .base import BaseStrategy, Signal


class BollingerStrategy(BaseStrategy):
    """布林带策略"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("布林带策略")
        self.period = period
        self.std_dev = std_dev
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算布林带
        ma = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        upper = ma + self.std_dev * std
        lower = ma - self.std_dev * std
        
        current_price = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        current_ma = ma.iloc[-1]
        
        # 突破上轨
        if current_price > current_upper:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"突破上轨 {current_upper:.2f}"
            )
        # 突破下轨
        elif current_price < current_lower:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason=f"跌破下轨 {current_lower:.2f}"
            )
        # 在轨道内
        elif current_price > current_ma:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="在中轨上方"
            )
        else:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="在中轨下方"
            )
    
    def get_params(self) -> dict:
        return {"period": self.period, "std_dev": self.std_dev}
