#!/usr/bin/env python3
"""
短期策略测试
"""

import sys
from pathlib import Path
import random
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.backtest_tool import BacktestTool

ASTOCK_POOL = [
    ('600519.SS', '贵州茅台'),
    ('601318.SS', '中国平安'),
    ('600036.SS', '招商银行'),
    ('600887.SS', '伊利股份'),
    ('600309.SS', '万华化学'),
    ('601888.SS', '中国中铁'),
    ('600028.SS', '中国石化'),
    ('600000.SS', '浦发银行'),
    ('600030.SS', '中信证券'),
    ('600016.SS', '民生银行'),
]

# 随机5只
random.seed(42)
selected = random.sample(ASTOCK_POOL, 5)

tool = BacktestTool(initial_capital=300000)

# 测试不同短期策略组合
print("="*60)
print("🎯 短期策略测试")
print("="*60)

# RSI+KDJ (对比基准)
tool.run(selected, ['rsi', 'kdj'], name="RSI+KDJ(基准)")

# 追涨组合
tool.run(selected, ['chase_up', 'volume', 'rsi'], name="追涨策略")

# 打板组合
tool.run(selected, ['limit_up', 'chase_up', 'volume'], name="打板策略")

# N字反包
tool.run(selected, ['n_pattern', 'rsi', 'kdj'], name="N字反包")

# 资金流向
tool.run(selected, ['money_flow', 'ma_divergence'], name="资金流向")

# 超短组合
tool.run(selected, ['rsi', 'kdj', 'wr', 'cci'], name="超短策略")
