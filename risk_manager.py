"""
风险管理模块 - 交易风险控制和资金管理
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

@dataclass
class RiskMetrics:
    """风险指标"""
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    var_95: float = 0.0  # 95% VaR
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0

class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("risk_manager")
        
        # 风险限制参数
        self.max_daily_loss = config.get('max_daily_loss', 1000)  # 最大日损失
        self.max_position_size = config.get('max_position_size', 10000)  # 最大仓位
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.10)  # 最大回撤10%
        self.max_leverage = config.get('max_leverage', 3.0)  # 最大杠杆
        
        # 仓位管理参数
        self.position_size_method = config.get('position_size_method', 'fixed')
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # 每笔交易风险2%
        
        # 风险监控数据
        self.positions: Dict[str, Dict[str, float]] = {}  # 账户持仓
        self.daily_pnl: Dict[str, float] = {}  # 日盈亏
        self.trade_history: List[Dict[str, Any]] = []  # 交易历史
        self.risk_metrics = RiskMetrics()
        
        # 风险状态
        self.is_risk_mode = False
        self.emergency_stop = False
        
    async def check_pre_trade_risk(self, order_data: Dict[str, Any]) -> bool:
        """交易前风险检查"""
        account_id = order_data.get('account_id', 'default')
        ticker = order_data['ticker']
        side = order_data['side']
        quantity = float(order_data['quantity'])
        price = float(order_data['price'])
        
        # 检查紧急停止状态
        if self.emergency_stop:
            self.logger.warning("紧急停止状态，拒绝所有交易")
            return False
        
        # 检查仓位限制
        if not await self._check_position_limits(account_id, ticker, quantity, side):
            return False
        
        # 检查日损失限制
        if not await self._check_daily_loss_limit(account_id):
            return False
        
        # 检查资金充足性
        if not await self._check_margin_requirements(account_id, quantity, price):
            return False
        
        # 检查回撤限制
        if not await self._check_drawdown_limit(account_id):
            return False
        
        return True
    
    async def _check_position_limits(self, account_id: str, ticker: str, quantity: float, side: str) -> bool:
        """检查仓位限制"""
        if account_id not in self.positions:
            self.positions[account_id] = {}
        
        current_position = self.positions[account_id].get(ticker, 0)
        
        if side == 'buy':
            new_position = current_position + quantity
        else:
            new_position = current_position - quantity
        
        # 检查单一仓位限制
        if abs(new_position) > self.max_position_size:
            self.logger.warning(f"仓位超限: {ticker} {new_position} > {self.max_position_size}")
            return False
        
        return True
    
    async def _check_daily_loss_limit(self, account_id: str) -> bool:
        """检查日损失限制"""
        current_daily_pnl = self.daily_pnl.get(account_id, 0)
        
        if current_daily_pnl < -self.max_daily_loss:
            self.logger.warning(f"日损失超限: {current_daily_pnl} < -{self.max_daily_loss}")
            self.is_risk_mode = True
            return False
        
        return True
    
    async def _check_margin_requirements(self, account_id: str, quantity: float, price: float) -> bool:
        """检查保证金要求"""
        required_margin = quantity * price / self.max_leverage
        # 这里应该检查实际可用资金
        # 简化实现，假设资金充足
        return True
    
    async def _check_drawdown_limit(self, account_id: str) -> bool:
        """检查回撤限制"""
        if self.risk_metrics.current_drawdown > self.max_drawdown_limit:
            self.logger.warning(f"回撤超限: {self.risk_metrics.current_drawdown:.4f} > {self.max_drawdown_limit}")
            self.is_risk_mode = True
            return False
        
        return True
    
    async def update_position(self, account_id: str, ticker: str, side: str, quantity: float, price: float):
        """更新仓位"""
        if account_id not in self.positions:
            self.positions[account_id] = {}
        
        if ticker not in self.positions[account_id]:
            self.positions[account_id][ticker] = 0
        
        if side == 'buy':
            self.positions[account_id][ticker] += quantity
        else:
            self.positions[account_id][ticker] -= quantity
        
        # 记录交易
        trade = {
            'timestamp': datetime.now(),
            'account_id': account_id,
            'ticker': ticker,
            'side': side,
            'quantity': quantity,
            'price': price,
            'value': quantity * price
        }
        self.trade_history.append(trade)
        
        # 更新盈亏
        await self._update_pnl(account_id, ticker, side, quantity, price)
        
        self.logger.info(f"更新仓位: {account_id} {ticker} {self.positions[account_id][ticker]}")
    
    async def _update_pnl(self, account_id: str, ticker: str, side: str, quantity: float, price: float):
        """更新盈亏"""
        # 简化的盈亏计算
        trade_value = quantity * price
        
        if side == 'sell':
            # 卖出时计算盈亏
            if account_id not in self.daily_pnl:
                self.daily_pnl[account_id] = 0
            
            # 假设平均成本价，简化计算
            pnl = trade_value * 0.001  # 假设0.1%的利润
            self.daily_pnl[account_id] += pnl
            self.risk_metrics.daily_pnl += pnl
            self.risk_metrics.total_pnl += pnl
    
    def calculate_position_size(self, account_balance: float, entry_price: float, stop_loss_price: float) -> float:
        """计算仓位大小"""
        if self.position_size_method == 'fixed':
            return self.config.get('fixed_position_size', 100)
        
        elif self.position_size_method == 'risk_based':
            # 基于风险的仓位计算
            risk_amount = account_balance * self.risk_per_trade
            price_risk = abs(entry_price - stop_loss_price)
            
            if price_risk > 0:
                position_size = risk_amount / price_risk
                return min(position_size, self.max_position_size)
        
        elif self.position_size_method == 'kelly':
            # 凯利公式仓位计算（简化版）
            win_rate = self.risk_metrics.win_rate
            profit_factor = self.risk_metrics.profit_factor
            
            if profit_factor > 0 and win_rate > 0:
                kelly_fraction = win_rate - ((1 - win_rate) / profit_factor)
                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制在25%以内
                
                return account_balance * kelly_fraction / entry_price
        
        return self.config.get('default_position_size', 100)
    
    async def update_risk_metrics(self):
        """更新风险指标"""
        if not self.trade_history:
            return
        
        # 计算胜率
        profitable_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
        self.risk_metrics.win_rate = len(profitable_trades) / len(self.trade_history)
        
        # 计算回撤
        equity_curve = self._calculate_equity_curve()
        if equity_curve:
            max_equity = max(equity_curve)
            current_equity = equity_curve[-1]
            self.risk_metrics.current_drawdown = (max_equity - current_equity) / max_equity
            self.risk_metrics.max_drawdown = max(self.risk_metrics.max_drawdown, 
                                                self.risk_metrics.current_drawdown)
    
    def _calculate_equity_curve(self) -> List[float]:
        """计算权益曲线"""
        equity_curve = [10000]  # 假设初始资金10000
        
        for trade in self.trade_history:
            pnl = trade.get('pnl', 0)
            equity_curve.append(equity_curve[-1] + pnl)
        
        return equity_curve
    
    async def emergency_stop_all(self):
        """紧急停止所有交易"""
        self.emergency_stop = True
        self.logger.critical("触发紧急停止！")
        
        # 这里应该取消所有挂单，平仓所有持仓
        # 简化实现
        for account_id in self.positions:
            for ticker in self.positions[account_id]:
                self.positions[account_id][ticker] = 0
        
        self.logger.info("所有仓位已平仓")
    
    def get_risk_report(self) -> Dict[str, Any]:
        """获取风险报告"""
        return {
            'risk_metrics': {
                'max_drawdown': self.risk_metrics.max_drawdown,
                'current_drawdown': self.risk_metrics.current_drawdown,
                'win_rate': self.risk_metrics.win_rate,
                'total_pnl': self.risk_metrics.total_pnl,
                'daily_pnl': self.risk_metrics.daily_pnl
            },
            'positions': self.positions,
            'daily_pnl': self.daily_pnl,
            'risk_limits': {
                'max_daily_loss': self.max_daily_loss,
                'max_position_size': self.max_position_size,
                'max_drawdown_limit': self.max_drawdown_limit
            },
            'risk_status': {
                'is_risk_mode': self.is_risk_mode,
                'emergency_stop': self.emergency_stop
            },
            'trade_count': len(self.trade_history)
        }