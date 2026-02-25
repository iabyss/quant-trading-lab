"""
ATR策略
波动率策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class ATRStrategy(BaseStrategy):
    """ATR策略 - 波动率突破"""
    
    def __init__(self, period: int = 14, multiplier: float = 2.0):
        super().__init__("ATR策略")
        self.period = period
        self.multiplier = multiplier
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.period).mean()
        
        # 计算通道
        current_close = close.iloc[-1]
        current_atr = atr.iloc[-1]
        upper = current_close + current_atr * self.multiplier
        lower = current_close - current_atr * self.multiplier
        
        # 突破上轨
        if current_close > upper:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"突破ATR通道上轨"
            )
        # 突破下轨
        elif current_close < lower:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason=f"跌破ATR通道下轨"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="震荡整理"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "multiplier": self.multiplier}
