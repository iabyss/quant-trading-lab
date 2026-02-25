"""
动量策略
追涨杀跌策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    """动量策略 - 追涨杀跌"""
    
    def __init__(self, period: int = 5, threshold: float = 0.02):
        super().__init__("动量策略")
        self.period = period
        self.threshold = threshold
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # N日涨幅
        momentum = (close.iloc[-1] - close.iloc[-self.period]) / close.iloc[-self.period]
        
        if momentum > self.threshold:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=min(momentum * 5, 1.0),
                reason=f"动量上涨 {momentum*100:.1f}%"
            )
        elif momentum < -self.threshold:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=min(abs(momentum) * 5, 1.0),
                reason=f"动量下跌 {momentum*100:.1f}%"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="动量中性"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "threshold": self.threshold}
