"""
动量策略
Momentum Strategy

策略逻辑:
- 价格动量: 上涨趋势中买入，下跌趋势中卖出
- 使用MACD判断趋势方向
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .. import FactorCalculator, SignalGenerator, SignalType, TradingSignal


class MomentumStrategy:
    """动量策略"""

    def __init__(self, lookback: int = 20, threshold: float = 0.05):
        """
        初始化策略

        Args:
            lookback: 回看周期
            threshold: 动量阈值 (5% = 0.05)
        """
        self.lookback = lookback
        self.threshold = threshold
        self.name = f"Momentum_{lookback}_{threshold}"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算动量指标"""
        df = data.copy()

        # 价格动量
        df['momentum'] = df['close'].pct_change(self.lookback)

        # 趋势确认 (MA20)
        df['sma20'] = FactorCalculator.sma(df['close'], 20)
        df['trend'] = np.where(df['close'] > df['sma20'], 1, -1)

        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)

        # 初始化信号
        df['signal'] = SignalType.HOLD.value

        # 动量 positive + 上升趋势 -> 买入
        buy_condition = (df['momentum'] > self.threshold) & (df['trend'] == 1)
        df.loc[buy_condition, 'signal'] = SignalType.BUY.value

        # 动量 negative + 下降趋势 -> 卖出
        sell_condition = (df['momentum'] < -self.threshold) & (df['trend'] == -1)
        df.loc[sell_condition, 'signal'] = SignalType.SELL.value

        df = df.dropna()
        return df

    def get_trading_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """获取交易信号列表"""
        df = self.generate_signals(data)

        signals = []
        for idx, row in df.iterrows():
            if row['signal'] == SignalType.BUY.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.BUY,
                    price=row['close'],
                    reason=f"动量: {row['momentum']*100:.2f}%, 趋势: {'上升' if row['trend'] == 1 else '下降'}"
                )
                signals.append(signal)
            elif row['signal'] == SignalType.SELL.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.SELL,
                    price=row['close'],
                    reason=f"动量: {row['momentum']*100:.2f}%, 趋势: {'上升' if row['trend'] == 1 else '下降'}"
                )
                signals.append(signal)

        return signals


class MACDStrategy:
    """MACD策略"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.name = f"MACD_{fast}_{slow}_{signal}"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算MACD指标"""
        df = data.copy()

        macd, signal_line, histogram = FactorCalculator.macd(
            df['close'], self.fast, self.slow, self.signal
        )

        df['macd'] = macd
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram

        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)

        df['signal'] = SignalType.HOLD.value

        # MACD金叉 -> 买入
        golden = SignalGenerator.macd_cross(df, 'macd', 'macd_signal')[0]
        df.loc[golden, 'signal'] = SignalType.BUY.value

        # MACD死叉 -> 卖出
        death = SignalGenerator.macd_cross(df, 'macd', 'macd_signal')[1]
        df.loc[death, 'signal'] = SignalType.SELL.value

        df = df.dropna()
        return df

    def get_trading_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """获取交易信号列表"""
        df = self.generate_signals(data)

        signals = []
        for idx, row in df.iterrows():
            if row['signal'] == SignalType.BUY.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.BUY,
                    price=row['close'],
                    reason=f"MACD金叉: MACD={row['macd']:.4f} > Signal={row['macd_signal']:.4f}"
                )
                signals.append(signal)
            elif row['signal'] == SignalType.SELL.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.SELL,
                    price=row['close'],
                    reason=f"MACD死叉: MACD={row['macd']:.4f} < Signal={row['macd_signal']:.4f}"
                )
                signals.append(signal)

        return signals


class BreakoutStrategy:
    """突破策略"""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.name = f"Breakout_{lookback}"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        df['signal'] = SignalType.HOLD.value

        # 价格突破20日高点 -> 买入
        breakout = SignalGenerator.breakout(df, self.lookback)
        df.loc[breakout, 'signal'] = SignalType.BUY.value

        # 价格跌破20日低点 -> 卖出
        support_break = SignalGenerator.support_break(df, self.lookback)
        df.loc[support_break, 'signal'] = SignalType.SELL.value

        df = df.dropna()
        return df

    def get_trading_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """获取交易信号列表"""
        df = self.generate_signals(data)

        signals = []
        for idx, row in df.iterrows():
            if row['signal'] == SignalType.BUY.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.BUY,
                    price=row['close'],
                    reason=f"突破{self.lookback}日高点"
                )
                signals.append(signal)
            elif row['signal'] == SignalType.SELL.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.SELL,
                    price=row['close'],
                    reason=f"跌破{self.lookback}日低点"
                )
                signals.append(signal)

        return signals


if __name__ == "__main__":
    import yfinance as yf

    # 测试
    data = yf.download("AAPL", period="2y", auto_adjust=True)
    data.reset_index(inplace=True)
    data.columns = [col.lower() for col in data.columns]
    data['symbol'] = 'AAPL'

    # 测试动量策略
    strategy = MomentumStrategy()
    signals = strategy.get_trading_signals(data)
    print(f"策略: {strategy.name}")
    print(f"买入: {sum(1 for s in signals if s.signal == SignalType.BUY)}")
    print(f"卖出: {sum(1 for s in signals if s.signal == SignalType.SELL)}")
