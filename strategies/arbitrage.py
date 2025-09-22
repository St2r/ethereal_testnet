"""
套利策略 - 利用不同交易对间的价差进行套利
"""
import asyncio
from typing import Dict, List, Any, Tuple
from .base_strategy import BaseStrategy

class ArbitrageStrategy(BaseStrategy):
    """套利策略"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Arbitrage", config)
        
        # 套利参数
        self.arbitrage_pairs = config.get('arbitrage_pairs', [])  # 套利对配置
        self.min_profit_threshold = config.get('min_profit_threshold', 0.002)  # 最小利润阈值
        self.max_volume = config.get('max_volume', 1.0)  # 最大交易量
        
    async def execute(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行套利策略"""
        if not self.is_running:
            return []
        
        orders = []
        
        # 检查所有套利机会
        for arb_pair in self.arbitrage_pairs:
            arb_orders = await self._check_arbitrage_opportunity(arb_pair, market_data)
            orders.extend(arb_orders)
        
        return orders
    
    async def _check_arbitrage_opportunity(self, arb_pair: Dict[str, Any], market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查套利机会"""
        ticker_a = arb_pair['ticker_a']
        ticker_b = arb_pair['ticker_b']
        exchange_rate = arb_pair.get('exchange_rate', 1.0)  # 汇率或转换比例
        
        if ticker_a not in market_data or ticker_b not in market_data:
            return []
        
        price_a = market_data[ticker_a]['price']
        price_b = market_data[ticker_b]['price']
        
        # 计算价差和利润率
        price_diff = price_a - (price_b * exchange_rate)
        profit_rate = abs(price_diff) / price_a
        
        if profit_rate < self.min_profit_threshold:
            return []
        
        orders = []
        volume = min(self.max_volume, self._calculate_optimal_volume(price_a, price_b))
        
        # 如果 A 比 B 贵，卖 A 买 B
        if price_diff > 0:
            orders.append({
                'ticker': ticker_a,
                'side': 'sell',
                'quantity': volume,
                'price': price_a * 0.999,  # 稍低于市价
                'type': 'limit',
                'strategy': self.name,
                'arbitrage_pair': f"{ticker_a}-{ticker_b}"
            })
            
            orders.append({
                'ticker': ticker_b,
                'side': 'buy',
                'quantity': volume * exchange_rate,
                'price': price_b * 1.001,  # 稍高于市价
                'type': 'limit',
                'strategy': self.name,
                'arbitrage_pair': f"{ticker_a}-{ticker_b}"
            })
        
        # 如果 B 比 A 贵，买 A 卖 B
        else:
            orders.append({
                'ticker': ticker_a,
                'side': 'buy',
                'quantity': volume,
                'price': price_a * 1.001,
                'type': 'limit',
                'strategy': self.name,
                'arbitrage_pair': f"{ticker_a}-{ticker_b}"
            })
            
            orders.append({
                'ticker': ticker_b,
                'side': 'sell',
                'quantity': volume * exchange_rate,
                'price': price_b * 0.999,
                'type': 'limit',
                'strategy': self.name,
                'arbitrage_pair': f"{ticker_a}-{ticker_b}"
            })
        
        if orders:
            self.logger.info(f"发现套利机会: {ticker_a} vs {ticker_b}, 利润率: {profit_rate:.4f}")
        
        return orders
    
    def _calculate_optimal_volume(self, price_a: float, price_b: float) -> float:
        """计算最优交易量"""
        # 这里可以添加更复杂的资金管理逻辑
        return min(self.max_volume, 100 / max(price_a, price_b))
    
    async def on_order_update(self, order_update: Dict[str, Any]):
        """处理订单更新"""
        if order_update['status'] == 'filled':
            arbitrage_pair = order_update.get('arbitrage_pair', '')
            self.logger.info(f"套利订单成交: {arbitrage_pair}")