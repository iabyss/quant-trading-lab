"""
数据获取模块
支持 A股、港股、美股、加密货币
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        self.cache = {}
    
    def download(self, symbol: str, period: str = "1y", 
                 interval: str = "1d", start: str = None, end: str = None) -> pd.DataFrame:
        """
        下载历史数据
        
        Args:
            symbol: 股票代码
                - A股: 600893.SS (上交所), 000001.SZ (深交所)
                - 港股: 0700.HK
                - 美股: AAPL, TSLA
                - 加密: BTC-USD, ETH-USD
            period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: K线周期 (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
            start: 开始日期 (YYYY-MM-DD)
            end: 结束日期 (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLCV data
        """
        # A股特殊处理
        if symbol.endswith('.SS') or symbol.endswith('.SZ'):
            symbol = symbol
        
        try:
            data = yf.download(
                symbol, 
                period=period, 
                interval=interval,
                start=start,
                end=end,
                progress=False
            )
            
            # 扁平化多级索引
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # 添加符号列
            data['Symbol'] = symbol
            
            return data
            
        except Exception as e:
            print(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()
    
    def get_realtime(self, symbol: str) -> Dict:
        """获取实时行情"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'price': info.get('currentPrice', 0),
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe': info.get('trailingPE', 0),
                'name': info.get('shortName', symbol),
                'timestamp': datetime.now()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_multiple(self, symbols: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
        """批量获取多只股票数据"""
        result = {}
        for symbol in symbols:
            result[symbol] = self.download(symbol, period)
        return result
    
    def get_ohlcv(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取最近N天的OHLCV数据"""
        end = datetime.now()
        start = end - timedelta(days=days)
        return self.download(symbol, start=start.strftime('%Y-%m-%d'))


# 单例
fetcher = DataFetcher()


# 便捷函数
def download(symbol: str, **kwargs) -> pd.DataFrame:
    """下载股票数据"""
    return fetcher.download(symbol, **kwargs)

def get_realtime(symbol: str) -> Dict:
    """获取实时行情"""
    return fetcher.get_realtime(symbol)

def get_multiple(symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
    """批量获取"""
    return fetcher.get_multiple(symbols, **kwargs)


if __name__ == "__main__":
    # 测试
    print("Testing data fetcher...")
    
    # A股
    df = download("600893.SS", period="1mo")
    print(f"A股数据: {len(df)} rows")
    
    # 美股
    df = download("AAPL", period="1mo")
    print(f"美股数据: {len(df)} rows")
    
    # 加密
    df = download("BTC-USD", period="1mo")
    print(f"BTC数据: {len(df)} rows")
    
    # 实时
    rt = get_realtime("AAPL")
    print(f"实时: {rt.get('price', 'N/A')}")
