#!/usr/bin/env python3
"""
终极优化 - 目标100%+
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

ASTOCK = [
    ('300014.SZ','亿纬锂能'), ('300033.SZ','同花顺'), ('300015.SZ','爱尔眼科'),
    ('300122.SZ','智飞生物'), ('300003.SZ','乐普医疗'),
]

random.seed(888)

def test(symbol, name, strategies, sl, tp):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 150: return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.0005, slippage=0.001, stamp_duty=0.001)
    
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

print("="*60)
print("终极优化 - 目标100%+")
print("="*60)

# 最优股票
best_stock = ('300014.SZ','亿纬锂能')

# 暴力测试
print(f"\n聚焦最佳股票: {best_stock[1]}")

tests = [
    (['macd'], 0.30, 3.0),
    (['macd'], 0.30, 4.0),
    (['macd'], 0.30, 5.0),
    (['macd'], 0.35, 4.0),
    (['macd'], 0.40, 5.0),
    (['macd', 'rsi'], 0.30, 4.0),
    (['rsi', 'macd', 'kdj'], 0.30, 5.0),
]

results = []
for strategies, sl, tp in tests:
    ret = test(best_stock[0], best_stock[1], strategies, sl, tp)
    if ret is not None:
        results.append((strategies, sl, tp, ret))
        sname = '+'.join(strategies)
        print(f"{sname} 止损{sl*100:.0f}% 止盈{tp*100:.0f}% → {ret:+.1f}%")

results.sort(key=lambda x: x[3], reverse=True)
print("\n🏆 最佳:")
r = results[0]
sname = '+'.join(r[0])
print(f"{sname} 止损{r[1]*100:.0f}% 止盈{r[2]*100:.0f}% → {r[3]:+.1f}%")

# 多只测试
print("\n" + "="*60)
print("多只验证")
print("="*60)

selected = random.sample(ASTOCK, 4)
best = results[0]

total = 0
for symbol, name in selected:
    ret = test(symbol, name, best[0], best[1], best[2])
    if ret:
        total += ret
        print(f"  {name}: {ret:+.1f}%")

avg = total / 4
print(f"\n平均: {avg:+.1f}%")
