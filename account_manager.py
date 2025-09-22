"""
账户管理模块 - 管理多个交易账户和资金分配
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class Account:
    """账户信息"""
    account_id: str
    api_key: str
    api_secret: str
    balance: Dict[str, float]  # 各币种余额
    available_balance: Dict[str, float]  # 可用余额
    positions: Dict[str, float]  # 持仓
    risk_limit: float  # 风险限制
    max_position_size: float  # 最大仓位
    is_active: bool = True

class AccountManager:
    """账户管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.accounts: Dict[str, Account] = {}
        self.logger = logging.getLogger("account_manager")
        
        # 初始化账户
        self._initialize_accounts()
    
    def _initialize_accounts(self):
        """初始化账户"""
        accounts_config = self.config.get('accounts', [])
        
        for account_config in accounts_config:
            account = Account(
                account_id=account_config['account_id'],
                api_key=account_config['api_key'],
                api_secret=account_config['api_secret'],
                balance=account_config.get('balance', {}),
                available_balance=account_config.get('available_balance', {}),
                positions=account_config.get('positions', {}),
                risk_limit=account_config.get('risk_limit', 0.02),
                max_position_size=account_config.get('max_position_size', 1000)
            )
            
            self.accounts[account.account_id] = account
            self.logger.info(f"初始化账户: {account.account_id}")
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户信息"""
        return self.accounts.get(account_id)
    
    def get_active_accounts(self) -> List[Account]:
        """获取活跃账户列表"""
        return [acc for acc in self.accounts.values() if acc.is_active]
    
    async def update_account_balance(self, account_id: str, balance_data: Dict[str, float]):
        """更新账户余额"""
        if account_id in self.accounts:
            self.accounts[account_id].balance.update(balance_data)
            self.logger.debug(f"更新账户 {account_id} 余额")
    
    async def update_account_positions(self, account_id: str, positions_data: Dict[str, float]):
        """更新账户持仓"""
        if account_id in self.accounts:
            self.accounts[account_id].positions.update(positions_data)
            self.logger.debug(f"更新账户 {account_id} 持仓")
    
    def check_risk_limits(self, account_id: str, new_position_size: float, ticker: str) -> bool:
        """检查风险限制"""
        account = self.get_account(account_id)
        if not account:
            return False
        
        current_position = account.positions.get(ticker, 0)
        total_position = abs(current_position + new_position_size)
        
        # 检查单一仓位限制
        if total_position > account.max_position_size:
            self.logger.warning(f"账户 {account_id} 仓位超限: {total_position} > {account.max_position_size}")
            return False
        
        # 检查风险限制
        account_value = sum(account.balance.values())
        position_value = total_position  # 简化计算
        risk_ratio = position_value / account_value if account_value > 0 else 1
        
        if risk_ratio > account.risk_limit:
            self.logger.warning(f"账户 {account_id} 风险超限: {risk_ratio:.4f} > {account.risk_limit}")
            return False
        
        return True
    
    def allocate_funds(self, total_amount: float, allocation_strategy: str = "equal") -> Dict[str, float]:
        """资金分配"""
        active_accounts = self.get_active_accounts()
        
        if not active_accounts:
            return {}
        
        allocation = {}
        
        if allocation_strategy == "equal":
            # 平均分配
            amount_per_account = total_amount / len(active_accounts)
            for account in active_accounts:
                allocation[account.account_id] = amount_per_account
        
        elif allocation_strategy == "risk_weighted":
            # 根据风险限制加权分配
            total_risk_capacity = sum(acc.risk_limit for acc in active_accounts)
            for account in active_accounts:
                weight = account.risk_limit / total_risk_capacity
                allocation[account.account_id] = total_amount * weight
        
        elif allocation_strategy == "balance_weighted":
            # 根据账户余额加权分配
            total_balance = sum(sum(acc.balance.values()) for acc in active_accounts)
            if total_balance > 0:
                for account in active_accounts:
                    account_balance = sum(account.balance.values())
                    weight = account_balance / total_balance
                    allocation[account.account_id] = total_amount * weight
        
        return allocation
    
    def get_account_statistics(self) -> Dict[str, Any]:
        """获取账户统计信息"""
        stats = {
            'total_accounts': len(self.accounts),
            'active_accounts': len(self.get_active_accounts()),
            'total_balance': {},
            'total_positions': {},
            'risk_utilization': {}
        }
        
        for account in self.accounts.values():
            # 汇总余额
            for currency, balance in account.balance.items():
                if currency not in stats['total_balance']:
                    stats['total_balance'][currency] = 0
                stats['total_balance'][currency] += balance
            
            # 汇总持仓
            for ticker, position in account.positions.items():
                if ticker not in stats['total_positions']:
                    stats['total_positions'][ticker] = 0
                stats['total_positions'][ticker] += position
            
            # 计算风险利用率
            account_value = sum(account.balance.values())
            position_value = sum(abs(pos) for pos in account.positions.values())
            risk_util = position_value / account_value if account_value > 0 else 0
            stats['risk_utilization'][account.account_id] = risk_util
        
        return stats