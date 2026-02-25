#!/usr/bin/env python3
"""
快速策略优化
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

ASTOCK = [('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
          ('600887.SS','伊利股份'), ('600309.SS','万华化学')]

def test(symbol, strategies, stop_loss, take_profit):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 200:
        return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=300000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    for i in range(50, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        if position == 0 and result['signal'] == 1 and result['strength'] >= 0.3:
            qty = int(engine.cash * 0.8 / price / 100) * 100
            if qty > 0:
                engine.buy(df.index[i], symbol, price, quantity=qty)
                position, entry = 1, price
        elif position == 1:
            if price < entry * (1 - stop_loss) or price > entry * (1 + take_profit):
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
        engine.equity_history.append(equity)
    
    return (engine.equity_history[-1] - 300000) / 300000 * 100 if engine.equity_history else 0

# 快速测试
print("="*50)
print("快速策略优化测试")
print("="*50)

combos = [
    (['rsi'], "RSI单策略", 0.10, 0.30),
    (['rsi', 'kdj'], "RSI+KDJ", 0.08, 0.25),
    (['rsi', 'kdj'], "RSI+KDJ", 0.10, 0.40),
    (['rsi', 'kdj', 'wr'], "RSI+KDJ+WR", 0.08, 0.30),
    (['macd', 'rsi'], "MACD+RSI", 0.10, 0.35),
    (['momentum'], "动量", 0.10, 0.50),
    (['breakout'], "突破", 0.10, 0.50),
    (['rsi', 'kdj', 'volume'], "三剑客", 0.08, 0.35),
    (['rsi', 'macd', 'volume'], "强势", 0.10, 0.40),
]

results = []
for strategies, name, sl, tp in combos:
    total = 0
    for symbol, _ in ASTOCK:
        ret = test(symbol, strategies, sl, tp)
        if ret: total += ret
    avg = total / len(ASTOCK)
    results.append((name, strategies, sl, tp, avg))
    print(f"{name} 止损{sl*100:.0f}% 止盈{tp*100:.0f}% → {avg:+.1f}%")

results.sort(key=lambda x: x[4], reverse=True)
print("\n🏆 最佳:")
for r in results[:3]:
    print(f"  {r[0]}: {r[4]:+.1f}%")
