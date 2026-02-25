"""
多策略组合系统
整合多种短期策略，根据市场状态自适应选择最优策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class StrategyResult:
    """策略结果"""
    name: str
    signal: int  # 1=buy, -1=sell, 0=hold
    strength: float  # 信号强度 0-1
    price: float
    reason: str


class MomentumStrategy:
    """动量策略 - 追涨杀跌"""
    
    def __init__(self, period: int = 5, threshold: float = 0.03):
        self.period = period
        self.threshold = threshold
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        close = df['close']
        
        # 动量指标：N日涨幅
        momentum = (close.iloc[-1] - close.iloc[-self.period]) / close.iloc[-self.period]
        
        if momentum > self.threshold:
            return StrategyResult(
                name="动量策略",
                signal=1,
                strength=min(momentum * 5, 1.0),
                price=close.iloc[-1],
                reason=f"动量 {momentum*100:.1f}% 超过阈值 {self.threshold*100}%"
            )
        elif momentum < -self.threshold:
            return StrategyResult(
                name="动量策略",
                signal=-1,
                strength=min(abs(momentum) * 5, 1.0),
                price=close.iloc[-1],
                reason=f"下跌动量 {momentum*100:.1f}%"
            )
        
        return StrategyResult(
            name="动量策略",
            signal=0,
            strength=0,
            price=close.iloc[-1],
            reason="动量中性"
        )


class BreakoutStrategy:
    """突破策略 - 20日高点突破"""
    
    def __init__(self, period: int = 20, atr_multiplier: float = 1.5):
        self.period = period
        self.atr_multiplier = atr_multiplier
    
    def _calc_atr(self, df: pd.DataFrame) -> float:
        """计算ATR"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.iloc[-self.period:].mean()
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        close = df['close']
        high = df['high']
        
        # 20日高点
        highest = high.iloc[-self.period:].max()
        current_price = close.iloc[-1]
        
        # ATR
        atr = self._calc_atr(df)
        
        # 突破判断
        if current_price > highest:
            breakout_strength = (current_price - highest) / atr if atr > 0 else 0
            return StrategyResult(
                name="突破策略",
                signal=1,
                strength=min(breakout_strength / 2, 1.0),
                price=current_price,
                reason=f"突破20日高点 {highest:.2f}"
            )
        elif current_price < highest * 0.95:
            return StrategyResult(
                name="突破策略",
                signal=-1,
                strength=0.5,
                price=current_price,
                reason="跌破20日高点支撑"
            )
        
        return StrategyResult(
            name="突破策略",
            signal=0,
            strength=0,
            price=current_price,
            reason="震荡整理"
        )


class RSIReversalStrategy:
    """RSI反转策略 - 超卖买入"""
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        close = df['close']
        
        # 计算RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_value = rsi.iloc[-1]
        
        if rsi_value < self.oversold:
            # 超卖，可能反转
            strength = (self.oversold - rsi_value) / self.oversold
            return StrategyResult(
                name="RSI反转",
                signal=1,
                strength=strength,
                price=close.iloc[-1],
                reason=f"RSI {rsi_value:.1f} 超卖"
            )
        elif rsi_value > self.overbought:
            # 超买，可能反转
            strength = (rsi_value - self.overbought) / (100 - self.overbought)
            return StrategyResult(
                name="RSI反转",
                signal=-1,
                strength=strength,
                price=close.iloc[-1],
                reason=f"RSI {rsi_value:.1f} 超买"
            )
        
        return StrategyResult(
            name="RSI反转",
            signal=0,
            strength=0,
            price=close.iloc[-1],
            reason=f"RSI {rsi_value:.1f} 中性"
        )


class MA排列Strategy:
    """均线多头排列策略"""
    
    def __init__(self, periods: List[int] = None):
        self.periods = periods or [5, 10, 20, 60]
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        close = df['close']
        
        mas = {p: close.rolling(window=p).mean().iloc[-1] for p in self.periods}
        
        # 多头排列：短期均线 > 长期均线
        if all(mas[self.periods[i]] > mas[self.periods[i+1]] for i in range(len(self.periods)-1)):
            # 计算强度
            avg_slope = np.mean([(mas[self.periods[i]] - mas[self.periods[i+1]])/mas[self.periods[i+1]] 
                               for i in range(len(self.periods)-1)])
            return StrategyResult(
                name="均线多头",
                signal=1,
                strength=min(avg_slope * 10, 1.0),
                price=close.iloc[-1],
                reason="均线多头排列"
            )
        
        # 空头排列
        elif all(mas[self.periods[i]] < mas[self.periods[i+1]] for i in range(len(self.periods)-1)):
            return StrategyResult(
                name="均线多头",
                signal=-1,
                strength=0.8,
                price=close.iloc[-1],
                reason="均线空头排列"
            )
        
        return StrategyResult(
            name="均线多头",
            signal=0,
            strength=0,
            price=close.iloc[-1],
            reason="均线纠缠"
        )


