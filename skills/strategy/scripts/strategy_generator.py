#!/usr/bin/env python3
"""
策略生成器
自动生成量化交易策略代码
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.fetcher import DataFetcher
from backtest.engine import BacktestEngine
from strategies.signals import generate_signals, SignalType


class StrategyGenerator:
    """策略生成器"""
    
    TEMPLATES = {
        'MA_CROSSOVER': '''
"""
{strategy_name} - 均线交叉策略
自动生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class {class_name}:
    """均线交叉策略"""
    
    def __init__(self, fast_period: int = {fast}, slow_period: int = {slow}):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = "{strategy_name}"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        close = data['close']
        
        fast_ma = close.rolling(window=self.fast_period).mean()
        slow_ma = close.rolling(window=self.slow_period).mean()
        
        # 信号
        signal = pd.Series(0, index=data.index)
        signal[fast_ma > slow_ma] = 1   # 买入
        signal[fast_ma <= slow_ma] = -1 # 卖出
        
        # 只在交叉时产生信号
        signal = signal.diff()
        signal[signal >= 0] = 0
        signal[signal < 0] = -1
        
        return signal
    
    def get_params(self) -> Dict:
        return {{
            'fast_period': self.fast_period,
            'slow_period': self.slow_period
        }}
''',
        'RSI_STRATEGY': '''
"""
{strategy_name} - RSI均值回归策略
自动生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class {class_name}:
    """RSI均值回归策略"""
    
    def __init__(self, period: int = {period}, oversold: int = {oversold}, overbought: int = {overbought}):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = "{strategy_name}"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        close = data['close']
        
        # 计算RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 信号
        signal = pd.Series(0, index=data.index)
        signal[rsi < self.oversold] = 1   # 超卖买入
        signal[rsi > self.overbought] = -1 # 超买卖出
        
        return signal
    
    def get_params(self) -> Dict:
        return {{
            'period': self.period,
            'oversold': self.oversold,
            'overbought': self.overbought
        }}
''',
        'MACD_TREND': '''
"""
{strategy_name} - MACD趋势策略
自动生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class {class_name}:
    """MACD趋势策略"""
    
    def __init__(self, fast: int = {fast}, slow: int = {slow}, signal: int = {signal}):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.name = "{strategy_name}"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        close = data['close']
        
        # 计算MACD
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=self.signal, adjust=False).mean()
        
        # 金叉死叉
        histogram = macd - signal_line
        signal = pd.Series(0, index=data.index)
        signal[(histogram > 0) & (histogram.shift(1) <= 0)] = 1  # 金叉
        signal[(histogram < 0) & (histogram.shift(1) >= 0)] = -1 # 死叉
        
        return signal
    
    def get_params(self) -> Dict:
        return {{
            'fast': self.fast,
            'slow': self.slow,
            'signal': self.signal
        }}
''',
        'BOLL_BREAKOUT': '''
