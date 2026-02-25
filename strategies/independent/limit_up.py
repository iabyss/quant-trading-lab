"""
涨停板策略
追涨停板策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class LimitUpStrategy(BaseStrategy):
    """涨停板策略 - 追涨停股"""
    
    def __init__(self, days: int = 3):
        super().__init__("涨停板策略")
        self.days = days  # 几天内涨停
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        high = df['high']
        
        # 计算涨跌幅
        change = (close - close.shift(1)) / close.shift(1) * 100
        
        # 最近N天有涨停
        limit_up_days = (change > 9.5).sum()
        
        # 连续涨停
        consecutive = 0
        for i in range(len(change)-1, -1, -1):
            if change.iloc[i] > 9.5:
                consecutive += 1
            else:
                break
        
        if consecutive >= self.days:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.9,
                reason=f"连续{consecutive}天涨停"
            )
        elif limit_up_days >= self.days:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.7,
                reason=f"{self.days}天内有涨停"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无涨停"
        )
    
    def get_params(self) -> dict:
        return {"days": self.days}
