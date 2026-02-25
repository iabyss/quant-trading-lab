"""
回测引擎
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Trade:
    """交易记录"""
    date: datetime
    symbol: str
    action: str  # 'BUY' or 'SELL'
    price: float
    quantity: int
    commission: float = 0
    notes: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_price: float
    entry_date: datetime


@dataclass
class BacktestResult:
    """回测结果"""
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_holding_days: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = None
    drawdown_curve: pd.Series = None


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 手续费率 0.1%
        slippage: float = 0.001,     # 滑点 0.1%
        stamp_duty: float = 0.001,   # 印花税 0.1% (卖出)
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stamp_duty = stamp_duty
        
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_history = []
        self.dates = []
    
    def buy(self, date: datetime, symbol: str, price: float, quantity: int = None, 
            amount: float = None, notes: str = "") -> bool:
        """
        买入
        
        Args:
            date: 交易日期
            symbol: 股票代码
            price: 价格
            quantity: 买入数量
            amount: 买入金额 (二选一)
            notes: 备注
        
        Returns:
            是否成功
        """
        # 计算成交价(含滑点)
        exec_price = price * (1 + self.slippage)
        
        # 计算数量或金额
        if amount and not quantity:
            quantity = int(amount / exec_price)
        elif quantity and not amount:
            amount = quantity * exec_price
        else:
            return False
        
        # 检查资金
        cost = quantity * exec_price * (1 + self.commission)
        if cost > self.cash:
            return False
        
        # 扣除手续费
        commission = cost * self.commission / (1 + self.commission)
        
        # 更新现金
        self.cash -= (cost - commission)
        
        # 更新持仓
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_price * pos.quantity + exec_price * quantity
            pos.quantity += quantity
            pos.avg_price = total_cost / pos.quantity
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=exec_price,
                entry_date=date
            )
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='BUY',
            price=exec_price,
            quantity=quantity,
            commission=commission,
            notes=notes
        ))
        
        return True
    
    def sell(self, date: datetime, symbol: str, price: float, 
             quantity: int = None, percent: float = None, notes: str = "") -> bool:
        """
        卖出
        
        Args:
            date: 交易日期
            symbol: 股票代码
            price: 价格
            quantity: 卖出数量
            percent: 卖出持仓比例 (0-1)
            notes: 备注
        """
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        # 计算卖出数量
        if percent:
            quantity = int(pos.quantity * percent)
        elif not quantity:
            quantity = pos.quantity
        
        quantity = min(quantity, pos.quantity)
        
        # 计算成交价(含滑点)
        exec_price = price * (1 - self.slippage)
        
        # 扣除手续费和印花税
        gross = quantity * exec_price
        commission = gross * self.commission
        stamp = gross * self.stamp_duty
        net = gross - commission - stamp
        
        # 更新现金
        self.cash += net
        
        # 更新持仓
        pos.quantity -= quantity
        if pos.quantity <= 0:
            del self.positions[symbol]
        
        # 记录交易
        self.trades.append(Trade(
            date=date,
            symbol=symbol,
            action='SELL',
            price=exec_price,
            quantity=quantity,
            commission=commission,
            notes=notes
        ))
        
        return True
    
    def get_equity(self, date: datetime, prices: Dict[str, float]) -> float:
        """计算当前权益"""
        portfolio_value = self.cash
        
        for symbol, pos in self.positions.items():
            if symbol in prices:
                portfolio_value += pos.quantity * prices[symbol]
        
        return portfolio_value
    
    def run(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        symbol: str = None,
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 行情数据
            strategy_func: 策略函数, 接收 (date, data, engine) 返回 signal
                signal: 'BUY', 'SELL', None
            symbol: 股票代码
        
        Returns:
            回测结果
        """
        self.reset()
        
        if symbol is None:
            symbol = data['Symbol'].iloc[0] if 'Symbol' in data.columns else 'UNKNOWN'
        
        prices = {}
        
        for i, (date, row) in enumerate(data.iterrows()):
            # 更新价格
            prices[symbol] = row['Close']
            
            # 获取信号
            signal = strategy_func(date, data.iloc[:i+1], self)
            
            # 执行信号
            if signal == 'BUY':
                # 买入半仓
                self.buy(date, symbol, row['Close'], amount=self.cash * 0.5)
            elif signal == 'SELL':
                # 卖出半仓
                self.sell(date, symbol, row['Close'], percent=0.5)
            
            # 记录权益
            equity = self.get_equity(date, prices)
            self.equity_history.append(equity)
            self.dates.append(date)
        
        # 最终平仓
        final_price = data['Close'].iloc[-1]
        if symbol in self.positions:
            self.sell(data.index[-1], symbol, final_price, notes='Final close')
        
        # 计算结果
        return self.calculate_result()
    
    def calculate_result(self) -> BacktestResult:
        """计算回测结果"""
        equity_curve = pd.Series(self.equity_history, index=self.dates)
        
        # 计算收益率
        returns = equity_curve.pct_change().dropna()
        
        # 总收益
        final_capital = self.equity_history[-1] if self.equity_history else self.initial_capital
        total_return = final_capital - self.initial_capital
        total_return_pct = (final_capital / self.initial_capital - 1) * 100
        
        # 夏普比率
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = (equity_curve - rolling_max).min()
        max_drawdown_pct = drawdown.min() * 100
        
        # 交易统计
        buy_trades = [t for t in self.trades if t.action == 'BUY']
        sell_trades = [t for t in self.trades if t.action == 'SELL']
        
        wins = []
        losses = []
        
        # 配对买卖计算盈亏
        position = {}
        for trade in self.trades:
            if trade.action == 'BUY':
                position[trade.symbol] = trade.price
            elif trade.action == 'SELL' and trade.symbol in position:
                profit = (trade.price - position[trade.symbol]) * trade.quantity
                if profit > 0:
                    wins.append(profit)
                else:
                    losses.append(abs(profit))
                del position[trade.symbol]
        
        winning_trades = len(wins)
        losing_trades = len(losses)
        total_trades = winning_trades + losing_trades
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = sum(wins) / sum(losses) if losses and sum(losses) > 0 else 0
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_holding_days=0,
            trades=self.trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown
        )
    
    def print_result(self, result: BacktestResult):
        """打印回测结果"""
        print("\n" + "="*50)
        print("📊 回测结果")
        print("="*50)
        print(f"初始资金:     ${result.initial_capital:,.2f}")
        print(f"最终资金:     ${result.final_capital:,.2f}")
        print(f"总收益:       ${result.total_return:,.2f} ({result.total_return_pct:.2f}%)")
        print(f"夏普比率:     {result.sharpe_ratio:.2f}")
        print(f"最大回撤:     ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
        print(f"胜率:         {result.win_rate:.1f}%")
        print(f"盈亏比:       {result.profit_factor:.2f}")
        print(f"交易次数:     {result.total_trades}")
        print(f"盈利交易:     {result.winning_trades}")
        print(f"亏损交易:     {result.losing_trades}")
        if result.winning_trades > 0:
            print(f"平均盈利:     ${result.avg_win:,.2f}")
        if result.losing_trades > 0:
            print(f"平均亏损:     ${result.avg_loss:,.2f}")
        print("="*50)


# 便捷函数
def backtest(data: pd.DataFrame, strategy_func: Callable, **kwargs) -> BacktestResult:
    """快速回测"""
    engine = BacktestEngine(**kwargs)
    return engine.run(data, strategy_func)


if __name__ == "__main__":
    # 测试
    from data.fetcher import download
    
    # 获取数据
    df = download("AAPL", period="1y")
    
    # 简单策略: MA交叉
    def strategy(date, data, engine):
        if len(data) < 60:
            return None
        
        ma10 = data['Close'].rolling(10).mean()
        ma30 = data['Close'].rolling(30).mean()
        
        # 当前和前一根
        if ma10.iloc[-1] > ma30.iloc[-1] and ma10.iloc[-2] <= ma30.iloc[-2]:
            return 'BUY'
        elif ma10.iloc[-1] < ma30.iloc[-1] and ma10.iloc[-2] >= ma30.iloc[-2]:
            return 'SELL'
        
        return None
    
    # 运行回测
    result = backtest(df, strategy, initial_capital=100000)
    
    # 打印结果
    engine = BacktestEngine()
    engine.print_result(result)
