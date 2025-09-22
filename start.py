#!/usr/bin/env python3
"""
Ethereal 测试网交易量刷取系统 - 快速启动脚本
"""
import subprocess
import sys
import json
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    try:
        import ethereal
        print("✓ ethereal-sdk 已安装")
    except ImportError:
        print("✗ ethereal-sdk 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "ethereal-sdk>=0.1.0b15"])
    
    try:
        import psutil
        print("✓ psutil 已安装")
    except ImportError:
        print("✗ psutil 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil>=5.9.0"])

def create_sample_config():
    """创建示例配置文件"""
    config_path = Path("config.json")
    if config_path.exists():
        print("✓ 配置文件已存在")
        return
    
    sample_config = {
        "accounts": [
            {
                "account_id": "account_1",
                "api_key": "your_api_key_1",
                "api_secret": "your_api_secret_1",
                "balance": {"USDT": 10000, "ETH": 5},
                "available_balance": {"USDT": 9000, "ETH": 4},
                "positions": {},
                "risk_limit": 0.02,
                "max_position_size": 1000
            }
        ],
        "strategies": {
            "self_hedging": {
                "enabled": True,
                "hedge_pairs": [
                    {
                        "ticker": "ETH-USDT",
                        "buy_account": "account_1",
                        "sell_account": "account_1"
                    }
                ],
                "volume_range": [0.01, 0.1],
                "price_offset": 0.0001,
                "execution_interval": 30
            },
            "grid_trading": {"enabled": False},
            "arbitrage": {"enabled": False},
            "market_making": {"enabled": False}
        },
        "risk_management": {
            "max_daily_loss": 1000,
            "max_position_size": 10000,
            "max_drawdown_limit": 0.10
        },
        "monitoring": {
            "log_file": "trading.log"
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print("✓ 已创建示例配置文件 config.json")
    print("  请编辑配置文件设置你的 API 密钥")

def main():
    """主函数"""
    print("=== Ethereal 测试网交易量刷取系统 ===")
    print("正在检查系统环境...")
    
    # 检查 Python 版本
    if sys.version_info < (3, 12):
        print(f"✗ Python 版本过低: {sys.version}")
        print("  需要 Python 3.12 或更高版本")
        return
    
    print(f"✓ Python 版本: {sys.version}")
    
    # 检查依赖
    check_dependencies()
    
    # 创建配置文件
    create_sample_config()
    
    print("\n=== 启动前检查清单 ===")
    print("1. ✓ 依赖包已安装")
    print("2. ✓ 配置文件已创建")
    print("3. ⚠️  请编辑 config.json 设置 API 密钥")
    print("4. ⚠️  确认在测试网环境下运行")
    
    response = input("\n是否现在启动系统? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        print("\n启动系统...")
        subprocess.run([sys.executable, "main.py"])
    else:
        print("\n请先配置 config.json 后手动运行:")
        print("  python main.py")

if __name__ == "__main__":
    main()