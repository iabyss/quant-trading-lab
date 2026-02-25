"""
策略工厂
选择并组合多种策略
"""

from typing import List, Dict
from .base import BaseStrategy, Signal
from .momentum import MomentumStrategy
from .breakout import BreakoutStrategy
from .rsi import RSIStrategy
from .ma import MAStrategy
from .volume import VolumeStrategy
from .macd import MACDStrategy


class StrategyFactory:
    """策略工厂 - 创建和管理策略"""
    
    # 注册所有可用策略
    REGISTRY = {
        'momentum': MomentumStrategy,
        'breakout': BreakoutStrategy,
        'rsi': RSIStrategy,
        'ma': MAStrategy,
        'volume': VolumeStrategy,
        'macd': MACDStrategy,
    }
    
    @classmethod
    def create(cls, strategy_name: str, **params) -> BaseStrategy:
        """创建策略实例"""
        if strategy_name not in cls.REGISTRY:
            raise ValueError(f"未知策略: {strategy_name}, 可用: {list(cls.REGISTRY.keys())}")
        
        strategy_class = cls.REGISTRY[strategy_name]
        return strategy_class(**params)
    
    @classmethod
    def create_multiple(cls, strategy_names: List[str], params_dict: Dict = None) -> List[BaseStrategy]:
        """创建多个策略"""
        params_dict = params_dict or {}
        strategies = []
        
        for name in strategy_names:
            params = params_dict.get(name, {})
            strategies.append(cls.create(name, **params))
        
        return strategies
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """列出所有可用策略"""
        return list(cls.REGISTRY.keys())


class HybridStrategy:
    """混合策略 - 组合多个策略"""
    
    def __init__(self, strategies: List[BaseStrategy] = None, strategy_names: List[str] = None):
        """
        初始化混合策略
        
        Args:
            strategies: 策略实例列表
            strategy_names: 策略名称列表 (会自动创建)
        """
        if strategies:
            self.strategies = strategies
        elif strategy_names:
            self.strategies = StrategyFactory.create_multiple(strategy_names)
        else:
            raise ValueError("需要提供 strategies 或 strategy_names")
    
    def analyze(self, df) -> Dict:
        """
        分析数据，返回组合信号
        
        Returns:
            {
                'signal': 1/-1/0,
                'strength': 0-1,
                'buy_score': float,
                'sell_score': float,
                'signals': [Signal, ...],
                'details': {...}
            }
        """
        buy_score = 0
        sell_score = 0
        signals = []
        
        for strategy in self.strategies:
            try:
                signal = strategy.analyze(df)
                signals.append(signal)
                
                if signal.signal == 1:
                    buy_score += signal.strength
                elif signal.signal == -1:
                    sell_score += signal.strength
                    
            except Exception as e:
                # 策略分析失败，跳过
                continue
        
        # 投票决定
        total = buy_score + sell_score
        
        if buy_score > sell_score and buy_score > total * 0.4:
            final_signal = 1
            strength = buy_score / len(self.strategies)
        elif sell_score > buy_score and sell_score > total * 0.4:
            final_signal = -1
            strength = sell_score / len(self.strategies)
        else:
            final_signal = 0
            strength = 0
        
        # 统计
        signal_count = {'buy': 0, 'sell': 0, 'hold': 0}
        for s in signals:
            if s.signal == 1:
                signal_count['buy'] += 1
            elif s.signal == -1:
                signal_count['sell'] += 1
            else:
                signal_count['hold'] += 1
        
        # 建议
        if final_signal == 1:
            if signal_count['buy'] >= len(self.strategies) * 0.6:
                recommendation = "强烈买入 ⭐⭐⭐"
            else:
                recommendation = "买入 ⭐⭐"
        elif final_signal == -1:
            if signal_count['sell'] >= len(self.strategies) * 0.6:
                recommendation = "强烈卖出 🔴🔴🔴"
            else:
                recommendation = "卖出 🔴🔴"
        else:
            recommendation = "持有 ➡️"
        
        return {
            'signal': final_signal,
            'strength': strength,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'signal_count': signal_count,
            'signals': signals,
            'recommendation': recommendation,
            'strategy_names': [s.name for s in self.strategies]
        }
    
    def get_params(self) -> Dict:
        """获取所有策略参数"""
        return {s.name: s.get_params() for s in self.strategies}


# 便捷函数
def create_hybrid(strategy_names: List[str], params: Dict = None) -> HybridStrategy:
    """创建混合策略的便捷函数"""
    return HybridStrategy(strategy_names=strategy_names)


# 预设组合
PRESETS = {
    '激进': ['momentum', 'breakout', 'volume'],  # 高风险高收益
    '稳健': ['ma', 'rsi', 'macd'],  # 低频稳定
    '平衡': ['momentum', 'ma', 'rsi', 'volume'],  # 平衡
    '全部': ['momentum', 'breakout', 'rsi', 'ma', 'volume', 'macd'],  # 全策略
}


def create_preset(name: str) -> HybridStrategy:
    """根据预设创建混合策略"""
    if name not in PRESETS:
        raise ValueError(f"未知预设: {name}, 可用: {list(PRESETS.keys())}")
    return HybridStrategy(strategy_names=PRESETS[name])
