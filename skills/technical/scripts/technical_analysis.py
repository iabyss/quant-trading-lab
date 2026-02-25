#!/usr/bin/env python3
"""
技术分析脚本
提供技术指标计算、信号生成、趋势分析等功能
"""

import sys
import json
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.fetcher import DataFetcher
from data.factors.technical import TechnicalFactors
from strategies.signals import SignalGenerator, SignalType


class TechnicalAnalysis:
    """技术分析主类"""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.factors = TechnicalFactors()
    
    def get_data(self, symbol: str, period: str = "3mo") -> str:
        """获取股票数据"""
        try:
            df = self.fetcher.download(symbol, period=period)
            if df.empty:
                return json.dumps({"error": f"无法获取 {symbol} 的数据"}, ensure_ascii=False)
            return df.to_json(orient='records')
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def calculate_indicators(self, symbol: str, indicators: str = "RSI,MACD,BOLL", 
                             period: int = 14) -> str:
        """
        计算技术指标
        
        Args:
            symbol: 股票代码
            indicators: 指标列表，逗号分隔
            period: 计算周期
        
        Returns:
            JSON格式的指标数据
        """
        try:
            # 获取数据
            df = self.fetcher.download(symbol, period="6mo")
            if df.empty:
                return json.dumps({"error": f"无法获取 {symbol} 的数据"}, ensure_ascii=False)
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            result = {
                "symbol": symbol,
                "last_price": float(close.iloc[-1]),
                "indicators": {}
            }
            
            # 计算各指标
            ind_list = [i.strip().upper() for i in indicators.split(',')]
            
            if 'MA' in ind_list or 'SMA' in ind_list:
                result['indicators']['MA'] = {
                    "MA5": float(self.factors.sma(close, 5).iloc[-1]),
                    "MA10": float(self.factors.sma(close, 10).iloc[-1]),
                    "MA20": float(self.factors.sma(close, 20).iloc[-1]),
                    "MA60": float(self.factors.sma(close, 60).iloc[-1]),
                }
            
            if 'EMA' in ind_list:
                result['indicators']['EMA'] = {
                    "EMA12": float(self.factors.ema(close, 12).iloc[-1]),
                    "EMA26": float(self.factors.ema(close, 26).iloc[-1]),
                }
            
            if 'RSI' in ind_list:
                rsi = self.factors.rsi(close, period)
                result['indicators']['RSI'] = {
                    "value": float(rsi.iloc[-1]),
                    "period": period,
                    "signal": "超买" if rsi.iloc[-1] > 70 else "超卖" if rsi.iloc[-1] < 30 else "中性"
                }
            
            if 'MACD' in ind_list:
                macd_df = self.factors.macd(close)
                result['indicators']['MACD'] = {
                    "macd": float(macd_df['macd'].iloc[-1]),
                    "signal": float(macd_df['signal'].iloc[-1]),
                    "histogram": float(macd_df['histogram'].iloc[-1]),
                    "crossover": "金叉" if macd_df['histogram'].iloc[-1] > 0 and macd_df['histogram'].iloc[-2] <= 0 
                                 else "死叉" if macd_df['histogram'].iloc[-1] < 0 and macd_df['histogram'].iloc[-2] >= 0 
                                 else "中性"
                }
            
            if 'BOLL' in ind_list:
                boll = self.factors.bollinger_bands(close, period=20)
                result['indicators']['BOLL'] = {
                    "upper": float(boll['upper'].iloc[-1]),
                    "middle": float(boll['middle'].iloc[-1]),
                    "lower": float(boll['lower'].iloc[-1]),
                    "position": "上轨" if close.iloc[-1] > boll['upper'].iloc[-1] 
                               else "下轨" if close.iloc[-1] < boll['lower'].iloc[-1] 
                               else "中轨"
                }
            
            if 'ATR' in ind_list:
                atr = self.factors.atr(high, low, close, period)
                result['indicators']['ATR'] = {
                    "value": float(atr.iloc[-1]),
                    "period": period
                }
            
            if 'KDJ' in ind_list:
                kdj = self.factors.stochastic(high, low, close)
                result['indicators']['KDJ'] = {
                    "K": float(kdj['k'].iloc[-1]),
                    "D": float(kdj['d'].iloc[-1]),
                    "J": float(3 * kdj['k'].iloc[-1] - 2 * kdj['d'].iloc[-1]),
                    "signal": "超买" if kdj['k'].iloc[-1] > 80 else "超卖" if kdj['k'].iloc[-1] < 20 else "中性"
                }
            
            if 'ADX' in ind_list:
                adx = self.factors.adx(high, low, close, period)
                result['indicators']['ADX'] = {
                    "value": float(adx.iloc[-1]),
                    "trend_strength": "强" if adx.iloc[-1] > 25 else "弱"
                }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def generate_signals(self, symbol: str, strategy: str = "combined") -> str:
        """
        生成交易信号
        
        Args:
            symbol: 股票代码
            strategy: 策略名称
        
        Returns:
            JSON格式的信号数据
        """
        try:
            df = self.fetcher.download(symbol, period="6mo")
            if df.empty:
                return json.dumps({"error": f"无法获取 {symbol} 的数据"}, ensure_ascii=False)
            
            generator = SignalGenerator(df)
            
            # 各策略信号
            signals = {}
            
            # 均线交叉
            ma_signal = generator.ma_crossover_signal(5, 20)
            signals['MA_CROSSOVER'] = {
                "signal": self._signal_to_str(ma_signal.iloc[-1]),
                "value": int(ma_signal.iloc[-1])
            }
            
            # RSI
            rsi_signal = generator.rsi_signal()
            signals['RSI'] = {
                "signal": self._signal_to_str(rsi_signal.iloc[-1]),
                "value": int(rsi_signal.iloc[-1])
            }
            
            # MACD
            macd_signal = generator.macd_signal()
            signals['MACD'] = {
                "signal": self._signal_to_str(macd_signal.iloc[-1]),
                "value": int(macd_signal.iloc[-1])
            }
            
            # 布林带
            boll_signal = generator.bollinger_breakout()
            signals['BOLL'] = {
                "signal": self._signal_to_str(boll_signal.iloc[-1]),
                "value": int(boll_signal.iloc[-1])
            }
            
            # 综合信号
            combined = generator.combined_signal()
            
            result = {
                "symbol": symbol,
                "last_price": float(df['Close'].iloc[-1]),
                "date": str(df.index[-1].date()),
                "signals": signals,
                "combined": {
                    "signal": self._signal_to_str(combined.iloc[-1]),
                    "value": float(combined.iloc[-1])
                },
                "recommendation": self._get_recommendation(combined.iloc[-1])
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def analyze_trend(self, symbol: str) -> str:
        """分析趋势"""
        try:
            df = self.fetcher.download(symbol, period="6mo")
            if df.empty:
                return json.dumps({"error": f"无法获取 {symbol} 的数据"}, ensure_ascii=False)
            
            close = df['Close']
            
            # 计算各周期均线
            ma5 = self.factors.sma(close, 5)
            ma10 = self.factors.sma(close, 10)
            ma20 = self.factors.sma(close, 20)
            ma60 = self.factors.sma(close, 60)
            
            # 判断趋势
            current_price = close.iloc[-1]
            
            # 多头排列: MA5 > MA10 > MA20 > MA60
            bullish = ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]
            bearish = ma5.iloc[-1] < ma10.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]
            
            if bullish:
                trend = "上升趋势"
                direction = "UP"
            elif bearish:
                trend = "下降趋势"
                direction = "DOWN"
            else:
                trend = "震荡整理"
                direction = "SIDEWAYS"
            
            # 趋势强度
            price_change_20d = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
            strength = min(100, abs(price_change_20d) * 5)
            
            result = {
                "symbol": symbol,
                "last_price": float(current_price),
                "trend": trend,
                "direction": direction,
                "strength": round(strength, 2),
                "ma排列": {
                    "MA5": round(float(ma5.iloc[-1]), 2),
                    "MA10": round(float(ma10.iloc[-1]), 2),
                    "MA20": round(float(ma20.iloc[-1]), 2),
                    "MA60": round(float(ma60.iloc[-1]), 2),
                },
                "20日涨幅": round(price_change_20d, 2)
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def comprehensive_analysis(self, symbol: str) -> str:
        """综合技术分析"""
        try:
            # 获取各项分析
            indicators = json.loads(self.calculate_indicators(symbol))
            signals = json.loads(self.generate_signals(symbol))
            trend = json.loads(self.analyze_trend(symbol))
            
            # 构建综合报告
            result = {
                "symbol": symbol,
                "last_price": signals.get("last_price"),
                "date": signals.get("date"),
                "summary": {
                    "trend": trend.get("trend"),
                    "overall_signal": signals.get("combined", {}).get("signal"),
                    "recommendation": signals.get("recommendation")
                },
                "indicators": indicators.get("indicators", {}),
                "signals": signals.get("signals", {}),
                "trend": trend
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def _signal_to_str(self, value: int) -> str:
        """转换信号值到字符串"""
        mapping = {
            2: "强烈买入",
            1: "买入",
            0: "持有",
            -1: "卖出",
            -2: "强烈卖出"
        }
        return mapping.get(value, "未知")
    
    def _get_recommendation(self, combined_value: float) -> str:
        """获取操作建议"""
        if combined_value >= 0.6:
            return "强烈买入 - 多指标共振，建议建仓"
        elif combined_value >= 0.3:
            return "买入 - 指标偏多，可以考虑加仓"
        elif combined_value >= -0.3:
            return "持有 - 信号中性，建议观望"
        elif combined_value >= -0.6:
            return "卖出 - 指标偏空，建议减仓"
        else:
            return "强烈卖出 - 多指标共振，建议清仓"


def main():
    parser = argparse.ArgumentParser(description="技术分析工具")
    parser.add_argument("command", choices=["indicators", "signals", "trend", "analysis"],
                       help="命令: indicators-计算指标, signals-生成信号, trend-分析趋势, analysis-综合分析")
    parser.add_argument("--symbol", "-s", required=True, help="股票代码")
    parser.add_argument("--indicators", "-i", default="RSI,MACD,BOLL", help="指标列表")
    parser.add_argument("--period", "-p", type=int, default=14, help="周期")
    parser.add_argument("--strategy", default="combined", help="策略")
    
    args = parser.parse_args()
    
    ta = TechnicalAnalysis()
    
    if args.command == "indicators":
        print(ta.calculate_indicators(args.symbol, args.indicators, args.period))
    elif args.command == "signals":
        print(ta.generate_signals(args.symbol, args.strategy))
    elif args.command == "trend":
        print(ta.analyze_trend(args.symbol))
    elif args.command == "analysis":
        print(ta.comprehensive_analysis(args.symbol))


if __name__ == "__main__":
    main()
