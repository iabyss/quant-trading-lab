#!/usr/bin/env python3
"""
标准化回测工具 v2
支持多种止盈止损策略
"""

import sys
from pathlib import Path
from datetime import datetime
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.independent import create_hybrid


class BacktestTool:
    """标准化回测工具"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.fetcher = DataFetcher()
    
    def run(self, symbols, strategy_names, stop_loss=0.05, period='1y', 
            stop_type="fixed", dynamic_tp=False,
            name="策略", period="1y"):
        """
        运行回测
        
        Args:
            symbols: 股票列表
            strategy_names: 策略列表
            stop_loss: 止损比例
            stop_type: 止损类型 (fixed/breakeven/dynamic)
            dynamic_tp: 是否动态止盈
            name: 策略名称
            period: 回测周期
        """
        print("="*60)
        print(f"🎯 回测: {name}")
        print(f"📈 策略: {strategy_names}")
        print(f"🛡️ 止损: {stop_type} {stop_loss*100:.0f}%")
        print(f"🎯 止盈: {'动态止盈' if dynamic_tp else '固定100%'}")
        print(f"📅 周期: {period}")
        print("="*60)
        
        results = []
        
        for symbol, stock_name in symbols:
            ret = self._backtest_single(
                symbol, stock_name, strategy_names, 
                period, stop_loss, stop_type, dynamic_tp
            )
            if ret:
                results.append(ret)
        
        if not results:
            print("❌ 无有效回测结果")
            return None
        
        # 汇总
        returns = [r['return'] for r in results]
        avg_return = np.mean(returns)
        
        # 上证指数
        benchmark = self._get_benchmark(period)
        
        print(f"\n📊 汇总:")
        print(f"  平均收益: {avg_return:+.2f}%")
        print(f"  上证指数: {benchmark:+.2f}%")
        print(f"  超额收益: {avg_return - benchmark:+.2f}%")
        print(f"  胜率: {sum(1 for r in returns if r > 0)}/{len(returns)}")
        
        # 绘图
        self._plot(results, avg_return, benchmark, name, strategy_names, stop_loss, stop_type, dynamic_tp)
        
        return {
            'name': name,
            'strategies': strategy_names,
            'stop_loss': stop_loss,
            'stop_type': stop_type,
            'dynamic_tp': dynamic_tp,
            'avg_return': avg_return,
            'benchmark': benchmark,
            'results': results
        }
    
    def _get_benchmark(self, period):
        try:
            df = self.fetcher.download('000001.SS', period=period)
            if df is not None and len(df) > 0:
                return (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
        except:
            pass
        return 0
    
    def _backtest_single(self, symbol, stock_name, strategy_names, period, 
                       stop_loss, stop_type, dynamic_tp):
        """回测单只"""
        df = self.fetcher.download(symbol, period=period)
        if df is None or len(df) < 200:
            return None
        
        df.columns = df.columns.str.lower()
        hybrid = create_hybrid(strategy_names)
        
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission=0.001, slippage=0.001, stamp_duty=0.001
        )
        
        position, entry = 0, 0
        peak_price = 0
        
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
                
                # 止损逻辑
                if stop_type == "fixed":
                    if pct < -stop_loss:
                        should_sell = True
                        reason = f"止损-{stop_loss*100:.0f}%"
                
                elif stop_type == "breakeven":
                    # 盈利后不允许亏钱
                    if pct < -stop_loss:
                        should_sell = True
                        reason = f"止损-{stop_loss*100:.0f}%"
                    elif pct < 0 and peak_price > entry * 1.02:  # 曾盈利2%以上
                        should_sell = True
                        reason = "保本"
                
                # 动态止盈
                if dynamic_tp and pct > 0.06:
                    if price > peak_price:
                        peak_price = price
                    drawback = (peak_price - price) / peak_price
                    if drawback > 0.30:
                        should_sell = True
                        reason = f"回撤止盈"
                elif pct > 1.0:  # 固定100%止盈
                    should_sell = True
                    reason = "止盈100%"
                
                if should_sell:
                    pos = engine.positions.get(symbol)
                    if pos:
                        engine.sell(df.index[i], symbol, price, quantity=pos.quantity)
                        position = 0
            
            if position == 1 and price > peak_price:
                peak_price = price
            
            equity = engine.cash + sum(p.quantity * price for p in engine.positions.values())
            engine.equity_history.append(equity)
        
        final = engine.equity_history[-1] if engine.equity_history else self.initial_capital
        ret = (final - self.initial_capital) / self.initial_capital * 100
        
        print(f"  {stock_name}: {ret:+.1f}%")
        
        return {
            'name': stock_name,
            'return': ret,
            'equity_curve': pd.Series(engine.equity_history) if engine.equity_history else None
        }
    
    def _plot(self, results, avg_return, benchmark, name, strategies, stop_loss, stop_type, dynamic_tp):
        """绘图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 权益曲线
        ax1 = axes[0, 0]
        for r in results:
            if r['equity_curve'] is not None:
                ax1.plot(r['equity_curve'].index, r['equity_curve'].values, 
                        label=f"{r['name']} ({r['return']:+.1f}%)", linewidth=2)
        ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title(f'{name} - Equity Curve', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 收益对比
        ax2 = axes[0, 1]
        names = [r['name'] for r in results]
        rets = [r['return'] for r in results]
        colors = ['green' if r > 0 else 'red' for r in rets]
        bars = ax2.bar(range(len(names)), rets, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.axhline(y=benchmark, color='blue', linestyle='--', label=f'SH Index ({benchmark:+.1f}%)')
        ax2.set_xticks(range(len(names)))
        ax2.set_xticklabels(names, rotation=45)
        ax2.set_title('Return Comparison', fontsize=14, fontweight='bold')
        ax2.legend()
        
        # 3. 策略信息
        ax3 = axes[1, 0]
        ax3.axis('off')
        
        info = f"""
Backtest Report
=========================
Strategy: {name}
Strategies: {', '.join(strategies)}
Stop Loss: {stop_type} {stop_loss*100:.0f}%
Take Profit: {'Dynamic' if dynamic_tp else 'Fixed 100%'}
Period: {self.period}

Results:
• Avg Return: {avg_return:+.2f}%
• Benchmark: {benchmark:+.2f}%
• Excess: {avg_return-benchmark:+.2f}%
"""
        ax3.text(0.1, 0.9, info, transform=ax3.transAxes, fontsize=11,
                 verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        
        # 保存
        output_dir = Path(__file__).parent / 'backtest_reports'
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f'backtest_{timestamp}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ 图表: {output_path}")


if __name__ == "__main__":
    # 测试
    ASTOCK = [('600519.SS','贵州茅台'), ('601318.SS','中国平安'), ('600036.SS','招商银行'),
              ('600887.SS','伊利股份'), ('600309.SS','万华化学')]
    
    random.seed(42)
    selected = random.sample(ASTOCK, 3)
    
    tool = BacktestTool()
    
    print("\n" + "="*60)
    print("测试1: 固定止损5%")
    print("="*60)
    tool.run(selected, ['rsi', 'kdj'], stop_loss=0.05, stop_type="fixed", name="固定止损")
    
    print("\n" + "="*60)
    print("测试2: 保本止损+动态止盈")
    print("="*60)
    tool.run(selected, ['rsi', 'kdj'], stop_loss=0.05, stop_type="breakeven", dynamic_tp=True, name="保本+动态止盈")
