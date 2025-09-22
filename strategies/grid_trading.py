"""
网格交易策略 - 在价格区间内设置多个网格进行交易
"""
import math
from typing import Dict, List, Any
from .base_strategy import BaseStrategy

class GridTradingStrategy(BaseStrategy):
    """网格交易策略"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("GridTrading", config)
        
        # 网格参数
        self.grid_count = config.get('grid_count', 10)  # 网格数量
        self.grid_spacing = config.get('grid_spacing', 0.005)  # 网格间距 (0.5%)
        self.base_volume = config.get('base_volume', 0.1)  # 基础交易量
        self.center_price = config.get('center_price', None)  # 中心价格
        
        self.grid_orders = {}  # 记录网格订单
        
    async def execute(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行网格策略"""
        if not self.is_running:
            return []
        
        orders = []
        
        # 获取当前市场价格
        for ticker in self.config.get('tickers', []):
            if ticker not in market_data:
                continue
                
            current_price = market_data[ticker]['price']
            
            # 如果没有设置中心价格，使用当前价格
            if self.center_price is None:
                self.center_price = current_price
            
            # 生成网格订单
            grid_orders = await self._generate_grid_orders(ticker, current_price)
            orders.extend(grid_orders)
        
        return orders
    
    async def _generate_grid_orders(self, ticker: str, current_price: float) -> List[Dict[str, Any]]:
        """生成网格订单"""
        orders = []
        
        # 计算网格价格点
        for i in range(-self.grid_count//2, self.grid_count//2 + 1):
            if i == 0:
                continue  # 跳过中心价格
                
            grid_price = self.center_price * (1 + i * self.grid_spacing)
            
            # 如果价格低于当前价格，下买单
            if grid_price < current_price:
                order = {
                    'ticker': ticker,
                    'side': 'buy',
                    'quantity': self.base_volume,
                    'price': grid_price,
                    'type': 'limit',
                    'strategy': self.name,
                    'grid_level': i
                }
                orders.append(order)
            
            # 如果价格高于当前价格，下卖单
            elif grid_price > current_price:
                order = {
                    'ticker': ticker,
                    'side': 'sell',
                    'quantity': self.base_volume,
                    'price': grid_price,
                    'type': 'limit',
                    'strategy': self.name,
                    'grid_level': i
                }
                orders.append(order)
        
        return orders
    
    async def on_order_update(self, order_update: Dict[str, Any]):
        """处理订单更新"""
        if order_update['status'] == 'filled':
            # 网格订单成交后，在对应位置下反向订单
            await self._place_reverse_order(order_update)
    
    async def _place_reverse_order(self, filled_order: Dict[str, Any]):
        """下反向订单"""
        ticker = filled_order['ticker']
        grid_level = filled_order.get('grid_level', 0)
        
        # 根据成交订单的方向，下反向订单
        if filled_order['side'] == 'buy':
            # 买单成交，在更高价格下卖单
            new_price = filled_order['price'] * (1 + self.grid_spacing)
            new_side = 'sell'
        else:
            # 卖单成交，在更低价格下买单
            new_price = filled_order['price'] * (1 - self.grid_spacing)
            new_side = 'buy'
        
        self.logger.info(f"网格订单成交，下反向订单: {ticker} {new_side} @ {new_price:.6f}")