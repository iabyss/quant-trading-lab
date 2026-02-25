"""
模拟交易执行模块
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"      # 市价单
    LIMIT = "LIMIT"       # 限价单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待成交
    FILLED = "FILLED"        # 已成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"   # 已拒绝


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    action: str  # 'BUY' or 'SELL'
    order_type: OrderType
    quantity: int
    price: float = None  # 限价单价格
    filled_price: float = None
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: datetime = None
    notes: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_price: float
    entry_date: datetime
    unrealized_pnl: float = 0


class TradingSimulator:
    """模拟交易执行器"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.001,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.order_id_counter = 0
        self.trade_history = []
    
    def create_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: float = None,
        notes: str = ""
    ) -> Order:
        """创建订单"""
        self.order_id_counter += 1
        order = Order(
            order_id=f"ORD_{self.order_id_counter:06d}",
            symbol=symbol,
            action=action,
            order_type=order_type,
            quantity=quantity,
            price=price,
            notes=notes
        )
        self.orders.append(order)
        return order
    
    def execute_order(self, order: Order, current_price: float) -> bool:
        """执行订单"""
        if order.status != OrderStatus.PENDING:
            return False
        
        # 计算成交价
        if order.action == 'BUY':
            exec_price = current_price * (1 + self.slippage)
        else:
            exec_price = current_price * (1 - self.slippage)
        
        # 计算成本
        total_cost = order.quantity * exec_price
        commission_cost = total_cost * self.commission
        
        if order.action == 'BUY':
            # 检查资金
            if total_cost + commission_cost > self.cash:
                order.status = OrderStatus.REJECTED
                return False
            
            # 扣除资金
            self.cash -= (total_cost + commission_cost)
            
            # 更新持仓
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_value = pos.avg_price * pos.quantity + exec_price * order.quantity
                pos.quantity += order.quantity
                pos.avg_price = total_value / pos.quantity
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_price=exec_price,
                    entry_date=datetime.now()
                )
        
        else:  # SELL
            if order.symbol not in self.positions:
                order.status = OrderStatus.REJECTED
                return False
            
            pos = self.positions[order.symbol]
            if pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                return False
            
            # 计算收益
            gross = order.quantity * exec_price
            commission_cost = gross * self.commission
            stamp_duty = gross * 0.001 if order.action == 'SELL' else 0
            net = gross - commission_cost - stamp_duty
            
            # 更新现金
            self.cash += net
            
            # 更新持仓
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                del self.positions[order.symbol]
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_price = exec_price
        order.filled_quantity = order.quantity
        order.filled_at = datetime.now()
        
        # 记录交易
        self.trade_history.append({
            'order_id': order.order_id,
            'symbol': order.symbol,
            'action': order.action,
            'quantity': order.quantity,
            'price': exec_price,
            'commission': commission_cost,
            'timestamp': order.filled_at
        })
        
        return True
    
    def process_market_order(self, symbol: str, action: str, quantity: int, 
                            current_price: float, notes: str = "") -> Order:
        """处理市价单"""
        order = self.create_order(symbol, action, quantity, OrderType.MARKET, notes=notes)
        self.execute_order(order, current_price)
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """获取组合市值"""
        positions_value = 0
        for symbol, pos in self.positions.items():
            if symbol in prices:
                positions_value += pos.quantity * prices[symbol]
                pos.unrealized_pnl = (prices[symbol] - pos.avg_price) * pos.quantity
            else:
                pos.unrealized_pnl = 0
        return self.cash + positions_value
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'cash': self.cash,
            'positions_count': len(self.positions),
            'pending_orders': len([o for o in self.orders if o.status == OrderStatus.PENDING]),
            'total_trades': len(self.trade_history)
        }
    
    def print_status(self):
        """打印状态"""
        print("\n" + "="*50)
        print("📊 模拟交易状态")
        print("="*50)
        print(f"现金:        ${self.cash:,.2f}")
        print(f"持仓数量:    {len(self.positions)}")
        print(f"待成交订单:  {len([o for o in self.orders if o.status == OrderStatus.PENDING])}")
        print(f"总交易次数:  {len(self.trade_history)}")
        
        if self.positions:
            print("\n📈 持仓明细:")
            for symbol, pos in self.positions.items():
                print(f"  {symbol}: {pos.quantity}股, 成本:{pos.avg_price:.2f}, 未实现盈亏:${pos.unrealized_pnl:,.2f}")
        
        print("="*50)


class StrategyExecutor:
    """策略执行器 - 连接策略信号和交易执行"""
    
    def __init__(self, simulator: TradingSimulator):
        self.simulator = simulator
    
    def execute_signal(self, symbol: str, signal: str, current_price: float, 
                      quantity: int = None):
        """
        执行信号
        
        signal: 'BUY', 'SELL', 'HOLD', 'CLOSE_ALL'
        """
        if signal == 'HOLD':
            return
        
        if signal == 'BUY':
            if quantity is None:
                # 使用一半资金
                available = self.simulator.cash * 0.5
                quantity = int(available / (current_price * 1.001))
            
            if quantity > 0:
                self.simulator.process_market_order(symbol, 'BUY', quantity, current_price)
                print(f"🟢 买入 {symbol} {quantity}股 @ ${current_price:.2f}")
        
        elif signal == 'SELL':
            pos = self.simulator.get_position(symbol)
            if pos:
                sell_qty = quantity or pos.quantity
                self.simulator.process_market_order(symbol, 'SELL', sell_qty, current_price)
                print(f"🔴 卖出 {symbol} {sell_qty}股 @ ${current_price:.2f}")
        
        elif signal == 'CLOSE_ALL':
            pos = self.simulator.get_position(symbol)
            if pos:
                self.simulator.process_market_order(symbol, 'SELL', pos.quantity, current_price)
                print(f"🔴 清仓 {symbol} {pos.quantity}股 @ ${current_price:.2f}")


if __name__ == "__main__":
    # 测试
    sim = TradingSimulator(initial_capital=100000)
    executor = StrategyExecutor(sim)
    
    print("初始状态:")
    sim.print_status()
    
    # 模拟交易
    executor.execute_signal('AAPL', 'BUY', current_price=150)
    executor.execute_signal('AAPL', 'BUY', current_price=155)
    
    print("\n交易后状态:")
    print(f"组合价值: ${sim.get_portfolio_value({'AAPL': 160}):,.2f}")
    sim.print_status()
