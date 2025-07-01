#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: test_enhanced_functionality.py
功能描述: 
    测试重构后的增强功能，演示如何获取更多股票信息
    
主要功能:
    1. 测试connect_parse_screener_picker_list的增强功能
    2. 展示新增字段的获取和使用
    3. 提供使用示例和数据展示
    
使用方式:
    python test_enhanced_functionality.py
    
注意事项:
    - 需要预先启动Chrome浏览器并开启远程调试端口9222
    - 确保已登录SeekingAlpha账户
"""

import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import json

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_func import connect_parse_screener_picker_list, get_ticker_rating_info


def test_enhanced_screener_list():
    """
    测试增强后的筛选器列表功能
    """
    print("=== 测试增强功能：获取完整的MyAlphaPicker列表信息 ===\n")
    
    try:
        # 连接到Chrome浏览器
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # 测试URL
        picker_list_url = "https://seekingalpha.com/screeners/967141c6704b-TopQuant"
        
        print(f"正在获取列表数据: {picker_list_url}")
        enhanced_data = connect_parse_screener_picker_list(
            url=picker_list_url,
            driver=driver,
            b_save_webpage_csv=True,
            save_path="./test_output"
        )
        
        if enhanced_data:
            print(f"\n✅ 成功获取 {len(enhanced_data)} 个股票的完整信息")
            
            # 显示数据结构
            print("\n📊 数据字段结构:")
            if enhanced_data:
                sample_stock = enhanced_data[0]
                for key, value in sample_stock.items():
                    print(f"  - {key}: {value}")
            
            # 分析和展示统计信息
            analyze_enhanced_data(enhanced_data)
            
            # 保存详细的JSON报告
            save_detailed_report(enhanced_data, "./test_output/enhanced_stock_report.json")
            
        else:
            print("❌ 未能获取到数据")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def analyze_enhanced_data(stocks_data):
    """
    分析增强数据并显示统计信息
    """
    print("\n📈 数据分析报告:")
    
    # 基本统计
    total_stocks = len(stocks_data)
    print(f"  总股票数量: {total_stocks}")
    
    # 价格统计
    prices = []
    market_caps = []
    sectors = {}
    
    for stock in stocks_data:
        # 价格分析
        price_str = stock.get('price', 'N/A')
        if price_str != 'N/A':
            try:
                price = float(price_str.replace('$', '').replace(',', ''))
                prices.append(price)
            except:
                pass
        
        # 市值分析
        market_cap = stock.get('market_cap', 'N/A')
        if market_cap != 'N/A':
            market_caps.append(market_cap)
        
        # 行业分析
        sector = stock.get('sector_industry', 'N/A')
        if sector != 'N/A':
            sectors[sector] = sectors.get(sector, 0) + 1
    
    # 价格统计
    if prices:
        print(f"  价格统计:")
        print(f"    - 平均价格: ${sum(prices)/len(prices):.2f}")
        print(f"    - 最高价格: ${max(prices):.2f}")
        print(f"    - 最低价格: ${min(prices):.2f}")
    
    # 市值分布
    if market_caps:
        print(f"  市值分布: (共{len(market_caps)}个有效数据)")
        market_cap_count = {}
        for cap in market_caps:
            if 'B' in cap:
                market_cap_count['大型股(>10B)'] = market_cap_count.get('大型股(>10B)', 0) + 1
            elif 'M' in cap:
                market_cap_count['中小型股(<10B)'] = market_cap_count.get('中小型股(<10B)', 0) + 1
        
        for cap_type, count in market_cap_count.items():
            print(f"    - {cap_type}: {count}个")
    
    # 行业分布（前5）
    if sectors:
        print(f"  行业分布 (前5名):")
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5]
        for sector, count in sorted_sectors:
            print(f"    - {sector}: {count}个")
    
    # 评级分布
    quant_ratings = {}
    for stock in stocks_data:
        rating = stock.get('quant_rating', 'N/A')
        if rating != 'N/A':
            quant_ratings[rating] = quant_ratings.get(rating, 0) + 1
    
    if quant_ratings:
        print(f"  Quant评级分布:")
        for rating, count in sorted(quant_ratings.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {rating}: {count}个")


def save_detailed_report(stocks_data, filename):
    """
    保存详细的JSON报告
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # 创建报告
        report = {
            "report_timestamp": pd.Timestamp.now().isoformat(),
            "total_stocks": len(stocks_data),
            "data_fields": list(stocks_data[0].keys()) if stocks_data else [],
            "stocks": stocks_data,
            "summary": {
                "strong_buy_count": len([s for s in stocks_data if s.get('quant_rating', '').lower() == 'strong buy']),
                "buy_count": len([s for s in stocks_data if s.get('quant_rating', '').lower() == 'buy']),
                "hold_count": len([s for s in stocks_data if s.get('quant_rating', '').lower() == 'hold']),
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: {filename}")
        
    except Exception as e:
        print(f"❌ 保存报告时发生错误: {e}")


def test_individual_stock_info():
    """
    测试单个股票信息获取
    """
    print("\n=== 测试单个股票信息获取 ===")
    
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=chrome_options)
        
        # 测试几个热门股票
        test_tickers = ["AAPL", "MSFT", "GOOGL"]
        
        for ticker in test_tickers:
            print(f"\n正在获取 {ticker} 的详细信息...")
            result = get_ticker_rating_info(ticker, driver)
            
            if result and 'ratings' in result:
                ratings = result['ratings']
                exchange = result.get('exchange', 'Unknown')
                
                print(f"  交易所: {exchange}")
                print(f"  评级历史记录数: {len(ratings)}")
                
                if ratings:
                    recent_rating = ratings[0]
                    print(f"  最新评级: {recent_rating.get('rating', 'N/A')} ({recent_rating.get('date', 'N/A')})")
    
    except Exception as e:
        print(f"❌ 测试单个股票信息时发生错误: {e}")


def main():
    """
    主测试函数
    """
    print("🚀 开始测试重构后的增强功能\n")
    
    # 确保输出目录存在
    os.makedirs("./test_output", exist_ok=True)
    
    # 测试增强的列表功能
    test_enhanced_screener_list()
    
    # 测试单个股票信息
    test_individual_stock_info()
    
    print("\n🎉 所有测试完成!")
    print("\n📝 测试结果说明:")
    print("1. CSV文件包含所有股票的完整信息")
    print("2. JSON报告包含统计分析和详细数据")
    print("3. 控制台输出显示实时处理状态")
    print("\n💡 新增功能:")
    print("- ✅ 公司名称 (company_name)")
    print("- ✅ 当前价格 (price)")
    print("- ✅ 变化百分比 (change_percent)")
    print("- ✅ 前收盘价 (prev_close)")
    print("- ✅ 市值 (market_cap)")
    print("- ✅ 行业信息 (sector_industry)")
    print("- ✅ 完整的评级信息 (quant/author/sell_side)")


if __name__ == "__main__":
    main() 