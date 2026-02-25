"""
基本面数据获取模块
支持A股、港股、美股真实数据
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import warnings
warnings.filterwarnings('ignore')

# 尝试导入数据源
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


class FundamentalData:
    """基本面数据获取"""
    
    def __init__(self, cache_dir: str = None, use_cache: bool = True):
        """
        初始化
        
        Args:
            cache_dir: 缓存目录
            use_cache: 是否使用缓存
        """
        self.cache_dir = cache_dir or 'data/fundamental_cache'
        self.use_cache = use_cache
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print(f"数据源状态: yfinance={'✓' if YFINANCE_AVAILABLE else '✗'}, akshare={'✓' if AKSHARE_AVAILABLE else '✗'}")
    
    def _get_stock_type(self, symbol: str) -> str:
        """
        判断股票类型
        
        Args:
            symbol: 股票代码
        
        Returns:
            'A' (A股), 'HK' (港股), 'US' (美股)
        """
        symbol = symbol.upper()
        
        if symbol.endswith('.HK') or symbol.endswith('.HK'):
            return 'HK'
        elif symbol.endswith('.SS') or symbol.endswith('.SZ'):
            return 'A'
        elif any(s in symbol for s in ['/VA', '/VB', '/VC']) or len(symbol) <= 5:
            return 'US'
        else:
            # 纯数字判断
            if symbol.isdigit():
                if len(symbol) == 6:
                    return 'A'
            return 'US'
    
    def _convert_hk_symbol(self, symbol: str) -> str:
        """转换港股代码为Yahoo Finance格式"""
        # 01810.HK -> 1810.HK
        if '.HK' in symbol.upper():
            code = symbol.replace('.HK', '').replace('.hk', '')
            # 去除前导0
            code = str(int(code))
            return f"{code}.HK"
        return symbol
    
    def get_financial_statement(self, symbol: str, year: int = None) -> Dict:
        """
        获取财务报表数据
        
        Args:
            symbol: 股票代码
            year: 年份 (默认最新)
        
        Returns:
            财务数据字典
        """
        stock_type = self._get_stock_type(symbol)
        
        # 尝试获取真实数据
        try:
            if stock_type == 'HK':
                return self._get_hk_financial_data(symbol)
            elif stock_type == 'US':
                return self._get_us_financial_data(symbol)
            elif stock_type == 'A':
                return self._get_a_stock_financial_data(symbol)
        except Exception as e:
            print(f"获取真实数据失败: {e}")
        
        # 返回模拟数据
        return self._mock_financial_data(symbol, year)
    
    def _get_hk_financial_data(self, symbol: str) -> Dict:
        """获取港股财务数据"""
        # 尝试使用yfinance
        if YFINANCE_AVAILABLE:
            try:
                yf_symbol = self._convert_hk_symbol(symbol)
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                if info:
                    return {
                        'symbol': symbol,
                        'year': datetime.now().year,
                        'market_cap': info.get('marketCap', 0),
                        'pe_ratio': info.get('trailingPE', 0) or 0,
                        'pb_ratio': info.get('priceToBook', 0) or 0,
                        'ps_ratio': info.get('priceToSalesTrailing12Months', 0) or 0,
                        'dividend_yield': info.get('dividendYield', 0) or 0,
                        'beta': info.get('beta', 0) or 0,
                        '52w_high': info.get('fiftyTwoWeekHigh', 0) or 0,
                        '52w_low': info.get('fiftyTwoWeekLow', 0) or 0,
                        'avg_volume': info.get('averageVolume', 0) or 0,
                        'profit_margin': info.get('profitMargins', 0) or 0,
                        'roe': info.get('returnOnEquity', 0) or 0,
                        'roa': info.get('returnOnAssets', 0) or 0,
                        'debt_to_equity': info.get('debtToEquity', 0) or 0,
                        'revenue': info.get('totalRevenue', 0) or 0,
                        'net_income': info.get('netIncomeToCommon', 0) or 0,
                        'eps': info.get('epsTrailingTwelveMonths', 0) or 0,
                        'revenue_growth': info.get('revenueGrowth', 0) or 0,
                        'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth', 0) or 0,
                        'source': 'yfinance'
                    }
            except Exception as e:
                print(f"yfinance获取失败: {e}")
        
        # 返回模拟数据
        return self._mock_financial_data(symbol, None)
    
    def _get_us_financial_data(self, symbol: str) -> Dict:
        """获取美股财务数据"""
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                if info:
                    return {
                        'symbol': symbol,
                        'year': datetime.now().year,
                        'market_cap': info.get('marketCap', 0),
                        'pe_ratio': info.get('trailingPE', 0) or 0,
                        'forward_pe': info.get('forwardPE', 0) or 0,
                        'pb_ratio': info.get('priceToBook', 0) or 0,
                        'ps_ratio': info.get('priceToSalesTrailing12Months', 0) or 0,
                        'dividend_yield': info.get('dividendYield', 0) or 0,
                        'beta': info.get('beta', 0) or 0,
                        '52w_high': info.get('fiftyTwoWeekHigh', 0) or 0,
                        '52w_low': info.get('fiftyTwoWeekLow', 0) or 0,
                        'avg_volume': info.get('averageVolume', 0) or 0,
                        'profit_margin': info.get('profitMargins', 0) or 0,
                        'operating_margin': info.get('operatingMargins', 0) or 0,
                        'roe': info.get('returnOnEquity', 0) or 0,
                        'roa': info.get('returnOnAssets', 0) or 0,
                        'debt_to_equity': info.get('debtToEquity', 0) or 0,
                        'current_ratio': info.get('currentRatio', 0) or 0,
                        'quick_ratio': info.get('quickRatio', 0) or 0,
                        'revenue': info.get('totalRevenue', 0) or 0,
                        'revenue_growth': info.get('revenueGrowth', 0) or 0,
                        'earnings_growth': info.get('earningsGrowth', 0) or 0,
                        'eps': info.get('epsTrailingTwelveMonths', 0) or 0,
                        'eps_forward': info.get('epsForward', 0) or 0,
                        'target_mean_price': info.get('targetMeanPrice', 0) or 0,
                        'recommendation': info.get('recommendationKey', 'N/A'),
                        'source': 'yfinance'
                    }
            except Exception as e:
                print(f"yfinance获取失败: {e}")
        
        return self._mock_financial_data(symbol, None)
    
    def _get_a_stock_financial_data(self, symbol: str) -> Dict:
        """获取A股财务数据"""
        # 尝试使用akshare
        if AKSHARE_AVAILABLE:
            try:
                # 提取股票代码
                code = symbol.replace('.SS', '').replace('.SZ', '')
                
                # 获取实时行情
                df = ak.stock_individual_info_em(symbol=code)
                if df is not None and len(df) > 0:
                    info = dict(zip(df['item'].tolist(), df['value'].tolist()))
                    
                    return {
                        'symbol': symbol,
                        'year': datetime.now().year,
                        'name': info.get('股票名称', ''),
                        'market_cap': self._parse_number(info.get('总市值', '0')),
                        'pe': self._parse_number(info.get('市盈率-动态', '0')),
                        'pb': self._parse_number(info.get('市净率', '0')),
                        'roe': self._parse_number(info.get('净资产收益率', '0')) / 100,
                        'revenue': self._parse_number(info.get('营业总收入', '0')),
                        'net_profit': self._parse_number(info.get('净利润', '0')),
                        'source': 'akshare'
                    }
            except Exception as e:
                print(f"akshare获取失败: {e}")
        
        return self._mock_financial_data(symbol, None)
    
    def _parse_number(self, s: str) -> float:
        """解析数字字符串"""
        if not s or s == '-':
            return 0
        try:
            # 处理亿、万等
            s = str(s).replace(',', '')
            if '亿' in s:
                return float(s.replace('亿', '')) * 1e8
            elif '万' in s:
                return float(s.replace('万', '')) * 1e4
            elif '%' in s:
                return float(s.replace('%', ''))
            return float(s)
        except:
            return 0
    
    def _mock_financial_data(self, symbol: str, year: int = None) -> Dict:
        """生成模拟财务数据"""
        return {
            'symbol': symbol,
            'year': year or datetime.now().year,
            'revenue': np.random.uniform(10, 100) * 1e8,
            'net_profit': np.random.uniform(1, 20) * 1e8,
            'total_assets': np.random.uniform(50, 500) * 1e8,
            'total_equity': np.random.uniform(20, 200) * 1e8,
            'roe': np.random.uniform(0.05, 0.25),
            'gross_margin': np.random.uniform(0.2, 0.5),
            'net_margin': np.random.uniform(0.05, 0.2),
            'debt_ratio': np.random.uniform(0.3, 0.7),
            'current_ratio': np.random.uniform(1, 3),
            'quick_ratio': np.random.uniform(0.5, 2),
            'source': 'mock'
        }
    
    def calculate_valuation(self, symbol: str, price: float) -> Dict:
        """
        计算估值指标
        
        Args:
            symbol: 股票代码
            price: 当前价格
        
        Returns:
            估值指标字典
        """
        financial = self.get_financial_statement(symbol)
        
        # 从真实数据获取估值
        pe_ratio = financial.get('pe_ratio') or financial.get('pe') or 0
        pb_ratio = financial.get('pb_ratio') or financial.get('pb') or 0
        market_cap = financial.get('market_cap', 0)
        dividend_yield = financial.get('dividend_yield', 0)
        
        # 如果有EPS，计算PE
        eps = financial.get('eps', 0)
        if eps and eps > 0 and price and price > 0:
            pe_ratio = price / eps
        
        # 计算PEG (假设利润增长10%)
        peg = pe_ratio / 10 if pe_ratio else 0
        
        return {
            'symbol': symbol,
            'price': price,
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'market_cap': market_cap,
            'dividend_yield': dividend_yield,
            'peg': peg,
            'source': financial.get('source', 'unknown')
        }
    
    def get_financial_ratios(self, symbol: str) -> Dict:
        """获取财务比率"""
        financial = self.get_financial_statement(symbol)
        
        return {
            'profitability': {
                'roe': financial.get('roe', 0),
                'roa': financial.get('roa', 0),
                'gross_margin': financial.get('gross_margin', 0),
                'net_margin': financial.get('profit_margin', 0) or financial.get('net_margin', 0),
            },
            'liquidity': {
                'current_ratio': financial.get('current_ratio', 0),
                'quick_ratio': financial.get('quick_ratio', 0),
            },
            'leverage': {
                'debt_ratio': financial.get('debt_ratio', 0),
                'debt_to_equity': financial.get('debt_to_equity', 0),
            },
            'efficiency': {
                'asset_turnover': financial.get('asset_turnover', 0),
            }
        }
    
    def get_dividend_info(self, symbol: str) -> Dict:
        """获取分红信息"""
        financial = self.get_financial_statement(symbol)
        
        return {
            'symbol': symbol,
            'dividend_yield': financial.get('dividend_yield', 0),
            'dividend_per_share': financial.get('dividend_per_share', 0),
            'payout_ratio': financial.get('payout_ratio', 0),
        }
    
    def get_growth_metrics(self, symbol: str) -> Dict:
        """获取增长指标"""
        financial = self.get_financial_statement(symbol)
        
        return {
            'revenue_growth': financial.get('revenue_growth', 0),
            'earnings_growth': financial.get('earnings_growth', 0) or financial.get('earnings_quarterly_growth', 0),
            'eps_growth': financial.get('eps_growth', 0),
        }
    
    def get_realtime_quote(self, symbol: str) -> Dict:
        """
        获取实时行情
        
        Args:
            symbol: 股票代码
        
        Returns:
            实时行情数据
        """
        stock_type = self._get_stock_type(symbol)
        
        if YFINANCE_AVAILABLE:
            try:
                if stock_type == 'HK':
                    yf_symbol = self._convert_hk_symbol(symbol)
                else:
                    yf_symbol = symbol
                
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                return {
                    'symbol': symbol,
                    'name': info.get('longName', info.get('shortName', '')),
                    'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                    'change': info.get('regularMarketChange', 0),
                    'change_pct': info.get('regularMarketChangePercent', 0),
                    'open': info.get('regularMarketOpen', 0),
                    'high': info.get('regularMarketDayHigh', 0),
                    'low': info.get('regularMarketDayLow', 0),
                    'volume': info.get('regularMarketVolume', 0),
                    'market_cap': info.get('marketCap', 0),
                    'pe': info.get('trailingPE', 0),
                    '52w_high': info.get('fiftyTwoWeekHigh', 0),
                    '52w_low': info.get('fiftyTwoWeekLow', 0),
                    'source': 'yfinance'
                }
            except Exception as e:
                print(f"获取实时行情失败: {e}")
        
        return {'symbol': symbol, 'error': '无法获取数据'}
    
    def get_all_metrics(self, symbol: str, price: float = None) -> Dict:
        """
        获取所有基本面指标
        
        Args:
            symbol: 股票代码
            price: 当前价格
        
        Returns:
            完整的基本面数据
        """
        # 如果没有提供价格，尝试获取实时价格
        if price is None:
            quote = self.get_realtime_quote(symbol)
            price = quote.get('price', 0)
        
        return {
            'quote': self.get_realtime_quote(symbol),
            'financial': self.get_financial_statement(symbol),
            'valuation': self.calculate_valuation(symbol, price),
            'ratios': self.get_financial_ratios(symbol),
            'dividend': self.get_dividend_info(symbol),
            'growth': self.get_growth_metrics(symbol),
        }


def get_fundamental_data(symbol: str, price: float = None) -> Dict:
    """
    快速获取基本面数据
    
    Args:
        symbol: 股票代码
        price: 当前价格
    
    Returns:
        基本面数据
    """
    fd = FundamentalData()
    return fd.get_all_metrics(symbol, price)


# 测试
if __name__ == "__main__":
    fd = FundamentalData()
    
    # 测试港股
    print("="*60)
    print("测试小米集团 (01810.HK)")
    print("="*60)
    
    quote = fd.get_realtime_quote('01810.HK')
    print(f"实时行情: {quote.get('price', 'N/A')}")
    
    financial = fd.get_financial_statement('01810.HK')
    print(f"数据来源: {financial.get('source', 'unknown')}")
