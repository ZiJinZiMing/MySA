#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: get_hold_rating_days_in_portfolios.py
功能描述: 
    获取当前持仓中的股票的Quant Ratings评级天数
    
主要功能:
    1. 连接到已打开的Chrome浏览器(使用debuggerAddress)
    2. 访问并下载投资组合页面
    3. 解析页面中的所有股票信息，包括:
       - 股票代码(Ticker)
       - Quant Ratings评级(如"Strong Buy")和分数(如4.79)
       - Author Ratings评级和分数
       - Sell-Side Ratings评级和分数
    4. 将分析结果保存到CSV文件

使用方式:
    1. 首先确保已启动Chrome浏览器并开启远程调试端口(端口9222)
    2. 运行本脚本，它会自动连接浏览器并执行所有操作
    3. 结果将保存在当前目录下的CSV文件中

命令行参数:
    --url: 投资组合URL (默认: https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124)
    --rating: 要筛选的评级类型 (默认: Hold, 可选: Strong Buy, Buy, Hold, Sell, Strong Sell)
    --output: 输出CSV文件名 (默认: rating_days.csv)
    --path: 保存路径 (默认: 当前目录)

注意事项:
    - 脚本通过debuggerAddress连接到已打开的Chrome浏览器
    - 支持键盘中断(Ctrl+C)，中断时会保存已收集的数据
"""

import csv
import os
import sys
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common_func import connect_parse_portfolio_picker_list, parse_ticker_rating_days


def create_csv_with_header(filename, rating_type="Hold"):
    """
    创建CSV文件并写入表头
    
    参数:
        filename (str): CSV文件名
        rating_type (str): 评级类型
    """
    if not os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['股票代码', f'{rating_type}评级天数'])
        print(f"创建CSV文件: {filename}")
    else:
        print(f"CSV文件已存在: {filename}")



def main():

    
    holdings_url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124"
    rating_type = [ "Hold", "Sell", "Strong Sell"]
    output_file = "hold_rating_days.csv"
    save_path = "."
    exclude_tickers = ["NVDA","AVGO","GOOG","TSLA","MSTR","IBIT","BTC-USD","VOO","TSM"]
    
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
        
        # 获取并分析持仓组合数据
        holdings_tickers = connect_parse_portfolio_picker_list(
            holdings_url,
            driver,
            b_save_webpage_csv=False,
            save_path=save_path,
        )

        if not holdings_tickers:
            print("未获取到任何持仓股票信息")
            return []

        print(f"已获取 {len(holdings_tickers)} 个持仓股票信息")

        match_rating="hold"
        # 创建CSV文件并写入表头
        create_csv_with_header(csv_filename, match_rating)

        # 计数器
        total_matched_stocks = 0
        processed_stocks = []

        # 遍历holdings_tickers中的股票，获取指定评级的股票
        for ticker in holdings_tickers:
            ticker_symbol = ticker.get('ticker', '')
            
            # 排除exclude_tickers列表中的ticker
            if ticker_symbol in exclude_tickers:
                print(f"跳过排除列表中的股票: {ticker_symbol}")
                continue
                
            if ticker.get('quant_rating', '').lower() == match_rating:
                total_matched_stocks += 1
                days = parse_ticker_rating_days(
                    ticker_symbol,
                    driver,
                    rating_list=rating_type,
                    desired_item_count=180
                )
                print(f"股票 {ticker_symbol} 的Quant Ratings评级为{match_rating}的天数: {days}")

                # 将股票代码和评级天数保存到csv文件中
                with open(csv_filename, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([ticker_symbol, days])

                # 记录处理结果
                ticker['rating_days'] = days
                processed_stocks.append(ticker)
        
        # 将processed_stocks写入更详细的CSV文件
        if processed_stocks:
            print(f"\n总计发现 {total_matched_stocks} 支{match_rating}评级股票")
            
            # 创建一个新的CSV文件，包含更多详细信息
            detailed_csv_filename = os.path.join(save_path, f"{match_rating}_detailed.csv")
            
            # 确定所有可能的列
            all_columns = set()
            for stock in processed_stocks:
                all_columns.update(stock.keys())
            
            # 排序列名，使ticker和rating_days出现在前面
            columns = ['ticker', 'rating_days']
            columns.extend([col for col in sorted(all_columns) if col not in columns])
            
            # 写入CSV文件
            with open(detailed_csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for stock in processed_stocks:
                    writer.writerow(stock)
            
            print(f"详细结果已保存到: {detailed_csv_filename}")
        else:
            print(f"\n未能处理任何{match_rating}评级股票")

    except KeyboardInterrupt:
        print("\n脚本被用户中断。")
    
    except Exception as e:
        print(f"\n处理过程中发生意外错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            print("\n脚本执行完毕或被中断。浏览器状态由用户控制。") 


if __name__ == "__main__":
    main() 