class VolumeBreakoutStrategy:
    """成交量突破策略"""
    
    def __init__(self, period: int = 20, volume_multiplier: float = 1.5):
        self.period = period
        self.volume_multiplier = volume_multiplier
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        close = df['close']
        volume = df['volume']
        
        # 成交量均线
        vol_ma = volume.iloc[-self.period:].mean()
        current_vol = volume.iloc[-1]
        
        # 价格变化
        price_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        
        # 放量上涨
        if current_vol > vol_ma * self.volume_multiplier and price_change > 0.01:
            return StrategyResult(
                name="成交量突破",
                signal=1,
                strength=min((current_vol / vol_ma - 1) * 2, 1.0),
                price=close.iloc[-1],
                reason=f"放量上涨 {current_vol/vol_ma:.1f}倍"
            )
        # 放量下跌
        elif current_vol > vol_ma * self.volume_multiplier and price_change < -0.01:
            return StrategyResult(
                name="成交量突破",
                signal=-1,
                strength=min((current_vol / vol_ma - 1) * 2, 1.0),
                price=close.iloc[-1],
                reason=f"放量下跌 {current_vol/vol_ma:.1f}倍"
            )
        
        return StrategyResult(
            name="成交量突破",
            signal=0,
            strength=0,
            price=close.iloc[-1],
            reason="成交量正常"
        )


class VWAPStrategy:
    """VWAP策略 - 均价突破"""
    
    def __init__(self, period: int = 1):
        self.period = period
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        """分析"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window=len(df)).sum() / df['volume'].sum()
        
        current_price = df['close'].iloc[-1]
        
        # 突破VWAP
        if current_price > vwap * 1.01:
            return StrategyResult(
                name="VWAP策略",
                signal=1,
                strength=0.7,
                price=current_price,
                reason="价格在VWAP上方"
            )
        elif current_price < vwap * 0.99:
            return StrategyResult(
                name="VWAP策略",
                signal=-1,
                strength=0.7,
                price=current_price,
                reason="价格在VWAP下方"
            )
        
        return StrategyResult(
            name="VWAP策略",
            signal=0,
            strength=0,
            price=current_price,
            reason="价格在VWAP附近"
        )


class CombinedStrategy:
    """组合策略 - 多策略投票"""
    
    def __init__(self):
        self.strategies = [
            MomentumStrategy(period=5, threshold=0.02),
            BreakoutStrategy(period=20),
            RSIReversalStrategy(period=14, oversold=35, overbought=65),
            MA排列Strategy(periods=[5, 10, 20]),
            VolumeBreakoutStrategy(period=20, volume_multiplier=1.5),
            VWAPStrategy(),
        ]
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """综合分析"""
        results = []
        buy_score = 0
        sell_score = 0
        
        for strategy in self.strategies:
            try:
                result = strategy.analyze(df)
                results.append(result)
                
                if result.signal == 1:
                    buy_score += result.strength
                elif result.signal == -1:
                    sell_score += result.strength
            except Exception as e:
                continue
        
        total = buy_score + sell_score
        
        # 多策略投票
        if buy_score > sell_score and buy_score > total * 0.4:
            final_signal = 1
            strength = buy_score / len(self.strategies)
        elif sell_score > buy_score and sell_score > total * 0.4:
            final_signal = -1
            strength = sell_score / len(self.strategies)
        else:
            final_signal = 0
            strength = 0
        
        # 统计各策略信号
        signal_count = {'buy': 0, 'sell': 0, 'hold': 0}
        for r in results:
            if r.signal == 1:
                signal_count['buy'] += 1
            elif r.signal == -1:
                signal_count['sell'] += 1
            else:
                signal_count['hold'] += 1
        
        return {
            'final_signal': final_signal,
            'strength': strength,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'signal_count': signal_count,
            'results': results,
            'price': df['close'].iloc[-1]
        }
    
    def get_recommendation(self, combined_result: Dict) -> str:
        """获取建议"""
        signal = combined_result['final_signal']
        strength = combined_result['strength']
        count = combined_result['signal_count']
        
        if signal == 1:
            if count['buy'] >= 4:
                return "强烈买入 ⭐⭐⭐"
            elif count['buy'] >= 3:
                return "买入 ⭐⭐"
            else:
                return "轻仓买入 ⭐"
        elif signal == -1:
            if count['sell'] >= 4:
                return "强烈卖出 🔴🔴🔴"
            elif count['sell'] >= 3:
                return "卖出 🔴🔴"
            else:
                return "轻仓卖出 🔴"
        
        return "持有 ➡️"


# 快速调用函数
def analyze_stock(df: pd.DataFrame) -> Dict:
    """分析股票"""
    strategy = CombinedStrategy()
    result = strategy.analyze(df)
    result['recommendation'] = strategy.get_recommendation(result)
    return result
