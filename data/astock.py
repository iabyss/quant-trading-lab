"""
A股数据获取模块
针对A股特殊规则优化
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime, timedelta


class AStockData:
    """A股数据获取"""
    
    # A股代码后缀映射
    EXCHANGE_SUFFIX = {
        'sh': '.SS',  # 上交所
        'sz': '.SZ',  # 深交所
        'ss': '.SS',  # 上交所别名
    }
    
    # 常用指数代码
    INDEX_CODES = {
        'sh000001': '.SS',  # 上证指数
        'sz399001': '',     # 深证成指
        'sz399006': '',     # 创业板指
        'sh000300': '.SS',  # 沪深300
        'sh000016': '.SS',  # 上证50
    }
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """
        标准化A股代码
        
        Args:
            code: 600893, 600893.SS, 000001.SZ 等
        
        Returns:
            yfinance格式代码
        """
        code = str(code).strip().upper()
        
        # 已经是yfinance格式
        if '.SS' in code or '.SZ' in code:
            return code
        
        # 纯数字代码
        if code.isdigit():
            if len(code) == 6:
                if code.startswith('6'):
                    return f"{code}.SS"
                elif code.startswith(('0', '3')):
                    return f"{code}.SZ"
        
        return code
    
    @staticmethod
    def download(
        code: str,
        period: str = "1y",
        start: str = None,
        end: str = None,
        adjust: bool = True
    ) -> pd.DataFrame:
        """
        下载A股数据
        
        Args:
            code: A股代码 (如 600893, 600893.SS)
            period: 周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
            start: 开始日期
            end: 结束日期
            adjust: 是否复权
        
        Returns:
            DataFrame with OHLCV
        """
        code = AStockData.normalize_code(code)
        
        try:
            data = yf.download(
                code,
                period=period,
                start=start,
                end=end,
                progress=False,
                auto_adjust=False  # A股建议不复权
            )
            
            # 扁平化多级索引
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            return data
            
        except Exception as e:
            print(f"Error downloading {code}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_realtime(code: str) -> Dict:
        """获取实时行情"""
        code = AStockData.normalize_code(code)
        
        try:
            ticker = yf.Ticker(code)
            info = ticker.info
            
            return {
                'code': code,
                'name': info.get('shortName', ''),
                'price': info.get('currentPrice', 0),
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'close': info.get('previousClose', 0),
                'volume': info.get('volume', 0),
                'amount': info.get('avgVolume', 0),
                'turnover': info.get('turnoverRate', 0),
                'pe': info.get('trailingPE', 0),
                'pb': info.get('priceToBook', 0),
                'market_cap': info.get('marketCap', 0),
                'timestamp': datetime.now()
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_kline(
        code: str,
        start: str = None,
        end: str = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            code: 股票代码
            start: 开始日期 YYYY-MM-DD
            end: 结束日期 YYYY-MM-DD
            interval: K线周期
                - 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
        
        Returns:
            K线数据
        """
        code = AStockData.normalize_code(code)
        
        # yfinance不支持A股分钟数据，回退到日线
        if interval in ['1m', '5m', '15m', '30m', '1h']:
            print(f"Warning: A股分钟数据暂不支持，自动切换为日线")
            interval = "1d"
        
        return AStockData.download(code, start=start, end=end)
    
    @staticmethod
    def get_recent_data(code: str, days: int = 30) -> pd.DataFrame:
        """获取最近N天数据"""
        end = datetime.now()
        start = end - timedelta(days=days * 2)  # 多取一些防止周末
        return AStockData.download(code, start=start.strftime('%Y-%m-%d'))


class AStockCalculator:
    """A股特有计算器"""
    
    @staticmethod
    def turnover_rate(volume: float, market_cap: float) -> float:
        """计算换手率"""
        if market_cap > 0:
            return (volume / market_cap) * 100
        return 0
    
    @staticmethod
    def pe_ttm(price: float, eps: float) -> float:
        """滚动市盈率"""
        if eps != 0:
            return price / eps
        return 0
    
    @staticmethod
    def pb(price: float, book_value: float) -> float:
        """市净率"""
        if book_value != 0:
            return price / book_value
        return 0
    
    @staticmethod
    def amplitude(high: float, low: float, prev_close: float) -> float:
        """振幅"""
        if prev_close > 0:
            return ((high - low) / prev_close) * 100
        return 0
    
    @staticmethod
    def change_pct(current: float, prev: float) -> float:
        """涨跌幅"""
        if prev > 0:
            return ((current - prev) / prev) * 100
        return 0


# 便捷函数
def download_astock(code: str, **kwargs) -> pd.DataFrame:
    """下载A股数据"""
    return AStockData.download(code, **kwargs)

def get_realtime_astock(code: str) -> Dict:
    """获取A股实时行情"""
    return AStockData.get_realtime(code)


if __name__ == "__main__":
    # 测试
    print("=" * 50)
    print("测试 A股数据获取")
    print("=" * 50)
    
    # 测试代码标准化
    codes = ['600893', '600893.SS', '000001', '000001.SZ']
    print("\n代码标准化测试:")
    for code in codes:
        normalized = AStockData.normalize_code(code)
        print(f"  {code} -> {normalized}")
    
    # 下载数据
    print("\n下载航发动力 (600893) 数据:")
    df = AStockData.download('600893', period='1mo')
    if len(df) > 0:
        print(f"  数据条数: {len(df)}")
        print(f"  最新收盘: {df['Close'].iloc[-1]:.2f}")
        print(f"  日期范围: {df.index[0]} ~ {df.index[-1]}")
    
    # 实时行情
    print("\n实时行情:")
    rt = AStockData.get_realtime('600893')
    if 'error' not in rt:
        print(f"  名称: {rt.get('name', 'N/A')}")
        print(f"  价格: {rt.get('price', 'N/A')}")
        print(f"  涨跌: {rt.get('price', 0) - rt.get('close', 0):+.2f}")
    else:
        print(f"  Error: {rt.get('error')}")
