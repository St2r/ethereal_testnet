"""
交易引擎 - 核心交易执行引擎
"""
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
from ethereal import AsyncRESTClient
from account_manager import AccountManager
from strategies.base_strategy import BaseStrategy

class Order:
    """订单类"""
    
    def __init__(self, order_data: Dict[str, Any]):
        self.order_id = str(uuid.uuid4())
        self.account_id = order_data.get('account_id')
        self.ticker = order_data['ticker']
        self.side = order_data['side']  # 'buy' or 'sell'
        self.quantity = float(order_data['quantity'])
        self.price = float(order_data['price'])
        self.order_type = order_data.get('type', 'limit')
        self.status = 'pending'
        self.strategy = order_data.get('strategy', 'unknown')
        self.created_at = datetime.now()
        self.filled_quantity = 0.0
        self.remaining_quantity = self.quantity
        self.metadata = order_data.get('metadata', {})

class TradingEngine:
    """交易引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_manager = AccountManager(config)
        self.strategies: Dict[str, BaseStrategy] = {}
        self.clients: Dict[str, AsyncRESTClient] = {}
        self.orders: Dict[str, Order] = {}
        self.market_data: Dict[str, Any] = {}
        
        self.logger = logging.getLogger("trading_engine")
        self.is_running = False
        
        # 回调函数
        self.order_update_callbacks: List[Callable] = []
        
        # 初始化客户端
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化交易客户端"""
        for account in self.account_manager.get_active_accounts():
            client = AsyncRESTClient({
                "base_url": "https://api.etherealtest.net",
                "api_key": account.api_key,
                "api_secret": account.api_secret
            })
            self.clients[account.account_id] = client
            self.logger.info(f"初始化客户端: {account.account_id}")
    
    def add_strategy(self, strategy: BaseStrategy):
        """添加交易策略"""
        self.strategies[strategy.name] = strategy
        self.logger.info(f"添加策略: {strategy.name}")
    
    def add_order_update_callback(self, callback: Callable):
        """添加订单更新回调"""
        self.order_update_callbacks.append(callback)
    
    async def start(self):
        """启动交易引擎"""
        self.is_running = True
        self.logger.info("交易引擎启动")
        
        # 启动所有策略
        for strategy in self.strategies.values():
            await strategy.start()
        
        # 启动主循环
        await asyncio.gather(
            self._market_data_loop(),
            self._strategy_execution_loop(),
            self._order_management_loop()
        )
    
    async def stop(self):
        """停止交易引擎"""
        self.is_running = False
        self.logger.info("交易引擎停止")
        
        # 停止所有策略
        for strategy in self.strategies.values():
            await strategy.stop()
        
        # 关闭所有客户端
        for client in self.clients.values():
            await client.close()
    
    async def _market_data_loop(self):
        """市场数据循环"""
        while self.is_running:
            try:
                await self._update_market_data()
                await asyncio.sleep(1)  # 每秒更新一次
            except Exception as e:
                self.logger.error(f"市场数据更新错误: {e}")
                await asyncio.sleep(5)
    
    async def _update_market_data(self):
        """更新市场数据"""
        # 使用第一个可用客户端获取市场数据
        if not self.clients:
            return
        
        client = next(iter(self.clients.values()))
        
        try:
            # 获取所有产品信息
            products = await client.list_products()
            
            for product in products:
                ticker = product.ticker
                # 这里应该获取实时价格，目前使用模拟数据
                self.market_data[ticker] = {
                    'price': 1.0,  # 模拟价格
                    'volume': 0.0,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            self.logger.error(f"获取市场数据失败: {e}")
    
    async def _strategy_execution_loop(self):
        """策略执行循环"""
        while self.is_running:
            try:
                # 并行执行所有策略
                strategy_tasks = []
                for strategy in self.strategies.values():
                    if strategy.is_running:
                        task = asyncio.create_task(self._execute_strategy(strategy))
                        strategy_tasks.append(task)
                
                if strategy_tasks:
                    await asyncio.gather(*strategy_tasks, return_exceptions=True)
                
                await asyncio.sleep(self.config.get('strategy_interval', 10))
            except Exception as e:
                self.logger.error(f"策略执行错误: {e}")
                await asyncio.sleep(5)
    
    async def _execute_strategy(self, strategy: BaseStrategy):
        """执行单个策略"""
        try:
            # 策略生成订单
            orders = await strategy.execute(self.market_data)
            
            # 处理生成的订单
            for order_data in orders:
                await self._submit_order(order_data)
        
        except Exception as e:
            self.logger.error(f"策略 {strategy.name} 执行错误: {e}")
    
    async def _submit_order(self, order_data: Dict[str, Any]):
        """提交订单"""
        try:
            # 创建订单对象
            order = Order(order_data)
            
            # 风险检查
            account_id = order.account_id or "default"
            if not self.account_manager.check_risk_limits(
                account_id, order.quantity, order.ticker
            ):
                self.logger.warning(f"订单风险检查失败: {order.order_id}")
                return
            
            # 获取对应的客户端
            client = self.clients.get(account_id)
            if not client:
                self.logger.error(f"账户 {account_id} 客户端不存在")
                return
            
            # 提交订单到交易所
            try:
                # 这里应该调用实际的下单API
                # exchange_order = await client.create_order(...)
                
                # 模拟订单提交成功
                order.status = 'submitted'
                self.orders[order.order_id] = order
                
                self.logger.info(f"订单提交成功: {order.order_id} {order.ticker} {order.side} {order.quantity}")
                
                # 通知策略订单更新
                await self._notify_order_update(order)
                
            except Exception as e:
                self.logger.error(f"订单提交失败: {e}")
                order.status = 'failed'
                await self._notify_order_update(order)
        
        except Exception as e:
            self.logger.error(f"订单处理错误: {e}")
    
    async def _order_management_loop(self):
        """订单管理循环"""
        while self.is_running:
            try:
                await self._update_order_status()
                await asyncio.sleep(2)  # 每2秒检查一次
            except Exception as e:
                self.logger.error(f"订单管理错误: {e}")
                await asyncio.sleep(5)
    
    async def _update_order_status(self):
        """更新订单状态"""
        # 检查所有待处理订单
        for order in list(self.orders.values()):
            if order.status in ['submitted', 'partial']:
                try:
                    # 这里应该查询实际订单状态
                    # 模拟订单成交
                    if order.status == 'submitted':
                        order.status = 'filled'
                        order.filled_quantity = order.quantity
                        order.remaining_quantity = 0
                        
                        await self._notify_order_update(order)
                        
                except Exception as e:
                    self.logger.error(f"更新订单状态失败: {order.order_id}, {e}")
    
    async def _notify_order_update(self, order: Order):
        """通知订单更新"""
        order_update = {
            'order_id': order.order_id,
            'account_id': order.account_id,
            'ticker': order.ticker,
            'side': order.side,
            'quantity': order.quantity,
            'filled_quantity': order.filled_quantity,
            'price': order.price,
            'status': order.status,
            'strategy': order.strategy,
            'timestamp': datetime.now()
        }
        
        # 通知对应策略
        strategy = self.strategies.get(order.strategy)
        if strategy:
            await strategy.on_order_update(order_update)
        
        # 调用回调函数
        for callback in self.order_update_callbacks:
            try:
                await callback(order_update)
            except Exception as e:
                self.logger.error(f"订单更新回调错误: {e}")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        status = {}
        for name, strategy in self.strategies.items():
            status[name] = {
                'name': strategy.name,
                'is_running': strategy.is_running,
                'config': strategy.config
            }
        return status
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计"""
        total_orders = len(self.orders)
        filled_orders = sum(1 for order in self.orders.values() if order.status == 'filled')
        
        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'fill_rate': filled_orders / total_orders if total_orders > 0 else 0,
            'orders_by_strategy': {},
            'orders_by_status': {}
        }