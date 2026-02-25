#!/usr/bin/env python3
"""
稳定性测试 - 随机年份 + 随机股票
"""

import sys
from pathlib import Path
import random
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

# 股票池
ASTOCK = [
    ('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
    ('600887.SS','伊利股份'), ('600309.SS','万华化学'), ('601888.SS','中国中铁'),
    ('600028.SS','中国石化'), ('600000.SS','浦发银行'), ('600030.SS','中信证券'),
    ('600016.SS','民生银行'), ('600585.SS','海螺水泥'), ('601166.SS','兴业银行'),
]

# 年份池
YEARS = ['1y', '2y', '3y', '5y']

def test(symbol, strategies, sl, tp, period):
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period=period)
    if df is None or len(df) < 200: return None
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
print("🎯 稳定性测试 - 随机年份 + 随机股票")
print("="*60)

# 随机选择
random.seed(datetime.now().second)
selected_stocks = random.sample(ASTOCK, 5)
selected_year = random.choice(YEARS)

print(f"\n📋 随机选择:")
print(f"  股票: {[s[1] for s in selected_stocks]}")
print(f"  回测周期: {selected_year}")
print(f"  策略: RSI (止损15%, 止盈50%)")

# 测试
results = []
for symbol, name in selected_stocks:
    ret = test(symbol, ['rsi'], 0.15, 0.50, selected_year)
    if ret is not None:
        results.append((name, ret))
        print(f"  {name}: {ret:+.1f}%")

if results:
    avg = sum(r[1] for r in results) / len(results)
    print(f"\n📊 平均收益: {avg:+.1f}%")
    print(f"  正收益: {sum(1 for r in results if r[1] > 0)}/{len(results)} ({sum(1 for r in results if r[1] > 0)/len(results)*100:.0f}%)")

# 多次测试不同年份
print("\n" + "="*60)
print("📈 不同年份稳定性测试")
print("="*60)

for year in YEARS:
    total, count = 0, 0
    for symbol, name in selected_stocks:
        ret = test(symbol, ['rsi'], 0.15, 0.50, year)
        if ret is not None:
            total += ret
            count += 1
    if count > 0:
        avg = total / count
        status = "✅" if avg > 0 else "❌"
        print(f"{year}: {avg:+.1f}% {status}")
