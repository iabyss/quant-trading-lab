"""
策略基类
所有策略必须继承此基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd


@dataclass
class Signal:
    """交易信号"""
    strategy_name: str
    signal: int  # 1=buy, -1=sell, 0=hold
    strength: float  # 0-1 信号强度
    reason: str  # 信号原因


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        分析数据，返回信号
        
        Args:
            df: 包含OHLCV的DataFrame
        
        Returns:
            Signal对象
        """
        pass
    
    def get_params(self) -> Dict:
        """获取策略参数"""
        return {}
    
    def set_params(self, **kwargs):
        """设置策略参数"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
