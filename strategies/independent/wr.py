"""
WR威廉指标策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class WRStrategy(BaseStrategy):
    """威廉指标策略"""
    
    def __init__(self, period: int = 14, oversold: int = 20, overbought: int = 80):
        super().__init__("WR策略")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算WR
        highest = high.rolling(window=self.period).max()
        lowest = low.rolling(window=self.period).min()
        
        wr = 100 * (highest - close) / (highest - lowest)
        
        wr_value = wr.iloc[-1]
        
        # 超卖买入 (威廉指标接近0)
        if wr_value < self.oversold:
            strength = (self.oversold - wr_value) / self.oversold
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=strength,
                reason=f"WR超卖 {wr_value:.1f}"
            )
        # 超买卖出 (威廉指标接近100)
        elif wr_value > self.overbought:
            strength = (wr_value - self.overbought) / (100 - self.overbought)
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=strength,
                reason=f"WR超买 {wr_value:.1f}"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason=f"WR中性 {wr_value:.1f}"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}
