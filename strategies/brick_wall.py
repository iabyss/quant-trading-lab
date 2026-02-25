"""
砖型图策略分析
Brick Wall Indicator Strategy Analysis

策略逻辑:
- 基于价格波动率的动量指标
- 当VAR6A上穿4时产生买入信号
- 当VAR6A下穿时产生卖出信号
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def calculate_brick_indicator(data: pd.DataFrame) -> pd.DataFrame:
    """计算砖型图指标"""
    data = data.copy()
    
    # 扁平化多级索引
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 计算基础变量
    high_4 = data['High'].rolling(window=4).max()
    low_4 = data['Low'].rolling(window=4).min()
    
    # VAR1A: (HHV(HIGH,4)-CLOSE)/(HHV(HIGH,4)-LLV(LOW,4))*100-90
    range_4 = high_4 - low_4
    data['VAR1A'] = ((high_4 - data['Close']) / range_4 * 100 - 90).fillna(0)
    
    # VAR2A: SMA(VAR1A,4,1)+100
    data['VAR2A'] = data['VAR1A'].rolling(window=4).mean() + 100
    
    # VAR3A: (CLOSE-LLV(LOW,4))/(HHV(HIGH,4)-LLV(LOW,4))*100
    data['VAR3A'] = ((data['Close'] - low_4) / range_4 * 100).fillna(0)
    
    # VAR4A: SMA(VAR3A,6,1)
    data['VAR4A'] = data['VAR3A'].rolling(window=6).mean()
    
    # VAR5A: SMA(VAR4A,6,1)+100
    data['VAR5A'] = data['VAR4A'].rolling(window=6).mean() + 100
    
    # VAR6A: VAR5A - VAR2A
    data['VAR6A'] = data['VAR5A'] - data['VAR2A']
    
    # 砖型图: IF(VAR6A>4, VAR6A-4, 0)
    data['砖型图'] = data['VAR6A'].apply(lambda x: max(x - 4, 0) if x > 4 else 0)
    
    return data


def generate_signals(data: pd.DataFrame) -> pd.DataFrame:
    """生成交易信号"""
    data = data.copy()
    
    # AA: (REF(砖型图,1)<砖型图) - 砖块变大
    data['AA'] = (data['砖型图'].shift(1) < data['砖型图']).astype(int)
    
    # BB: (REF(砖型图,1)>砖型图) - 砖块变小
    data['BB'] = (data['砖型图'].shift(1) > data['砖型图']).astype(int)
    
    # CC: REF(AA,1)=0 && AA=1 首次从0变1
    data['CC'] = ((data['AA'].shift(1) == 0) & (data['AA'] == 1)).astype(int)
    
    # XG: CC>0 买入信号
    data['Buy_Signal'] = (data['CC'] > 0).astype(int)
    
    # 卖出信号: BB首次从0变1
    data['Sell_Signal'] = ((data['BB'].shift(1) == 0) & (data['BB'] == 1)).astype(int)
    
    return data


def backtest(data: pd.DataFrame, initial_capital: float = 10000) -> dict:
    """回测策略"""
    data = data.dropna().copy()
    
    # 持仓状态
    position = 0
    entry_price = 0
    trades = []
    
    for i in range(1, len(data)):
        # 买入信号 且 未持仓
        if data.iloc[i]['Buy_Signal'] == 1 and position == 0:
            position = 1
            entry_price = data.iloc[i]['Close']
            trades.append({
                'type': 'BUY',
                'date': data.index[i],
                'price': entry_price,
                'brick': data.iloc[i]['砖型图']
            })
        
        # 卖出信号 且 持仓
        elif data.iloc[i]['Sell_Signal'] == 1 and position == 1:
            position = 0
            exit_price = data.iloc[i]['Close']
            profit_pct = (exit_price - entry_price) / entry_price * 100
            trades.append({
                'type': 'SELL',
                'date': data.index[i],
                'price': exit_price,
                'brick': data.iloc[i]['砖型图'],
                'profit_pct': profit_pct
            })
    
    # 计算收益
    if trades:
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        total_profit = sum(t.get('profit_pct', 0) for t in trades if t['type'] == 'SELL')
        wins = sum(1 for t in trades if t['type'] == 'SELL' and t.get('profit_pct', 0) > 0)
        losses = sum(1 for t in trades if t['type'] == 'SELL' and t.get('profit_pct', 0) <= 0)
        win_rate = wins / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            'total_trades': len(buy_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'trades': trades
        }
    
    return {'total_trades': 0, 'trades': []}


def analyze_strategy(symbol: str, period: str = "2y"):
    """分析策略"""
    print(f"\n{'='*60}")
    print(f"📊 砖型图策略分析: {symbol}")
    print(f"{'='*60}")
    
    # 下载数据
    print("📥 下载数据...")
    data = yf.download(symbol, period=period)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 计算指标
    print("📊 计算指标...")
    data = calculate_brick_indicator(data)
    data = generate_signals(data)
    
    # 回测
    print("🔬 回测中...")
    results = backtest(data)
    
    # 打印结果
    print(f"\n📈 回测结果:")
    print(f"  总交易次数: {results['total_trades']}")
    print(f"  盈利次数:   {results.get('wins', 0)}")
    print(f"  亏损次数:   {results.get('losses', 0)}")
    print(f"  胜率:       {results.get('win_rate', 0):.1f}%")
    print(f"  总收益:     {results.get('total_profit', 0):.2f}%")
    
    # 打印交易记录
    print(f"\n📋 交易记录:")
    for t in results['trades'][:10]:
        if t['type'] == 'BUY':
            print(f"  🟢 买入 {t['date'].strftime('%Y-%m-%d')} @ {t['price']:.2f} 砖值:{t['brick']:.2f}")
        else:
            print(f"  🔴 卖出 {t['date'].strftime('%Y-%m-%d')} @ {t['price']:.2f} 砖值:{t['brick']:.2f} 收益:{t.get('profit_pct', 0):.2f}%")
    
    return data, results


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    analyze_strategy(symbol)
