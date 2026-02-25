#!/usr/bin/env python3
"""
小盘股暴力测试 - all in策略
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

ASTOCK = [
    ('300033.SZ','同花顺'), ('300015.SZ','爱尔眼科'), ('300003.SZ','乐普医疗'),
    ('300122.SZ','智飞生物'), ('300014.SZ','亿纬锂能'), 
]

random.seed(99)
selected = random.sample(ASTOCK, 3)

def test(symbol, name, strategies, sl, tp):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 150: return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    for i in range(20, len(df)):
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

print("="*50)
print("小盘股ALL IN测试")
print("="*50)

# 暴力参数
tests = [
    (['rsi'], 0.20, 2.0),   # 止损20%, 止盈200%
    (['rsi'], 0.25, 3.0),   # 止损25%, 止盈300%
    (['macd'], 0.20, 2.0),
    (['macd'], 0.25, 3.0),
    (['rsi', 'kdj'], 0.20, 2.0),
]

for strategies, sl, tp in tests:
    total, valid = 0, 0
    for symbol, name in selected:
        ret = test(symbol, name, strategies, sl, tp)
        if ret is not None:
            total += ret
            valid += 1
            print(f"  {name}: {ret:+.1f}%")
    
    if valid > 0:
        avg = total / valid
        sname = '+'.join(strategies)
        print(f"{sname} 止损{sl*100:.0f}% 止盈{tp*100:.0f}% → {avg:+.1f}%\n")
