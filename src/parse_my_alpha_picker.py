#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: parse_my_alpha_picker.py
功能描述: 
    本脚本用于自动化获取并分析 SeekingAlpha 网站的 MyAlphaPicker 列表中的股票信息。
    
主要功能:
    1. 连接到已打开的Chrome浏览器(使用debuggerAddress)
    2. 访问并下载 MyAlphaPicker 列表页面
    3. 解析页面中的所有股票代码(Ticker)
    4. 对每个股票调用 parse_picker_rating 模块获取其 Quant Ratings 历史
    5. 分析每个股票最近连续 "Strong Buy" 评级的天数
    6. 将分析结果保存到CSV文件，包含股票代码和连续Strong Buy天数

使用方式:
    1. 首先确保已启动Chrome浏览器并开启远程调试端口(端口9222)
    2. 运行本脚本，它会自动连接浏览器并执行所有操作
    3. 结果将保存在当前目录下的CSV文件中

注意事项:
    - 脚本设计了随机延时机制，以避免频繁请求被网站限制
    - 支持键盘中断(Ctrl+C)，中断时会保存已收集的数据
"""

import os
import random  # 导入random模块
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common_func import parse_ticker_rating_days, connect_parse_screener_picker_list, connect_parse_portfolio_picker_list


def save_summary_data_to_csv(data_list, save_path, filename):
    """
    将汇总数据保存到CSV文件。
    参数:
        data_list (list): 包含字典的列表，每个字典代表一行数据。
        save_path (str): CSV文件的保存路径。
        filename (str): CSV文件的名称。
    """
    if not data_list:
        print("\\n没有数据可写入总结CSV文件。")
        return

    summary_df = pd.DataFrame(data_list)
    summary_csv_full_path = os.path.join(save_path, filename)
    try:
        summary_df.to_csv(summary_csv_full_path, index=False, encoding='utf-8')
        print(f"\\n已将数据总结保存到: {summary_csv_full_path}")
    except Exception as e:
        print(f"\\n保存总结CSV时发生错误: {str(e)}")

if __name__ == "__main__":
    picker_list_url = "https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker" #MyAlphaPicker列表
    current_save_path = "." 
    summary_filename = "alpha_picker_strong_buy_summary.csv"
    
    results_for_csv = [] 
    driver = None 
    ticker_processed_count = 0 # 初始化已处理ticker的计数器
    long_delay_interval = 10 # 每处理10个ticker后执行长延时

    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器以下载picker列表页面...")
        driver = webdriver.Chrome(options=chrome_options)

        # 获取MyAlphaPicker列表
        print("获取MyAlphaPicker列表...")
        my_alpha_picker_data = connect_parse_screener_picker_list(picker_list_url, driver, b_save_webpage_csv=True)
        
        # 从数据中提取ticker列表
        my_alpha_pickers = [stock['ticker'] for stock in my_alpha_picker_data if 'ticker' in stock]
        
        # 保存完整的股票数据，包括评级信息
        if my_alpha_picker_data:
            try:
                complete_data_filename = "alpha_picker_complete_data.csv"
                complete_df = pd.DataFrame(my_alpha_picker_data)
                complete_csv_path = os.path.join(current_save_path, complete_data_filename)
                complete_df.to_csv(complete_csv_path, index=False, encoding='utf-8')
                print(f"\n完整股票数据（含评级信息）已保存到: {complete_csv_path}")
            except Exception as e:
                print(f"\n保存完整股票数据时发生错误: {str(e)}")
        
        # 获取投资组合
        print("获取持仓组合...")
        my_holdings_url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124"
        my_holdings_data = connect_parse_portfolio_picker_list(my_holdings_url, driver, b_save_webpage_csv=True)
        
        # 从数据中提取ticker列表
        my_holdings = [stock['ticker'] for stock in my_holdings_data if 'ticker' in stock]
        
        # 保存持仓组合完整数据
        if my_holdings_data:
            try:
                holdings_data_filename = "portfolio_holdings_complete_data.csv"
                holdings_df = pd.DataFrame(my_holdings_data)
                holdings_csv_path = os.path.join(current_save_path, holdings_data_filename)
                holdings_df.to_csv(holdings_csv_path, index=False, encoding='utf-8')
                print(f"\n持仓组合完整数据已保存到: {holdings_csv_path}")
            except Exception as e:
                print(f"\n保存持仓组合完整数据时发生错误: {str(e)}")
        
        # 获取观察列表
        print("获取观察列表...")
        my_watch_list_url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63351093"
        my_watch_list_data = connect_parse_portfolio_picker_list(my_watch_list_url, driver)
        
        # 从数据中提取ticker列表
        my_watch_list = [stock['ticker'] for stock in my_watch_list_data if 'ticker' in stock]
        
        # 保存观察列表完整数据
        if my_watch_list_data:
            try:
                watchlist_data_filename = "portfolio_watchlist_complete_data.csv"
                watchlist_df = pd.DataFrame(my_watch_list_data)
                watchlist_csv_path = os.path.join(current_save_path, watchlist_data_filename)
                watchlist_df.to_csv(watchlist_csv_path, index=False, encoding='utf-8')
                print(f"\n观察列表完整数据已保存到: {watchlist_csv_path}")
            except Exception as e:
                print(f"\n保存观察列表完整数据时发生错误: {str(e)}")

        # 从my_alpha_pickers中去掉my_holdings和my_watch_list中的股票
        all_tickers = [ticker for ticker in my_alpha_pickers if ticker not in my_holdings and ticker not in my_watch_list]
        print(f"\\n将为以下股票代码分析 Quant Ratings: {len(all_tickers)}个 - {all_tickers}")

        if not all_tickers:
            print("未能从 MyAlphaPicker 页面提取到任何股票代码，程序终止。")
        else:
            print(f"\\n将为以下股票代码分析 Quant Ratings: {len(all_tickers)}个 - {all_tickers}")

            for ticker_name in all_tickers:
                ticker_processed_count += 1 # 递增计数器

                # 每处理一定数量的ticker后，执行一次较长的随机延时
                if ticker_processed_count % long_delay_interval == 0 and ticker_processed_count > 0:
                    long_random_delay = random.uniform(10, 30) # 10到30秒的长延时
                    print(f"\\n已处理 {ticker_processed_count} 个ticker，执行额外长延时 {long_random_delay:.2f} 秒...")
                    time.sleep(long_random_delay)

                print(f"\\n--- 开始处理 Ticker ({ticker_processed_count}/{len(all_tickers)}): {ticker_name} ---")
                # ticker_rating_url = f"https://seekingalpha.com/symbol/{ticker_name}/ratings/quant-ratings"
                
                streak_days = parse_ticker_rating_days(
                    ticker_name,
                    save_path=current_save_path,
                    driver=driver,
                    b_save_webpage=True,
                )
                results_for_csv.append({'Ticker': ticker_name, 'RecentStrongBuyStreakDays': streak_days})

                print(f"--- 完成处理 Ticker: {ticker_name} ---")
        
        print("\\n所有股票处理完毕。")
        save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename)

    except KeyboardInterrupt:
        print("\\n脚本被用户中断。正在保存已收集的数据...")
        save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename) 
    
    except Exception as e:
        print(f"\\n处理过程中发生意外错误: {e}")
        print("正在尝试保存已收集的数据...")
        save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename) 

    finally:
        if driver:
            print("\\n脚本执行完毕或被中断。浏览器状态由用户控制。")
            pass 



