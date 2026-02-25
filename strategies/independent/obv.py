"""
OBV能量潮策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class OBVStrategy(BaseStrategy):
    """OBV能量潮策略"""
    
    def __init__(self, period: int = 20):
        super().__init__("OBV策略")
        self.period = period
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 计算OBV
        obv = (pd.Series(index=close.index, dtype=float))
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        # OBV均线
        obv_ma = obv.rolling(window=self.period).mean()
        
        # OBV突破均线
        if obv.iloc[-1] > obv_ma.iloc[-1] and obv.iloc[-2] <= obv_ma.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.7,
                reason="OBV突破均线"
            )
        elif obv.iloc[-1] < obv_ma.iloc[-1] and obv.iloc[-2] >= obv_ma.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason="OBV跌破均线"
            )
        
        # OBV趋势
        if obv.iloc[-1] > obv.iloc[-self.period]:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="OBV上升趋势"
            )
        else:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="OBV下降趋势"
            )
    
    def get_params(self) -> dict:
        return {"period": self.period}
