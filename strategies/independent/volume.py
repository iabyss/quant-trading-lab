"""
成交量策略
放量突破策略
"""

import pandas as pd
from .base import BaseStrategy, Signal


class VolumeStrategy(BaseStrategy):
    """成交量策略 - 放量突破"""
    
    def __init__(self, period: int = 20, volume_multiplier: float = 1.5):
        super().__init__("成交量策略")
        self.period = period
        self.volume_multiplier = volume_multiplier
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 成交量均线
        vol_ma = volume.iloc[-self.period:].mean()
        current_vol = volume.iloc[-1]
        
        # 价格变化
        price_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        
        # 放量上涨
        if current_vol > vol_ma * self.volume_multiplier and price_change > 0.01:
            strength = min((current_vol / vol_ma - 1) * 2, 1.0)
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=strength,
                reason=f"放量上涨 {current_vol/vol_ma:.1f}倍"
            )
        # 放量下跌
        elif current_vol > vol_ma * self.volume_multiplier and price_change < -0.01:
            strength = min((current_vol / vol_ma - 1) * 2, 1.0)
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=strength,
                reason=f"放量下跌 {current_vol/vol_ma:.1f}倍"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="成交量正常"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "volume_multiplier": self.volume_multiplier}
