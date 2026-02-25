#!/usr/bin/env python3
"""
策略参数优化工具
目标: 找到最优策略组合和参数
"""

import sys
from pathlib import Path
import random
from datetime import datetime
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid


def run_backtest(symbol, strategy_names, initial_capital=300000, 
                 stop_loss=0.05, take_profit=0.15, min_strength=0.3):
    """回测单只股票"""
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    
    if df is None or len(df) < 200:
        return None
    
    df.columns = df.columns.str.lower()
    hybrid = create_hybrid(strategy_names)
    
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
        date = df.index[i]
        result = hybrid.analyze(df.iloc[:i+1])
        
        if position == 0 and result['signal'] == 1 and result['strength'] >= min_strength:
            amount = engine.cash * 0.8  # 提高到80%仓位
            quantity = int(amount / price / 100) * 100
            if quantity > 0:
                engine.buy(date, symbol, price, quantity=quantity)
                position = 1
                entry_price = price
        
        elif position == 1:
            # 灵活止盈止损
            if price < entry_price * (1 - stop_loss):
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(date, symbol, price, quantity=pos.quantity)
                    position = 0
            elif price > entry_price * (1 + take_profit):
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(date, symbol, price, quantity=pos.quantity)
                    position = 0
        
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * price
        engine.equity_history.append(equity)
    
    final = engine.equity_history[-1] if engine.equity_history else initial_capital
    return (final - initial_capital) / initial_capital * 100


def optimize():
    """参数优化"""
    print("="*60)
    print("🎯 策略参数优化 - 目标100%+收益")
    print("="*60)
    
    # 测试股票池
    ASTOCK = [
        ('600519.SS', '贵州茅台'),
        ('601318.SS', '中国平安'),
        ('600036.SS', '招商银行'),
        ('600887.SS', '伊利股份'),
        ('600309.SS', '万华化学'),
    ]
    
    # 策略组合
    strategy_combos = [
        (['rsi', 'kdj'], "RSI+KDJ"),
        (['rsi', 'kdj', 'wr'], "RSI+KDJ+WR"),
        (['rsi', 'kdj', 'cci'], "RSI+KDJ+CCI"),
        (['macd', 'rsi'], "MACD+RSI"),
        (['macd', 'bollinger'], "MACD+布林"),
        (['momentum', 'volume'], "动量+成交量"),
        (['breakout', 'volume'], "突破+成交量"),
        (['rsi', 'macd', 'volume'], "RSI+MACD+成交量"),
        (['kdj', 'macd', 'rsi'], "KDJ+MACD+RSI"),
    ]
    
    # 参数组合
    param_combinations = [
        # (stop_loss, take_profit, min_strength)
        (0.03, 0.10, 0.3),  # 激进
        (0.05, 0.15, 0.3),  # 中等
        (0.08, 0.20, 0.3),  # 保守
        (0.10, 0.25, 0.3),  # 更保守
        (0.10, 0.30, 0.3),  # 长线
        (0.05, 0.20, 0.2),  # 低门槛
        (0.08, 0.25, 0.2),  # 低门槛保守
        (0.10, 0.30, 0.2),  # 长线低门槛
    ]
    
    results = []
    
    # 遍历所有组合
    for strategies, sname in strategy_combos:
        for stop_loss, take_profit, min_strength in param_combinations:
            total_return = 0
            valid_count = 0
            
            for symbol, name in ASTOCK:
                ret = run_backtest(symbol, strategies, 
                                 stop_loss=stop_loss, 
                                 take_profit=take_profit,
                                 min_strength=min_strength)
                if ret is not None:
                    total_return += ret
                    valid_count += 1
            
            if valid_count > 0:
                avg_return = total_return / valid_count
                results.append({
                    'strategies': sname,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'min_strength': min_strength,
                    'avg_return': avg_return
                })
    
    # 排序
    results.sort(key=lambda x: x['avg_return'], reverse=True)
    
    # 输出Top10
    print("\n🏆 Top 10 策略组合:")
    print("="*60)
    for i, r in enumerate(results[:10], 1):
        print(f"{i}. {r['strategies']}")
        print(f"   止损:{r['stop_loss']*100:.0f}% 止盈:{r['take_profit']*100:.0f}% "
              f"强度:{r['min_strength']} → 收益:{r['avg_return']:+.2f}%")
    
    # 最佳参数
    best = results[0]
    print("\n" + "="*60)
    print(f"🏆 最佳策略: {best['strategies']}")
    print(f"   止损: {best['stop_loss']*100:.0f}%")
    print(f"   止盈: {best['take_profit']*100:.0f}%")
    print(f"   预期收益: {best['avg_return']:+.2f}%")
    print("="*60)
    
    return results[:5]


if __name__ == "__main__":
    optimize()
