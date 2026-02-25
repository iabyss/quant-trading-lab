#!/usr/bin/env python3
"""
基本面分析脚本
提供财务数据、估值指标、选股筛选等功能
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.fundamental import FundamentalData
from data.fetcher import DataFetcher


class FundamentalAnalysis:
    """基本面分析主类"""
    
    def __init__(self):
        self.fd = FundamentalData()
        self.fetcher = DataFetcher()
    
    def get_financial_data(self, symbol: str, statement_type: str = "income",
                          period: str = "annual") -> str:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            statement_type: 报表类型 (income/balance/cashflow)
            period: 周期 (annual/quarterly)
        
        Returns:
            JSON格式数据
        """
        try:
            data = self.fd.get_financial_statement(symbol)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def get_valuation(self, symbol: str, price: float = None) -> str:
        """
        获取估值数据
        
        Args:
            symbol: 股票代码
            price: 当前价格
        
        Returns:
            JSON格式数据
        """
        try:
            # 如果没有提供价格，尝试获取
            if price is None:
                df = self.fetcher.download(symbol, period="1d")
                if df is not None and len(df) > 0:
                    price = df['Close'].iloc[-1]
                else:
                    price = 0
            
            valuation = self.fd.calculate_valuation(symbol, price)
            return json.dumps(valuation, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def get_financial_ratios(self, symbol: str) -> str:
        """获取财务比率"""
        try:
            ratios = self.fd.get_financial_ratios(symbol)
            return json.dumps(ratios, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def screen_stocks(self, criteria: dict) -> str:
        """
        选股筛选
        
        Args:
            criteria: 筛选条件
        
        Returns:
            JSON格式结果
        """
        try:
            stocks = self.fd.screening(criteria)
            
            # 获取每只股票的基本面
            results = []
            for symbol in stocks:
                try:
                    valuation = self.fd.calculate_valuation(symbol, 10)
                    ratios = self.fd.get_financial_ratios(symbol)
                    
                    results.append({
                        'symbol': symbol,
                        'pe_ratio': valuation.get('pe_ratio', 0),
                        'pb_ratio': valuation.get('pb_ratio', 0),
                        'roe': ratios['profitability']['roe'],
                        'net_margin': ratios['profitability']['net_margin'],
                    })
                except:
                    continue
            
            return json.dumps({
                "criteria": criteria,
                "results": results,
                "count": len(results)
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def compare_stocks(self, symbols: list) -> str:
        """对比多只股票"""
        try:
            results = []
            
            for symbol in symbols:
                try:
                    valuation = self.fd.calculate_valuation(symbol, 10)
                    ratios = self.fd.get_financial_ratios(symbol)
                    growth = self.fd.get_growth_metrics(symbol)
                    
                    results.append({
                        'symbol': symbol,
                        'valuation': valuation,
                        'profitability': ratios['profitability'],
                        'growth': growth
                    })
                except:
                    continue
            
            # 构建对比表格
            comparison = {
                'stocks': symbols,
                'metrics': {
                    'pe': {s['symbol']: s['valuation'].get('pe_ratio', 0) for s in results},
                    'pb': {s['symbol']: s['valuation'].get('pb_ratio', 0) for s in results},
                    'roe': {s['symbol']: s['profitability'].get('roe', 0) for s in results},
                    'net_margin': {s['symbol']: s['profitability'].get('net_margin', 0) for s in results},
                    'revenue_growth': {s['symbol']: s['growth'].get('revenue_growth', 0) for s in results},
                }
            }
            
            return json.dumps(comparison, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def comprehensive_analysis(self, symbol: str) -> str:
        """综合基本面分析"""
        try:
            # 获取当前价格
            df = self.fetcher.download(symbol, period="1d")
            price = df['Close'].iloc[-1] if df is not None and len(df) > 0 else 0
            
            # 获取各项数据
            financial = self.fd.get_financial_statement(symbol)
            valuation = self.fd.calculate_valuation(symbol, price)
            ratios = self.fd.get_financial_ratios(symbol)
            dividend = self.fd.get_dividend_info(symbol)
            growth = self.fd.get_growth_metrics(symbol)
            
            # 综合评分
            score = 0
            if ratios['profitability']['roe'] > 0.15:
                score += 25
            elif ratios['profitability']['roe'] > 0.10:
                score += 15
            
            if 0 < valuation.get('pe_ratio', 0) < 25:
                score += 25
            
            if growth.get('profit_growth', 0) > 0.2:
                score += 25
            
            if dividend.get('dividend_yield', 0) > 0.02:
                score += 25
            
            result = {
                'symbol': symbol,
                'price': price,
                'financial': financial,
                'valuation': valuation,
                'ratios': ratios,
                'dividend': dividend,
                'growth': growth,
                'score': score,
                'rating': 'A' if score >= 80 else 'B' if score >= 60 else 'C' if score >= 40 else 'D'
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="基本面分析工具")
    parser.add_argument("command", 
                       choices=["financial", "valuation", "ratios", "screen", "compare", "analysis"],
                       help="命令")
    parser.add_argument("--symbol", "-s", help="股票代码")
    parser.add_argument("--symbols", "-S", help="股票代码列表(逗号分隔)")
    parser.add_argument("--statement", default="income", help="报表类型")
    parser.add_argument("--period", default="annual", help="周期")
    parser.add_argument("--price", "-p", type=float, help="当前价格")
    parser.add_argument("--criteria", "-c", help="筛选条件JSON")
    
    args = parser.parse_args()
    
    fa = FundamentalAnalysis()
    
    if args.command == "financial":
        print(fa.get_financial_data(args.symbol, args.statement, args.period))
    elif args.command == "valuation":
        print(fa.get_valuation(args.symbol, args.price))
    elif args.command == "ratios":
        print(fa.get_financial_ratios(args.symbol))
    elif args.command == "screen":
        criteria = json.loads(args.criteria) if args.criteria else {}
        print(fa.screen_stocks(criteria))
    elif args.command == "compare":
        symbols = args.symbols.split(',') if args.symbols else []
        print(fa.compare_stocks(symbols))
    elif args.command == "analysis":
        print(fa.comprehensive_analysis(args.symbol))


if __name__ == "__main__":
    main()
