"""
资金流向策略
主力资金流入
"""

import pandas as pd
from .base import BaseStrategy, Signal


class MoneyFlowStrategy(BaseStrategy):
    """资金流向策略"""
    
    def __init__(self, period: int = 5):
        super().__init__("资金流向")
        self.period = period
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 简单资金流: 价涨量增
        price_change = close.diff()
        
        # 资金流入: 价格上涨且成交量放大
        vol_change = volume.diff() / volume.shift(1)
        
        inflow_days = 0
        for i in range(-self.period, 0):
            if price_change.iloc[i] > 0 and vol_change.iloc[i] > 0:
                inflow_days += 1
        
        if inflow_days >= self.period * 0.7:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.7,
                reason=f"连续{inflow_days}天资金流入"
            )
        
        outflow_days = 0
        for i in range(-self.period, 0):
            if price_change.iloc[i] < 0:
                outflow_days += 1
        
        if outflow_days >= self.period * 0.7:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason=f"连续{outflow_days}天资金流出"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="资金平衡"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}
