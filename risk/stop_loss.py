"""
风控模块 - 止损机制
"""

import pandas as pd
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StopLossRule:
    """止损规则"""
    name: str
    type: str  # 'fixed', 'trailing', 'atr'
    value: float  # 百分比或ATR倍数
    enabled: bool = True


class StopLossManager:
    """止损管理器"""
    
    def __init__(self):
        self.rules = {}
        self.positions = {}  # symbol -> entry_info
    
    def add_rule(self, rule: StopLossRule):
        """添加止损规则"""
        self.rules[rule.name] = rule
    
    def set_positions(self, positions: Dict):
        """设置持仓"""
        self.positions = positions
    
    def check_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        atr: float = None,
        high_price: float = None
    ) -> Optional[str]:
        """
        检查是否触发止损
        
        Returns:
            'STOP_LOSS', 'TAKE_PROFIT', None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # 计算收益率
        return_pct = (current_price - entry_price) / entry_price
        
        # 检查固定止损
        if 'fixed_loss' in self.rules and self.rules['fixed_loss'].enabled:
            if return_pct <= -self.rules['fixed_loss'].value:
                return 'STOP_LOSS'
        
        # 检查止盈
        if 'fixed_profit' in self.rules and self.rules['fixed_profit'].enabled:
            if return_pct >= self.rules['fixed_profit'].value:
                return 'TAKE_PROFIT'
        
        # 检查移动止损
        if 'trailing' in self.rules and self.rules['trailing'].enabled:
            if high_price:
                trailing_stop = high_price * (1 - self.rules['trailing'].value)
                if current_price <= trailing_stop:
                    return 'STOP_LOSS'
        
        # 检查ATR止损
        if 'atr' in self.rules and self.rules['atr'].enabled and atr:
            atr_stop = entry_price - atr * self.rules['atr'].value
            if current_price <= atr_stop:
                return 'STOP_LOSS'
        
        return None
    
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_pct: float,
        risk_pct: float = 0.02
    ) -> int:
        """
        计算仓位大小            capital: 可用资金
           
        
        Args:
 entry_price: 入场价格
            stop_loss_pct: 止损百分比
            risk_pct: 风险承受能力 (默认2%)
        
        Returns:
            买入股数
        """
        risk_amount = capital * risk_pct
        risk_per_share = entry_price * stop_loss_pct
        shares = int(risk_amount / risk_per_share)
        return shares
    
    def should_enter(
        self,
        symbol: str,
        price: float,
        atr: float = None,
        rsi: float = None,
        ma_trend: str = None
    ) -> bool:
        """
        检查是否可以入场
        
        Args:
            price: 当前价格
            atr: ATR值
            rsi: RSI值
            ma_trend: 'up', 'down', 'neutral'
        """
        # RSI过滤
        if rsi:
            if 'rsi_oversold' in self.rules:
                if rsi < self.rules['rsi_oversold'].value:
                    return True
            if 'rsi_overbought' in self.rules:
                if rsi > self.rules['rsi_overbought'].value:
                    return False
        
        # 趋势过滤
        if ma_trend and 'trend_filter' in self.rules:
            rule = self.rules['trend_filter']
            if rule.type == 'up' and ma_trend != 'up':
                return False
            elif rule.type == 'down' and ma_trend != 'down':
                return True


class RiskMonitor:
    """风险监控"""
    
    def __init__(self, max_drawdown: float = 0.15, max_position_pct: float = 0.3):
        self.max_drawdown = max_drawdown  # 最大回撤限制
        self.max_position_pct = max_position_pct  # 单票最大仓位
        self.daily_loss_limit = 0.05  # 单日最大亏损5%
        
        self.peak_equity = 0
        self.today_pnl = 0
    
    def update(self, current_equity: float, today_pnl: float = 0):
        """更新权益"""
        self.today_pnl = today_pnl
        
        # 更新峰值
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
    
    def check_risk(self, current_equity: float) -> Dict[str, bool]:
        """检查风险状态"""
        # 当前回撤
        if self.peak_equity > 0:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        else:
            current_drawdown = 0
        
        return {
            'drawdown_exceeded': current_drawdown >= self.max_drawdown,
            'daily_loss_exceeded': abs(self.today_pnl) / self.peak_equity >= self.daily_loss_limit if self.peak_equity > 0 else False,
            'should_stop': current_drawdown >= self.max_drawdown or 
                          (abs(self.today_pnl) / self.peak_equity >= self.daily_loss_limit if self.peak_equity > 0 else False)
        }
    
    def get_risk_report(self, positions: Dict, prices: Dict, capital: float) -> str:
        """生成风险报告"""
        total_value = sum(pos['quantity'] * prices.get(pos['symbol'], 0) 
                        for pos in positions.values())
        position_ratio = total_value / capital if capital > 0 else 0
        
        current_drawdown = 0
        if self.peak_equity > 0:
            current_drawdown = (self.peak_equity - total_value - capital) / self.peak_equity
        
        report = f"""
📊 风险监控报告
================
总权益:       ${total_value + capital:,.2f}
持仓比例:     {position_ratio*100:.1f}%
当前回撤:    {current_drawdown*100:.1f}%
最大回撤:    {self.max_drawdown*100:.1f}%
日亏损限制:  {self.daily_loss_limit*100:.1f}%

持仓明细:
"""
        for symbol, pos in positions.items():
            value = pos['quantity'] * prices.get(symbol, 0)
            pnl_pct = (prices.get(symbol, 0) - pos['entry_price']) / pos['entry_price'] * 100
            report += f"  {symbol}: {pos['quantity']}股, 成本:{pos['entry_price']:.2f}, 当前:{prices.get(symbol, 0):.2f}, 盈亏:{pnl_pct:+.1f}%\n"
        
        return report


# 预设风控配置
def create_default_stoploss() -> StopLossManager:
    """创建默认止损配置"""
    manager = StopLossManager()
    
    # 固定止损 -5%
    manager.add_rule(StopLossRule(
        name='fixed_loss',
        type='fixed',
        value=-0.05,
        enabled=True
    ))
    
    # 止盈 +15%
    manager.add_rule(StopLossRule(
        name='fixed_profit',
        type='fixed',
        value=0.15,
        enabled=True
    ))
    
    # 移动止损 5%
    manager.add_rule(StopLossRule(
        name='trailing',
        type='trailing',
        value=0.05,
        enabled=True
    ))
    
    # ATR止损 2倍ATR
    manager.add_rule(StopLossRule(
        name='atr',
        type='atr',
        value=2.0,
        enabled=False
    ))
    
    return manager


if __name__ == "__main__":
    # 测试
    manager = create_default_stoploss()
    
    # 模拟持仓
    manager.positions = {
        'AAPL': {'entry_price': 150, 'quantity': 100}
    }
    
    # 检查止损
    signal = manager.check_stop_loss('AAPL', 150, 140)
    print(f"止损信号: {signal}")
    
    # 计算仓位
    size = manager.calculate_position_size(100000, 150, 0.05)
    print(f"建议买入: {size}股")
