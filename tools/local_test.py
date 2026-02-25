#!/usr/bin/env python3
"""
本地数据快速测试
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.local_data import load_stock, list_stocks
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

# 随机5只
stocks = list_stocks()
random.seed(42)
selected = random.sample(stocks, 5)

print("="*60)
print("本地数据快速测试")
print("="*60)
print(f"股票: {selected}")

def test(symbol, strategies, sl, tp):
    try:
        df = load_stock(symbol)
        if df is None or len(df) < 500: return None
    except:
        return None
    
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

# 测试
print("\n策略: RSI+KDJ | 止损5% 止盈50%")
print("-"*40)

total = 0
for symbol in selected:
    ret = test(symbol, ['rsi', 'kdj'], 0.05, 0.50)
    if ret:
        total += ret
        print(f"  {symbol}: {ret:+.1f}%")

avg = total / 5
print(f"\n平均: {avg:+.1f}%")
