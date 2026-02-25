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
from .bollinger import BollingerStrategy
from .kdj import KDJStrategy
from .cci import CCIStrategy
from .atr import ATRStrategy
from .dma import DMAStrategy
from .trix import TRIXStrategy
from .wr import WRStrategy
from .obv import OBVStrategy
from .limit_up import LimitUpStrategy
from .chase_up import ChaseUpStrategy
from .n_pattern import NPatternStrategy
from .money_flow import MoneyFlowStrategy
from .ma_divergence import MaDivergenceStrategy

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
    'BollingerStrategy',
    'KDJStrategy',
    'CCIStrategy',
    'ATRStrategy',
    'DMAStrategy',
    'TRIXStrategy',
    'WRStrategy',
    'OBVStrategy',
    'LimitUpStrategy',
    'ChaseUpStrategy',
    'NPatternStrategy',
    'MoneyFlowStrategy',
    'MaDivergenceStrategy',
]
