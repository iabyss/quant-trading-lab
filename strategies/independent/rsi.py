"""
RSI反转策略
RSI超卖买入，超买卖出
"""

import pandas as pd
from .base import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    """RSI反转策略"""
    
    def __init__(self, period: int = 14, oversold: int = 35, overbought: int = 65):
        super().__init__("RSI策略")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_value = rsi.iloc[-1]
        
        if rsi_value < self.oversold:
            strength = (self.oversold - rsi_value) / self.oversold
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=strength,
                reason=f"RSI {rsi_value:.1f} 超卖"
            )
        elif rsi_value > self.overbought:
            strength = (rsi_value - self.overbought) / (100 - self.overbought)
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=strength,
                reason=f"RSI {rsi_value:.1f} 超买"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason=f"RSI {rsi_value:.1f} 中性"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "oversold": self.oversold, "overbought": self.overbought}