"""
{strategy_name} - 布林带突破策略
自动生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class {class_name}:
    """布林带突破策略"""
    
    def __init__(self, period: int = {period}, std_dev: float = {std_dev}):
        self.period = period
        self.std_dev = std_dev
        self.name = "{strategy_name}"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        close = data['close']
        
        # 计算布林带
        ma = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        upper = ma + self.std_dev * std
        lower = ma - self.std_dev * std
        
        # 信号
        signal = pd.Series(0, index=data.index)
        signal[close > upper] = 1   # 突破上轨买入
        signal[close < lower] = -1 # 跌破下轨卖出
        
        return signal
    
    def get_params(self) -> Dict:
        return {{
            'period': self.period,
            'std_dev': self.std_dev
        }}
''',
    }
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.output_dir = Path(__file__).parent.parent.parent / "strategies" / "generated"
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_strategy(self, template: str, strategy_name: str = None, 
                         params: Dict = None) -> str:
        """生成策略代码"""
        if template not in self.TEMPLATES:
            return json.dumps({
                "error": f"未知模板: {template}",
                "available_templates": list(self.TEMPLATES.keys())
            }, ensure_ascii=False)
        
        params = params or {}
        
        # 生成类名
        class_name = (strategy_name or template).upper().replace('-', '_') + 'Strategy'
        
        # 填充参数
        template_code = self.TEMPLATES[template].format(
            strategy_name=strategy_name or template,
            class_name=class_name,
            fast=params.get('fast_period', 5),
            slow=params.get('slow_period', 20),
            period=params.get('period', 14),
            oversold=params.get('oversold', 30),
            overbought=params.get('overbought', 70),
            fast=params.get('fast', 12),
            slow=params.get('slow', 26),
            signal=params.get('signal', 9),
            std_dev=params.get('std_dev', 2.0)
        )
        
        # 保存文件
        filename = f"{class_name.lower()}.py"
        filepath = self.output_dir / filename
        filepath.write_text(template_code)
        
        return json.dumps({
            "success": True,
            "strategy_name": strategy_name or template,
            "class_name": class_name,
            "file": str(filepath),
            "params": params,
            "code": template_code
        }, ensure_ascii=False, indent=2)
    
    def backtest_strategy(self, symbol: str, template: str, 
                          start_date: str = None, end_date: str = None,
                          params: Dict = None) -> str:
        """回测策略"""
        try:
            # 获取数据
            df = self.fetcher.download(symbol, start=start_date, end=end_date)
            if df.empty:
                return json.dumps({"error": f"无法获取 {symbol} 数据"}, ensure_ascii=False)
            
            # 生成信号
            strategy_params = params or {}
            signal = generate_signals(df, template.lower(), strategy_params)
            
            # 回测
            engine = BacktestEngine(initial_capital=100000)
            
            # 执行回测
            for i in range(len(df)):
                date = df.index[i]
                price = df['Close'].iloc[i]
                sig = signal.iloc[i] if i < len(signal) else 0
                
                if sig == 1:  # 买入
                    engine.buy(date, symbol, price, amount=10000)
                elif sig == -1:  # 卖出
                    if symbol in engine.positions:
                        qty = engine.positions[symbol].quantity
                        engine.sell(date, symbol, price, quantity=qty)
                
                # 更新权益
                equity = engine.cash
                for pos in engine.positions.values():
                    equity += pos.quantity * price
                engine.equity_history.append(equity)
                engine.dates.append(date)
            
            # 计算结果
            initial = 100000
            final = engine.equity_history[-1] if engine.equity_history else initial
            total_return = (final - initial) / initial * 100
            
            result = {
                "symbol": symbol,
                "template": template,
                "period": f"{start_date} ~ {end_date}",
                "results": {
                    "initial_capital": initial,
                    "final_capital": round(final, 2),
                    "total_return_pct": round(total_return, 2),
                    "total_trades": len(engine.trades),
                    "winning_trades": sum(1 for t in engine.trades if t.action == 'SELL' and 
                                         t.price > next((x for x in engine.trades if x.symbol == t.symbol and x.action == 'BUY'), None))
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    
    def list_templates(self) -> str:
        """列出所有模板"""
        templates = []
        for name, code in self.TEMPLATES.items():
            # 提取策略描述
            desc = ""
            if "MA_CROSSOVER" in name:
                desc = "均线交叉策略，快线突破慢线买入"
            elif "RSI" in name:
                desc = "RSI均值回归，低于30买入高于70卖出"
            elif "MACD" in name:
                desc = "MACD金叉死叉策略"
            elif "BOLL" in name:
                desc = "布林带突破策略"
            
            templates.append({
                "name": name,
                "description": desc
            })
        
        return json.dumps({"templates": templates}, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="策略生成器")
    parser.add_argument("command", choices=["generate", "backtest", "list"],
                       help="命令: generate-生成策略, backtest-回测, list-列表示例")
    parser.add_argument("--template", "-t", help="策略模板")
    parser.add_argument("--name", "-n", help="策略名称")
    parser.add_argument("--symbol", "-s", help="股票代码")
    parser.add_argument("--start", default="2024-01-01", help="开始日期")
    parser.add_argument("--end", default="2025-01-01", help="结束日期")
    parser.add_argument("--params", "-p", help="参数字符串 JSON格式")
    
    args = parser.parse_args()
    
    generator = StrategyGenerator()
    params = json.loads(args.params) if args.params else {}
    
    if args.command == "generate":
        if not args.template:
            print("错误: 需要指定 --template")
            return
        print(generator.generate_strategy(args.template, args.name, params))
    elif args.command == "backtest":
        if not args.symbol or not args.template:
            print("错误: 需要指定 --symbol 和 --template")
            return
        print(generator.backtest_strategy(args.symbol, args.template, args.start, args.end, params))
    elif args.command == "list":
        print(generator.list_templates())


if __name__ == "__main__":
    main()
