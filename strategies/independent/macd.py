"""
MACD策略
MACD金叉死叉
"""

import pandas as pd
from .base import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    """MACD策略 - 金叉死叉"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD策略")
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        
        # 计算MACD
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=self.signal_period, adjust=False).mean()
        
        histogram = macd - signal_line
        
        # 金叉
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason="MACD金叉"
            )
        # 死叉
        elif histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.8,
                reason="MACD死叉"
            )
        
        # 在零轴上方
        if macd.iloc[-1] > 0:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="MACD多头"
            )
        else:
            return Signal(
                strategy_name=self.name,
                signal=0,
                strength=0.3,
                reason="MACD空头"
            )
    
    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "signal": self.signal_period}
