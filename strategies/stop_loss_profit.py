#!/usr/bin/env python3
"""
止盈止损策略模块
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class TradeRule:
    """交易规则"""
    should_sell: bool
    reason: str


class StopLossStrategy:
    """止盈止损策略基类"""
    
    def __init__(self, default_stop_loss: float = 0.05):
        """
        初始化
        
        Args:
            default_stop_loss: 默认止损比例 (0.05 = 5%)
        """
        self.default_stop_loss = default_stop_loss
    
    def should_sell(self, current_price: float, entry_price: float, 
                   peak_price: float = None) -> TradeRule:
        """
        判断是否卖出
        
        Args:
            current_price: 当前价格
            entry_price: 买入价格
            peak_price: 持仓期间最高价
        
        Returns:
            TradeRule(should_sell, reason)
        """
        raise NotImplementedError


class DefaultStopLoss(StopLossStrategy):
    """默认止损 - 固定百分比止损"""
    
    def __init__(self, stop_loss: float = 0.05):
        super().__init__(stop_loss)
        self.stop_loss = stop_loss
    
    def should_sell(self, current_price: float, entry_price: float,
                   peak_price: float = None) -> TradeRule:
        pct = (current_price - entry_price) / entry_price
        
        if pct < -self.stop_loss:
            return TradeRule(True, f"止损-{self.stop_loss*100:.0f}%")
        
        return TradeRule(False, "")


class BreakevenStopLoss(StopLossStrategy):
    """
    保本止损策略
    
    规则：
    1. 默认止损 5%
    2. 盈利后不允许亏钱，否则立刻卖出
    """
    
    def __init__(self, stop_loss: float = 0.05):
        super().__init__(stop_loss)
        self.stop_loss = stop_loss
    
    def should_sell(self, current_price: float, entry_price: float,
                   peak_price: float = None) -> TradeRule:
        pct = (current_price - entry_price) / entry_price
        
        # 1. 默认止损
        if pct < -self.stop_loss:
            return TradeRule(True, f"止损-{self.stop_loss*100:.0f}%")
        
        # 2. 盈利后不允许亏钱 (保本)
        # 如果曾经盈利超过2%，现在回到成本价就卖出
        if peak_price and entry_price:
            peak_pct = (peak_price - entry_price) / entry_price
            if peak_pct > 0.02 and pct <= 0:
                return TradeRule(True, "保本")
        
        return TradeRule(False, "")


class DynamicTakeProfit(StopLossStrategy):
    """
    动态止盈 + 保本止损策略
    
    规则：
    1. 默认止损 5%
    2. 盈利后不允许亏钱
    3. 动态止盈：盈利>6%后，回撤50%止盈
    """
    
    def __init__(self, stop_loss: float = 0.05, 
                 min_profit: float = 0.06,
                 drawdown: float = 0.50):
        """
        初始化
        
        Args:
            stop_loss: 默认止损比例 (0.05 = 5%)
            min_profit: 动态止盈最小盈利要求 (0.06 = 6%)
            drawdown: 回撤止盈比例 (0.50 = 50%)
        """
        super().__init__(stop_loss)
        self.stop_loss = stop_loss
        self.min_profit = min_profit
        self.drawdown = drawdown
    
    def should_sell(self, current_price: float, entry_price: float,
                   peak_price: float = None) -> TradeRule:
        pct = (current_price - entry_price) / entry_price
        
        # 1. 默认止损
        if pct < -self.stop_loss:
            return TradeRule(True, f"止损-{self.stop_loss*100:.0f}%")
        
        # 2. 盈利后不允许亏钱 (保本)
        if peak_price and entry_price:
            peak_pct = (peak_price - entry_price) / entry_price
            if peak_pct > 0.02 and pct <= 0:
                return TradeRule(True, "保本")
        
        # 3. 动态止盈：盈利>6%后，回撤50%止盈
        if peak_price and entry_price:
            peak_pct = (peak_price - entry_price) / entry_price
            
            # 盈利超过最小要求
            if peak_pct > self.min_profit:
                # 计算回撤
                drawdown_pct = (peak_price - current_price) / peak_price
                
                # 回撤超过设定值
                if drawdown_pct > self.drawdown:
                    return TradeRule(True, f"动态止盈(回撤{drawdown_pct*100:.0f}%)")
        
        return TradeRule(False, "")


class AggressiveStrategy(DynamicTakeProfit):
    """
    激进策略 - 更高止盈
    
    在DynamicTakeProfit基础上，盈利>10%后回撤30%止盈
    """
    
    def __init__(self, stop_loss: float = 0.05):
        super().__init__(stop_loss, min_profit=0.10, drawdown=0.30)


class ConservativeStrategy(DynamicTakeProfit):
    """
    保守策略 - 更早止盈
    
    盈利>5%后回撤20%止盈
    """
    
    def __init__(self, stop_loss: float = 0.05):
        super().__init__(stop_loss, min_profit=0.05, drawdown=0.20)


# 预设策略
PRESETS = {
    'default': DynamicTakeProfit,  # 默认：动态止盈
    'breakeven': BreakevenStopLoss,  # 保本
    'aggressive': AggressiveStrategy,  # 激进
    'conservative': ConservativeStrategy,  # 保守
    'fixed': DefaultStopLoss,  # 固定止损
}


def get_strategy(name: str = 'default', **kwargs) -> StopLossStrategy:
    """
    获取止盈止损策略
    
    Args:
        name: 策略名称 ('default', 'breakeven', 'aggressive', 'conservative', 'fixed')
        **kwargs: 策略参数
    
    Returns:
        StopLossStrategy实例
    """
    if name not in PRESETS:
        raise ValueError(f"未知策略: {name}, 可用: {list(PRESETS.keys())}")
    
    return PRESETS[name](**kwargs)


# 测试
if __name__ == "__main__":
    # 测试默认策略
    print("="*50)
    print("止盈止损策略测试")
    print("="*50)
    
    # 场景1: 亏损超过5%
    strategy = get_strategy('default')
    result = should_sell = strategy.should_sell(95, 100, 100)
    print(f"\n场景1: 亏损6%")
    print(f"  价格: 95, 成本: 100")
    print(f"  卖出: {result.should_sell}, 原因: {result.reason}")
    
    # 场景2: 盈利后回到成本价
    result = strategy.should_sell(100, 100, 110)
    print(f"\n场景2: 盈利后回到成本价")
    print(f"  价格: 100, 成本: 100, 最高: 110")
    print(f"  卖出: {result.should_sell}, 原因: {result.reason}")
    
    # 场景3: 盈利>6%后回撤50%
    result = strategy.should_sell(108, 100, 120)
    print(f"\n场景3: 盈利8%后回撤50%")
    print(f"  价格: 108, 成本: 100, 最高: 120")
    print(f"  卖出: {result.should_sell}, 原因: {result.reason}")
    
    # 场景4: 盈利5%，未到止盈点
    result = strategy.should_sell(104, 100, 105)
    print(f"\n场景4: 盈利5%，未到止盈点")
    print(f"  价格: 104, 成本: 100, 最高: 105")
    print(f"  卖出: {result.should_sell}, 原因: {result.reason}")
