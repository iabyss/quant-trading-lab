"""
DMA策略
平行线差指标
"""

import pandas as pd
from .base import BaseStrategy, Signal


class DMAStrategy(BaseStrategy):
    """DMA策略"""
    
    def __init__(self, fast: int = 10, slow: int = 50):
        super().__init__("DMA策略")
        self.fast = fast
        self.slow = slow
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算DMA
        dma_fast = close.rolling(window=self.fast).mean()
        dma_slow = close.rolling(window=self.slow).mean()
        dd = dma_fast - dma_slow
        ama = dd.rolling(window=self.fast).mean()
        
        # 金叉
        if dd.iloc[-1] > ama.iloc[-1] and dd.iloc[-2] <= ama.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason="DMA金叉"
            )
        # 死叉
        elif dd.iloc[-1] < ama.iloc[-1] and dd.iloc[-2] >= ama.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason="DMA死叉"
            )
        
        # 多头
        if dd.iloc[-1] > ama.iloc[-1]:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="多头排列"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0.3,
            reason="空头排列"
        )
    
    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow}
