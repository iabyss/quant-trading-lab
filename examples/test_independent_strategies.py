#!/usr/bin/env python3
"""
独立策略框架测试
演示如何选择和组合策略
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime, timedelta

from data.fetcher import DataFetcher
from strategies.independent import (
    create_hybrid, create_preset, StrategyFactory, HybridStrategy
)


def test_strategy_selection():
    """测试策略选择"""
    print("="*60)
    print("🎯 独立策略框架测试")
    print("="*60)
    
    # 1. 列出所有可用策略
    print("\n📋 可用策略:")
    for name in StrategyFactory.list_strategies():
        print(f"  - {name}")
    
    # 2. 预设组合
    print("\n📋 预设组合:")
    for name, strategies in [('激进', ['momentum', 'breakout', 'volume']),
                               ('稳健', ['rsi', 'ma', 'macd']),
                               ('平衡', ['momentum', 'ma', 'rsi', 'volume']),
                               ('全部', ['momentum', 'breakout', 'rsi', 'ma', 'volume', 'macd'])]:
        print(f"  - {name}: {strategies}")
    
    # 3. 自定义组合
    print("\n📋 自定义组合示例:")
    print("  # 选择任意策略组合")
    print("  hybrid = create_hybrid(['momentum', 'rsi', 'volume'])")
    print("  # 或带参数")
    print("  hybrid = create_hybrid(['momentum', 'rsi'], params={'rsi': {'oversold': 30}})")


def run_backtest(strategy_names, symbol='600519.SS', initial_capital=300000):
    """运行回测"""
    print(f"\n{'='*50}")
    print(f"回测: {symbol}")
    print(f"策略: {strategy_names}")
    print(f"{'='*50}")
    
    # 获取数据
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    
    if df is None or len(df) < 200:
        print(f"❌ 数据不足")
        return None
    
    df.columns = df.columns.str.lower()
    
    # 创建混合策略
    hybrid = create_hybrid(strategy_names)
    
    # 回测
    from backtest.engine import BacktestEngine
    
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
        
        # 获取信号
        result = hybrid.analyze(df.iloc[:i+1])
        
        # 交易逻辑
        if position == 0 and result['signal'] == 1 and result['strength'] >= 0.3:
            amount = engine.cash * 0.5
            quantity = int(amount / price / 100) * 100
            if quantity > 0:
                engine.buy(df.index[i], symbol, price, quantity=quantity)
                position = 1
                entry_price = price
                print(f"买入 @ {price:.2f} 信号:{result['recommendation']}")
        
        elif position == 1:
            # 止损/止盈
            if price < entry_price * 0.95 or price > entry_price * 1.15:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                    print(f"卖出 @ {price:.2f} 原因:{'止损' if price < entry_price * 0.95 else '止盈'}")
                    position = 0
        
        # 更新权益
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * price
        engine.equity_history.append(equity)
        engine.dates.append(df.index[i])
    
    # 结果
    initial = initial_capital
    final = engine.equity_history[-1] if engine.equity_history else initial
    total_return = (final - initial) / initial * 100
    
    print(f"\n📊 结果:")
    print(f"  初始: {initial:,}")
    print(f"  最终: {final:,.0f}")
    print(f"  收益: {total_return:.2f}%")
    print(f"  交易: {len(engine.trades)}次")
    
    return total_return


def main():
    # 测试框架
    test_strategy_selection()
    
    # 测试不同组合
    print("\n" + "="*60)
    print("🧪 测试不同策略组合")
    print("="*60)
    
    test_cases = [
        ['momentum'],  # 单策略
        ['rsi'],  # 单策略
        ['momentum', 'rsi'],  # 2策略
        ['momentum', 'rsi', 'volume'],  # 3策略
        ['momentum', 'breakout', 'rsi', 'ma', 'volume', 'macd'],  # 全部
    ]
    
    results = []
    for strategies in test_cases:
        ret = run_backtest(strategies, '601888.SS')
        results.append((strategies, ret))
    
    # 汇总
    print("\n" + "="*60)
    print("📈 汇总")
    print("="*60)
    print(f"{'组合':<40} {'收益率':>10}")
    print("-"*55)
    for strategies, ret in results:
        name = '+'.join(strategies)
        print(f"{name:<40} {ret:>9.2f}%")


if __name__ == "__main__":
    main()
