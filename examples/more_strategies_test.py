#!/usr/bin/env python3
"""
更多组合策略测试
"""

import sys
from pathlib import Path
from datetime import datetime
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid

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
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    
    if df is None or len(df) < 200:
        return None
    
    df.columns = df.columns.str.lower()
    hybrid = create_hybrid(strategy_names)
    
    engine = BacktestEngine(initial_capital=initial_capital, commission=0.001, slippage=0.001, stamp_duty=0.001)
    
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
        
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * price
        engine.equity_history.append(equity)
    
    initial = initial_capital
    final = engine.equity_history[-1] if engine.equity_history else initial
    return (final - initial) / initial * 100


def main():
    print("="*60)
    print("🎯 更多组合策略测试")
    print("="*60)
    
    # 随机5只股票
    random.seed(datetime.now().minute)
    selected = random.sample(ASTOCK_POOL, 5)
    
    print(f"\n📋 测试股票:")
    for code, name in selected:
        print(f"  {code} - {name}")
    
    # 更多组合测试
    strategies_to_test = [
        (['rsi', 'kdj'], 'RSI+KDJ'),
        (['rsi', 'wr'], 'RSI+WR'),
        (['rsi', 'cci'], 'RSI+CCI'),
        (['kdj', 'wr'], 'KDJ+WR'),
        (['rsi', 'kdj', 'wr'], 'RSI+KDJ+WR'),
        (['rsi', 'kdj', 'cci', 'wr'], 'RSI+KDJ+CCI+WR'),
        (['macd', 'atr'], 'MACD+ATR'),
        (['macd', 'bollinger', 'atr'], 'MACD+布林+ATR'),
        (['obv', 'volume'], 'OBV+成交量'),
        (['trix', 'dma'], 'TRIX+DMA'),
    ]
    
    all_results = []
    
    for strategy_names, name in strategies_to_test:
        print(f"\n{'='*50}")
        print(f"📈 策略: {name}")
        
        results = []
        for code, name_stock in selected:
            ret = run_backtest(code, strategy_names)
            if ret is not None:
                print(f"  {code}: {ret:+.2f}%")
                results.append(ret)
        
        if results:
            avg = np.mean(results)
            print(f"  平均: {avg:+.2f}%")
            all_results.append((name, avg, results))
    
    # 排名
    print("\n" + "="*60)
    print("🏆 策略排名")
    print("="*60)
    all_results.sort(key=lambda x: x[1], reverse=True)
    
    for i, (name, avg, _) in enumerate(all_results, 1):
        print(f"{i}. {name}: {avg:+.2f}%")
    
    print(f"\n🏆 最佳: {all_results[0][0]} ({all_results[0][1]:+.2f}%)")


if __name__ == "__main__":
    main()
