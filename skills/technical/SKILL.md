---
name: "technical-analysis"
description: "技术分析Skill，计算30+技术指标，生成买卖信号，支持MA、RSI、MACD、K线形态等分析"
---

# Technical Analysis Skill

技术分析工具，计算各种技术指标并生成交易信号。

## 支持的功能

### 1. calculate_indicators 计算技术指标

计算常用的技术分析指标。

**支持的指标:**
- **趋势指标**: MA, EMA, SMA, VWAP, TRIX
- **动量指标**: RSI, ROC, CCI, Williams %R, Stochastic
- **波动率指标**: ATR, BOLL, KELTNER, Donchian Channel
- **成交量指标**: OBV, ADL, ADX, MFI, CMF
- **MACD指标**: MACD, Signal Line, Histogram

**参数:**
- `symbol`: 股票代码
- `indicators`: 指标列表，如 "RSI,MACD,BOLL"
- `period`: 指标周期 (默认: 14)
- `data`: 可选的数据DataFrame

**使用示例:**
```
计算AAPL的RSI指标
查询茅台的MACD指标
显示比特币的布林带数据
```

### 2. generate_signals 生成交易信号

基于技术指标生成买入/卖出信号。

**信号类型:**
- STRONG_BUY (强烈买入)
- BUY (买入)
- HOLD (持有)
- SELL (卖出)
- STRONG_SELL (强烈卖出)

**支持的策略:**
- MA_CROSSOVER - 均线交叉
- RSI - RSI超买超卖
- MACD - MACD金叉死叉
- BOLL - 布林带突破
- COMBINED - 多指标组合

**使用示例:**
```
生成苹果的买入信号
查询特斯拉的技术信号
显示贵州茅台的RSI信号
```

### 3. analyze_trend 分析趋势

分析标的的趋势方向和强度。

**返回:**
- 趋势方向: UP, DOWN, SIDEWAYS
- 趋势强度: 0-100
- 均线多头/空头排列

**使用示例:**
```
分析A股上证指数趋势
查询腾讯控股趋势方向
显示比特币近期趋势
```

### 4. detect_patterns 检测K线形态

识别常见的K线形态。

**支持的形态:**
- 锤子线 (Hammer)
- 上吊线 (Hanging Man)
- 吞没形态 (Engulfing)
- 十字星 (Doji)
-  Morning/Evening Star
- 旗形 (Flag)
- 三角整理 (Triangle)

**使用示例:**
```
检测AAPL的K线形态
查询特斯拉近期形态
显示茅台的形态分析
```

### 5. analyze_volume 分析成交量

分析成交量异常和资金流向。

**返回:**
- 放量/缩量信号
- 资金流入/流出
- OBV趋势

**使用示例:**
```
分析成交量异常
查询资金流向
显示OBV指标
```

### 6. comprehensive_analysis 综合分析

返回完整的技术分析报告。

**包含:**
- 所有关键指标值
- 买卖信号汇总
- 趋势判断
- 风险提示
- 操作建议

**使用示例:**
```
综合分析特斯拉
查询茅台技术面
显示苹果完整分析
```

## 常用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| symbol | 股票代码 | 必填 |
| period | 计算周期 | 14 |
| fast_period | 快线周期 | 12 |
| slow_period | 慢线周期 | 26 |
| signal_period | 信号线周期 | 9 |

## 指标参数参考

| 指标 | 常用周期 | 说明 |
|------|---------|------|
| RSI | 6, 14, 21 | 超买>70, 超卖<30 |
| MACD | 12, 26, 9 | 金叉买入, 死叉卖出 |
| BOLL | 20, 2 | 突破上轨买入, 跌破下轨卖出 |
| KDJ | 9, 3, 3 | K>D买入, K<D卖出 |
| ATR | 14 | 衡量波动率 |
| ADX | 14 | >25表示趋势形成 |

## 使用流程

1. 用户请求计算指标 → 使用 `calculate_indicators`
2. 用户请求买卖信号 → 使用 `generate_signals`
3. 用户分析趋势 → 使用 `analyze_trend`
4. 用户分析形态 → 使用 `detect_patterns`
5. 用户请求综合分析 → 使用 `comprehensive_analysis`

## 数据来源

- 使用项目内的 `data/factors/technical.py` 计算指标
- 行情数据来自 `market-data` skill
- 可直接传入 DataFrame 进行计算
