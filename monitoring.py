"""
监控和日志系统
"""
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_volume: float
    average_execution_time: float
    success_rate: float
    pnl: float
    
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "trading_data.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建订单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                account_id TEXT,
                ticker TEXT,
                side TEXT,
                quantity REAL,
                price REAL,
                status TEXT,
                strategy TEXT,
                created_at TEXT,
                filled_at TEXT,
                pnl REAL
            )
        ''')
        
        # 创建性能指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                timestamp TEXT PRIMARY KEY,
                total_trades INTEGER,
                successful_trades INTEGER,
                failed_trades INTEGER,
                total_volume REAL,
                average_execution_time REAL,
                success_rate REAL,
                pnl REAL
            )
        ''')
        
        # 创建风险事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                severity TEXT,
                description TEXT,
                account_id TEXT,
                ticker TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_order(self, order_data: Dict[str, Any]):
        """保存订单数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO orders 
            (order_id, account_id, ticker, side, quantity, price, status, strategy, created_at, filled_at, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_data.get('order_id'),
            order_data.get('account_id'),
            order_data.get('ticker'),
            order_data.get('side'),
            order_data.get('quantity'),
            order_data.get('price'),
            order_data.get('status'),
            order_data.get('strategy'),
            order_data.get('created_at'),
            order_data.get('filled_at'),
            order_data.get('pnl', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_performance_metrics(self, metrics: PerformanceMetrics):
        """保存性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO performance_metrics 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.timestamp.isoformat(),
            metrics.total_trades,
            metrics.successful_trades,
            metrics.failed_trades,
            metrics.total_volume,
            metrics.average_execution_time,
            metrics.success_rate,
            metrics.pnl
        ))
        
        conn.commit()
        conn.close()
    
    def log_risk_event(self, event_type: str, severity: str, description: str, 
                      account_id: str = None, ticker: str = None):
        """记录风险事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO risk_events 
            (timestamp, event_type, severity, description, account_id, ticker)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            severity,
            description,
            account_id,
            ticker
        ))
        
        conn.commit()
        conn.close()

class MonitoringSystem:
    """监控系统"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
        self.db_manager = DatabaseManager()
        
        # 监控指标
        self.metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'execution_times': [],
            'last_update': datetime.now()
        }
        
        # 警报配置
        self.alert_config = config.get('alerts', {})
        self.alert_channels = []
        
        self.is_running = False
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("monitoring_system")
        logger.setLevel(logging.INFO)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器
        log_file = self.config.get('log_file', 'trading.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    async def start(self):
        """启动监控系统"""
        self.is_running = True
        self.logger.info("监控系统启动")
        
        # 启动监控循环
        await asyncio.gather(
            self._performance_monitoring_loop(),
            self._health_check_loop(),
            self._alert_processing_loop()
        )
    
    async def stop(self):
        """停止监控系统"""
        self.is_running = False
        self.logger.info("监控系统停止")
    
    async def _performance_monitoring_loop(self):
        """性能监控循环"""
        while self.is_running:
            try:
                await self._update_performance_metrics()
                await asyncio.sleep(60)  # 每分钟更新一次
            except Exception as e:
                self.logger.error(f"性能监控错误: {e}")
                await asyncio.sleep(60)
    
    async def _update_performance_metrics(self):
        """更新性能指标"""
        now = datetime.now()
        
        # 计算成功率
        total_trades = self.metrics['successful_trades'] + self.metrics['failed_trades']
        success_rate = (self.metrics['successful_trades'] / total_trades) if total_trades > 0 else 0
        
        # 计算平均执行时间
        avg_execution_time = (
            sum(self.metrics['execution_times']) / len(self.metrics['execution_times'])
            if self.metrics['execution_times'] else 0
        )
        
        # 创建性能指标对象
        metrics = PerformanceMetrics(
            timestamp=now,
            total_trades=total_trades,
            successful_trades=self.metrics['successful_trades'],
            failed_trades=self.metrics['failed_trades'],
            total_volume=self.metrics['total_volume'],
            average_execution_time=avg_execution_time,
            success_rate=success_rate,
            pnl=0.0  # 需要从其他模块获取
        )
        
        # 保存到数据库
        self.db_manager.save_performance_metrics(metrics)
        
        # 记录日志
        self.logger.info(f"性能指标更新: 成功率 {success_rate:.2%}, 总交易量 {self.metrics['total_volume']:.2f}")
        
        # 重置执行时间列表（保持最近100个）
        if len(self.metrics['execution_times']) > 100:
            self.metrics['execution_times'] = self.metrics['execution_times'][-100:]
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                self.logger.error(f"健康检查错误: {e}")
                await asyncio.sleep(30)
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        # 检查内存使用
        import psutil
        memory_usage = psutil.virtual_memory().percent
        
        if memory_usage > 90:
            await self._send_alert("high_memory_usage", f"内存使用率过高: {memory_usage:.1f}%")
        
        # 检查成功率
        total_trades = self.metrics['successful_trades'] + self.metrics['failed_trades']
        if total_trades > 10:
            success_rate = self.metrics['successful_trades'] / total_trades
            if success_rate < 0.8:
                await self._send_alert("low_success_rate", f"成功率过低: {success_rate:.2%}")
        
        # 检查平均执行时间
        if self.metrics['execution_times']:
            avg_time = sum(self.metrics['execution_times']) / len(self.metrics['execution_times'])
            if avg_time > 5.0:  # 超过5秒
                await self._send_alert("slow_execution", f"执行时间过长: {avg_time:.2f}秒")
    
    async def _alert_processing_loop(self):
        """警报处理循环"""
        while self.is_running:
            try:
                # 处理待发送的警报
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"警报处理错误: {e}")
                await asyncio.sleep(10)
    
    async def _send_alert(self, alert_type: str, message: str):
        """发送警报"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'severity': 'warning'
        }
        
        self.logger.warning(f"警报: {alert_type} - {message}")
        
        # 记录到数据库
        self.db_manager.log_risk_event(alert_type, 'warning', message)
    
    async def on_order_update(self, order_update: Dict[str, Any]):
        """订单更新回调"""
        # 更新统计
        if order_update['status'] == 'filled':
            self.metrics['successful_trades'] += 1
            self.metrics['total_volume'] += order_update.get('quantity', 0)
        elif order_update['status'] == 'failed':
            self.metrics['failed_trades'] += 1
        
        # 保存订单数据
        self.db_manager.save_order(order_update)
    
    async def on_execution_time(self, execution_time: float):
        """记录执行时间"""
        self.metrics['execution_times'].append(execution_time)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        total_trades = self.metrics['successful_trades'] + self.metrics['failed_trades']
        success_rate = (self.metrics['successful_trades'] / total_trades) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'successful_trades': self.metrics['successful_trades'],
            'failed_trades': self.metrics['failed_trades'],
            'success_rate': success_rate,
            'total_volume': self.metrics['total_volume'],
            'average_execution_time': (
                sum(self.metrics['execution_times']) / len(self.metrics['execution_times'])
                if self.metrics['execution_times'] else 0
            ),
            'last_update': self.metrics['last_update'].isoformat()
        }
    
    def get_historical_data(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """获取历史数据"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM performance_metrics 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]