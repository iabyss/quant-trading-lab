"""
追涨策略
突破近期高点追涨
"""

import pandas as pd
from .base import BaseStrategy, Signal


class ChaseUpStrategy(BaseStrategy):
    """追涨策略 - 突破N日高点"""
    
    def __init__(self, period: int = 20, strength: float = 0.03):
        super().__init__("追涨策略")
        self.period = period  # 周期
        self.strength = strength  # 涨幅要求
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        high = df['high']
        
        # 20日高点
        highest = high.iloc[-self.period:].max()
        current = close.iloc[-1]
        
        # 涨幅
        change_pct = (current - close.iloc[-2]) / close.iloc[-2]
        
        # 突破高点且涨幅够
        if current > highest * 1.01 and change_pct > self.strength:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"突破{self.period}日高点+涨幅{change_pct*100:.1f}%"
            )
        
        # 接近高点
        if current > highest * 0.98:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="接近高点"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无追涨信号"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "strength": self.strength}
