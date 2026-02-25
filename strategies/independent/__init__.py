"""
独立策略模块
每个策略独立文件，可自由组合
"""

from .base import BaseStrategy, Signal
from .factory import StrategyFactory, HybridStrategy, create_hybrid, create_preset, PRESETS
from .momentum import MomentumStrategy
from .breakout import BreakoutStrategy
from .rsi import RSIStrategy
from .ma import MAStrategy
from .volume import VolumeStrategy
from .macd import MACDStrategy

__all__ = [
    'BaseStrategy',
    'Signal',
    'StrategyFactory',
    'HybridStrategy',
    'create_hybrid',
    'create_preset',
    'PRESETS',
    'MomentumStrategy',
    'BreakoutStrategy',
    'RSIStrategy',
    'MAStrategy',
    'VolumeStrategy',
    'MACDStrategy',
]
