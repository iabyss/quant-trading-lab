#!/usr/bin/env python3
"""
决策团队选股回测
随机选取20只A股，挑选3只进行回测
"""

import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.signals import generate_signals
from backtest.performance import PerformanceAnalyzer

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# A股股票池随机 (模拟选择20只) - 排除指数
ASTOCK_POOL = [
    '600519.SS',  # 贵州茅台
    '600000.SS',  # 浦发银行
    '600036.SS',  # 招商银行
    '600016.SS',  # 民生银行
    '600030.SS',  # 中信证券
    '600887.SS',  # 伊利股份
    '601318.SS',  # 中国平安
    '601398.SS',  # 工商银行
    '600028.SS',  # 中国石化
    '601288.SS',  # 农业银行
    '601988.SS',  # 中国银行
    '600309.SS',  # 万华化学
    '600585.SS',  # 海螺水泥
    '600690.SS',  # 青岛海尔
    '601888.SS',  # 中国中铁
    '601668.SS',  # 中国建筑
    '600276.SS',  # 恒瑞医药
    '000002.SS',  # 万科A
    '000333.SS',  # 美的集团
    '000651.SS',  # 格力电器
    '000725.SS',  # 京东方A
    '002415.SS',  # 海康威视
    '002594.SS',  # 比亚迪
    '002475.SS',  # 立讯精密
    '300750.SS',  # 宁德时代
    '300059.SS',  # 东方财富
    '600900.SS',  # 长江电力
    '601166.SS',  # 兴业银行
    '600050.SS',  # 中国联通
    '600050.SS',  # 中国联通
]

def select_random_stocks(pool, n=20):
    """随机选择n只股票"""
    selected = random.sample(pool, min(n, len(pool)))
    return selected

def backtest_stock(symbol, start_date, end_date, initial_capital=10000000):
    """回测单只股票"""
    print(f"\n{'='*50}")
    print(f"回测: {symbol}")
    print(f"时间: {start_date} ~ {end_date}")
    print(f"{'='*50}")
    
    fetcher = DataFetcher()
    
    # 获取数据
    print(f"正在获取 {symbol} 数据...")
    df = fetcher.download(symbol, period="5y")
    df.columns = df.columns.str.lower()  # 统一列名为小写
    
    if df.empty or len(df) < 100:
        print(f"❌ {symbol} 数据不足，跳过")
        return None
    
    print(f"✓ 获取数据 {len(df)} 条")
    
    # 生成信号 (使用MACD策略) - 统一列名为小写
    df.columns = df.columns.str.lower()
    signals = generate_signals(df, 'macd', {'fast': 12, 'slow': 26, 'signal': 9})
    
    # 回测
    engine = BacktestEngine(
        initial_capital=10000000,  # 改为100万
        commission=0.001,
        slippage=0.001,
        stamp_duty=0.001
    )
    
    position = 0  # 0=空仓, 1=持仓
    
    for i in range(20, len(df)):  # 跳过前20天（等待指标计算）
        date = df.index[i]
        price = df['close'].iloc[i]
        signal = signals.iloc[i]
        
        if signal == 1 and position == 0:  # 买入信号且空仓
            # 买入一半仓位
            amount = engine.cash * 0.5
            quantity = int(amount / price / 100) * 100  # 整手
            if quantity > 0:
                engine.buy(date, symbol, price, quantity=quantity)
                position = 1
                print(f"  买入 {date.date()} @ {price:.2f} x {quantity}")
        
        elif signal == -1 and position == 1:  # 卖出信号且持仓
            # 卖出全部
            pos = engine.positions.get(symbol)
            if pos:
                engine.sell(date, symbol, price, quantity=pos.quantity)
                position = 0
                print(f"  卖出 {date.date()} @ {price:.2f}")
        
        # 更新权益
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * df['close'].iloc[i]
        engine.equity_history.append(equity)
        engine.dates.append(date)
    
    # 最终平仓
    if position == 1:
        date = df.index[-1]
        price = df['close'].iloc[-1]
        pos = engine.positions.get(symbol)
        if pos:
            engine.sell(date, symbol, price, quantity=pos.quantity)
            print(f"  最终平仓 {date.date()} @ {price:.2f}")
    
    # 计算结果
    if not engine.equity_history:
        print(f"❌ 无交易记录")
        return None
    
    initial = initial_capital
    final = engine.equity_history[-1]
    total_return = (final - initial) / initial * 100
    
    # 创建权益曲线
    equity_curve = pd.Series(engine.equity_history, index=engine.dates)
    
    # 绩效分析
    analyzer = PerformanceAnalyzer(equity_curve, engine.trades)
    metrics = analyzer.calculate_all()
    
    print(f"\n📊 回测结果:")
    print(f"  初始资金: {initial:,.0f}")
    print(f"  最终资金: {final:,.0f}")
    print(f"  总收益: {total_return:.2f}%")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"  最大回撤: {metrics.max_drawdown_pct:.2f}%")
    print(f"  交易次数: {len(engine.trades)}")
    print(f"  胜率: {metrics.win_rate:.1f}%")
    
    return {
        'symbol': symbol,
        'initial': initial,
        'final': final,
        'return': total_return,
        'sharpe': metrics.sharpe_ratio,
        'max_dd': metrics.max_drawdown_pct,
        'trades': len(engine.trades),
        'win_rate': metrics.win_rate,
        'equity_curve': equity_curve,
        'df': df,
        'signals': signals
    }

