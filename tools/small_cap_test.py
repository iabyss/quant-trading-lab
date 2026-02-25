#!/usr/bin/env python3
"""
小盘股激进策略测试 v2
目标: 年化100%+
"""

import sys
from pathlib import Path
import random
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

# 小盘股池 (随机选取)
ASTOCK = [
    ('300033.SZ','同花顺'), ('300015.SZ','爱尔眼科'), ('300003.SZ','乐普医疗'),
    ('300122.SZ','智飞生物'), ('300014.SZ','亿纬锂能'), ('300759.SZ','惠伦高科'),
    ('300001.SZ','睿创微纳'), ('300012.SZ','华测检测'), ('300456.SZ','华测检测'),
    ('300456.SZ','华测'), ('300001.SZ','睿创'), ('300003.SZ','乐普'),
    ('300122.SZ','智飞'), ('300014.SZ','亿纬'), ('300015.SZ','爱尔'),
    ('300759.SZ','惠伦'), ('300033.SZ','同花顺'), ('300456.SZ','检测'),
]

random.seed(42)

def test(symbol, name, strategies, sl, tp):
    """激进回测"""
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 200: 
        print(f"  {name}: 数据不足")
        return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.002, stamp_duty=0.001)
    
    position, entry = 0, 0
    trades = 0
    
    for i in range(30, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        # 激进: 只要有信号就满仓
        if position == 0 and result['signal'] == 1:
            qty = int(engine.cash / price / 100) * 100
            if qty > 0:
                engine.buy(df.index[i], symbol, price, quantity=qty)
                position, entry = 1, price
                trades += 1
        
        elif position == 1:
            pct = (price - entry) / entry
            if pct < -sl or pct > tp:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        
        equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
        engine.equity_history.append(equity)
    
    ret = (engine.equity_history[-1] - 100000) / 100000 * 100 if engine.equity_history else 0
    return ret, trades

print("="*60)
print("小盘股激进策略测试 v2")
print("="*60)

# 随机选5只
selected = random.sample(ASTOCK, 5)
print(f"\n股票: {[s[1] for s in selected]}")

# 测试不同策略
tests = [
    (['rsi'], "RSI", 0.10, 0.60),
    (['rsi'], "RSI", 0.15, 0.80),
    (['rsi'], "RSI", 0.15, 1.00),
    (['rsi', 'kdj'], "RSI+KDJ", 0.15, 1.00),
    (['macd', 'rsi'], "MACD+RSI", 0.15, 1.20),
    (['macd', 'rsi'], "MACD+RSI", 0.20, 1.50),
]

results = []
for strategies, name, sl, tp in tests:
    total, valid = 0, 0
    for symbol, sname in selected:
        result = test(symbol, sname, strategies, sl, tp)
        if result:
            ret, trades = result
            total += ret
            valid += 1
            print(f"  {sname}: {ret:+.1f}% ({trades}次)")
    
    if valid > 0:
        avg = total / valid
        results.append((name, strategies, sl, tp, avg))
        print(f"→ 平均: {avg:+.1f}%\n")

results.sort(key=lambda x: x[4], reverse=True)
print("\n🏆 Top:")
for r in results[:3]:
    print(f"  {r[0]}: 止损{r[2]*100:.0f}% 止盈{r[3]*100:.0f}% → {r[4]:+.1f}%")
