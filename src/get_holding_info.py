#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取ticker的持仓信息
获取信息：Symbol/Price/Shares/Weight/Value

专注于获取投资组合的基本持仓信息，不包含评级数据
"""

import csv
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common_func import connect_parse_portfolio_picker_list



def create_csv_with_header(filename):
    """
    创建CSV文件并写入表头
    
    参数:
        filename (str): CSV文件名
    """
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Symbol', 'Price', 'Shares', 'Weight', 'Value'])
        print(f"创建CSV文件: {filename}")
    else:
        print(f"CSV文件已存在: {filename}")


def main():
    """
    获取投资组合持仓信息的主函数
    专注于获取Symbol/Price/Shares/Weight/Value基本信息
    """
    # holdings_url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124"
    # holdings_url = "https://seekingalpha.com/account/portfolio/total_view?portfolioId=63326124"
    holdings_url = "https://seekingalpha.com/account/portfolio/total_view?portfolioId=64139349"
    output_file = "holdings_basic_info.csv"
    save_path = "."
    
    # 确保保存路径存在
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        print(f"创建保存路径: {save_path}")
    
    # CSV文件完整路径
    csv_filename = os.path.join(save_path, output_file)
    
    driver = None
    
    try:
        # 连接到已打开的Chrome浏览器
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # 获取持仓组合数据
        holdings_data = connect_parse_portfolio_picker_list(
            holdings_url,
            driver,
            b_save_webpage_csv=True,
            save_path=save_path,
        )
        
        if not holdings_data:
            print("未获取到任何持仓股票信息")
            return []

        print(f"已获取 {len(holdings_data)} 个持仓股票信息")

        # 创建基本信息CSV文件
        create_csv_with_header(csv_filename)

        # 将基本持仓信息写入CSV文件
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Symbol', 'Price', 'Shares', 'Weight', 'Value'])
            
            for stock in holdings_data:
                symbol = stock.get('ticker', 'N/A')
                price = stock.get('price', 'N/A')
                shares = stock.get('shares', 'N/A')
                weight = stock.get('weight', 'N/A')
                value = stock.get('value', 'N/A')
                
                writer.writerow([symbol, price, shares, weight, value])

        print(f"基本持仓信息已保存到: {csv_filename}")

        # 显示统计摘要
        print(f"\n📊 持仓统计摘要:")
        print(f"  总持仓股票数量: {len(holdings_data)}")
        
        # 权重统计
        weights = [stock.get('weight', '0%') for stock in holdings_data if stock.get('weight', 'N/A') != 'N/A']
        if weights:
            try:
                weight_values = [float(w.replace('%', '')) for w in weights if '%' in w]
                if weight_values:
                    print(f"  持仓权重统计:")
                    print(f"    - 总权重: {sum(weight_values):.2f}%")
                    print(f"    - 平均权重: {sum(weight_values)/len(weight_values):.2f}%")
                    print(f"    - 最大权重: {max(weight_values):.2f}%")
                    print(f"    - 最小权重: {min(weight_values):.2f}%")
            except Exception as e:
                print(f"    权重统计计算出错: {e}")

        # 股票价值统计
        values = []
        for stock in holdings_data:
            value_str = stock.get('value', '0')
            if value_str != 'N/A' and value_str != '0':
                try:
                    # 移除逗号并转换为float
                    value_num = float(value_str.replace(',', ''))
                    values.append(value_num)
                except:
                    pass
        
        if values:
            print(f"  持仓价值统计:")
            print(f"    - 总价值: ${sum(values):,.2f}")
            print(f"    - 平均价值: ${sum(values)/len(values):,.2f}")
            print(f"    - 最大持仓价值: ${max(values):,.2f}")

        # 显示前10个持仓（按权重排序）
        def safe_weight_convert(stock):
            """安全地转换权重值为float"""
            weight = stock.get('weight', '0%')
            if weight in ['N/A', '-', '', None]:
                return 0
            try:
                # 移除%符号并转换为float
                weight_str = str(weight).replace('%', '')
                return float(weight_str)
            except (ValueError, TypeError):
                return 0
        
        sorted_stocks = sorted(holdings_data, 
                             key=safe_weight_convert, 
                             reverse=True)[:10]
        
        if sorted_stocks:
            print(f"\n🏆 权重最大的前10支股票:")
            for i, stock in enumerate(sorted_stocks):
                symbol = stock.get('ticker', 'N/A')
                price = stock.get('price', 'N/A')
                shares = stock.get('shares', 'N/A')
                weight = stock.get('weight', 'N/A')
                value = stock.get('value', 'N/A')
                print(f"  {i+1:2d}. {symbol:6s} | 价格: {price:>8s} | 股数: {shares:>8s} | 权重: {weight:>6s} | 价值: {value:>10s}")

    except KeyboardInterrupt:
        print("\n脚本被用户中断。")
    
    except Exception as e:
        print(f"\n处理过程中发生意外错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            print("\n脚本执行完毕。浏览器状态由用户控制。") 


if __name__ == "__main__":
    main() 