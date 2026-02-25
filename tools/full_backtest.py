#!/usr/bin/env python3
"""
完整回测工具 - 带日期和基准对比
"""

import sys
from pathlib import Path
import random
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from data.local_data import list_stocks, load_stock
from backtest.engine import BacktestEngine
from strategies.stop_loss_profit import get_strategy
from strategies.independent import create_hybrid


class FullBacktest:
    """完整回测工具"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
    
    def run(self, stocks, strategy, stop_loss_name='default', period='5y', name='策略'):
        """
        运行回测
        
        Args:
            stocks: 股票列表
            strategy: 策略函数
            stop_loss_name: 止盈止损策略名称
            period: 回测周期
            name: 策略名称
        """
        print("="*60)
        print(f"🎯 {name}")
        print(f"📅 周期: {period}")
        print(f"🛡️ 止盈止损: {stop_loss_name}")
        print("="*60)
        
        stop_strategy = get_strategy(stop_loss_name)
        
        results = []
        benchmark_returns = []
        
        for code in stocks:
            try:
                df = load_stock(code)
                if df is None or len(df) < 500:
                    continue
            except:
                continue
            
            # 记录日期
            start_date = df.index[0].strftime('%Y-%m-%d')
            end_date = df.index[-1].strftime('%Y-%m-%d')
            
            # 计算基准收益
            benchmark_ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            benchmark_returns.append(benchmark_ret)
            
            # 回测
            engine = BacktestEngine(
                initial_capital=self.initial_capital,
                commission=0.001, slippage=0.001, stamp_duty=0.001
            )
            
            position, entry, peak = 0, 0, 0
            
            for i in range(30, len(df)):
                price = df['close'].iloc[i]
                signal = strategy(df.iloc[:i+1])
                
                if position == 0 and signal.signal == 1:
                    qty = int(engine.cash / price / 100) * 100
                    if qty > 0:
                        engine.buy(df.index[i], code, price, quantity=qty)
                        position, entry, peak = 1, price, price
                
                elif position == 1:
                    rule = stop_strategy.should_sell(price, entry, peak)
                    if rule.should_sell:
                        pos = engine.positions.get(code)
                        if pos:
                            engine.sell(df.index[i], code, price, quantity=pos.quantity)
                            position = 0
                
                if position == 1 and price > peak:
                    peak = price
                
                equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
                engine.equity_history.append(equity)
            
            final = engine.equity_history[-1] if engine.equity_history else self.initial_capital
            ret = (final - self.initial_capital) / self.initial_capital * 100
            
            stock_name = code.replace('_', '.').replace('.SS', '').replace('.SZ', '')
            
            results.append({
                'code': code,
                'name': stock_name,
                'return': ret,
                'benchmark': benchmark_ret,
                'excess': ret - benchmark_ret,
                'start_date': start_date,
                'end_date': end_date,
                'trades': len(engine.trades)
            })
            
            print(f"  {stock_name}: {ret:+.1f}% (基准:{benchmark_ret:+.1f}%)")
        
        if not results:
            print("❌ 无有效结果")
            return None
        
        # 汇总
        avg_return = np.mean([r['return'] for r in results])
        avg_benchmark = np.mean(benchmark_returns)
        avg_excess = np.mean([r['excess'] for r in results])
        win_rate = sum(1 for r in results if r['return'] > 0) / len(results) * 100
        
        print(f"\n📊 汇总:")
        print(f"  平均收益: {avg_return:+.2f}%")
        print(f"  基准收益: {avg_benchmark:+.2f}%")
        print(f"  超额收益: {avg_excess:+.2f}%")
        print(f"  胜率: {win_rate:.0f}%")
        
        # 绘图
        self._plot(results, name)
        
        return results
    
    def _plot(self, results, name):
        """绘图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 收益对比
        ax1 = axes[0, 0]
        names = [r['name'] for r in results]
        returns = [r['return'] for r in results]
        benchmarks = [r['benchmark'] for r in results]
        
        x = np.arange(len(names))
        width = 0.35
        
        ax1.bar(x - width/2, returns, width, label='策略', color='blue', alpha=0.7)
        ax1.bar(x + width/2, benchmarks, width, label='基准', color='gray', alpha=0.7)
        ax1.axhline(y=0, color='black', linewidth=0.5)
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=45)
        ax1.set_title(f'{name} - 收益对比', fontweight='bold')
        ax1.legend()
        
        # 2. 超额收益
        ax2 = axes[0, 1]
        excesses = [r['excess'] for r in results]
        colors = ['green' if e > 0 else 'red' for e in excesses]
        ax2.bar(names, excesses, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.set_xticklabels(names, rotation=45)
        ax2.set_title('超额收益', fontweight='bold')
        
        # 3. 日期信息
        ax3 = axes[1, 0]
        ax3.axis('off')
        
        info = f"""
回测详情:
"""
        for r in results:
            info += f"{r['name']}: {r['start_date']} ~ {r['end_date']}\n"
        
        ax3.text(0.1, 0.9, info, transform=ax3.transAxes, fontsize=9,
                 verticalalignment='top', fontfamily='monospace')
        
        # 4. 汇总
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        avg_return = np.mean([r['return'] for r in results])
        avg_benchmark = np.mean([r['benchmark'] for r in results])
        avg_excess = avg_return - avg_benchmark
        win_rate = sum(1 for r in results if r['return'] > 0) / len(results) * 100
        
        summary = f"""
汇总:
• 平均收益: {avg_return:+.2f}%
• 基准收益: {avg_benchmark:+.2f}%
• 超额收益: {avg_excess:+.2f}%
• 胜率: {win_rate:.0f}%
• 股票数: {len(results)}
"""
        
        ax4.text(0.1, 0.9, summary, transform=ax4.transAxes, fontsize=12,
                 verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        
        # 保存
        output_dir = Path(__file__).parent / 'backtest_reports'
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plt.savefig(output_dir / f'backtest_{timestamp}.png', dpi=150, bbox_inches='tight')
        print(f"\n✅ 图表已保存")


# N字反包策略
def n_pattern_strategy(df):
    from dataclasses import dataclass
    @dataclass
    class Signal:
        signal: int
        strength: float
        reason: str
    
    if len(df) < 3:
        return Signal(0, 0, "")
    
    yesterday = df['close'].iloc[-2] - df['open'].iloc[-2]
    today = df['close'].iloc[-1] - df['open'].iloc[-1]
    
    if yesterday < -0.02 and today > 0:
        return Signal(1, 0.8, "N字反包")
    
    return Signal(0, 0, "")


# 测试
if __name__ == "__main__":
    random.seed(42)
    stocks = random.sample(list_stocks(), 5)
    
    bt = FullBacktest()
    bt.run(stocks, n_pattern_strategy, 'default', '5y', 'N字反包策略')
