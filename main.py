"""
Ethereal 测试网交易量刷取主程序
低磨损策略自动化交易系统
"""
import asyncio
import json
import logging
from pathlib import Path

from trading_engine import TradingEngine
from risk_manager import RiskManager
from monitoring import MonitoringSystem

# 策略导入
from strategies.self_hedging import SelfHedgingStrategy
from strategies.grid_trading import GridTradingStrategy
from strategies.arbitrage import ArbitrageStrategy
from strategies.market_making import MarketMakingStrategy

async def main():
    """主程序"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("main")
    
    try:
        # 加载配置
        config_path = Path("config.json")
        if not config_path.exists():
            logger.error("配置文件 config.json 不存在")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info("配置文件加载成功")
        
        # 初始化系统组件
        logger.info("初始化交易引擎...")
        trading_engine = TradingEngine(config)
        
        logger.info("初始化风险管理器...")
        risk_manager = RiskManager(config.get('risk_management', {}))
        
        logger.info("初始化监控系统...")
        monitoring_system = MonitoringSystem(config.get('monitoring', {}))
        
        # 添加策略
        strategies_config = config.get('strategies', {})
        
        if strategies_config.get('self_hedging', {}).get('enabled', False):
            logger.info("添加自对冲策略...")
            strategy = SelfHedgingStrategy(strategies_config['self_hedging'])
            trading_engine.add_strategy(strategy)
        
        if strategies_config.get('grid_trading', {}).get('enabled', False):
            logger.info("添加网格交易策略...")
            strategy = GridTradingStrategy(strategies_config['grid_trading'])
            trading_engine.add_strategy(strategy)
        
        if strategies_config.get('arbitrage', {}).get('enabled', False):
            logger.info("添加套利策略...")
            strategy = ArbitrageStrategy(strategies_config['arbitrage'])
            trading_engine.add_strategy(strategy)
        
        if strategies_config.get('market_making', {}).get('enabled', False):
            logger.info("添加做市策略...")
            strategy = MarketMakingStrategy(strategies_config['market_making'])
            trading_engine.add_strategy(strategy)
        
        # 设置回调
        trading_engine.add_order_update_callback(monitoring_system.on_order_update)
        trading_engine.add_order_update_callback(
            lambda order_update: risk_manager.update_position(
                order_update['account_id'],
                order_update['ticker'],
                order_update['side'],
                order_update['filled_quantity'],
                order_update['price']
            )
        )
        
        logger.info("系统初始化完成")
        
        # 启动系统
        logger.info("=== 启动 Ethereal 交易量刷取系统 ===")
        logger.info("策略概况:")
        for strategy_name, strategy_config in strategies_config.items():
            if strategy_config.get('enabled', False):
                logger.info(f"  ✓ {strategy_name}: 已启用")
            else:
                logger.info(f"  ✗ {strategy_name}: 已禁用")
        
        # 显示账户信息
        logger.info("账户概况:")
        for account in config.get('accounts', []):
            logger.info(f"  账户 {account['account_id']}: 余额 {account['balance']}")
        
        # 并行运行所有组件
        await asyncio.gather(
            trading_engine.start(),
            monitoring_system.start(),
            risk_manager_loop(risk_manager),
            status_reporter(trading_engine, risk_manager, monitoring_system)
        )
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭系统...")
    except Exception as e:
        logger.error(f"系统错误: {e}")
    finally:
        logger.info("系统已停止")

async def risk_manager_loop(risk_manager: RiskManager):
    """风险管理循环"""
    while True:
        try:
            await risk_manager.update_risk_metrics()
            
            # 检查是否需要紧急停止
            risk_report = risk_manager.get_risk_report()
            if risk_report['risk_status']['emergency_stop']:
                break
                
            await asyncio.sleep(60)  # 每分钟更新一次
        except Exception as e:
            logging.getLogger("risk_manager_loop").error(f"风险管理循环错误: {e}")
            await asyncio.sleep(60)

async def status_reporter(trading_engine: TradingEngine, risk_manager: RiskManager, 
                         monitoring_system: MonitoringSystem):
    """状态报告器"""
    logger = logging.getLogger("status_reporter")
    
    while True:
        try:
            await asyncio.sleep(300)  # 每5分钟报告一次
            
            # 获取各模块状态
            strategy_status = trading_engine.get_strategy_status()
            order_stats = trading_engine.get_order_statistics()
            risk_report = risk_manager.get_risk_report()
            monitoring_metrics = monitoring_system.get_current_metrics()
            
            # 打印状态报告
            logger.info("=== 系统状态报告 ===")
            logger.info(f"总订单数: {order_stats['total_orders']}")
            logger.info(f"成功订单数: {order_stats['filled_orders']}")
            logger.info(f"成功率: {order_stats['fill_rate']:.2%}")
            logger.info(f"总交易量: {monitoring_metrics['total_volume']:.2f}")
            logger.info(f"当前盈亏: {risk_report['risk_metrics']['total_pnl']:.2f}")
            logger.info(f"最大回撤: {risk_report['risk_metrics']['max_drawdown']:.2%}")
            
            # 策略状态
            logger.info("策略状态:")
            for name, status in strategy_status.items():
                status_text = "运行中" if status['is_running'] else "已停止"
                logger.info(f"  {name}: {status_text}")
            
            # 风险状态
            if risk_report['risk_status']['is_risk_mode']:
                logger.warning("⚠️  系统处于风险模式")
            
            if risk_report['risk_status']['emergency_stop']:
                logger.critical("🛑 系统紧急停止")
                
        except Exception as e:
            logger.error(f"状态报告错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
