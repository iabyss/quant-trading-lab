"""
KDJ随机指标策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class KDJStrategy(BaseStrategy):
    """KDJ策略"""
    
    def __init__(self, k_period: int = 9, d_period: int = 3, oversold: int = 20, overbought: int = 80):
        super().__init__("KDJ策略")
        self.k_period = k_period
        self.d_period = d_period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算KDJ
        lowest_low = low.rolling(window=self.k_period).min()
        highest_high = high.rolling(window=self.k_period).max()
        
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=self.d_period).mean()
        j = 3 * k - 2 * d
        
        k_value = k.iloc[-1]
        d_value = d.iloc[-1]
        j_value = j.iloc[-1]
        
        # 金叉买入
        if k_value > d_value and k.iloc[-2] <= d.iloc[-2]:
            if k_value < self.oversold:
                return Signal(
                    strategy_name=self.name,
                    signal=1,
                    strength=0.9,
                    reason=f"KDJ金叉超卖 K={k_value:.1f}"
                )
            else:
                return Signal(
                    strategy_name=self.name,
                    signal=1,
                    strength=0.6,
                    reason=f"KDJ金叉 K={k_value:.1f}"
                )
        
        # 死叉卖出
        elif k_value < d_value and k.iloc[-2] >= d.iloc[-2]:
            if k_value > self.overbought:
                return Signal(
                    strategy_name=self.name,
                    signal=-1,
                    strength=0.9,
                    reason=f"KDJ死叉超买 K={k_value:.1f}"
                )
            else:
                return Signal(
                    strategy_name=self.name,
                    signal=-1,
                    strength=0.6,
                    reason=f"KDJ死叉 K={k_value:.1f}"
                )
        
        # J值超买超卖
        if j_value > 100:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason=f"J值超买 {j_value:.1f}"
            )
        elif j_value < 0:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.7,
                reason=f"J值超卖 {j_value:.1f}"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason=f"K={k_value:.1f} D={d_value:.1f}"
        )
    
    def get_params(self) -> dict:
        return {"k_period": self.k_period, "d_period": self.d_period}
