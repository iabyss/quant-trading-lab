"""
均线发散策略
均线多头发散
"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal


class MaDivergenceStrategy(BaseStrategy):
    """均线发散策略"""
    
    def __init__(self, periods: list = None):
        super().__init__("均线发散")
        self.periods = periods or [5, 10, 20]
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算各均线
        mas = {}
        for p in self.periods:
            mas[p] = close.rolling(window=p).mean().iloc[-1]
            mas_prev = close.rolling(window=p).mean().iloc[-2]
        
        # 计算斜率
        slopes = {}
        for p in self.periods:
            ma_now = close.rolling(window=p).mean().iloc[-1]
            ma_prev = close.rolling(window=p).mean().iloc[-5]  # 5日前
            slopes[p] = (ma_now - ma_prev) / ma_prev
        
        # 所有均线向上且发散
        all_up = all(slopes[p] > 0 for p in self.periods)
        all_diverging = all(slopes[self.periods[i]] > slopes[self.periods[i+1]] 
                           for i in range(len(self.periods)-1))
        
        if all_up and all_diverging:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason="均线多头发散"
            )
        
        # 所有均线向下
        all_down = all(slopes[p] < 0 for p in self.periods)
        if all_down:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason="均线空头发散"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="均线纠缠"
        )
    
    def get_params(self) -> dict:
        return {"periods": self.periods}
