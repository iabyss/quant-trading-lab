#!/usr/bin/env python3
"""
高级止损止盈策略测试
1. 默认止损5%
2. 盈利后不允许亏钱 (保本止损)
3. 动态止盈: 盈利>6%时，回撤30%止盈
"""

import sys
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

ASTOCK = [
    ('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
    ('600887.SS','伊利股份'), ('600309.SS','万华化学'), ('601888.SS','中国中铁'),
    ('600028.SS','中国石化'), ('600000.SS','浦发银行'), ('600030.SS','中信证券'),
    ('600016.SS','民生银行'), ('600585.SS','海螺水泥'), ('601166.SS','兴业银行'),
]

random.seed(42)
selected = random.sample(ASTOCK, 5)

def test_advanced(symbol, name, strategies, initial_sl=0.05, dynamic_tp=True):
    """高级止损止盈回测"""
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    if df is None or len(df) < 200: return None
    df.columns = df.columns.str.lower()
    
    hybrid = create_hybrid(strategies)
    engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
    position, entry = 0, 0
    peak_price = 0  # 最高价
    
    for i in range(30, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        if position == 0 and result['signal'] == 1:
            qty = int(engine.cash / price / 100) * 100
            if qty > 0:
                engine.buy(df.index[i], symbol, price, quantity=qty)
                position, entry, peak_price = 1, price, price
        
        elif position == 1:
            pct = (price - entry) / entry
            should_sell = False
            reason = ""
            
            # 1. 默认止损 -5%
            if pct < -initial_sl:
                should_sell = True
                reason = f"止损-{initial_sl*100:.0f}%"
            
            # 2. 盈利后不允许亏钱 (保本)
            elif pct > 0 and pct < 0:
                # 如果曾经盈利过，现在回到成本价
                should_sell = True
                reason = "保本"
            
            # 3. 动态止盈: 盈利>6%后，回撤30%止盈
            elif dynamic_tp and pct > 0.06:
                # 计算回撤
                if price > peak_price:
                    peak_price = price
                
                drawback_pct = (peak_price - price) / peak_price
                
                # 回撤超过30%
                if drawback_pct > 0.30:
                    should_sell = True
                    reason = f"动态止盈(回撤{drawback_pct*100:.0f}%)"
            
            # 4. 固定止盈 (备选)
            elif pct > 1.0:  # 100%止盈
                should_sell = True
                reason = "止盈100%"
            
            if should_sell:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        
        # 更新峰值
        if position == 1 and price > peak_price:
            peak_price = price
            
        equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
        engine.equity_history.append(equity)
    
    return (engine.equity_history[-1] - 100000) / 100000 * 100 if engine.equity_history else 0

print("="*60)
print("高级止损止盈策略测试")
print("="*60)
print("\n策略逻辑:")
print("1. 默认止损: -5%")
print("2. 盈利后不允许亏钱 (保本)")
print("3. 动态止盈: 盈利>6%后，回撤30%止盈")
print(f"\n股票: {[s[1] for s in selected]}")

# 测试
tests = [
    (['rsi'], "RSI"),
    (['rsi', 'kdj'], "RSI+KDJ"),
    (['macd'], "MACD"),
    (['macd', 'rsi'], "MACD+RSI"),
    (['rsi', 'kdj', 'wr'], "三剑客"),
]

results = []
for strategies, name in tests:
    total, valid = 0, 0
    for symbol, sname in selected:
        ret = test_advanced(symbol, sname, strategies)
        if ret is not None:
            total += ret
            valid += 1
            print(f"  {sname}: {ret:+.1f}%")
    
    if valid > 0:
        avg = total / valid
        results.append((name, strategies, avg))
        print(f"→ 平均: {avg:+.1f}%\n")

results.sort(key=lambda x: x[2], reverse=True)
print("="*60)
print("🏆 排名:")
for i, r in enumerate(results[:5], 1):
    print(f"{i}. {r[0]}: {r[2]:+.1f}%")
