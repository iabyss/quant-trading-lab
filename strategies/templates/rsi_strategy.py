"""
RSI 策略
RSI (Relative Strength Index) 策略

策略逻辑:
- RSI < 30 时超卖，可能反弹 -> 买入信号
- RSI > 70 时超买，可能回调 -> 卖出信号
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .. import FactorCalculator, SignalGenerator, SignalType, TradingSignal


class RSIStrategy:
    """RSI 策略"""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        """
        初始化策略

        Args:
            period: RSI周期
            oversold: 超卖阈值
            overbought: 超买阈值
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"RSI_{period}_{oversold}_{overbought}"

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算RSI指标"""
        df = data.copy()
        df['rsi'] = FactorCalculator.rsi(df['close'], self.period)
        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)

        # 初始化信号
        df['signal'] = SignalType.HOLD.value

        # RSI超卖 -> 买入
        oversold = df['rsi'] < self.oversold
        # 之前不在超卖区域
        prev_oversold = df['rsi'].shift(1) >= self.oversold
        df.loc[oversold & prev_oversold, 'signal'] = SignalType.BUY.value

        # RSI超买 -> 卖出
        overbought = df['rsi'] > self.overbought
        prev_overbought = df['rsi'].shift(1) <= self.overbought
        df.loc[overbought & prev_overbought, 'signal'] = SignalType.SELL.value

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
                    reason=f"RSI超卖: {row['rsi']:.2f} < {self.oversold}"
                )
                signals.append(signal)
            elif row['signal'] == SignalType.SELL.value:
                signal = TradingSignal(
                    date=str(idx.date()) if hasattr(idx, 'date') else str(idx),
                    symbol=row.get('symbol', ''),
                    signal=SignalType.SELL,
                    price=row['close'],
                    reason=f"RSI超买: {row['rsi']:.2f} > {self.overbought}"
                )
                signals.append(signal)

        return signals


class RSIDivergenceStrategy:
    """RSI背离策略"""

    def __init__(self, period: int = 14):
        self.period = period
        self.name = f"RSI_Divergence_{period}"

    def find_divergence(self, data: pd.DataFrame) -> pd.DataFrame:
        """寻找RSI背离"""
        df = data.copy()
        df['rsi'] = FactorCalculator.rsi(df['close'], self.period)

        # 价格创新高但RSI没有 -> 顶背离
        price_high = df['high'].rolling(5).max()
        rsi_high = df['rsi'].rolling(5).max()

        df['bearish_divergence'] = (df['high'] == price_high) & (df['rsi'] < rsi_high.shift(1))

        # 价格创新低但RSI没有 -> 底背离
        price_low = df['low'].rolling(5).min()
        rsi_low = df['rsi'].rolling(5).min()

        df['bullish_divergence'] = (df['low'] == price_low) & (df['rsi'] > rsi_low.shift(1))

        return df


if __name__ == "__main__":
    import yfinance as yf

    # 测试
    data = yf.download("AAPL", period="1y", auto_adjust=True)
    data.reset_index(inplace=True)
    data.columns = [col.lower() for col in data.columns]
    data['symbol'] = 'AAPL'

    strategy = RSIStrategy()
    signals = strategy.get_trading_signals(data)

    print(f"策略: {strategy.name}")
    print(f"买入: {sum(1 for s in signals if s.signal == SignalType.BUY)}")
    print(f"卖出: {sum(1 for s in signals if s.signal == SignalType.SELL)}")
