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

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import random # 导入random模块

from common_func import parse_ticker_rating_days

# 全局变量，控制是否将下载的网页保存到本地文件
SAVE_WEBPAGES = False # 设置为 False 则不保存HTML文件


def connect_to_chrome_and_download_picker_list_page(url, driver=None, save_path=".", html_file_name=None):
    """
    连接到已打开的Chrome浏览器，下载 MyAlphaPicker 列表网页，确保滚动到底部并等待。
    """

    try:
        print(f"正在打开picker列表网页: {url}")
        driver.get(url)

        print("等待picker列表页面初步加载完成...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='top-rated-ticker-wrapper']"))
            )
            print("特定元素 data-test-id='top-rated-ticker-wrapper' 已定位。")
        except Exception as e:
            print(f"等待特定元素 data-test-id='top-rated-ticker-wrapper' 超时或未找到，将尝试继续执行。错误: {str(e)}")

        # 循环滚动到底部以加载所有ticker
        print("开始滚动页面以确保所有ticker加载...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts_for_list = 15 # 针对列表页的滚动次数上限
        consecutive_no_change_attempts = 0

        while scroll_attempts < max_scroll_attempts_for_list:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # 等待新内容加载
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                consecutive_no_change_attempts += 1
                print(f"页面高度未改变，连续未变次数: {consecutive_no_change_attempts}")
                if consecutive_no_change_attempts >= 3: # 如果连续3次高度不变，认为已到底部
                    print("页面高度连续多次未变，认为已到达底部。")
                    break
            else:
                consecutive_no_change_attempts = 0 # 高度变化，重置计数器
                print(f"页面已滚动，新高度: {new_height}")
            last_height = new_height
            scroll_attempts += 1
            if scroll_attempts >= max_scroll_attempts_for_list:
                print(f"已达到列表页最大滚动尝试次数 ({max_scroll_attempts_for_list})。")

        print("滚动完成，额外等待5秒确保所有内容渲染完毕...")
        time.sleep(5)
        
        page_source = driver.page_source

        if html_file_name is None:
            parsed_url = urlparse(url)
            html_file_name = re.sub(r'[\\/*?:"<>|]', "_", parsed_url.netloc + parsed_url.path.replace('/', '_'))
            if not html_file_name.endswith('.html'):
                html_file_name += '.html'
        
        if SAVE_WEBPAGES:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            html_full_path = os.path.join(save_path, html_file_name)
            with open(html_full_path, "w", encoding="utf-8") as file:
                file.write(page_source)
            print(f"Picker列表HTML页面已保存到: {html_full_path}")
        else:
            print("SAVE_WEBPAGES 为 False，跳过保存 Picker列表HTML页面。")
            
        return page_source, html_file_name
        
    except Exception as e:
        print(f"下载picker列表页面时发生错误: {str(e)}")
        if driver: 
             pass
        return None, None, None


def parse_ticker_symbols_from_page(page_source, b_save_csv, save_path, source_html_filename): # source_html_filename might not be relevant if not saving
    """
    从HTML页面源码中解析、打印股票代码，并将它们保存到CSV文件。
    股票代码位于 data-test-id="top-rated-ticker-name" 的 span 标签内部的子 span 中。
    """
    if not page_source:
        print("页面源码为空，无法解析股票代码。")
        return []

    soup = BeautifulSoup(page_source, 'html.parser')
    
    ticker_name_spans = soup.find_all('span', attrs={'data-test-id': 'top-rated-ticker-name'})
    
    if not ticker_name_spans:
        print("未能找到包含股票代码的元素 (data-test-id='top-rated-ticker-name')。")
        return []
        
    print("\\n提取到的股票代码:")
    tickers_list = []
    for span in ticker_name_spans:
        inner_span = span.find('span')
        if inner_span and inner_span.string:
            ticker = inner_span.string.strip()
            if ticker:
                print(ticker) 
                tickers_list.append(ticker)
    
    if not tickers_list:
        print("未能在找到的元素中提取到有效的股票代码，或提取的代码为空。CSV文件未生成。")
        return []

    if b_save_csv :
        #
        try:
            df = pd.DataFrame(tickers_list, columns=['Ticker'])
            # Use a fixed name or derive from URL if source_html_filename is None when not saving
            if source_html_filename: # source_html_filename is still passed
                 base_name = os.path.splitext(source_html_filename)[0]
            else: # Fallback if filename wasn't generated (e.g. if SAVE_WEBPAGES was false and filename logic skipped)
                base_name = "my_alpha_picker_list"
            csv_filename = f"{base_name}_tickers.csv"
            csv_full_path = os.path.join(save_path, csv_filename)
            df.to_csv(csv_full_path, index=False, encoding='utf-8', header=True)
            print(f"\\n股票代码已成功保存到: {csv_full_path}")
        except Exception as e:
            print(f"保存股票代码到CSV时发生错误: {str(e)}")
    pass

    return tickers_list

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

        picker_page_source, picker_html_filename = connect_to_chrome_and_download_picker_list_page(
            picker_list_url,
            driver,
            current_save_path
        )
        
        all_tickers = []
        if picker_page_source:
            all_tickers = parse_ticker_symbols_from_page(picker_page_source, True, current_save_path, picker_html_filename)
            # all_tickers = ["CM","GVA","HENOY","GAP","VIRT","OFG","CINF","AXON","ET","LYFT","BAP","ALL","CPF","MT","COF","BZ","SMP","TGTX"]
            
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
                
                # rating_page_source, rating_html_filename, driver = connect_to_chrome_and_download_ticker_rating_page(
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



