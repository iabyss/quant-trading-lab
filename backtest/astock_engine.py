"""
A股回测引擎
针对A股交易规则优化:
- T+1 交易制度
- 印花税 0.1% (仅卖出)
- 手续费最低5元
- 涨跌停板 10%/20%
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class AStockTrade:
    """A股交易记录"""
    date: datetime
    code: str
    name: str
    action: str  # 'BUY' or 'SELL'
    price: float
    quantity: int
    amount: float  # 成交金额
    commission: float  # 手续费
    stamp_duty: float  # 印花税
    total_cost: float  # 总成本
    reason: str = ""


@dataclass
class AStockPosition:
    """A股持仓"""
    code: str
    name: str
    quantity: int
    avg_cost: float  # 持仓成本
    available: int  # 可卖数量 (T+1)
    entry_date: datetime
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_cost


@dataclass
class AStockBacktestResult:
    """回测结果"""
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit: float
    avg_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    trading_days: int
    trades: List[AStockTrade] = field(default_factory=list)


class AStockBacktestEngine:
    """A股回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.0003,  # 万3手续费
        min_commission: float = 5,          # 最低5元
        stamp_duty_rate: float = 0.001,     # 千1印花税 (仅卖出)
        slippage: float = 0.001,            # 滑点 0.1%
        limit_up_ratio: float = 0.10,        # 涨停板 10%
        limit_down_ratio: float = -0.10,    # 跌停板 -10%
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.slippage = slippage
        self.limit_up_ratio = limit_up_ratio
        self.limit_down_ratio = limit_down_ratio
        
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.cash = self.initial_capital
        self.positions: Dict[str, AStockPosition] = {}
        self.trades: List[AStockTrade] = []
        self.equity_curve = []
        self.dates = []
        
        # 今日买入列表 (T+1)
        self.today_buy: Dict[str, int] = {}
    
    def _calculate_commission(self, amount: float) -> float:
        """计算手续费"""
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)
    
    def _calculate_stamp_duty(self, amount: float) -> float:
        """计算印花税"""
        return amount * self.stamp_duty_rate
    
    def _get_limit_price(self, price: float, action: str) -> float:
        """计算涨跌停价"""
        if action == 'BUY':
            # 涨停板不能买入
            return price * (1 + self.limit_up_ratio)
        else:
            # 跌停板不能卖出
            return price * (1 + self.limit_down_ratio)
    
    def can_buy(self, code: str, price: float, quantity: int) -> Tuple[bool, str]:
        """检查是否可以买入"""
        # 检查涨跌停
        limit_price = self._get_limit_price(price, 'BUY')
        if price >= limit_price:
            return False, "涨停板无法买入"
        
        # 计算成本
        cost = price * quantity * (1 + self.slippage)
        commission = self._calculate_commission(cost)
        total_cost = cost + commission
        
        # 检查资金
        if total_cost > self.cash:
            return False, f"资金不足 (需要{total_cost:.2f}, 剩余{self.cash:.2f})"
        
        return True, ""
    
    def can_sell(self, code: str, quantity: int) -> Tuple[bool, str]:
        """检查是否可以卖出"""
        if code not in self.positions:
            return False, "无持仓"
        
        pos = self.positions[code]
        if pos.available < quantity:
            return False, f"可卖数量不足 (可卖{pos.available}, 要卖{quantity})"
        
        return True, ""
    
    def buy(
        self,
        date: datetime,
        code: str,
        name: str,
        price: float,
        quantity: int = None,
        amount: float = None,
        reason: str = ""
    ) -> bool:
        """
        买入A股
        
        Args:
            date: 交易日期
            code: 股票代码
            name: 股票名称
            price: 价格
            quantity: 买入数量 (手*100)
            amount: 买入金额
            reason: 买入原因
        
        Returns:
            是否成功
        """
        # 数量必须为100的整数倍 (A股1手=100股)
        if quantity and quantity % 100 != 0:
            quantity = (quantity // 100) * 100
        
        # 计算数量
        if amount and not quantity:
            quantity = int(amount / price / 100) * 100
            quantity = max(quantity, 100)
        
        if not quantity:
            return False
        
        # 检查是否可以买入
        can_buy, msg = self.can_buy(code, price, quantity)
        if not can_buy:
            print(f"  ⚠️ {msg}")
            return False
        
        # 成交价(含滑点)
        exec_price = price * (1 + self.slippage)
        
        # 计算费用
        gross_amount = exec_price * quantity
        commission = self._calculate_commission(gross_amount)
        total_cost = gross_amount + commission
        
        # 扣除现金
        self.cash -= total_cost
        
        # 更新持仓 (T+1, 当天买的不能卖)
        if code in self.positions:
            pos = self.positions[code]
            total_cost_basis = pos.avg_cost * pos.quantity + exec_price * quantity
            pos.quantity += quantity
            pos.avg_cost = total_cost_basis / pos.quantity
            pos.available = pos.quantity  # T+1, 明天才能卖
        else:
            self.positions[code] = AStockPosition(
                code=code,
                name=name,
                quantity=quantity,
                avg_cost=exec_price,
                available=0,  # T+1, 今天不能卖
                entry_date=date
            )
        
        # 记录今日买入 (T+1)
        self.today_buy[code] = self.today_buy.get(code, 0) + quantity
        
        # 记录交易
        self.trades.append(AStockTrade(
            date=date,
            code=code,
            name=name,
            action='BUY',
            price=exec_price,
            quantity=quantity,
            amount=gross_amount,
            commission=commission,
            stamp_duty=0,
            total_cost=total_cost,
            reason=reason
        ))
        
        return True
    
    def sell(
        self,
        date: datetime,
        code: str,
        price: float,
        quantity: int = None,
        percent: float = None,
        reason: str = ""
    ) -> bool:
        """
        卖出A股
        
        Args:
            date: 交易日期
            code: 股票代码
            price: 价格
            quantity: 卖出数量
            percent: 卖出比例 (0-1)
            reason: 卖出原因
        """
        if code not in self.positions:
            return False
        
        pos = self.positions[code]
        
        # 计算卖出数量
        if percent:
            quantity = int(pos.available * percent)
        elif not quantity:
            quantity = pos.available
        
        quantity = min(quantity, pos.available)
        if quantity <= 0:
            return False
        
        # 检查涨跌停
        limit_price = self._get_limit_price(price, 'SELL')
        if price <= limit_price:
            print(f"  ⚠️ 跌停板无法卖出")
            return False
        
        # 成交价(含滑点)
        exec_price = price * (1 - self.slippage)
        
        # 计算费用
        gross_amount = exec_price * quantity
        commission = self._calculate_commission(gross_amount)
        stamp_duty = self._calculate_stamp_duty(gross_amount)
        total_proceeds = gross_amount - commission - stamp_duty
        
        # 更新现金
        self.cash += total_proceeds
        
        # 更新持仓
        pos.quantity -= quantity
        pos.available -= quantity
        
        if pos.quantity <= 0:
            del self.positions[code]
        
        # 记录交易
        name = pos.name
        self.trades.append(AStockTrade(
            date=date,
            code=code,
            name=name,
            action='SELL',
            price=exec_price,
            quantity=quantity,
            amount=gross_amount,
            commission=commission,
            stamp_duty=stamp_duty,
            total_cost=-total_proceeds,
            reason=reason
        ))
        
        return True
    
    def update_t1(self, date: datetime):
        """T+1 结算: 今日买入变为可卖"""
        for code, qty in self.today_buy.items():
            if code in self.positions:
                self.positions[code].available += qty
        self.today_buy = {}
    
    def get_equity(self, prices: Dict[str, float]) -> float:
        """计算总权益"""
        portfolio_value = self.cash
        for code, pos in self.positions.items():
            if code in prices:
                portfolio_value += pos.quantity * prices[code]
        return portfolio_value
    
    def run(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        code: str = None,
        name: str = "Unknown"
    ) -> AStockBacktestResult:
        """
        运行回测
        
        Args:
            data: 行情数据
            strategy_func: 策略函数 (date, data, engine) -> signal
                signal: 'BUY', 'SELL', 'SELL_ALL', None
            code: 股票代码
            name: 股票名称
        """
        self.reset()
        
        if code is None:
            code = data['Symbol'].iloc[0] if 'Symbol' in data.columns else 'UNKNOWN'
        
        prices = {}
        
        for i, (date, row) in enumerate(data.iterrows()):
            prices[code] = row['Close']
            
            # T+1 结算
            if i > 0:
                self.update_t1(date)
            
            # 获取信号
            signal = strategy_func(date, data.iloc[:i+1], self)
            
            # 执行信号
            if signal == 'BUY':
                # 默认买入半仓
                buy_amount = self.cash * 0.5
                self.buy(date, code, name, row['Close'], amount=buy_amount, reason='策略信号')
            elif signal == 'SELL':
                # 默认卖出半仓
                self.sell(date, code, row['Close'], percent=0.5, reason='策略信号')
            elif signal == 'SELL_ALL':
                self.sell(date, code, row['Close'], quantity=999999, reason='清仓信号')
            
            # 记录权益
            equity = self.get_equity(prices)
            self.equity_curve.append(equity)
            self.dates.append(date)
        
        # 最终平仓
        if code in self.positions:
            final_price = data['Close'].iloc[-1]
            self.sell(data.index[-1], code, final_price, reason='回测结束平仓')
        
        return self.calculate_result()
    
    def calculate_result(self) -> AStockBacktestResult:
        """计算回测结果"""
        if not self.equity_curve:
            return None
        
        equity_series = pd.Series(self.equity_curve, index=self.dates)
        
        # 基础统计
        final_capital = self.equity_curve[-1]
        total_return = final_capital - self.initial_capital
        total_return_pct = (final_capital / self.initial_capital - 1) * 100
        
        # 年化收益
        trading_days = len(self.equity_curve)
        years = trading_days / 252
        annual_return = ((final_capital / self.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # 夏普比率
        returns = equity_series.pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = (equity_series - rolling_max).min()
        max_drawdown_pct = drawdown.min() * 100
        
        # 交易统计
        sell_trades = [t for t in self.trades if t.action == 'SELL']
        
        profits = []
        losses = []
        
        for trade in sell_trades:
            # 计算这笔卖出的盈亏
            if trade.code in self.positions:
                continue
            
            # 找到对应的买入
            buys = [t for t in self.trades if t.action == 'BUY' and t.code == trade.code]
            if buys:
                avg_buy_price = np.mean([t.price for t in buys])
                profit = (trade.price - avg_buy_price) * trade.quantity - trade.commission - trade.stamp_duty
                if profit > 0:
                    profits.append(profit)
                else:
                    losses.append(abs(profit))
        
        winning_trades = len(profits)
        losing_trades = len(losses)
        total_trades = winning_trades + losing_trades
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        
        profit_factor = sum(profits) / sum(losses) if losses and sum(losses) > 0 else 0
        
        # 连胜连亏
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in sell_trades:
            if trade.code in self.positions:
                continue
            buys = [t for t in self.trades if t.action == 'BUY' and t.code == trade.code]
            if buys:
                avg_buy_price = np.mean([t.price for t in buys])
                profit = (trade.price - avg_buy_price) * trade.quantity
                if profit > 0:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        return AStockBacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            trading_days=trading_days,
            trades=self.trades
        )
    
    def print_result(self, result: AStockBacktestResult):
        """打印回测结果"""
        if not result:
            print("No results")
            return
        
        print("\n" + "="*60)
        print("📊 A股回测结果")
        print("="*60)
        print(f"初始资金:        ¥{result.initial_capital:,.2f}")
        print(f"最终资金:        ¥{result.final_capital:,.2f}")
        print(f"总收益:          ¥{result.total_return:+,.2f} ({result.total_return_pct:+.2f}%)")
        print(f"年化收益:        {result.annual_return:+.2f}%")
        print(f"夏普比率:        {result.sharpe_ratio:.2f}")
        print(f"最大回撤:        ¥{result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
        print("-"*60)
        print(f"交易次数:        {result.total_trades}")
        print(f"盈利次数:        {result.winning_trades}")
        print(f"亏损次数:        {result.losing_trades}")
        print(f"胜率:            {result.win_rate:.1f}%")
        print(f"盈亏比:          {result.profit_factor:.2f}")
        print(f"平均盈利:        ¥{result.avg_profit:,.2f}")
        print(f"平均亏损:        ¥{result.avg_loss:,.2f}")
        print(f"交易天数:        {result.trading_days}")
        print("="*60)


# 便捷函数
def backtest_astock(
    data: pd.DataFrame,
    strategy_func: Callable,
    **kwargs
) -> AStockBacktestResult:
    """快速A股回测"""
    engine = AStockBacktestEngine(**kwargs)
    return engine.run(data, strategy_func)


if __name__ == "__main__":
    from data.astock import AStockData
    
    # 测试
    print("="*60)
    print("A股回测引擎测试 - 航发动力 (600893)")
    print("="*60)
    
    # 获取数据
    df = AStockData.download('600893', period='1y')
    print(f"\n数据: {len(df)} 条")
    
    # MA交叉策略
    def ma_strategy(date, data, engine):
        if len(data) < 60:
            return None
        
        ma10 = data['Close'].rolling(10).mean()
        ma30 = data['Close'].rolling(30).mean()
        
        if ma10.iloc[-1] > ma30.iloc[-1] and ma10.iloc[-2] <= ma30.iloc[-2]:
            return 'BUY'
        elif ma10.iloc[-1] < ma30.iloc[-1] and ma10.iloc[-2] >= ma30.iloc[-2]:
            return 'SELL'
        
        return None
    
    # 回测
    engine = AStockBacktestEngine(initial_capital=100000)
    result = engine.run(df, ma_strategy, code='600893', name='航发动力')
    engine.print_result(result)
