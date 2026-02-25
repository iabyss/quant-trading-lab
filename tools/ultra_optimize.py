#!/usr/bin/env python3
"""
暴力优化 - 3年回测
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

ASTOCK = [('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
          ('600887.SS','伊利股份'), ('600309.SS','万华化学'), ('601888.SS','中国中铁'),
          ('600028.SS','中国石化'), ('600000.SS','浦发银行'), ('600030.SS','中信证券'),
          ('600016.SS','民生银行'), ('600585.SS','海螺水泥'), ('601166.SS','兴业银行')]

random.seed(123)
selected = random.sample(ASTOCK, 6)

def test(symbol, strategies, sl, tp, period):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period=period)
    if df is None or len(df) < 400: return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    for i in range(50, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        if position == 0 and result['signal'] == 1:
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
print("暴力优化 - 3年回测")
print("="*60)

tests = [
    (['rsi'], "RSI", 0.15, 0.50),
    (['rsi'], "RSI", 0.20, 0.80),
    (['rsi', 'kdj'], "双RSI", 0.15, 0.60),
    (['rsi', 'kdj'], "双RSI", 0.20, 1.00),
    (['macd'], "MACD", 0.20, 1.00),
    (['macd', 'rsi'], "MACD+RSI", 0.20, 1.00),
]

results = []
for strategies, name, sl, tp in tests:
    total, valid = 0, 0
    for symbol, sname in selected:
        ret = test(symbol, strategies, sl, tp, "3y")
        if ret is not None:
            total += ret
            valid += 1
    
    if valid > 0:
        avg = total / valid
        results.append((name, sl, tp, avg))
        print(f"{name} 止损{sl*100:.0f}% 止盈{tp*100:.0f}% → {avg:+.1f}%")

results.sort(key=lambda x: x[3], reverse=True)
print("\n🏆 最佳:")
r = results[0]
print(f"{r[0]}: 止损{r[1]*100:.0f}% 止盈{r[2]*100:.0f}% → {r[3]:+.1f}%")
