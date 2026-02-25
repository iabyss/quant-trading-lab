"""
仓位管理模块
"""

import numpy as np
from typing import Dict, Optional


class PositionSizing:
    """仓位管理"""
    
    @staticmethod
    def fixed_amount(capital: float, amount: float, price: float) -> int:
        """
        固定金额买入
        
        Args:
            capital: 总资金
            amount: 买入金额
            price: 价格
        
        Returns:
            可买入数量
        """
        quantity = int(amount / price / 100) * 100  # 整手
        return max(0, quantity)
    
    @staticmethod
    def fixed_percent(capital: float, percent: float, price: float) -> int:
        """
        固定比例仓位
        
        Args:
            capital: 总资金
            percent: 仓位比例 (0-1)
            price: 价格
        
        Returns:
            可买入数量
        """
        amount = capital * percent
        return PositionSizing.fixed_amount(capital, amount, price)
    
    @staticmethod
    def fixed_shares(capital: float, shares: int, price: float, max_percent: float = 0.3) -> int:
        """
        固定股数买入（带仓位限制）
        
        Args:
            capital: 总资金
            shares: 目标股数
            price: 价格
            max_percent: 最大仓位比例
        
        Returns:
            实际买入数量
        """
        max_amount = capital * max_percent
        max_shares = int(max_amount / price / 100) * 100
        
        return min(shares, max_shares)
    
    @staticmethod
    def kelly(capital: float, win_rate: float, avg_win: float, 
              avg_loss: float, price: float, max_kelly: float = 0.25) -> int:
        """
        Kelly公式仓位管理
        
        Args:
            capital: 总资金
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损（正值）
            price: 价格
            max_kelly: 最大Kelly比例
        
        Returns:
            买入数量
        """
        if avg_loss <= 0:
            return 0
        
        # Kelly = W - (1-W)/R
        # W = win_rate, R = avg_win/avg_loss
        win_loss_ratio = avg_win / avg_loss
        kelly = win_rate - (1 - win_rate) / win_loss_ratio
        
        # 限制最大仓位
        kelly = min(kelly, max_kelly)
        kelly = max(kelly, 0)  # 不允许负数
        
        amount = capital * kelly
        return PositionSizing.fixed_amount(capital, amount, price)
    
    @staticmethod
    def volatility_based(capital: float, target_vol: float, 
                        historical_vol: float, price: float,
                        max_percent: float = 0.3) -> int:
        """
        基于波动率的
        
        Args:
仓位管理            capital: 总资金
            target_vol: 目标波动率
            historical_vol: 历史波动率
            price: 价格
            max_percent: 最大仓位比例
        
        Returns:
            买入数量
        """
        if historical_vol <= 0:
            return 0
        
        # 波动率调整仓位
        vol_ratio = target_vol / historical_vol
        vol_ratio = min(vol_ratio, 2.0)  # 最多2倍
        
        percent = min(max_percent, 0.1 * vol_ratio)  # 基础10%仓位
        
        amount = capital * percent
        return PositionSizing.fixed_amount(capital, amount, price)
    
    @staticmethod
    def martingale(capital: float, base_amount: float, price: float,
                   last_win: bool = None, sequence: list = None) -> int:
        """
        马丁格尔仓位管理
        
        Args:
            capital: 总资金
            base_amount: 基础金额
            price: 价格
            last_win: 上次是否盈利
            sequence: 连续序列
        
        Returns:
            买入数量
        """
        if sequence is None:
            sequence = []
        
        # 计算连续亏损次数
        losses = sum(1 for x in sequence if x < 0) if sequence else 0
        
        # 亏损后翻倍
        amount = base_amount * (2 ** losses)
        amount = min(amount, capital * 0.5)  # 最多一半仓位
        
        return PositionSizing.fixed_amount(capital, amount, price)
    
    @staticmethod
    def anti_martingale(capital: float, base_amount: float, price: float,
                        last_win: bool = None, sequence: list = None) -> int:
        """
        反马丁格尔仓位管理（盈利加仓）
        
        Args:
            capital: 总资金
            base_amount: 基础金额
            price: 价格
            last_win: 上次是否盈利
            sequence: 连续序列
        
        Returns:
            买入数量
        """
        if sequence is None:
            sequence = []
        
        # 计算连续盈利次数
        wins = sum(1 for x in sequence if x > 0) if sequence else 0
        
        # 盈利后加仓
        amount = base_amount * (1.5 ** wins)
        amount = min(amount, capital * 0.3)  # 最多30%仓位
        
        return PositionSizing.fixed_amount(capital, amount, price)
    
    @staticmethod
    def optimal_f(capital: float, trades: list, price: float,
                  max_percent: float = 0.3) -> int:
        """
        Optimal F 仓位管理
        
        Args:
            capital: 总资金
            trades: 历史交易盈亏列表
            price: 价格
            max_percent: 最大仓位比例
        
        Returns:
            买入数量
        """
        if not trades or len(trades) < 10:
            return PositionSizing.fixed_percent(capital, 0.1, price)
        
        # 计算Optimal F
        trades_arr = np.array(trades)
        max_loss = abs(trades_arr.min())
        
        if max_loss == 0:
            return PositionSizing.fixed_percent(capital, 0.1, price)
        
        # 遍历找最优f
        best_f = 0
        best_twr = 0
        
        for f in np.arange(0.01, 1.0, 0.01):
            # 计算TWR
            twr = 1
            for t in trades_arr:
                if t > 0:
                    twr *= (1 + f * t / max_loss)
                else:
                    twr *= (1 + f * t / max_loss)
            
            if twr > best_twr:
                best_twr = twr
                best_f = f
        
        # 应用仓位
        percent = min(best_f * 0.1, max_percent)
        
        return PositionSizing.fixed_percent(capital, percent, price)


