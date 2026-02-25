#!/usr/bin/env python3
"""
成交量打板策略测试
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine

# 动态导入成交量策略
import importlib.util

ASTOCK = [
    ('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
    ('600887.SS','伊利股份'), ('600309.SS','万华化学'), 
]

random.seed(42)
selected = random.sample(ASTOCK, 3)

def create_strategy(name):
    """创建策略"""
    # 简化版策略定义
    strategies = {
        'volume_breakout': lambda: VolumeBreakoutStrategy(),
        'volume_surge': lambda: VolumePriceStrategy(),
        'high_volume': lambda: HighVolumeStrategy(),
        'money_wave': lambda: MoneyWaveStrategy(),
    }
    return strategies.get(name)()

# 简化版策略类
class VolumeBreakoutStrategy:
    name = "成交量突破"
    def analyze(self, df):
        from dataclasses import dataclass
        @dataclass
        class Signal:
            strategy_name: str
            signal: int
            strength: float
            reason: str
        
        volume = df['volume']
        close = df['close']
        
        vol_ma = volume.rolling(20).mean()
        if volume.iloc[-1] > vol_ma.iloc[-1] * 2 and close.iloc[-1] > close.iloc[-20]:
            return Signal(self.name, 1, 0.8, "放量突破")
        return Signal(self.name, 0, 0, "无信号")

class VolumePriceStrategy:
    name = "量价齐升"
    def analyze(self, df):
        from dataclasses import dataclass
        @dataclass
        class Signal:
            strategy_name: str
            signal: int
            strength: float
            reason: str
        
        up = 0
        for i in range(-5, 0):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                up += 1
        
        if up >= 4:
            return Signal(self.name, 1, 0.8, "连续上涨")
        return Signal(self.name, 0, 0, "无信号")

class HighVolumeStrategy:
    name = "高量能"
    def analyze(self, df):
        from dataclasses import dataclass
        @dataclass
        class Signal:
            strategy_name: str
            signal: int
            strength: float
            reason: str
        
        vol_mean = df['volume'].iloc[-20:].mean()
        if df['volume'].iloc[-1] > vol_mean * 2:
            return Signal(self.name, 1, 0.7, "量能放大")
        return Signal(self.name, 0, 0, "无信号")

class MoneyWaveStrategy:
    name = "资金波浪"
    def analyze(self, df):
        from dataclasses import dataclass
        @dataclass
        class Signal:
            strategy_name: str
            signal: int
            strength: float
            reason: str
        
        net = 0
        for i in range(-5, 0):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                net += df['volume'].iloc[i]
            else:
                net -= df['volume'].iloc[i]
        
        if net > 0:
            return Signal(self.name, 1, 0.6, "资金流入")
        return Signal(self.name, -1, 0.6, "资金流出")

def test(symbol, name, strategy, sl, tp):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 200: return None
    df.columns = df.columns.str.lower()
    
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    
    for i in range(30, len(df)):
        price = df['close'].iloc[i]
        signal = strategy.analyze(df.iloc[:i+1])
        
        if position == 0 and signal.signal == 1:
            qty = int(engine.cash / price / 100) * 100
            if qty > 0:
                engine.buy(df.index[i], symbol, price, quantity=qty)
                position, entry = 1, price
        
        elif position == 1:
            pct = (price - entry) / entry
            if pct < -sl or pct > tp:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        
        equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
        engine.equity_history.append(equity)
    
    return (engine.equity_history[-1] - 100000) / 100000 * 100 if engine.equity_history else 0

print("="*60)
print("成交量打板策略测试")
print("="*60)

strategies = [
    (VolumeBreakoutStrategy(), "成交量突破"),
    (VolumePriceStrategy(), "量价齐升"),
    (HighVolumeStrategy(), "高量能"),
    (MoneyWaveStrategy(), "资金波浪"),
]

results = []
for strategy, sname in strategies:
    print(f"\n策略: {sname} | 止损5% 止盈50%")
    print("-"*40)
    
    total = 0
    for symbol, name in selected:
        ret = test(symbol, name, strategy, 0.05, 0.50)
        if ret:
            total += ret
            print(f"  {name}: {ret:+.1f}%")
    
    avg = total / 3
    results.append((sname, avg))
    print(f"→ 平均: {avg:+.1f}%")

results.sort(key=lambda x: x[1], reverse=True)
print("\n" + "="*60)
print("🏆 排名:")
for i, (sname, avg) in enumerate(results, 1):
    print(f"{i}. {sname}: {avg:+.1f}%")
