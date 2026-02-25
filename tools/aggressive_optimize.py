#!/usr/bin/env python3
"""
激进参数优化 - 目标100%
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

# 随机10只
ASTOCK = [('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
          ('600887.SS','伊利股份'), ('600309.SS','万华化学'), ('601888.SS','中国中铁'),
          ('600028.SS','中国石化'), ('600000.SS','浦发银行'), ('600030.SS','中信证券'),
          ('600016.SS','民生银行')]

random.seed(42)
selected = random.sample(ASTOCK, 5)

def test(symbol, strategies, sl, tp):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 200: return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    for i in range(30, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        # 满仓操作
        if position == 0 and result['signal'] == 1:
            qty = int(engine.cash / price / 100) * 100
            if qty > 0:
                engine.buy(df.index[i], symbol, price, quantity=qty)
                position, entry = 1, price
        
        elif position == 1:
            if price < entry * (1 - sl) or price > entry * (1 + tp):
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        
        equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
        engine.equity_history.append(equity)
    
    return (engine.equity_history[-1] - 100000) / 100000 * 100 if engine.equity_history else 0

print("="*50)
print("激进参数优化 - 目标100%")
print("="*50)

# 测试更激进参数
tests = [
    (['rsi'], "RSI", 0.15, 0.50),
    (['rsi'], "RSI", 0.20, 0.80),
    (['rsi', 'kdj'], "RSI+KDJ", 0.15, 0.50),
    (['rsi', 'kdj'], "RSI+KDJ", 0.20, 0.80),
    (['rsi', 'kdj'], "RSI+KDJ", 0.25, 1.00),
    (['macd'], "MACD", 0.20, 0.80),
    (['macd', 'rsi'], "MACD+RSI", 0.20, 1.00),
    (['momentum'], "动量", 0.20, 1.00),
    (['rsi', 'kdj', 'wr'], "超短", 0.15, 0.60),
    (['rsi', 'kdj', 'wr'], "超短", 0.20, 1.00),
]

results = []
for strategies, name, sl, tp in tests:
    total, valid = 0, 0
    for symbol, sname in selected:
        ret = test(symbol, strategies, sl, tp)
        if ret is not None:
            total += ret
            valid += 1
    
    if valid > 0:
        avg = total / valid
        results.append((name, strategies, sl, tp, avg))
        print(f"{name} 止损{sl*100:.0f}% 止盈{tp*100:.0f}% → {avg:+.1f}%")

results.sort(key=lambda x: x[4], reverse=True)
print("\n🏆 Top 3:")
for r in results[:3]:
    print(f"  {r[0]}: 止损{r[2]*100:.0f}% 止盈{r[3]*100:.0f}% → {r[4]:+.1f}%")
