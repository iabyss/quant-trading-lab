"""
成交量相关打板策略
"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, Signal


class VolumeBreakoutStrategy(BaseStrategy):
    """成交量突破策略 - 放量突破"""
    
    def __init__(self, period: int = 20, volume_multi: float = 2.0):
        super().__init__("成交量突破")
        self.period = period
        self.volume_multi = volume_multi
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 成交量均线
        vol_ma = volume.rolling(window=self.period).mean()
        current_vol = volume.iloc[-1]
        
        # 价格突破
        price_change = (close.iloc[-1] - close.iloc[-self.period]) / close.iloc[-self.period]
        
        # 放量且上涨
        if current_vol > vol_ma.iloc[-1] * self.volume_multi and price_change > 0.05:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.9,
                reason=f"放量{current_vol/vol_ma.iloc[-1]:.1f}倍+上涨{price_change*100:.1f}%"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无放量"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period, "volume_multi": self.volume_multi}


class VolumePriceStrategy(BaseStrategy):
    """量价齐升策略"""
    
    def __init__(self, period: int = 5):
        super().__init__("量价齐升")
        self.period = period
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 连续N天价涨量增
        up_days = 0
        for i in range(-self.period, 0):
            price_up = close.iloc[i] > close.iloc[i-1]
            vol_up = volume.iloc[i] > volume.iloc[i-1]
            if price_up and vol_up:
                up_days += 1
        
        if up_days >= self.period * 0.8:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.8,
                reason=f"连续{up_days}天量价齐升"
            )
        
        # 连续下跌
        down_days = 0
        for i in range(-self.period, 0):
            if close.iloc[i] < close.iloc[i-1]:
                down_days += 1
        
        if down_days >= self.period * 0.8:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason=f"连续下跌"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="中性"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}


class VolumeMABreakoutStrategy(BaseStrategy):
    """成交量均线 breakout"""
    
    def __init__(self, period: int = 5):
        super().__init__("量能 breakout")
        self.period = period
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        volume = df['volume']
        
        # 量能突破5日均线
        vol_ma5 = volume.rolling(window=5).mean().iloc[-1]
        vol_ma20 = volume.rolling(window=20).mean().iloc[-1]
        
        # 量能放大
        if volume.iloc[-1] > vol_ma5 * 1.5 and vol_ma5 > vol_ma20:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.7,
                reason="量能放大突破"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无信号"
        )
    
    def get_params(self) -> dict:
        return {"period": self.period}


class HighVolumeStrategy(BaseStrategy):
    """高量能策略 - 成交量突增"""
    
    def __init__(self, zscore: float = 2.0):
        super().__init__("高量能")
        self.zscore = zscore
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        volume = df['volume']
        
        # 计算Z-score
        vol_mean = volume.iloc[-20:].mean()
        vol_std = volume.iloc[-20:].std()
        
        if vol_std == 0:
            return Signal(self.name, 0, 0, "数据不足")
        
        z = (volume.iloc[-1] - vol_mean) / vol_std
        
        if z > self.zscore:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=min(z / 5, 1.0),
                reason=f"量能Z={z:.1f}"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="正常量能"
        )
    
    def get_params(self) -> dict:
        return {"zscore": self.zscore}


class VolumeSupportStrategy(BaseStrategy):
    """量能支撑策略 - 回调到量能支撑位"""
    
    def __init__(self):
        super().__init__("量能支撑")
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 回调到20日均量支撑
        vol_ma20 = volume.rolling(window=20).mean().iloc[-1]
        
        # 价跌量缩
        if (close.iloc[-1] < close.iloc[-5] and 
            volume.iloc[-1] < vol_ma20):
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.6,
                reason="价跌量缩到支撑"
            )
        
        # 放量下跌
        if volume.iloc[-1] > vol_ma20 * 1.5 and close.iloc[-1] < close.iloc[-1]:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=0.7,
                reason="放量下跌"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="中性"
        )
    
    def get_params(self) -> dict:
        return {}


# 额外策略
class LimitVolumeStrategy(BaseStrategy):
    """地量见地价策略"""
    
    def __init__(self, threshold: float = 0.3):
        super().__init__("地量")
        self.threshold = threshold
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        volume = df['volume']
        
        # 成交量创20日新低
        vol_min = volume.iloc[-20:].min()
        
        if volume.iloc[-1] < vol_min * (1 + self.threshold):
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=0.6,
                reason="地量信号"
            )
        
        return Signal(
            strategy_name=self.name,
            signal=0,
            strength=0,
            reason="无信号"
        )
    
    def get_params(self) -> dict:
        return {"threshold": self.threshold}


class MoneyWaveStrategy(BaseStrategy):
    """资金波浪策略"""
    
    def __init__(self):
        super().__init__("资金波浪")
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        close = df['close']
        volume = df['volume']
        
        # 资金净流入 = 价涨量增 - 价跌量缩
        net_flow = 0
        for i in range(-5, 0):
            if close.iloc[i] > close.iloc[i-1]:
                net_flow += volume.iloc[i]
            else:
                net_flow -= volume.iloc[i]
        
        if net_flow > 0:
            return Signal(
                strategy_name=self.name,
                signal=1,
                strength=min(net_flow / volume.mean() / 10, 1.0),
                reason="资金净流入"
            )
        else:
            return Signal(
                strategy_name=self.name,
                signal=-1,
                strength=min(abs(net_flow) / volume.mean() / 10, 1.0),
                reason="资金净流出"
            )
    
    def get_params(self) -> dict:
        return {}
