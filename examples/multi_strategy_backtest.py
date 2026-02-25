#!/usr/bin/env python3
"""
多策略组合回测
测试组合策略在A股市场的表现
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
from strategies.multi_strategy import CombinedStrategy, analyze_stock
from backtest.performance import PerformanceAnalyzer

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# A股股票池
ASTOCK_POOL = [
    ('600519.SS', '贵州茅台'),
    ('601318.SS', '中国平安'),
    ('600036.SS', '招商银行'),
    ('000651.SS', '格力电器'),
    ('600887.SS', '伊利股份'),
    ('600309.SS', '万华化学'),
    ('601888.SS', '中国中铁'),
    ('600028.SS', '中国石化'),
    ('600000.SS', '浦发银行'),
    ('600030.SS', '中信证券'),
]


def run_multi_strategy_backtest(symbol, start_date, end_date, initial_capital=300000):
    """运行多策略组合回测"""
    print(f"\n{'='*50}")
    print(f"多策略组合回测: {symbol}")
    print(f"{'='*50}")
    
    fetcher = DataFetcher()
    df = fetcher.download(symbol, period="1y")
    
    if df is None or len(df) < 200:
        print(f"❌ 数据不足")
        return None
    
    df.columns = df.columns.str.lower()
    
    # 初始化策略
    strategy = CombinedStrategy()
    
    # 回测
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=0.001,
        slippage=0.001,
        stamp_duty=0.001
    )
    
    position = 0  # 0=空仓, 1=持仓
    entry_price = 0
    
    # 记录信号
    signals_log = []
    
    for i in range(50, len(df)):
        date = df.index[i]
        price = df['close'].iloc[i]
        
        # 获取信号
        result = strategy.analyze(df.iloc[:i+1])
        result['recommendation'] = strategy.get_recommendation(result)
        
        # 交易逻辑
        if position == 0:
            # 空仓，满足买入条件
            if result['final_signal'] == 1 and result['strength'] >= 0.3:
                # 买入半仓
                amount = engine.cash * 0.5
                quantity = int(amount / price / 100) * 100
                if quantity > 0:
                    engine.buy(date, symbol, price, quantity=quantity)
                    position = 1
                    entry_price = price
                    name = dict(ASTOCK_POOL).get(symbol, symbol)
                    signals_log.append(f"买入 {date.date()} {name} @ {price:.2f} 信号:{result['recommendation']}")
        
        elif position == 1:
            # 持仓，檢查賣出
            should_sell = False
            reason = ""
            
            # 止损: -5%
            if price < entry_price * 0.95:
                should_sell = True
                reason = "止损-5%"
            
            # 止盈: +15%
            elif price > entry_price * 1.15:
                should_sell = True
                reason = "止盈+15%"
            
            # 卖出信号
            elif result['final_signal'] == -1:
                should_sell = True
                reason = f"卖出信号"
            
            if should_sell:
                pos = engine.positions.get(symbol)
                if pos:
                    engine.sell(date, symbol, price, quantity=pos.quantity)
                    name = dict(ASTOCK_POOL).get(symbol, symbol)
                    signals_log.append(f"卖出 {date.date()} {name} @ {price:.2f} 原因:{reason}")
                    position = 0
        
        # 更新权益
        equity = engine.cash
        for sym, pos in engine.positions.items():
            equity += pos.quantity * price
        engine.equity_history.append(equity)
        engine.dates.append(date)
    
    # 最终平仓
    if position == 1:
        date = df.index[-1]
        price = df['close'].iloc[-1]
        pos = engine.positions.get(symbol)
        if pos:
            engine.sell(date, symbol, price, quantity=pos.quantity)
            name = dict(ASTOCK_POOL).get(symbol, symbol)
            signals_log.append(f"平仓 {date.date()} {name} @ {price:.2f}")
    
    # 结果
    initial = initial_capital
    final = engine.equity_history[-1] if engine.equity_history else initial
    total_return = (final - initial) / initial * 100
    
    equity_curve = pd.Series(engine.equity_history, index=engine.dates)
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
    
    if signals_log:
        print(f"\n📝 信号记录 (前10条):")
        for log in signals_log[:10]:
            print(f"  {log}")
    
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
        'signals': signals_log
    }


def main():
    print("="*60)
    print("🎯 多策略组合回测")
    print("="*60)
    
    # 回测参数
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    print(f"\n📅 回测时间: {start_date} ~ {end_date} (1年)")
    print(f"💰 初始资金: 300,000")
    print(f"📈 策略: 多策略组合 (动量+突破+RSI+均线+成交量+VWAP)")
    
    # 随机选择3只股票
    random.seed(datetime.now().day)
    selected = random.sample(ASTOCK_POOL, 3)
    
    print(f"\n📋 测试股票:")
    for code, name in selected:
        print(f"  {code} - {name}")
    
    # 回测
    results = []
    for code, name in selected:
        result = run_multi_strategy_backtest(code, start_date, end_date)
        if result:
            results.append(result)
    
    # 汇总
    print("\n" + "="*60)
    print("📈 汇总结果")
    print("="*60)
    
    if results:
        print(f"\n{'股票':<15} {'收益率':>10} {'夏普':>8} {'最大回撤':>10} {'交易次数':>8}")
        print("-"*55)
        for r in results:
            print(f"{r['symbol']:<15} {r['return']:>9.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>9.2f}% {r['trades']:>8}")
        
        # 最佳
        best = max(results, key=lambda x: x['return'])
        print(f"\n🏆 最佳: {best['symbol']} ({best['return']:.2f}%)")
        
        # 绘图
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for r in results:
            ax.plot(r['equity_curve'].index, r['equity_curve'].values, 
                   label=f"{r['symbol']} ({r['return']:.1f}%)", linewidth=2)
        
        # 基准线
        ax.axhline(y=300000, color='gray', linestyle='--', alpha=0.5, label='Initial')
        
        ax.set_title('Multi-Strategy Portfolio Backtest', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Capital')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = Path(__file__).parent / 'multi_strategy_backtest.png'
        plt.savefig(output_path, dpi=150)
        print(f"\n✅ 图表已保存: {output_path}")


if __name__ == "__main__":
    main()
