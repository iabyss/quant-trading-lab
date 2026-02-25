#!/usr/bin/env python3
"""
标准化回测工具
生成回测报告和图表
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
from backtest.performance import PerformanceAnalyzer
from strategies.independent import create_hybrid


class BacktestTool:
    """标准化回测工具"""
    
    def __init__(self, initial_capital=300000):
        self.initial_capital = initial_capital
        self.fetcher = DataFetcher()
        
    def run(self, symbols, strategy_names, name="策略", period="1y", 
            stop_loss=0.05, take_profit=0.15):
        """
        运行回测
        
        Args:
            symbols: 股票列表 [('600519.SS', '贵州茅台'), ...]
            strategy_names: 策略列表 ['rsi', 'kdj']
            name: 策略名称
            period: 回测周期
            stop_loss: 止损比例
            take_profit: 止盈比例
        
        Returns:
            回测结果字典
        """
        print("="*60)
        print(f"🎯 回测: {name}")
        print(f"📈 策略: {strategy_names}")
        print(f"📅 周期: {period}")
        print("="*60)
        
        results = []
        
        # 获取上证指数数据作为基准
        benchmark_return = self._get_benchmark(period)
        
        for symbol, stock_name in symbols:
            ret = self._backtest_single(
                symbol, stock_name, strategy_names, 
                period, stop_loss, take_profit
            )
            if ret:
                results.append(ret)
        
        if not results:
            print("❌ 无有效回测结果")
            return None
        
        # 汇总
        summary = self._summary(results, benchmark_return, name)
        
        # 绘图
        self._plot(results, summary, name)
        
        return summary
    
    def _get_benchmark(self, period):
        """获取上证指数基准收益"""
        try:
            df = self.fetcher.download('000001.SS', period=period)
            if df is not None and len(df) > 0:
                return (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
        except:
            pass
        return 0
    
    def _backtest_single(self, symbol, stock_name, strategy_names, period, stop_loss, take_profit):
        """回测单只股票"""
        df = self.fetcher.download(symbol, period=period)
        
        if df is None or len(df) < 200:
            print(f"  {symbol}: 数据不足")
            return None
        
        df.columns = df.columns.str.lower()
        hybrid = create_hybrid(strategy_names)
        
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission=0.001,
            slippage=0.001,
            stamp_duty=0.001
        )
        
        position = 0
        entry_price = 0
        trades = []
        
        for i in range(50, len(df)):
            price = df['close'].iloc[i]
            date = df.index[i]
            result = hybrid.analyze(df.iloc[:i+1])
            
            if position == 0 and result['signal'] == 1 and result['strength'] >= 0.3:
                amount = engine.cash * 0.5
                quantity = int(amount / price / 100) * 100
                if quantity > 0:
                    engine.buy(date, symbol, price, quantity=quantity)
                    position = 1
                    entry_price = price
                    trades.append(('BUY', date, price))
            
            elif position == 1:
                if price < entry_price * (1 - stop_loss) or price > entry_price * (1 + take_profit):
                    pos = engine.positions.get(symbol)
                    if pos:
                        engine.sell(date, symbol, price, quantity=pos.quantity)
                        trades.append(('SELL', date, price))
                        position = 0
            
            # 更新权益
            equity = engine.cash
            for sym, pos in engine.positions.items():
                equity += pos.quantity * price
            engine.equity_history.append(equity)
            engine.dates.append(date)
        
        final = engine.equity_history[-1] if engine.equity_history else self.initial_capital
        total_return = (final - self.initial_capital) / self.initial_capital * 100
        
        print(f"  {stock_name}: {total_return:+.2f}% ({len(trades)//2}次)")
        
        return {
            'symbol': symbol,
            'name': stock_name,
            'return': total_return,
            'trades': len(trades) // 2,
            'equity_curve': pd.Series(engine.equity_history, index=engine.dates) if engine.equity_history else None
        }
    
    def _summary(self, results, benchmark_return, name):
        """汇总结果"""
        returns = [r['return'] for r in results]
        
        return {
            'strategy_name': name,
            'avg_return': np.mean(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns) * 100,
            'results': results,
            'benchmark_return': benchmark_return,
            'initial_capital': self.initial_capital
        }
    
    def _plot(self, results, summary, name):
        """绘图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 权益曲线
        ax1 = axes[0, 0]
        for r in results:
            if r['equity_curve'] is not None:
                ax1.plot(r['equity_curve'].index, r['equity_curve'].values, 
                        label=f"{r['name']} ({r['return']:+.1f}%)", linewidth=2)
        
        # 基准线
        benchmark = self.initial_capital * np.ones(len(results[0]['equity_curve'])) if results and results[0]['equity_curve'] is not None else []
        if len(benchmark) > 0:
            ax1.plot(results[0]['equity_curve'].index, benchmark, 
                    '--', color='gray', label='基准', alpha=0.7)
        
        ax1.axhline(y=self.initial_capital, color='black', linestyle=':', alpha=0.5)
        ax1.set_title(f'{name} - 权益曲线', fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('资金')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. 收益率对比
        ax2 = axes[0, 1]
        names = [r['name'] for r in results]
        returns = [r['return'] for r in results]
        colors = ['green' if r > 0 else 'red' for r in returns]
        bars = ax2.bar(range(len(names)), returns, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.axhline(y=summary['benchmark_return'], color='blue', linestyle='--', 
                    label=f'上证指数 ({summary["benchmark_return"]:+.1f}%)')
        ax2.set_xticks(range(len(names)))
        ax2.set_xticklabels(names, rotation=45, ha='right')
        ax2.set_title('收益率对比', fontsize=14, fontweight='bold')
        ax2.set_ylabel('收益率 (%)')
        ax2.legend()
        
        for bar, ret in zip(bars, returns):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{ret:.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=9)
        
        # 3. 统计表格
        ax3 = axes[1, 0]
        ax3.axis('off')
        
        table_data = [
            ['平均收益率', f"{summary['avg_return']:+.2f}%"],
            ['最高收益率', f"{summary['max_return']:+.2f}%"],
            ['最低收益率', f"{summary['min_return']:+.2f}%"],
            ['胜率', f"{summary['win_rate']:.1f}%"],
            ['基准收益(上证)', f"{summary['benchmark_return']:+.2f}%"],
            ['超额收益', f"{summary['avg_return'] - summary['benchmark_return']:+.2f}%"],
        ]
        
        table = ax3.table(cellText=table_data, colLabels=['指标', '数值'],
                         cellLoc='center', loc='center', colWidths=[0.4, 0.3])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 2)
        ax3.set_title('绩效汇总', fontsize=14, fontweight='bold', y=0.9)
        
        # 4. 策略信息
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        info = f"""
回测参数:
• 初始资金: {self.initial_capital:,}
• 回测周期: 1年
• 止损: -5%
• 止盈: +15%

策略: {name}

股票池:
"""
        for r in results:
            info += f"• {r['name']}: {r['return']:+.2f}%\n"
        
        ax4.text(0.1, 0.9, info, transform=ax4.transAxes, fontsize=10,
                 verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        
        # 保存
        output_dir = Path(__file__).parent / 'backtest_reports'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f'backtest_{timestamp}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        
        print(f"\n✅ 图表已保存: {output_path}")
        
        # 打印报告
        print("\n" + "="*60)
        print("📊 回测报告")
        print("="*60)
        print(f"  策略: {name}")
        print(f"  平均收益: {summary['avg_return']:+.2f}%")
        print(f"  上证指数: {summary['benchmark_return']:+.2f}%")
        print(f"  超额收益: {summary['avg_return'] - summary['benchmark_return']:+.2f}%")
        print(f"  胜率: {summary['win_rate']:.1f}%")
        print("="*60)


# 便捷函数
def quick_backtest(symbols, strategy_names, name="策略"):
    """快速回测"""
    tool = BacktestTool(initial_capital=300000)
    return tool.run(symbols, strategy_names, name=name)


if __name__ == "__main__":
    # 示例
    ASTOCK_POOL = [
        ('600519.SS', '贵州茅台'),
        ('601318.SS', '中国平安'),
        ('600036.SS', '招商银行'),
        ('600887.SS', '伊利股份'),
        ('600309.SS', '万华化学'),
    ]
    
    import random
    random.seed(42)
    selected = random.sample(ASTOCK_POOL, 3)
    
    tool = BacktestTool(initial_capital=300000)
    tool.run(selected, ['rsi', 'kdj'], name="RSI+KDJ策略")
