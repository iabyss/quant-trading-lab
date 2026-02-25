"""
突破策略
20日高点突破策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class BreakoutStrategy(BaseStrategy):
    """突破策略 - 20日高点突破"""
    
    def __init__(self, period: int = 20):
        super().__init__("突破策略")
        self.period = period
    
    def _calc_atr(self, df: pd.DataFrame) -> float:
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.iloc[-self.period:].mean()
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        high = df['high']
        
        # 20日高点
        highest = high.iloc[-self.period:].max()
        current_price = close.iloc[-1]
        
        if current_price > highest:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"突破20日高点 {highest:.2f}"
            )
        elif current_price < highest * 0.95:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.5,
                reason="跌破20日高点支撑"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="震荡整理"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}
