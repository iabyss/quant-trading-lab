"""
简单移动平均线交叉策略
Simple Moving Average Crossover Strategy

策略逻辑:
- 当短期MA上穿长期MA时买入(黄金交叉)
- 当短期MA下穿长期MA时卖出(死亡交叉)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def download_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """下载历史数据"""
    data = yf.download(symbol, period=period)
    # 扁平化多级索引列
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data


def calculate_ma(data: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    """计算移动平均线"""
    data = data.copy()
    data['MA_short'] = data['Close'].rolling(window=short_window).mean()
    data['MA_long'] = data['Close'].rolling(window=long_window).mean()
    return data


def generate_signals(data: pd.DataFrame) -> pd.DataFrame:
    """生成交易信号"""
    data = data.copy()
    data['Signal'] = 0
    
    # 黄金交叉 = 买入信号 (短期MA从下往上穿越长期MA)
    data.loc[data['MA_short'] > data['MA_long'], 'Signal'] = 1
    
    # 死亡交叉 = 卖出信号 (短期MA从上往下穿越长期MA)
    data.loc[data['MA_short'] < data['MA_long'], 'Signal'] = -1
    
    # 只在信号变化时产生交易
    data['Position'] = data['Signal'].diff()
    
    return data


def backtest(data: pd.DataFrame, initial_capital: float = 10000):
    """简单回测"""
    data = data.dropna().copy()
    
    # 计算每日收益
    data['Daily_Return'] = data['Close'].pct_change()
    
    # 策略收益 (持仓时才有收益)
    data['Strategy_Return'] = data['Daily_Return'] * data['Signal'].shift(1)
    
    # 累计收益
    data['Cumulative_Market'] = (1 + data['Daily_Return'].fillna(0)).cumprod()
    data['Cumulative_Strategy'] = (1 + data['Strategy_Return'].fillna(0)).cumprod()
    
    # 最终收益
    final_market = data['Cumulative_Market'].iloc[-1] * initial_capital
    final_strategy = data['Cumulative_Strategy'].iloc[-1] * initial_capital
    
    # 计算指标
    total_return = (final_strategy - initial_capital) / initial_capital * 100
    market_return = (final_market - initial_capital) / initial_capital * 100
    
    # 夏普比率 (简化版)
    sharpe = data['Strategy_Return'].mean() / data['Strategy_Return'].std() * np.sqrt(252)
    
    # 最大回撤
    rolling_max = data['Cumulative_Strategy'].cummax()
    drawdown = (data['Cumulative_Strategy'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100
    
    results = {
        'initial_capital': initial_capital,
        'final_value': final_strategy,
        'total_return': total_return,
        'market_return': market_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'total_trades': (data['Position'].abs() > 0).sum()
    }
    
    return data, results


def plot_results(data: pd.DataFrame, symbol: str):
    """绘制结果"""
    # 确保只使用有效数据
    plot_data = data.dropna().copy()
    
    # 重命名列以适应多级索引
    if isinstance(plot_data.columns, pd.MultiIndex):
        plot_data.columns = plot_data.columns.get_level_values(0)
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    
    # 价格和MA
    axes[0].plot(plot_data['Close'], label='Price', linewidth=1)
    axes[0].plot(plot_data['MA_short'], label='MA 20', linewidth=1)
    axes[0].plot(plot_data['MA_long'], label='MA 50', linewidth=1)
    buy_signals = plot_data[plot_data['Position'] == 2]
    sell_signals = plot_data[plot_data['Position'] == -2]
    if len(buy_signals) > 0:
        axes[0].scatter(buy_signals.index, buy_signals['Close'], 
                        marker='^', color='green', s=100, label='Buy')
    if len(sell_signals) > 0:
        axes[0].scatter(sell_signals.index, sell_signals['Close'], 
                        marker='v', color='red', s=100, label='Sell')
    axes[0].set_title(f'{symbol} Price & Moving Averages')
    axes[0].legend()
    axes[0].grid(True)
    
    # 累计收益
    axes[1].plot(plot_data['Cumulative_Market'], label='Market', linewidth=1)
    axes[1].plot(plot_data['Cumulative_Strategy'], label='Strategy', linewidth=1)
    axes[1].set_title('Cumulative Returns')
    axes[1].legend()
    axes[1].grid(True)
    
    # 回撤
    rolling_max = plot_data['Cumulative_Strategy'].cummax()
    drawdown = (plot_data['Cumulative_Strategy'] - rolling_max) / rolling_max * 100
    axes[2].fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
    axes[2].set_title('Drawdown %')
    axes[2].grid(True)
    
    plt.tight_layout()
    plt.savefig(f'backtests/{symbol}_ma_crossover.png', dpi=150)
    plt.close()
    print(f"📊 图表已保存到: backtests/{symbol}_ma_crossover.png")


def run_strategy(symbol: str = "AAPL", short_ma: int = 20, long_ma: int = 50):
    """运行策略"""
    print(f"=" * 50)
    print(f"策略: 移动平均线交叉")
    print(f"标的: {symbol}")
    print(f"参数: 短期MA={short_ma}, 长期MA={long_ma}")
    print(f"=" * 50)
    
    # 获取数据
    print("\n📥 下载数据中...")
    data = download_data(symbol, "2y")
    
    # 计算MA
    print("📊 计算移动平均线...")
    data = calculate_ma(data, short_ma, long_ma)
    
    # 生成信号
    print("🎯 生成交易信号...")
    data = generate_signals(data)
    
    # 回测
    print("🔬 运行回测...")
    data, results = backtest(data)
    
    # 打印结果
    print("\n" + "=" * 50)
    print("📈 回测结果")
    print("=" * 50)
    print(f"初始资金:     ${results['initial_capital']:,.2f}")
    print(f"最终价值:     ${results['final_value']:,.2f}")
    print(f"策略收益:     {results['total_return']:.2f}%")
    print(f"市场收益:     {results['market_return']:.2f}")
    print(f"夏普比率:     {results['sharpe_ratio']:.2f}")
    print(f"最大回撤:     {results['max_drawdown']:.2f}%")
    print(f"总交易次数:   {results['total_trades']}")
    print("=" * 50)
    
    # 绘图
    plot_results(data, symbol)
    
    return results


if __name__ == "__main__":
    import sys
    
    # 默认测试AAPL
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    run_strategy(symbol)
