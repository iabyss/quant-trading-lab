"""
信号生成模块
基于技术指标产生交易信号
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = 1
    SELL = -1
    HOLD = 0
    STRONG_BUY = 2
    STRONG_SELL = -2


class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, data: pd.DataFrame):
        """
        初始化信号生成器
        
        Args:
            data: 包含 OHLCV 的 DataFrame
        """
        self.data = data.copy()
        self.signals = pd.Series(0, index=data.index)
    
    def ma_crossover_signal(self, fast_period: int = 5, slow_period: int = 20) -> pd.Series:
        """
        均线交叉信号
        
        Args:
            fast_period: 快速均线周期
            slow_period: 慢速均线周期
        
        Returns:
            信号序列
        """
        fast_ma = self.data['close'].rolling(window=fast_period).mean()
        slow_ma = self.data['close'].rolling(window=slow_period).mean()
        
        # 交叉信号
        signal = pd.Series(0, index=self.data.index)
        signal[fast_ma > slow_ma] = 1
        signal[fast_ma <= slow_ma] = -1
        
        # 只在变化时产生信号
        signal = signal.diff()
        signal[signal > 0] = SignalType.BUY.value
        signal[signal < 0] = SignalType.SELL.value
        signal[signal == 0] = SignalType.HOLD.value
        
        return signal
    
    def rsi_signal(self, period: int = 14, oversold: int = 30, overbought: int = 70) -> pd.Series:
        """
        RSI 信号
        
        Args:
            period: RSI周期
            oversold: 超卖阈值
            overbought: 超买阈值
        
        Returns:
            信号序列
        """
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signal = pd.Series(SignalType.HOLD.value, index=self.data.index)
        signal[rsi < oversold] = SignalType.BUY.value
        signal[rsi > overbought] = SignalType.SELL.value
        signal[rsi < oversold - 10] = SignalType.STRONG_BUY.value
        signal[rsi > overbought + 10] = SignalType.STRONG_SELL.value
        
        return signal
    
    def macd_signal(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """
        MACD 信号
        
        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        
        Returns:
            信号序列
        """
        ema_fast = self.data['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.data['close'].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        
        # MACD 金叉/死叉
        macd_hist = macd - signal_line
        signal = pd.Series(SignalType.HOLD.value, index=self.data.index)
        
        # 金叉买入，死叉卖出
        signal[(macd_hist > 0) & (macd_hist.shift(1) <= 0)] = SignalType.BUY.value
        signal[(macd_hist < 0) & (macd_hist.shift(1) >= 0)] = SignalType.SELL.value
        
        # 零轴交叉
        signal[(macd > 0) & (macd.shift(1) <= 0)] = SignalType.STRONG_BUY.value
        signal[(macd < 0) & (macd.shift(1) >= 0)] = SignalType.STRONG_SELL.value
        
        return signal
    
    def bollinger_breakout(self, period: int = 20, std_dev: float = 2) -> pd.Series:
        """
        布林带突破信号
        
        Args:
            period: 周期
            std_dev: 标准差倍数
        
        Returns:
            信号序列
        """
        ma = self.data['close'].rolling(window=period).mean()
        std = self.data['close'].rolling(window=period).std()
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        signal = pd.Series(SignalType.HOLD.value, index=self.data.index)
        
        # 突破上轨做多，跌破下轨做空
        signal[self.data['close'] > upper] = SignalType.BUY.value
        signal[self.data['close'] < lower] = SignalType.SELL.value
        signal[(self.data['close'] > ma) & (self.data['close'] < upper)] = SignalType.HOLD.value
        signal[(self.data['close'] < ma) & (self.data['close'] > lower)] = SignalType.HOLD.value
        
        return signal
    
    def double_ma_ribbon(self, periods: List[int] = None) -> pd.Series:
        """
        双均线带信号 (短期均线在长期均线上方做多)
        
        Args:
            periods: 均线周期列表
        
        Returns:
            信号序列
        """
        if periods is None:
            periods = [5, 10, 20, 60]
        
        close = self.data['close']
        mas = {p: close.rolling(window=p).mean() for p in periods}
        
        # 多头排列: 短期 > 中期 > 长期
        signal = pd.Series(0, index=self.data.index)
        
        for i in range(len(periods) - 1):
            fast = periods[i]
            slow = periods[i + 1]
            if fast in mas and slow in mas:
                signal += (mas[fast] > mas[slow]).astype(int) * (i + 1)
        
        # 归一化
        max_score = sum(range(1, len(periods)))
        signal = signal / max_score * 2 - 1  # -1 到 1
        
        return signal
    
    def volume_price_trend(self, period: int = 20) -> pd.Series:
        """
        量价趋势信号
        
        Args:
            period: 周期
        
        Returns:
            信号序列
        """
        # 价格变化率
        price_change = self.data['close'].pct_change()
        
        # 成交量变化率
        volume_change = self.data['volume'].pct_change()
        
        # 趋势确认: 价涨量增 或 价跌量减
        signal = pd.Series(SignalType.HOLD.value, index=self.data.index)
        signal[(price_change > 0) & (volume_change > 0)] = SignalType.BUY.value
        signal[(price_change < 0) & (volume_change < 0)] = SignalType.SELL.value
        
        # 放量突破
        vol_ma = self.data['volume'].rolling(window=period).mean()
        price_ma = self.data['close'].rolling(window=period).mean()
        
        signal[(self.data['volume'] > vol_ma * 1.5) & 
               (self.data['close'] > price_ma)] = SignalType.STRONG_BUY.value
        signal[(self.data['volume'] > vol_ma * 1.5) & 
               (self.data['close'] < price_ma)] = SignalType.STRONG_SELL.value
        
        return signal
    
    def combined_signal(self, weights: Dict[str, float] = None) -> pd.Series:
        """
        组合信号 (多指标加权)
        
        Args:
            weights: 各信号权重 {'ma_crossover': 0.3, 'rsi': 0.3, 'macd': 0.4}
        
        Returns:
            综合信号序列
        """
        if weights is None:
            weights = {
                'ma_crossover': 0.25,
                'rsi': 0.25,
                'macd': 0.25,
                'bollinger': 0.25
            }
        
        signals = {}
        
        if 'ma_crossover' in weights:
            signals['ma_crossover'] = self.ma_crossover_signal()
        
        if 'rsi' in weights:
            signals['rsi'] = self.rsi_signal()
        
        if 'macd' in weights:
            signals['macd'] = self.macd_signal()
        
        if 'bollinger' in weights:
            signals['bollinger'] = self.bollinger_breakout()
        
        # 加权组合
        combined = pd.Series(0.0, index=self.data.index)
        total_weight = sum(weights.values())
        
        for name, weight in weights.items():
            if name in signals:
                combined += signals[name] * (weight / total_weight)
        
        # 转换为信号
        result = pd.Series(SignalType.HOLD.value, index=self.data.index)
        result[combined > 0.3] = SignalType.BUY.value
        result[combined < -0.3] = SignalType.SELL.value
        result[combined > 0.6] = SignalType.STRONG_BUY.value
        result[combined < -0.6] = SignalType.STRONG_SELL.value
        
        return result


def generate_signals(data: pd.DataFrame, strategy: str = 'ma_crossover', 
                     params: Dict = None) -> pd.Series:
    """
    快速生成信号
    
    Args:
        data: OHLCV 数据
        strategy: 策略名称
        params: 策略参数
    
    Returns:
        信号序列
    """
    if params is None:
        params = {}
    
    generator = SignalGenerator(data)
    
    strategies = {
        'ma_crossover': lambda: generator.ma_crossover_signal(
            params.get('fast_period', 5),
            params.get('slow_period', 20)
        ),
        'rsi': lambda: generator.rsi_signal(
            params.get('period', 14),
            params.get('oversold', 30),
            params.get('overbought', 70)
        ),
        'macd': lambda: generator.macd_signal(
            params.get('fast', 12),
            params.get('slow', 26),
            params.get('signal', 9)
        ),
        'bollinger': lambda: generator.bollinger_breakout(
            params.get('period', 20),
            params.get('std_dev', 2)
        ),
        'combined': lambda: generator.combined_signal(params.get('weights'))
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return strategies[strategy]()
