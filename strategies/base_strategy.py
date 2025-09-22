"""
基础策略抽象类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime

class BaseStrategy(ABC):
    """交易策略基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_running = False
        self.logger = logging.getLogger(f"strategy.{name}")
        
        # 策略参数
        self.max_position_size = config.get('max_position_size', 1000)
        self.risk_limit = config.get('risk_limit', 0.02)  # 2% 风险限制
        self.min_spread = config.get('min_spread', 0.0001)  # 最小价差
        
    @abstractmethod
    async def execute(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行策略，返回订单列表"""
        pass
    
    @abstractmethod
    async def on_order_update(self, order_update: Dict[str, Any]):
        """订单状态更新回调"""
        pass
    
    async def start(self):
        """启动策略"""
        self.is_running = True
        self.logger.info(f"策略 {self.name} 已启动")
    
    async def stop(self):
        """停止策略"""
        self.is_running = False
        self.logger.info(f"策略 {self.name} 已停止")
    
    def calculate_position_size(self, price: float, risk_amount: float) -> float:
        """计算仓位大小"""
        return min(risk_amount / price, self.max_position_size)