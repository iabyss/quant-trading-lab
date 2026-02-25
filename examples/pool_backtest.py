#!/usr/bin/env python3
"""
决策团队选股回测 - 股票池模式
每次只持有1只股票，卖出后从股票池中选择最优
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

# A股股票池
ASTOCK_POOL = [
    ('600519.SS', '贵州茅台'),
    ('601318.SS', '中国平安'),
    ('600036.SS', '招商银行'),
    ('000651.SS', '格力电器'),
    ('000333.SS', '美的集团'),
    ('600887.SS', '伊利股份'),
    ('600309.SS', '万华化学'),
    ('601888.SS', '中国中铁'),
    ('600028.SS', '中国石化'),
    ('600000.SS', '浦发银行'),
]

def get_pool_data(symbols, period="5y"):
    """获取股票池所有股票数据"""
    fetcher = DataFetcher()
    data = {}
    
    for symbol in symbols:
        print(f"  获取 {symbol} 数据...", end=" ")
        df = fetcher.download(symbol, period=period)
        if df is not None and len(df) > 200:
            df.columns = df.columns.str.lower()
            data[symbol] = df
            print(f"✓ {len(df)} 条")
        else:
            print(f"✗ 数据不足")
    
    return data

def select_best_stock(pool_data, current_date_idx, signals_cache):
    """
    从股票池中选择最优股票
    逻辑: 选择MACD金叉信号最强的（histogram值最大的）
    """
    best_stock = None
    best_score = -999
    
    for symbol, df in pool_data.items():
        if current_date_idx >= len(df):
            continue
        
        # 获取该股票的信号
        if symbol not in signals_cache:
            continue
        
        signal_series = signals_cache[symbol]
        if current_date_idx >= len(signal_series):
            continue
        
        signal = signal_series.iloc[current_date_idx]
        
        # 选择有买入信号的，评分高的
        if signal >= 1:  # 买入信号
            # 获取当前histogram值作为评分
            macd_df = df.copy()
            close = macd_df['close']
            ema_fast = close.ewm(span=12, adjust=False).mean()
            ema_slow = close.ewm(span=26, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal_line
            
            if current_date_idx < len(histogram):
                score = histogram.iloc[current_date_idx]
                if score > best_score:
                    best_score = score
                    best_stock = symbol
    
    return best_stock

def run_pool_backtest(pool, initial_capital=1000000):
    """运行股票池回测"""
    print("\n" + "="*60)
    print("🎯 股票池模式回测")
    print("="*60)
    
    symbols = [s[0] for s in pool]
    print(f"\n股票池: {[s[1] for s in pool]}")
    
    # 获取所有股票数据
    print("\n📥 获取股票池数据...")
    pool_data = get_pool_data(symbols)
    
    if not pool_data:
        print("❌ 无法获取股票数据")
        return None
    
    # 生成所有股票的信号
    print("\n📊 计算交易信号...")
    signals_cache = {}
    for symbol, df in pool_data.items():
        signals_cache[symbol] = generate_signals(df, 'macd')
    
    # 找到最早的数据起点
    min_len = min(len(df) for df in pool_data.values())
    print(f"共同交易日: {min_len} 天")
    
    # 回测
    print("\n🔄 开始回测...")
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,
        slippage=0.001,
        stamp_duty=0.001
    )
    
    current_stock = None
    position = 0
    trade_log = []
    
    # 遍历每一天
    for i in range(50, min_len):  # 跳过前50天等待指标稳定
        # 获取当前日期（使用第一个股票的日期）
        first_symbol = list(pool_data.keys())[0]
        date = pool_data[first_symbol].index[i]
        
        # 如果没有持仓，选择最优股票买入
        if position == 0:
            best_stock = select_best_stock(pool_data, i, signals_cache)
            
            if best_stock and best_stock in pool_data:
                df = pool_data[best_stock]
                price = df['close'].iloc[i]
                
                # 买入一半仓位
                amount = engine.cash * 0.5
                quantity = int(amount / price / 100) * 100
                
                if quantity > 0:
                    result = engine.buy(date, best_stock, price, quantity=quantity)
                    if result:
                        current_stock = best_stock
                        position = 1
                        name = dict(pool).get(best_stock, best_stock)
                        trade_log.append(f"买入 {date.date()} {name} @ {price:.2f} x {quantity}")
        
        # 如果有持仓，检查是否卖出
        elif position == 1 and current_stock:
            df = pool_data[current_stock]
            price = df['close'].iloc[i]
            signal = signals_cache[current_stock].iloc[i]
            
            # 卖出信号 或 发现更好机会
            if signal == -1:  # 卖出信号
                pos = engine.positions.get(current_stock)
                if pos:
                    engine.sell(date, current_stock, price, quantity=pos.quantity)
                    name = dict(pool).get(current_stock, current_stock)
                    trade_log.append(f"卖出 {date.date()} {name} @ {price:.2f}")
                    position = 0
                    current_stock = None
        
        # 更新权益
        equity = engine.cash
        for sym, pos in engine.positions.items():
            if sym in pool_data:
                equity += pos.quantity * pool_data[sym]['close'].iloc[i]
        engine.equity_history.append(equity)
        engine.dates.append(date)
    
    # 最终平仓
    if position == 1 and current_stock:
        first_symbol = list(pool_data.keys())[0]
        date = pool_data[first_symbol].index[-1]
        price = pool_data[current_stock]['close'].iloc[-1]
        pos = engine.positions.get(current_stock)
        if pos:
            engine.sell(date, current_stock, price, quantity=pos.quantity)
            name = dict(pool).get(current_stock, current_stock)
            trade_log.append(f"最终平仓 {date.date()} {name} @ {price:.2f}")
    
    # 计算结果
    initial = initial_capital
    final = engine.equity_history[-1] if engine.equity_history else initial
    total_return = (final - initial) / initial * 100
    
    # 绩效分析
    equity_curve = pd.Series(engine.equity_history, index=engine.dates)
    analyzer = PerformanceAnalyzer(equity_curve, engine.trades)
    metrics = analyzer.calculate_all()
    
    return {
        'initial': initial,
        'final': final,
        'return': total_return,
        'sharpe': metrics.sharpe_ratio,
        'max_dd': metrics.max_drawdown_pct,
        'trades': len(engine.trades),
        'win_rate': metrics.win_rate,
        'equity_curve': equity_curve,
        'trade_log': trade_log,
        'pool_data': pool_data
    }

def plot_result(result, pool, output_path):
    """绘制结果图表"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # 图1: 权益曲线
    ax1 = axes[0]
    ax1.plot(result['equity_curve'].index, result['equity_curve'].values, 
             'b-', linewidth=2, label='Strategy')
    
    # 基准线
    benchmark = result['initial'] * np.ones(len(result['equity_curve']))
    ax1.plot(result['equity_curve'].index, benchmark, 'r--', 
             alpha=0.5, label='Initial Capital')
    
    ax1.set_title('Equity Curve - Pool Trading', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Capital')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 图2: 绩效指标
    ax2 = axes[1]
    ax2.axis('off')
    
    # 绩效表格
    table_data = [
        ['Initial Capital', f"¥{result['initial']:,.0f}"],
        ['Final Capital', f"¥{result['final']:,.0f}"],
        ['Total Return', f"{result['return']:.2f}%"],
        ['Sharpe Ratio', f"{result['sharpe']:.2f}"],
        ['Max Drawdown', f"{result['max_dd']:.2f}%"],
        ['Total Trades', str(result['trades'])],
        ['Win Rate', f"{result['win_rate']:.1f}%"],
    ]
    
    table = ax2.table(
        cellText=table_data,
        colLabels=['Metric', 'Value'],
        cellLoc='center',
        loc='center',
        colWidths=[0.3, 0.3]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    
    ax2.set_title('Performance Metrics', fontsize=14, fontweight='bold', y=0.85)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存: {output_path}")

def main():
    print("="*60)
    print("🎯 决策团队选股回测 - 股票池模式")
    print("="*60)
    
    # 随机选择10只股票
    random.seed(42)  # 固定随机种子以便复现
    selected_pool = random.sample(ASTOCK_POOL, 10)
    
    print("\n📋 股票池:")
    for i, (code, name) in enumerate(selected_pool, 1):
        print(f"  {i:2d}. {code} - {name}")
    
    # 运行回测
    result = run_pool_backtest(selected_pool)
    
    if result:
        print("\n" + "="*60)
        print("📊 回测结果")
        print("="*60)
        print(f"\n  初始资金: ¥{result['initial']:,.0f}")
        print(f"  最终资金: ¥{result['final']:,.0f}")
        print(f"  总收益率: {result['return']:.2f}%")
        print(f"  夏普比率: {result['sharpe']:.2f}")
        print(f"  最大回撤: {result['max_dd']:.2f}%")
        print(f"  交易次数: {result['trades']}")
        print(f"  胜率: {result['win_rate']:.1f}%")
        
        print("\n📝 交易记录:")
        for log in result['trade_log']:
            print(f"  {log}")
        
        # 绘图
        output_path = Path(__file__).parent / 'pool_backtest_result.png'
        plot_result(result, selected_pool, output_path)
        
        # 更新MD文档
        md_path = Path(__file__).parent / 'backtest_pool_test.md'
        md_content = f"""# 决策团队选股回测 - 股票池模式

## 测试目的
验证决策团队在10只股票池中轮动交易的表现

## 测试规则
1. **股票池**: 随机选择10只A股
2. **持仓限制**: 每次最多持有1只股票
3. **买入逻辑**: 卖出后，从股票池中选择MACD金叉信号最强的股票买入
4. **回测周期**: 近5年数据
5. **初始资金**: 100万

## 选股池

| 序号 | 股票代码 | 名称 |
|------|----------|------|
"""
        for i, (code, name) in enumerate(selected_pool, 1):
            md_content += f"| {i} | {code} | {name} |\n"
        
        md_content += f"""
## 回测结果

| 指标 | 数值 |
|------|------|
| 初始资金 | ¥{result['initial']:,.0f} |
| 最终资金 | ¥{result['final']:,.0f} |
| 总收益率 | **{result['return']:.2f}%** |
| 夏普比率 | {result['sharpe']:.2f} |
| 最大回撤 | {result['max_dd']:.2f}% |
| 交易次数 | {result['trades']} |
| 胜率 | {result['win_rate']:.1f}% |

## 交易记录

"""
        for log in result['trade_log']:
            md_content += f"- {log}\n"
        
        md_path.write_text(md_content)
        print(f"\n✅ 文档已更新: {md_path}")

if __name__ == "__main__":
    main()
