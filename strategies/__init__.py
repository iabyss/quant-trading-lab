"""
策略引擎核心模块
提供因子计算、信号生成、策略评估等核心功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = 1
    SELL = -1
    HOLD = 0


class PositionType(Enum):
    """持仓类型"""
    LONG = 1
    SHORT = -1
    CASH = 0


@dataclass
class TradingSignal:
    """交易信号"""
    date: str
    symbol: str
    signal: SignalType
    price: float
    quantity: int = 0
    reason: str = ""
    confidence: float = 1.0  # 置信度 0-1


@dataclass
class StrategyResult:
    """策略结果"""
    symbol: str
    strategy_name: str
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    signals: List[TradingSignal]


class FactorCalculator:
    """技术因子计算器"""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指数"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带"""
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均趋向指数"""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = FactorCalculator.atr(high, low, close, period)
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        return dx.rolling(window=period).mean()

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """随机指标"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return k, d

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    @staticmethod
    def volume_profile(close: pd.Series, volume: pd.Series, bins: int = 20) -> Dict:
        """成交量分布"""
        df = pd.DataFrame({'close': close, 'volume': volume}).dropna()
        if df.empty:
            return {}

        hist, bin_edges = np.histogram(df['close'], bins=bins, weights=df['volume'])
        max_idx = np.argmax(hist)

        return {
            'poc': (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2,  # Point of Control
            'volume_area': sum(hist[hist > np.mean(hist)]),  # Volume Area
            'total_volume': df['volume'].sum()
        }


class SignalGenerator:
    """信号生成器"""

    @staticmethod
    def golden_cross(df: pd.DataFrame, short_col: str = 'sma_short', long_col: str = 'sma_long') -> pd.Series:
        """黄金交叉 - 短期上穿长期"""
        return (df[short_col] > df[long_col]) & (df[short_col].shift(1) <= df[long_col].shift(1))

    @staticmethod
    def death_cross(df: pd.DataFrame, short_col: str = 'sma_short', long_col: str = 'sma_long') -> pd.Series:
        """死亡交叉 - 短期下穿长期"""
        return (df[short_col] < df[long_col]) & (df[short_col].shift(1) >= df[long_col].shift(1))

    @staticmethod
    def rsi_overbought(df: pd.Series, threshold: float = 70) -> pd.Series:
        """RSI超买"""
        return df > threshold

    @staticmethod
    def rsi_oversold(df: pd.Series, threshold: float = 30) -> pd.Series:
        """RSI超卖"""
        return df < threshold

    @staticmethod
    def macd_cross(df: pd.DataFrame, macd_col: str = 'macd', signal_col: str = 'macd_signal') -> pd.Series:
        """MACD金叉/死叉"""
        golden = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
        death = (df[macd_col] < df[signal_col]) & (df[macd_col].shift(1) >= df[signal_col].shift(1))
        return golden, death

    @staticmethod
    def breakout(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """价格突破"""
        high = df['high'].rolling(window=period).max()
        return df['close'] > high.shift(1)

    @staticmethod
    def support_break(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """支撑跌破"""
        low = df['low'].rolling(window=period).min()
        return df['close'] < low.shift(1)


class StrategyEvaluator:
    """策略评估器"""

    @staticmethod
    def calculate_returns(prices: pd.Series) -> pd.Series:
        """计算收益率"""
        return prices.pct_change()

    @staticmethod
    def calculate_cumulative_returns(prices: pd.Series) -> pd.Series:
        """计算累计收益"""
        return (1 + prices.pct_change()).cumprod() - 1

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """夏普比率"""
        excess_returns = returns - risk_free_rate / 252
        if returns.std() == 0:
            return 0
        return np.sqrt(252) * excess_returns.mean() / returns.std()

    @staticmethod
    def max_drawdown(cumulative_returns: pd.Series) -> float:
        """最大回撤"""
        rolling_max = cumulative_returns.cummax()
        drawdown = cumulative_returns - rolling_max
        return drawdown.min()

    @staticmethod
    def calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
        """卡玛比率"""
        annualized = returns.mean() * 252
        if max_drawdown == 0:
            return 0
        return annualized / abs(max_drawdown)

    @staticmethod
    def win_rate(trades: List[Dict]) -> float:
        """胜率"""
        if not trades:
            return 0
        winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return winning / len(trades)

    @staticmethod
    def profit_factor(trades: List[Dict]) -> float:
        """盈利因子"""
        if not trades:
            return 0
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        return gross_profit / gross_loss

    @staticmethod
    def evaluate_strategy(data: pd.DataFrame, signals: pd.Series, initial_capital: float = 10000) -> Dict:
        """综合评估策略表现"""
        # 计算持仓
        position = signals.shift(1).fillna(0)

        # 计算收益
        returns = data['close'].pct_change()
        strategy_returns = returns * position

        # 累计收益
        cumulative = (1 + strategy_returns).cumprod()
        market_cumulative = (1 + returns).cumprod()

        # 计算指标
        result = {
            'total_return': (cumulative.iloc[-1] - 1) if len(cumulative) > 0 else 0,
            'annualized_return': cumulative.iloc[-1] ** (252 / len(cumulative)) - 1 if len(cumulative) > 0 else 0,
            'sharpe_ratio': StrategyEvaluator.sharpe_ratio(strategy_returns.dropna()),
            'max_drawdown': StrategyEvaluator.max_drawdown(cumulative),
            'win_rate': StrategyEvaluator.win_rate([]),  # 需要成交记录
            'trade_count': (signals.diff().abs() > 0).sum(),
            'market_return': (market_cumulative.iloc[-1] - 1) if len(market_cumulative) > 0 else 0,
            'alpha': (cumulative.iloc[-1] - market_cumulative.iloc[-1]) if len(cumulative) > 0 else 0
        }

        return result


# 导出
__all__ = [
    'SignalType',
    'PositionType',
    'TradingSignal',
    'StrategyResult',
    'FactorCalculator',
    'SignalGenerator',
    'StrategyEvaluator'
]
