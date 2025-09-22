"""
做市策略 - 在买卖盘口提供流动性
"""
import asyncio
from typing import Dict, List, Any
from .base_strategy import BaseStrategy

class MarketMakingStrategy(BaseStrategy):
    """做市策略"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("MarketMaking", config)
        
        # 做市参数
        self.spread_ratio = config.get('spread_ratio', 0.002)  # 价差比例
        self.order_size = config.get('order_size', 0.1)  # 订单大小
        self.max_inventory = config.get('max_inventory', 1.0)  # 最大库存
        self.inventory_skew = config.get('inventory_skew', 0.5)  # 库存偏斜
        
        self.current_inventory = {}  # 当前库存
        
    async def execute(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行做市策略"""
        if not self.is_running:
            return []
        
        orders = []
        
        for ticker in self.config.get('tickers', []):
            if ticker not in market_data:
                continue
            
            market_price = market_data[ticker]['price']
            current_inv = self.current_inventory.get(ticker, 0)
            
            # 计算买卖价格
            bid_price, ask_price = self._calculate_bid_ask_prices(market_price, current_inv)
            
            # 计算订单数量（考虑库存）
            bid_size, ask_size = self._calculate_order_sizes(current_inv)
            
            if bid_size > 0:
                orders.append({
                    'ticker': ticker,
                    'side': 'buy',
                    'quantity': bid_size,
                    'price': bid_price,
                    'type': 'limit',
                    'strategy': self.name
                })
            
            if ask_size > 0:
                orders.append({
                    'ticker': ticker,
                    'side': 'sell',
                    'quantity': ask_size,
                    'price': ask_price,
                    'type': 'limit',
                    'strategy': self.name
                })
        
        return orders
    
    def _calculate_bid_ask_prices(self, market_price: float, inventory: float) -> tuple:
        """计算买卖价格"""
        base_spread = market_price * self.spread_ratio
        
        # 根据库存调整价差
        inventory_adjustment = inventory * self.inventory_skew * base_spread
        
        bid_price = market_price - base_spread/2 - inventory_adjustment
        ask_price = market_price + base_spread/2 - inventory_adjustment
        
        return bid_price, ask_price
    
    def _calculate_order_sizes(self, inventory: float) -> tuple:
        """计算订单大小"""
        # 根据库存调整订单大小
        inventory_ratio = inventory / self.max_inventory
        
        # 如果库存过多，减少买单，增加卖单
        if inventory > 0:
            bid_size = self.order_size * (1 - inventory_ratio)
            ask_size = self.order_size * (1 + inventory_ratio)
        else:
            bid_size = self.order_size * (1 + abs(inventory_ratio))
            ask_size = self.order_size * (1 - abs(inventory_ratio))
        
        # 确保不超过最大库存限制
        if abs(inventory) >= self.max_inventory:
            if inventory > 0:
                bid_size = 0  # 停止买入
            else:
                ask_size = 0  # 停止卖出
        
        return max(0, bid_size), max(0, ask_size)
    
    async def on_order_update(self, order_update: Dict[str, Any]):
        """处理订单更新"""
        if order_update['status'] == 'filled':
            ticker = order_update['ticker']
            side = order_update['side']
            quantity = order_update['quantity']
            
            # 更新库存
            if ticker not in self.current_inventory:
                self.current_inventory[ticker] = 0
            
            if side == 'buy':
                self.current_inventory[ticker] += quantity
            else:
                self.current_inventory[ticker] -= quantity
            
            self.logger.info(f"做市订单成交: {ticker} {side} {quantity}, 当前库存: {self.current_inventory[ticker]:.4f}")