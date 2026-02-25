"""
绩效分析模块
计算回测绩效指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    # 收益指标
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annual_return: float = 0.0
    annual_return_pct: float = 0.0
    
    # 风险指标
    volatility: float = 0.0
    annual_volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration: int = 0
    
    # 风险调整收益
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_days: float = 0.0
    
    # 择时能力
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    
    # 其他
    omega_ratio: float = 0.0
    tail_ratio: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, equity_curve: pd.Series, trades: List = None, 
                 benchmark: pd.Series = None, risk_free_rate: float = 0.03):
        """
        初始化绩效分析器
        
        Args:
            equity_curve: 权益曲线 (Series, index为日期)
            trades: 交易记录列表
            benchmark: 基准收益曲线
            risk_free_rate: 无风险利率 (年化)
        """
        self.equity_curve = equity_curve.dropna()
        self.trades = trades or []
        self.benchmark = benchmark
        self.risk_free_rate = risk_free_rate
        
        # 计算日收益率
        self.returns = self.equity_curve.pct_change().dropna()
        
    def calculate_all(self) -> PerformanceMetrics:
        """计算所有指标"""
        metrics = PerformanceMetrics()
        
        # 收益指标
        metrics.total_return = self.equity_curve.iloc[-1] - self.equity_curve.iloc[0]
        metrics.total_return_pct = (self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1) * 100
        
        # 年化收益
        days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        years = days / 365 if days > 0 else 1
        metrics.annual_return = metrics.total_return / years
        metrics.annual_return_pct = ((1 + metrics.total_return_pct / 100) ** (1 / years) - 1) * 100
        
        # 风险指标
        metrics.volatility = self.returns.std()
        metrics.annual_volatility = metrics.volatility * np.sqrt(252)
        
        # 最大回撤
        dd, dd_pct, duration = self.calculate_max_drawdown()
        metrics.max_drawdown = dd
        metrics.max_drawdown_pct = dd_pct
        metrics.max_drawdown_duration = duration
        
        # 风险调整收益
        metrics.sharpe_ratio = self.calculate_sharpe_ratio()
        metrics.sortino_ratio = self.calculate_sortino_ratio()
        metrics.calmar_ratio = metrics.annual_return_pct / abs(metrics.max_drawdown_pct) if metrics.max_drawdown_pct != 0 else 0
        
        # 交易统计
        if self.trades:
            self._calculate_trade_metrics(metrics)
        
        # 基准比较
        if self.benchmark is not None:
            metrics.information_ratio = self.calculate_information_ratio()
        
        # 其他指标
        metrics.omega_ratio = self.calculate_omega_ratio()
        metrics.tail_ratio = self.calculate_tail_ratio()
        metrics.skewness = self.returns.skew()
        metrics.kurtosis = self.returns.kurtosis()
        
        return metrics
    
    def calculate_sharpe_ratio(self, periods_per_year: int = 252) -> float:
        """
        计算夏普比率
        
        Args:
            periods_per_year: 年化周期数 (252 for daily)
        
        Returns:
            夏普比率
        """
        if len(self.returns) == 0 or self.returns.std() == 0:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / periods_per_year
        return np.sqrt(periods_per_year) * excess_returns.mean() / self.returns.std()
    
    def calculate_sortino_ratio(self, periods_per_year: int = 252) -> float:
        """
        计算索提诺比率 (只考虑下行风险)
        
        Args:
            periods_per_year: 年化周期数
        
        Returns:
            索提诺比率
        """
        if len(self.returns) == 0:
            return 0.0
        
        excess_returns = self.returns - self.risk_free_rate / periods_per_year
        downside_returns = self.returns[self.returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        downside_std = downside_returns.std()
        return np.sqrt(periods_per_year) * excess_returns.mean() / downside_std
    
    def calculate_max_drawdown(self) -> Tuple[float, float, int]:
        """
        计算最大回撤
        
        Returns:
            (最大回撤金额, 最大回撤百分比, 回撤持续天数)
        """
        cumulative = self.equity_curve
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        drawdown_pct = (cumulative / running_max - 1) * 100
        
        max_dd = drawdown.min()
        max_dd_pct = drawdown_pct.min()
        
        # 计算回撤持续天数
        dd_duration = 0
        max_duration = 0
        in_drawdown = False
        
        for i in range(len(cumulative)):
            if drawdown.iloc[i] < 0:
                if not in_drawdown:
                    in_drawdown = True
                    dd_duration = 0
                dd_duration += 1
            else:
                if in_drawdown:
                    max_duration = max(max_duration, dd_duration)
                    in_drawdown = False
        
        max_duration = max(max_duration, dd_duration)
        
        return abs(max_dd), abs(max_dd_pct), max_duration
    
    def calculate_information_ratio(self, periods_per_year: int = 252) -> float:
        """
        计算信息比率 (相对于基准)
        
        Args:
            periods_per_year: 年化周期数
        
        Returns:
            信息比率
        """
        if self.benchmark is None or len(self.benchmark) == 0:
            return 0.0
        
        # 对齐基准
        returns = self.returns
        bench_returns = self.benchmark.pct_change().dropna()
        
        # 找到共同日期
        common_idx = returns.index.intersection(bench_returns.index)
        if len(common_idx) == 0:
            return 0.0
        
        returns = returns.loc[common_idx]
        bench_returns = bench_returns.loc[common_idx]
        
        active_returns = returns - bench_returns
        tracking_error = active_returns.std() * np.sqrt(periods_per_year)
        
        if tracking_error == 0:
            return 0.0
        
        return active_returns.mean() * periods_per_year / tracking_error
    
    def calculate_omega_ratio(self, threshold: float = 0.0) -> float:
        """
        计算Omega比率
        
        Args:
            threshold: 阈值收益率
        
        Returns:
            Omega比率
        """
        if len(self.returns) == 0:
            return 0.0
        
        excess = self.returns - threshold
        gains = excess[excess > 0].sum()
        losses = abs(excess[excess < 0].sum())
        
        if losses == 0:
            return float('inf') if gains > 0 else 0.0
        
        return gains / losses
    
    def calculate_tail_ratio(self) -> float:
        """
        计算尾部比率 (右尾/左尾)
        
        Returns:
            尾部比率
        """
        if len(self.returns) == 0:
            return 0.0
        
        # 95%分位
        right_tail = abs(self.returns.quantile(0.95))
        left_tail = abs(self.returns.quantile(0.05))
        
        if left_tail == 0:
            return 0.0
        
        return right_tail / left_tail
    
    def _calculate_trade_metrics(self, metrics: PerformanceMetrics):
        """计算交易相关指标"""
        if not self.trades:
            return
        
        winning_trades = []
        losing_trades = []
        holding_periods = []
        
        for trade in self.trades:
            if hasattr(trade, 'pnl'):
                pnl = trade.pnl
                if pnl > 0:
                    winning_trades.append(pnl)
                elif pnl < 0:
                    losing_trades.append(pnl)
            
            if hasattr(trade, 'holding_days'):
                holding_periods.append(trade.holding_days)
        
        metrics.total_trades = len(self.trades)
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades * 100
        
        if winning_trades:
            metrics.avg_win = np.mean(winning_trades)
            metrics.largest_win = max(winning_trades)
        
        if losing_trades:
            metrics.avg_loss = np.mean(losing_trades)
            metrics.largest_loss = min(losing_trades)
        
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            metrics.profit_factor = float('inf')
        
        if holding_periods:
            metrics.avg_holding_days = np.mean(holding_periods)
    
    def get_equity_curve(self) -> pd.DataFrame:
        """
        获取完整权益曲线数据
        
        Returns:
            包含权益、回撤、收益率的DataFrame
        """
        df = pd.DataFrame({
            'equity': self.equity_curve
        })
        
        df['running_max'] = df['equity'].expanding().max()
        df['drawdown'] = df['equity'] - df['running_max']
        df['drawdown_pct'] = (df['equity'] / df['running_max'] - 1) * 100
        df['returns'] = df['equity'].pct_change()
        
        return df
    
    def generate_report(self) -> str:
        """
        生成绩效报告
        
        Returns:
            格式化的报告文本
        """
        metrics = self.calculate_all()
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                      绩效分析报告                               ║
╠══════════════════════════════════════════════════════════════╣
║ 收益指标                                                      ║
╠══════════════════════════════════════════════════════════════╣
  总收益:           {metrics.total_return:>12,.2f} ({metrics.total_return_pct:>8.2f}%)
  年化收益:         {metrics.annual_return:>12,.2f} ({metrics.annual_return_pct:>8.2f}%)
  
║ 风险指标                                                      ║
╠══════════════════════════════════════════════════════════════╣
  波动率 (年化):    {metrics.annual_volatility:>12.2f}%
  最大回撤:         {metrics.max_drawdown:>12,.2f} ({metrics.max_drawdown_pct:>8.2f}%)
  回撤持续天数:     {metrics.max_drawdown_duration:>12} 天
  
║ 风险调整收益                                                   ║
╠══════════════════════════════════════════════════════════════╣
  夏普比率:         {metrics.sharpe_ratio:>12.2f}
  索提诺比率:       {metrics.sortino_ratio:>12.2f}
  卡玛比率:         {metrics.calmar_ratio:>12.2f}
  
║ 交易统计                                                       ║
╠══════════════════════════════════════════════════════════════╣
  总交易次数:       {metrics.total_trades:>12}
  盈利次数:         {metrics.winning_trades:>12}
  亏损次数:         {metrics.losing_trades:>12}
  胜率:             {metrics.win_rate:>12.2f}%
  盈亏比:           {metrics.profit_factor:>12.2f}
  平均盈利:         {metrics.avg_win:>12,.2f}
  平均亏损:         {metrics.avg_loss:>12,.2f}
  平均持仓天数:     {metrics.avg_holding_days:>12.1f}
  
║ 其他指标                                                       ║
╠══════════════════════════════════════════════════════════════╣
  Omega比率:        {metrics.omega_ratio:>12.2f}
  尾部比率:         {metrics.tail_ratio:>12.2f}
  偏度:             {metrics.skewness:>12.2f}
  峰度:             {metrics.kurtosis:>12.2f}
╚══════════════════════════════════════════════════════════════╝
"""
        return report


def analyze_performance(equity_curve: pd.Series, trades: List = None,
                       benchmark: pd.Series = None, risk_free_rate: float = 0.03) -> PerformanceMetrics:
    """
    快速绩效分析
    
    Args:
        equity_curve: 权益曲线
        trades: 交易记录
        benchmark: 基准曲线
        risk_free_rate: 无风险利率
    
    Returns:
        绩效指标
    """
    analyzer = PerformanceAnalyzer(equity_curve, trades, benchmark, risk_free_rate)
    return analyzer.calculate_all()
