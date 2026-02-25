"""
CCI商品通道指数策略
"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal


class CCIStrategy(BaseStrategy):
    """CCI策略"""
    
    def __init__(self, period: int = 14, oversold: int = -100, overbought: int = 100):
        super().__init__("CCI策略")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算典型价格
        tp = (high + low + close) / 3
        
        # 计算SMA
        sma = tp.rolling(window=self.period).mean()
        
        # 计算平均偏差
        mad = tp.rolling(window=self.period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        
        # 计算CCI
        cci = (tp - sma) / (0.015 * mad)
        
        cci_value = cci.iloc[-1]
        
        # 超卖买入
        if cci_value < self.oversold:
            strength = abs(cci_value - self.oversold) / 100
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=min(strength, 1.0),
                reason=f"CCI超卖 {cci_value:.1f}"
            )
        # 超买卖出
        elif cci_value > self.overbought:
            strength = (cci_value - self.overbought) / 100
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=min(strength, 1.0),
                reason=f"CCI超买 {cci_value:.1f}"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason=f"CCI中性 {cci_value:.1f}"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}