def plot_backtest(results, output_path):
    """绘制回测图表"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 图1: 权益曲线对比
    ax1 = axes[0]
    benchmark_returns = []
    
    for i, r in enumerate(results):
        if r:
            ax1.plot(r['equity_curve'].index, r['equity_curve'].values, 
                    label=f"{r['symbol']} ({r['return']:.1f}%)", linewidth=2)
    
    # 添加基准 (买入持有)
    if results[0]:
        df = results[0]['df']
        if len(df) > 0:
            benchmark = df['close'] / df['close'].iloc[0] * results[0]['initial']
            ax1.plot(df.index, benchmark.values, '--', label='基准(买入持有)', 
                    color='gray', alpha=0.7)
    
    ax1.set_title('权益曲线对比', fontsize=14, fontweight='bold')
    ax1.set_xlabel('日期')
    ax1.set_ylabel('资金')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 图2: 收益柱状图
    ax2 = axes[1]
    symbols = [r['symbol'] if r else '' for r in results]
    returns = [r['return'] if r else 0 for r in results]
    colors = ['green' if r > 0 else 'red' for r in returns]
    bars = ax2.bar(symbols, returns, color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('收益率对比', fontsize=14, fontweight='bold')
    ax2.set_ylabel('收益率 (%)')
    
    # 添加数值标签
    for bar, ret in zip(bars, returns):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{ret:.1f}%', ha='center', va='bottom' if height > 0 else 'top')
    
    # 图3: 绩效指标表
    ax3 = axes[2]
    ax3.axis('off')
    
    # 创建表格数据
    table_data = []
    for r in results:
        if r:
            table_data.append([
                r['symbol'],
                f"{r['initial']:,.0f}",
                f"{r['final']:,.0f}",
                f"{r['return']:.2f}%",
                f"{r['sharpe']:.2f}",
                f"{r['max_dd']:.2f}%",
                f"{r['trades']}",
                f"{r['win_rate']:.1f}%"
            ])
    
    if table_data:
        table = ax3.table(
        cellText=table_data,
        colLabels=['股票', '初始资金', '最终资金', '收益率', '夏普比率', '最大回撤', '交易次数', '胜率'],
        cellLoc='center',
        loc='center',
        colWidths=[0.1, 0.12, 0.12, 0.1, 0.1, 0.1, 0.1, 0.1]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    ax3.set_title('绩效指标汇总', fontsize=14, fontweight='bold', y=0.9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存: {output_path}")

def main():
    print("="*60)
    print("🎯 决策团队选股回测")
    print("="*60)
    
    # 随机选择20只股票
    print("\n📋 第一步: 随机选择20只A股")
    selected_20 = select_random_stocks(ASTOCK_POOL, 20)
    print(f"随机选中的20只股票:")
    for i, s in enumerate(selected_20, 1):
        print(f"  {i:2d}. {s}")
    
    # 强行挑选3只 (这里用随机选择的前3只作为"挑选"结果)
    print("\n🎯 第二步: 挑选3只进行回测")
    selected_3 = selected_20[:3]
    print(f"挑选的3只股票: {selected_3}")
    
    # 回测参数
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    
    print(f"\n📅 回测时间: {start_date} ~ {end_date} (近5年)")
    print(f"💰 初始资金: 100,000")
    
    # 回测
    results = []
    for symbol in selected_3:
        result = backtest_stock(symbol, start_date, end_date)
        results.append(result)
    
    # 汇总
    print("\n" + "="*60)
    print("📈 回测汇总")
    print("="*60)
    
    valid_results = [r for r in results if r]
    
    if valid_results:
        print(f"\n{'股票':<12} {'收益率':>10} {'夏普比率':>10} {'最大回撤':>10} {'交易次数':>8}")
        print("-"*55)
        for r in valid_results:
            print(f"{r['symbol']:<12} {r['return']:>9.2f}% {r['sharpe']:>10.2f} {r['max_dd']:>9.2f}% {r['trades']:>8}")
        
        # 最佳选择
        best = max(valid_results, key=lambda x: x['return'])
        print(f"\n🏆 最佳表现: {best['symbol']} (收益率 {best['return']:.2f}%)")
    
    # 绘图
    output_path = Path(__file__).parent / 'backtest_results.png'
    plot_backtest(results, output_path)

if __name__ == "__main__":
    main()
