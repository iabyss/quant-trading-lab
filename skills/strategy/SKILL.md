---
name: "strategy-generator"
description: "策略生成器，根据用户需求自动生成量化交易策略代码，支持均线、RSI、MACD、布林带等策略模板"
---

# Strategy Generator Skill

自动生成量化交易策略代码。

## 功能

### 1. generate_strategy 生成策略

根据模板和参数生成策略代码。

**支持的策略模板:**
- MA_CROSSOVER - 均线交叉策略
- RSI_STRATEGY - RSI均值回归策略
- MACD_TREND - MACD趋势策略
- BOLL_BREAKOUT - 布林带突破策略
- MOMENTUM - 动量策略
- DUAL_MARIBON - 双均线带策略

**参数:**
- `template`: 策略模板名称
- `symbol`: 股票代码 (可选)
- `params`: 策略参数

**使用示例:**
```
生成一个MACD策略
创建一个RSI均值回归策略
生成布林带突破策略代码
```

### 2. backtest_strategy 回测策略

使用历史数据回测策略表现。

**参数:**
- `symbol`: 股票代码
- `strategy`: 策略名称
- `start_date`: 开始日期
- `end_date`: 结束日期

**返回:**
- 总收益率
- 夏普比率
- 最大回撤
- 胜率
- 交易次数

**使用示例:**
```
回测MACD策略在过去一年
回测RSI策略在茅台上的表现
```

### 3. optimize_parameters 参数优化

寻找最优策略参数。

**参数:**
- `strategy`: 策略名称
- `symbol`: 股票代码
- `param_grid`: 参数网格

**使用示例:**
```
优化MACD参数
寻找RSI最优周期
```

### 4. list_templates 列出模板

查看所有可用的策略模板。

**使用示例:**
```
有哪些策略模板
列出所有策略
```

## 策略模板说明

### MA_CROSSOVER (均线交叉)
- 快线突破慢线买入，死叉卖出
- 参数: fast_period, slow_period

### RSI_STRATEGY (RSI均值回归)
- RSI<30买入，RSI>70卖出
- 参数: period, oversold, overbought

### MACD_TREND (MACD趋势)
- MACD金叉买入，死叉卖出
- 参数: fast, slow, signal

### BOLL_BREAKOUT (布林带突破)
- 突破上轨买入，跌破下轨卖出
- 参数: period, std_dev

### MOMENTUM (动量策略)
- 上涨趋势中买入，下跌趋势中卖出
- 参数: period, threshold

## 使用流程

1. 用户请求生成策略 → 使用 `generate_strategy`
2. 用户回测策略 → 使用 `backtest_strategy`
3. 用户优化参数 → 使用 `optimize_parameters`
4. 用户查看模板 → 使用 `list_templates`

## 输出格式

生成的策略代码保存在:
- `strategies/templates/` 目录
- 包含完整的策略类和回测示例
