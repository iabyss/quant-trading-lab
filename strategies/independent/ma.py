"""
均线策略
均线多头/空头排列
"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal


class MAStrategy(BaseStrategy):
    """均线策略 - 多头/空头排列"""
    
    def __init__(self, periods: list = None):
        super().__init__("均线策略")
        self.periods = periods or [5, 10, 20, 60]
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        mas = {p: close.rolling(window=p).mean().iloc[-1] for p in self.periods}
        
        # 多头排列
        if all(mas[self.periods[i]] > mas[self.periods[i+1]] for i in range(len(self.periods)-1)):
            avg_slope = np.mean([(mas[self.periods[i]] - mas[self.periods[i+1]])/mas[self.periods[i+1]] 
                               for i in range(len(self.periods)-1)])
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=min(avg_slope * 10, 1.0),
                reason="均线多头排列"
            )
        
        # 空头排列
        elif all(mas[self.periods[i]] < mas[self.periods[i+1]] for i in range(len(self.periods)-1)):
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason="均线空头排列"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="均线纠缠"
        )
    
    def get_params(self) -> dict:
        return {"periods": self.periods}
