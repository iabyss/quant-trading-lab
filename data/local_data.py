#!/usr/bin/env python3
"""
快速读取本地股票数据
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data' / 'stocks_10y'

def load_stock(code: str) -> pd.DataFrame:
    """
    加载本地股票数据
    
    Args:
        code: 股票代码 (如 '600519.SS')
    
    Returns:
        DataFrame
    """
    # 转换格式
    filename = code.replace('.', '_') + '.csv'
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"数据文件不存在: {filename}")
    
    df = pd.read_csv(filepath, parse_dates=['Date'], index_col='Date')
    df.columns = df.columns.str.lower()
    
    return df

def list_stocks() -> list:
    """列出所有本地股票"""
    files = list(DATA_DIR.glob('*.csv'))
    stocks = []
    for f in files:
        code = f.stem.replace('_', '.')
        stocks.append(code)
    return stocks

def get_random_stocks(n: int = 5) -> list:
    """随机获取n只股票"""
    import random
    stocks = list_stocks()
    return random.sample(stocks, min(n, len(stocks)))

# 测试
if __name__ == "__main__":
    print(f"本地股票数量: {len(list_stocks())}")
    print(f"\n随机5只: {get_random_stocks(5)}")
    
    # 测试读取
    df = load_stock('600519.SS')
    print(f"\n贵州茅台数据: {len(df)} 条")
    print(df.tail())
