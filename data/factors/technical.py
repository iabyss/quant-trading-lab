"""
技术因子计算模块
"""

import pandas as pd
import numpy as np
from typing import Optional


class TechnicalFactors:
    """技术因子计算"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """RSI指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD指标"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return pd.DataFrame({
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        })
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """布林带"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return pd.DataFrame({
            'upper': upper,
            'middle': sma,
            'lower': lower
        })
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ATR平均真实波幅"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """随机指标"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return pd.DataFrame({'k': k, 'd': d})
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ADX趋向指标"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = TechnicalFactors.atr(high, low, close, period)
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def volume_profile(data: pd.DataFrame, bins: int = 50) -> pd.DataFrame:
        """成交量分布"""
        data = data.copy()
        data['price_range'] = pd.cut(data['Close'], bins=bins)
        vol_profile = data.groupby('price_range')['Volume'].sum()
        return vol_profile
    
    @staticmethod
    def calculate_all(data: pd.DataFrame) -> pd.DataFrame:
        """计算所有基础技术指标"""
        df = data.copy()
        
        # 确保列名正确
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        close = df['Close']
        high = df.get('High', close)
        low = df.get('Low', close)
        volume = df.get('Volume', pd.Series(1, index=close.index))
        
        # 均线
        for period in [5, 10, 20, 30, 60, 120, 250]:
            df[f'SMA_{period}'] = TechnicalFactors.sma(close, period)
            df[f'EMA_{period}'] = TechnicalFactors.ema(close, period)
        
        # RSI
        df['RSI_14'] = TechnicalFactors.rsi(close, 14)
        df['RSI_28'] = TechnicalFactors.rsi(close, 28)
        
        # MACD
        macd = TechnicalFactors.macd(close)
        df['MACD'] = macd['macd']
        df['MACD_Signal'] = macd['signal']
        df['MACD_Hist'] = macd['histogram']
        
        # 布林带
        bb = TechnicalFactors.bollinger_bands(close)
        df['BB_Upper'] = bb['upper']
        df['BB_Middle'] = bb['middle']
        df['BB_Lower'] = bb['lower']
        df['BB_Width'] = (bb['upper'] - bb['lower']) / bb['middle']
        
        # ATR
        df['ATR_14'] = TechnicalFactors.atr(high, low, close, 14)
        
        # 随机指标
        stoch = TechnicalFactors.stochastic(high, low, close)
        df['Stoch_K'] = stoch['k']
        df['Stoch_D'] = stoch['d']
        
        # ADX
        df['ADX_14'] = TechnicalFactors.adx(high, low, close, 14)
        
        # 成交量指标
        df['Volume_SMA_20'] = TechnicalFactors.sma(volume, 20)
        df['Volume_Ratio'] = volume / df['Volume_SMA_20']
        
        # 价格变化
        df['Daily_Return'] = close.pct_change()
        df['Volatility_20'] = df['Daily_Return'].rolling(20).std() * np.sqrt(252)
        
        return df


# 便捷函数
def sma(data: pd.Series, period: int) -> pd.Series:
    return TechnicalFactors.sma(data, period)

def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    return TechnicalFactors.rsi(data, period)

def macd(data: pd.Series, **kwargs) -> pd.DataFrame:
    return TechnicalFactors.macd(data, **kwargs)

def calculate_all(data: pd.DataFrame) -> pd.DataFrame:
    return TechnicalFactors.calculate_all(data)


if __name__ == "__main__":
    from data.fetcher import download
    
    # 测试
    df = download("AAPL", period="1mo")
    factors = calculate_all(df)
    print(factors.columns.tolist())
    print(factors.tail())
