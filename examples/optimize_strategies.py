#!/usr/bin/env python3
"""
优化后的策略回测
测试多种组合在5只股票上的表现
"""

import sys
from pathlib import Path
from datetime import datetime
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

# A股股票池
ASTOCK_POOL = [
    ('600519.SS', '贵州茅台'),
    ('601318.SS', '中国平安'),
    ('600036.SS', '招商银行'),
    ('600887.SS', '伊利股份'),
    ('600309.SS', '万华化学'),
    ('601888.SS', '中国中铁'),
    ('600028.SS', '中国石化'),
    ('600000.SS', '浦发银行'),
    ('600030.SS', '中信证券'),
    ('600016.SS', '民生银行'),
    ('600585.SS', '海螺水泥'),
    ('601166.SS', '兴业银行'),
    ('600050.SS', '中国联通'),
    ('600900.SS', '长江电力'),
    ('600276.SS', '恒瑞医药'),
]


def run_backtest(symbol, strategy_names, initial_capital=300000):
    """运行回测"""
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    
    if df is None or len(df) < 200:
        return None
    
    df.columns = df.columns.str.lower()
    
    # 创建混合策略
    hybrid = create_hybrid(strategy_names)
    
    # 回测
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,
        slippage=0.001,
        stamp_duty=0.001
    )
    
    position = 0
    entry_price = 0
    
    for i in range(50, len(df)):
        price = df['close'].iloc[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        if position == 0 and result['signal'] == 1 and result['strength'] >= 0.3:
            amount = engine.cash * 0.5
            quantity = int(amount / price / 100) * 100
            if quantity > 0:
                engine.buy(df.index[i], symbol, price, quantity=quantity)
                position = 1
                entry_price = price
        
        elif position == 1:
            if price < entry_price * 0.95 or price > entry_price * 1.15:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    position = 0
        
        # 更新权益
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * price
        engine.equity_history.append(equity)
    
    initial = initial_capital
    final = engine.equity_history[-1] if engine.equity_history else initial
    total_return = (final - initial) / initial * 100
    
    return {
        'symbol': symbol,
        'return': total_return,
        'trades': len(engine.trades),
        'final': final
    }


def main():
    print("="*60)
    print("🎯 策略优化回测 - 5只股票")
    print("="*60)
    
    # 随机选择5只股票
    random.seed(datetime.now().minute)
    selected = random.sample(ASTOCK_POOL, 5)
    
    print(f"\n📋 测试股票:")
    for code, name in selected:
        print(f"  {code} - {name}")
    
    # 测试不同策略组合
    strategies_to_test = [
        (['rsi'], 'RSI单策略'),
        (['rsi', 'kdj'], 'RSI+KDJ'),
        (['rsi', 'volume'], 'RSI+成交量'),
        (['momentum', 'rsi', 'volume'], '动量+RSI+成交量'),
        (['rsi', 'kdj', 'cci'], 'RSI+KDJ+CCI'),
        (['macd', 'bollinger', 'volume'], 'MACD+布林+成交量'),
    ]
    
    all_results = []
    
    for strategy_names, name in strategies_to_test:
        print(f"\n{'='*50}")
        print(f"📈 策略: {name}")
        print(f"{'='*50}")
        
        results = []
        for code, name_stock in selected:
            ret = run_backtest(code, strategy_names)
            if ret:
                print(f"  {code}: {ret['return']:+.2f}% ({ret['trades']}次)")
                results.append(ret)
        
        if results:
            avg_return = np.mean([r['return'] for r in results])
            print(f"\n  平均收益: {avg_return:+.2f}%")
            all_results.append((strategy_names, name, results, avg_return))
    
    # 找最佳策略
    print("\n" + "="*60)
    print("🏆 策略排名")
    print("="*60)
    
    all_results.sort(key=lambda x: x[3], reverse=True)
    
    for i, (strategies, name, results, avg) in enumerate(all_results, 1):
        print(f"{i}. {name}: {avg:+.2f}%")
    
    # 最佳策略详细结果
    print("\n" + "="*60)
    print(f"🏆 最佳策略: {all_results[0][1]}")
    print("="*60)
    print(f"{'股票':<15} {'收益率':>10} {'交易次数':>10}")
    print("-"*40)
    for r in all_results[0][2]:
        print(f"{r['symbol']:<15} {r['return']:>+9.2f}% {r['trades']:>10}")


if __name__ == "__main__":
    main()