class Portfolio:
    """组合管理"""
    
    def __init__(self, capital: float, max_positions: int = 3):
        """
        初始化组合
        
        Args:
            capital: 初始资金
            max_positions: 最大持仓数
        """
        self.capital = capital
        self.cash = capital
        self.max_positions = max_positions
        self.positions = {}  # {symbol: {'quantity': int, 'avg_price': float}}
        self.history = []
    
    def can_buy(self) -> bool:
        """是否可以买入"""
        return len(self.positions) < self.max_positions and self.cash > 0
    
    def buy(self, symbol: str, price: float, quantity: int) -> bool:
        """
        买入
        
        Args:
            symbol: 股票代码
            price: 价格
            quantity: 数量
        
        Returns:
            是否成功
        """
        cost = price * quantity
        
        if cost > self.cash:
            return False
        
        if symbol in self.positions:
            # 补仓
            pos = self.positions[symbol]
            total_cost = pos['avg_price'] * pos['quantity'] + price * quantity
            pos['quantity'] += quantity
            pos['avg_price'] = total_cost / pos['quantity']
        else:
            if not self.can_buy():
                return False
            self.positions[symbol] = {
                'quantity': quantity,
                'avg_price': price
            }
        
        self.cash -= cost
        return True
    
    def sell(self, symbol: str, price: float, quantity: int = None) -> float:
        """
        卖出
        
        Args:
            symbol: 股票代码
            price: 价格
            quantity: 数量 (None表示全部)
        
        Returns:
            卖出金额
        """
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        
        if quantity is None or quantity >= pos['quantity']:
            # 全部卖出
            quantity = pos['quantity']
            del self.positions[symbol]
        else:
            # 部分卖出
            pos['quantity'] -= quantity
        
        proceeds = price * quantity
        self.cash += proceeds
        
        return proceeds
    
    def get_position_value(self, prices: Dict[str, float]) -> float:
        """
        获取持仓市值
        
        Args:
            prices: 当前价格 {symbol: price}
        
        Returns:
            持仓市值
        """
        value = 0
        for symbol, pos in self.positions.items():
            if symbol in prices:
                value += pos['quantity'] * prices[symbol]
        return value
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """获取总权益"""
        return self.cash + self.get_position_value(prices)
    
    def get_weights(self, prices: Dict[str, float]) -> Dict[str, float]:
        """获取持仓权重"""
        total = self.get_total_value(prices)
        if total == 0:
            return {}
        
        weights = {}
        for symbol, pos in self.positions.items():
            if symbol in prices:
                weight = pos['quantity'] * prices[symbol] / total
                weights[symbol] = weight
        
        return weights
    
    def rebalance(self, target_weights: Dict[str, float], prices: Dict[str, float]):
        """
        调仓
        
        Args:
            target_weights: 目标权重 {symbol: weight}
            prices: 当前价格
        """
        total_value = self.get_total_value(prices)
        
        # 全部清仓
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            if symbol in prices:
                self.sell(symbol, prices[symbol], pos['quantity'])
        
        # 按目标权重买入
        for symbol, weight in target_weights.items():
            if symbol in prices:
                amount = total_value * weight
                quantity = int(amount / prices[symbol] / 100) * 100
                if quantity > 0:
                    self.buy(symbol, prices[symbol], quantity)
    
    def record(self, prices: Dict[str, float]):
        """记录当前状态"""
        total_value = self.get_total_value(prices)
        self.history.append({
            'cash': self.cash,
            'position_value': self.get_position_value(prices),
            'total_value': total_value
        })
    
    def get_returns(self) -> list:
        """获取收益率序列"""
        if not self.history:
            return []
        
        values = [h['total_value'] for h in self.history]
        returns = []
        for i in range(1, len(values)):
            ret = (values[i] - values[i-1]) / values[i-1]
            returns.append(ret)
        
        return returns
