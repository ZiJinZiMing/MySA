#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: parse_top_quant.py
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
    - 支持从已存在的CSV缓存文件中读取数据，避免重复查询
"""

import os
import random  # 导入random模块
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common_func import connect_parse_screener_picker_list, connect_parse_portfolio_picker_list, get_ticker_rating_info


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


def load_cached_data(save_path, filename):
    """
    从CSV文件中加载缓存数据。
    
    参数:
        save_path (str): CSV文件的保存路径。
        filename (str): CSV文件的名称。
        
    返回:
        dict: 以ticker为键，连续Strong Buy天数为值的字典。
        list: 包含所有缓存数据的原始列表格式。
    """
    cached_data_dict = {}
    cached_data_list = []

    cache_file_path = os.path.join(save_path, filename)
    if os.path.exists(cache_file_path):
        try:
            cached_df = pd.read_csv(cache_file_path)
            cached_data_list = cached_df.to_dict('records')

            # 转换为字典格式以便快速查找
            for record in cached_data_list:
                if 'Ticker' in record and 'RecentStrongBuyStreakDays' in record:
                    cached_data_dict[record['Ticker']] = record['RecentStrongBuyStreakDays']

            print(f"已从 {cache_file_path} 加载 {len(cached_data_dict)} 条缓存数据")
        except Exception as e:
            print(f"读取缓存文件时发生错误: {str(e)}")
    else:
        print(f"未找到缓存文件: {cache_file_path}")

    return cached_data_dict, cached_data_list


def get_buy_rating_info(ticker_name, driver=None):
    """
    获取特定股票的买入评级信息
    
    参数:
        ticker_name (str): 股票代码
        driver (WebDriver, optional): Selenium WebDriver对象
        
    返回:
        tuple: (recent_strong_buy_days, recent_strong_buy_or_buy_days, effect_days_in_strong_buy_or_buy)
            - recent_strong_buy_days: 最近连续Strong Buy的天数
            - recent_strong_buy_or_buy_days: 最近连续Strong Buy或Buy的天数
            - effect_days_in_strong_buy_or_buy: 在连续Strong Buy或Buy天数期间内Strong Buy的天数
    """
    result  = get_ticker_rating_info(ticker_name, driver=driver)
    rating_info = result['ratings']
    exchange = result['exchange']

    # 初始化计数器
    recent_strong_buy_days = 0  # 最近连续StrongBuy的天数
    recent_buy_days = 0  # 最近连续StrongBuy或Buy的天数
    # 连续StrongBuy或Buy的天数过程中StrongBuy的天数
    strong_buy_days_in_recent_buy = 0
    
    # 检查是否成功获取评级信息
    if not rating_info:
        print(f"未能获取到{ticker_name}的评级信息")
        return recent_strong_buy_days, recent_buy_days, strong_buy_days_in_recent_buy, exchange

    # 从最新日期（列表末尾）开始向前处理
    for entry in rating_info:
        rating = entry.get('rating', '').strip()

        # 检查是否为Strong Buy
        if rating.lower() == 'strong buy':
            recent_strong_buy_days += 1
        else:
            # 遇到非Buy/Strong Buy评级，两个连续计数都中断
            break

        # 从最新日期（列表末尾）开始向前处理
    for entry in rating_info:
        rating = entry.get('rating', '').strip()

        # 检查是否为Strong Buy
        if rating.lower() == 'strong buy' or rating.lower() == 'buy':
            recent_buy_days += 1
            # 检查是否为Buy
            if rating.lower() == 'strong buy':
                # Buy符合Strong Buy或Buy的条件
                strong_buy_days_in_recent_buy += 1
        else:
            # 遇到非Buy/Strong Buy评级，两个连续计数都中断
            break



    print(f"{ticker_name} 评级分析结果:")
    print(f"  最近连续Strong Buy天数: {recent_strong_buy_days}")
    print(f"  最近连续Strong Buy或Buy天数: {recent_buy_days}")
    print(f"  连续Strong Buy或Buy期间内Strong Buy的天数: {strong_buy_days_in_recent_buy}")
    
    return recent_strong_buy_days, recent_buy_days, strong_buy_days_in_recent_buy, exchange



def test_get_buy_rating_info():

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    print("正在连接到Chrome浏览器以下载picker列表页面...")
    driver = webdriver.Chrome(options=chrome_options)
    ticker_name = "STRT"

    result = get_buy_rating_info(ticker_name, driver=driver)
    print(result)

    return



def main():
    # picker_list_url = "https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker"  # MyAlphaPicker列表
    picker_list_url = "https://seekingalpha.com/screeners/967141c6704b-TopQuant"  # TioQuant列表
    current_save_path = "."
    summary_filename = "alpha_picker_strong_buy_summary.csv"

    # 加载缓存数据
    cached_ticker_data, cached_results = load_cached_data(current_save_path, summary_filename)

    results_for_csv = cached_results.copy() if cached_results else []
    driver = None
    ticker_processed_count = 0  # 初始化已处理ticker的计数器
    long_delay_interval = 10  # 每处理10个ticker后执行长延时
    long_delay_interval_2 = 40  # 每处理40个ticker后执行长延时

    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器以下载picker列表页面...")
        driver = webdriver.Chrome(options=chrome_options)

        # 获取MyAlphaPicker列表
        print("获取MyAlphaPicker列表...")
        my_alpha_picker_data = connect_parse_screener_picker_list(picker_list_url, driver, b_save_webpage_csv=False)

        # 从数据中提取ticker列表和基本信息
        if not my_alpha_picker_data:
            print("未能获取到MyAlphaPicker数据")
            return

        print(f"\\n获取到 {len(my_alpha_picker_data)} 个股票的基本信息")

        # 遍历每个ticker并分析其评级历史
        for stock_info in my_alpha_picker_data:
            ticker = stock_info.get('ticker', '')
            if not ticker:
                continue

            # 检查是否已经在缓存中
            if ticker in cached_ticker_data:
                print(f"\\n跳过已缓存的ticker: {ticker} (连续Strong Buy天数: {cached_ticker_data[ticker]})")
                continue

            print(f"\\n正在分析 {ticker} 的评级历史...")

            # 随机延时
            delay = random.uniform(1, 3)
            print(f"等待 {delay:.1f} 秒...")
            time.sleep(delay)

            try:
                # 获取买入评级信息
                recent_strong_buy_days, recent_buy_days, strong_buy_days_in_recent_buy, exchange = get_buy_rating_info(ticker, driver)

                # 创建综合结果记录
                result_record = {
                    'Ticker': ticker,
                    'CompanyName': stock_info.get('company_name', 'N/A'),
                    'Price': stock_info.get('price', 'N/A'),
                    'ChangePercent': stock_info.get('change_percent', 'N/A'),
                    'PrevClose': stock_info.get('prev_close', 'N/A'),
                    'MarketCap': stock_info.get('market_cap', 'N/A'),
                    'SectorIndustry': stock_info.get('sector_industry', 'N/A'),
                    'Exchange': exchange,
                    'QuantRating': stock_info.get('quant_rating', 'N/A'),
                    'QuantScore': stock_info.get('quant_score', 'N/A'),
                    'AuthorRating': stock_info.get('author_rating', 'N/A'),
                    'AuthorScore': stock_info.get('author_score', 'N/A'),
                    'SellSideRating': stock_info.get('sell_side_rating', 'N/A'),
                    'SellSideScore': stock_info.get('sell_side_score', 'N/A'),
                    'RecentStrongBuyStreakDays': recent_strong_buy_days,
                    'RecentBuyStreakDays': recent_buy_days,
                    'StrongBuyDaysInBuyStreak': strong_buy_days_in_recent_buy,
                }

                results_for_csv.append(result_record)
                ticker_processed_count += 1

                print(f"已处理 {ticker_processed_count} 个ticker")

                # 每处理一定数量的ticker后保存一次数据
                if ticker_processed_count % 5 == 0:
                    save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename)
                    print(f"\\n已保存进度 (处理了 {ticker_processed_count} 个ticker)")

                # 长延时机制
                if ticker_processed_count % long_delay_interval == 0:
                    long_delay = random.uniform(5, 10)
                    print(f"\\n每 {long_delay_interval} 个ticker执行长延时 {long_delay:.1f} 秒...")
                    time.sleep(long_delay)

                if ticker_processed_count % long_delay_interval_2 == 0:
                    very_long_delay = random.uniform(20, 30)
                    print(f"\\n每 {long_delay_interval_2} 个ticker执行超长延时 {very_long_delay:.1f} 秒...")
                    time.sleep(very_long_delay)

            except KeyboardInterrupt:
                print(f"\\n用户中断，已处理 {ticker_processed_count} 个ticker")
                break

            except Exception as e:
                print(f"\\n处理 {ticker} 时发生错误: {str(e)}")
                # 即使发生错误，也要记录基本信息
                result_record = {
                    'Ticker': ticker,
                    'CompanyName': stock_info.get('company_name', 'N/A'),
                    'Price': stock_info.get('price', 'N/A'),
                    'ChangePercent': stock_info.get('change_percent', 'N/A'),
                    'PrevClose': stock_info.get('prev_close', 'N/A'),
                    'MarketCap': stock_info.get('market_cap', 'N/A'),
                    'SectorIndustry': stock_info.get('sector_industry', 'N/A'),
                    'Exchange': 'Error',
                    'QuantRating': stock_info.get('quant_rating', 'N/A'),
                    'QuantScore': stock_info.get('quant_score', 'N/A'),
                    'AuthorRating': stock_info.get('author_rating', 'N/A'),
                    'AuthorScore': stock_info.get('author_score', 'N/A'),
                    'SellSideRating': stock_info.get('sell_side_rating', 'N/A'),
                    'SellSideScore': stock_info.get('sell_side_score', 'N/A'),
                    'RecentStrongBuyStreakDays': -1,  # 错误标记
                    'RecentBuyStreakDays': -1,
                    'StrongBuyDaysInBuyStreak': -1,
                }
                results_for_csv.append(result_record)
                ticker_processed_count += 1

        # 最终保存所有结果
        save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename)

        print(f"\\n\\n=== 分析完成 ===")
        print(f"总共分析了 {ticker_processed_count} 个股票")
        print(f"结果已保存到: {os.path.join(current_save_path, summary_filename)}")

        # 显示统计信息
        if results_for_csv:
            strong_buy_stocks = [r for r in results_for_csv if r.get('RecentStrongBuyStreakDays', 0) > 0]
            buy_stocks = [r for r in results_for_csv if r.get('RecentBuyStreakDays', 0) > 0]
            
            print(f"\\n=== 统计信息 ===")
            print(f"有连续Strong Buy评级的股票数量: {len(strong_buy_stocks)}")
            print(f"有连续Buy评级的股票数量: {len(buy_stocks)}")
            
            if strong_buy_stocks:
                print(f"\\n连续Strong Buy天数最多的前5支股票:")
                strong_buy_sorted = sorted(strong_buy_stocks, key=lambda x: x.get('RecentStrongBuyStreakDays', 0), reverse=True)
                for i, stock in enumerate(strong_buy_sorted[:5]):
                    print(f"  {i+1}. {stock['Ticker']} ({stock.get('CompanyName', 'N/A')}): {stock['RecentStrongBuyStreakDays']}天")
                    print(f"     行业: {stock.get('SectorIndustry', 'N/A')}, 市值: {stock.get('MarketCap', 'N/A')}")

    except KeyboardInterrupt:
        print("\\n程序被用户中断")
        if results_for_csv:
            save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename)
            print(f"已保存当前进度到: {os.path.join(current_save_path, summary_filename)}")

    except Exception as e:
        print(f"\\n处理过程中发生意外错误: {e}")
        import traceback
        traceback.print_exc()
        if results_for_csv:
            save_summary_data_to_csv(results_for_csv, current_save_path, summary_filename)
            print(f"已保存当前进度到: {os.path.join(current_save_path, summary_filename)}")

    finally:
        if driver:
            print("\\n脚本执行完毕。浏览器保持打开状态。")

if __name__ == "__main__":
    main()
    # test_get_buy_rating_info()