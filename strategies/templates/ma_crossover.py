"""
移动平均线交叉策略
MA Crossover Strategy

策略逻辑:
- 当短期MA上穿长期MA时买入(黄金交叉)
- 当短期MA下穿长期MA时卖出(死亡交叉)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .. import FactorCalculator, SignalGenerator, SignalType, TradingSignal


class MACrossoverStrategy:
    """移动平均线交叉策略"""

    def __init__(self, short_period: int = 20, long_period: int = 50):
        """
        初始化策略

        Args:
            short_period: 短期MA周期
            long_period: 长期MA周期
        """
        self.short_period = short_period
        self.long_period = long_period
        self.name = f"MA_Cross_{short_period}_{long_period}"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()

        # 计算移动平均线
        df['sma_short'] = FactorCalculator.sma(df['close'], self.short_period)
        df['sma_long'] = FactorCalculator.sma(df['close'], self.long_period)

        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            data: 包含OHLCV数据的DataFrame

        Returns:
            带有信号的DataFrame
        """
        df = self.calculate_indicators(data)

        # 初始化信号列
        df['signal'] = SignalType.HOLD.value

        # 黄金交叉 - 买入信号
        golden = SignalGenerator.golden_cross(df, 'sma_short', 'sma_long')
        df.loc[golden, 'signal'] = SignalType.BUY.value

        # 死亡交叉 - 卖出信号
        death = SignalGenerator.death_cross(df, 'sma_short', 'sma_long')
        df.loc[death, 'signal'] = SignalType.SELL.value

        # 去除NaN
        df = df.dropna()

        return df

    def get_trading_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
        """获取交易信号列表"""
        df = self.generate_signals(data)

        signals = []
        for idx, row in df.iterrows():
            # 处理索引类型
            if hasattr(idx, 'date'):
                date_str = str(idx.date())
            else:
                date_str = str(idx)

            if row['signal'] == SignalType.BUY.value:
                signal = TradingSignal(
                    date=date_str,
                    symbol=row.get('symbol', ''),
                    signal=SignalType.BUY,
                    price=row['close'],
                    reason=f"黄金交叉: MA{self.short_period}={row['sma_short']:.2f} > MA{self.long_period}={row['sma_long']:.2f}"
                )
                signals.append(signal)
            elif row['signal'] == SignalType.SELL.value:
                signal = TradingSignal(
                    date=date_str,
                    symbol=row.get('symbol', ''),
                    signal=SignalType.SELL,
                    price=row['close'],
                    reason=f"死亡交叉: MA{self.short_period}={row['sma_short']:.2f} < MA{self.long_period}={row['sma_long']:.2f}"
                )
                signals.append(signal)

        return signals


class DualMACrossStrategy:
    """双MA交叉策略 (可配置多组MA)"""

    def __init__(self, ma_pairs: List[tuple] = None):
        """
        Args:
            ma_pairs: MA周期对列表，如 [(5, 20), (10, 50)]
        """
        self.ma_pairs = ma_pairs or [(20, 50)]
        self.strategies = [MACrossoverStrategy(short, long) for short, long in self.ma_pairs]

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """多组MA信号合成"""
        all_signals = []

        for strategy in self.strategies:
            df = strategy.generate_signals(data)
            all_signals.append(df['signal'])

        # 多数投票
        combined = pd.concat(all_signals, axis=1)
        df['combined_signal'] = combined.mode(axis=1)[0]

        return df


# 示例运行
if __name__ == "__main__":
    import yfinance as yf

    # 获取数据
    data = yf.download("AAPL", period="2y", auto_adjust=True)
    data.reset_index(inplace=True)
    data.columns = [col.lower() for col in data.columns]
    data['symbol'] = 'AAPL'

    # 运行策略
    strategy = MACrossoverStrategy(short_period=20, long_period=50)
    df = strategy.generate_signals(data)

    # 打印信号
    signals = strategy.get_trading_signals(data)
    print(f"策略: {strategy.name}")
    print(f"总信号数: {len(signals)}")

    buy_signals = [s for s in signals if s.signal == SignalType.BUY]
    sell_signals = [s for s in signals if s.signal == SignalType.SELL]

    print(f"买入信号: {len(buy_signals)}")
    print(f"卖出信号: {len(sell_signals)}")
