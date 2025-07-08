#!/usr/bin/env python3
"""
MSTR/BTC溢价监控基本使用示例
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gui.core.api_client import APIClient
from gui.core.data_manager import PremiumData
from gui.services.monitor_service import MonitorService


def basic_monitoring_example():
    """基本监控示例"""
    print("MSTR/BTC溢价监控基本示例")
    print("=" * 50)
    
    # 初始化组件
    api_client = APIClient("your_finnhub_api_key_here")
    data_manager = PremiumData(max_points=100)
    monitor_service = MonitorService(api_client, data_manager)
    
    # 测试API连接
    print("测试API连接...")
    if api_client.test_connection():
        print("✓ API连接成功")
    else:
        print("✗ API连接失败，请检查API密钥")
        return
    
    # 获取一次数据
    print("\n获取当前数据...")
    try:
        mstr_price = api_client.get_ticker_price("MSTR")
        btc_price = api_client.get_ticker_price("BTCUSD")
        
        if mstr_price and btc_price:
            # 计算溢价率
            btc_per_share = 0.00207973  # 默认值
            premium = ((mstr_price / (btc_price * btc_per_share)) - 1) * 100
            
            print(f"MSTR价格: ${mstr_price:.2f}")
            print(f"BTC价格: ${btc_price:.2f}")
            print(f"溢价率: {premium:.2f}%")
            
            # 添加到数据管理器
            from datetime import datetime
            data_manager.add_data_point(datetime.now(), mstr_price, btc_price, premium)
            
            print(f"\n数据点数量: {data_manager.get_data_count()}")
            
        else:
            print("✗ 获取价格数据失败")
            
    except Exception as e:
        print(f"✗ 发生错误: {e}")


def api_client_example():
    """API客户端使用示例"""
    print("\nAPI客户端示例")
    print("=" * 30)
    
    # 创建API客户端
    api_client = APIClient("your_api_key", timeout=5)
    
    # 获取多个股票价格
    symbols = ["MSTR", "BTCUSD", "AAPL", "TSLA"]
    
    for symbol in symbols:
        try:
            price = api_client.get_ticker_price(symbol)
            if price:
                print(f"{symbol}: ${price:.2f}")
            else:
                print(f"{symbol}: 获取失败")
        except Exception as e:
            print(f"{symbol}: 错误 - {e}")


def data_manager_example():
    """数据管理器使用示例"""
    print("\n数据管理器示例")
    print("=" * 30)
    
    # 创建数据管理器
    data_manager = PremiumData(max_points=10)
    
    # 添加模拟数据
    from datetime import datetime, timedelta
    base_time = datetime.now()
    
    for i in range(5):
        timestamp = base_time + timedelta(minutes=i)
        mstr_price = 300.0 + i * 2.5
        btc_price = 50000.0 + i * 100
        premium = 25.0 + i * 0.5
        
        data_manager.add_data_point(timestamp, mstr_price, btc_price, premium)
    
    # 获取数据统计
    stats = data_manager.get_statistics()
    print(f"数据点数量: {stats['count']}")
    print(f"平均溢价率: {stats['avg_premium']:.2f}%")
    print(f"最大溢价率: {stats['max_premium']:.2f}%")
    print(f"最小溢价率: {stats['min_premium']:.2f}%")
    
    # 获取最新数据
    latest = data_manager.get_latest_data()
    if latest:
        print(f"最新数据: {latest[0]} - 溢价率: {latest[3]:.2f}%")


if __name__ == "__main__":
    print("选择示例:")
    print("1. 基本监控示例")
    print("2. API客户端示例")
    print("3. 数据管理器示例")
    print("4. 运行所有示例")
    
    try:
        choice = input("\n请输入选择 (1-4): ")
        
        if choice == "1":
            basic_monitoring_example()
        elif choice == "2":
            api_client_example()
        elif choice == "3":
            data_manager_example()
        elif choice == "4":
            basic_monitoring_example()
            api_client_example()
            data_manager_example()
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")