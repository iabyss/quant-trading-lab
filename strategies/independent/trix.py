"""
TRIX策略
三重指数平滑移动平均
"""

import pandas as pd
from .base import BaseStrategy, Signal


class TRIXStrategy(BaseStrategy):
    """TRIX策略"""
    
    def __init__(self, period: int = 12, signal: int = 9):
        super().__init__("TRIX策略")
        self.period = period
        self.signal = signal
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算TRIX
        ema1 = close.ewm(span=self.period, adjust=False).mean()
        ema2 = ema1.ewm(span=self.period, adjust=False).mean()
        ema3 = ema2.ewm(span=self.period, adjust=False).mean()
        
        trix = ema3.pct_change() * 100
        signal_line = trix.ewm(span=self.signal, adjust=False).mean()
        
        # 金叉
        if trix.iloc[-1] > signal_line.iloc[-1] and trix.iloc[-2] <= signal_line.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason="TRIX金叉"
            )
        # 死叉
        elif trix.iloc[-1] < signal_line.iloc[-1] and trix.iloc[-2] >= signal_line.iloc[-2]:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason="TRIX死叉"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0.3,
            reason="TRIX中性"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "signal": self.signal}
