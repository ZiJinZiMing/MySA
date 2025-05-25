#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: parse_picker_rating.py
功能描述: 
    本模块负责获取并分析 SeekingAlpha 网站上特定股票的 Quant Ratings 历史数据。
    作为 parse_my_alpha_picker.py 的辅助模块使用。

主要功能:
    1. connect_and_parse_ticker_rating: 
       - 连接到已打开的Chrome浏览器
       - 访问指定股票的Quant Ratings页面
       - 滚动页面以确保加载足够多的历史评级数据
       - 可选保存页面HTML到本地
       
    2. analyze_strong_buy_streak:
       - 分析页面中的评级历史数据
       - 计算从最近一天开始的连续 "Strong Buy" 评级天数
       - 返回连续天数值
       
使用方式:
    1. 可作为独立脚本运行，用于测试单个股票的评级分析
    2. 可被 parse_my_alpha_picker.py 导入并调用其功能
    
注意事项:
    - 脚本通过 debuggerAddress 连接到已打开的Chrome浏览器
    - 评级分析从最新日期向过去扫描，计算连续Strong Buy天数
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


# 连接到已打开的Chrome浏览器，获取网页内容，可选保存网页。
def parse_ticker_rating_days(ticker_name, driver=None, b_save_webpage=False, rating="Strong Buy", save_path="./picker_rating", html_file_name=None):
    """
    连接到已打开的Chrome浏览器，获取网页内容，可选保存网页。
    
    参数:
        ticker_name (str): 股票代码
        b_save_webpage (bool): 是否保存网页
        html_file_name (str, optional): HTML文件名
    """

    url = f"https://seekingalpha.com/symbol/{ticker_name}/ratings/quant-ratings"

    try:
        if driver is None:
            # 连接到已打开的Chrome浏览器
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            print("正在连接到Chrome浏览器以获取ticker评级页面...")
            driver = webdriver.Chrome(options=chrome_options)

        # 打开网页
        print(f"正在打开网页: {url}")
        driver.get(url)

        # 等待页面加载完成
        print("等待页面加载完成...")
        try:
            # 修改等待条件，等待 data-test-id="table-body-infinite" 元素出现
            # 同时将等待超时时间保持为30秒
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='table-body-infinite']"))
            )
            print("特定元素 data-test-id='table-body-infinite' 已定位。")

            # 循环滚动直到加载足够多的条目
            max_scroll_attempts = 30  # 最多尝试滚动30次，避免无限循环
            desired_item_count = 90
            scroll_attempt = 0

            while scroll_attempt < max_scroll_attempts:
                # 计算当前加载的条目数量
                # 使用类名来定位表格行，这些类名来自用户提供的HTML片段
                # 'tr.wyOal.aq4es.t_YUL.GAfu6'
                # 在By.CSS_SELECTOR中，类名之间的空格用点（.）连接
                items = driver.find_elements(By.CSS_SELECTOR, "tr.wyOal.aq4es.t_YUL.GAfu6")
                current_item_count = len(items)
                print(f"当前已加载 {current_item_count} 个条目。")

                if current_item_count >= desired_item_count:
                    print(f"已加载 {current_item_count} 个条目，达到目标数量 {desired_item_count}。")
                    break

                # 向下滚动页面
                print("向下滚动页面以加载更多条目...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待2秒让新内容加载

                # 检查是否有新的内容加载，或者是否到达页面底部且无法再加载
                new_items = driver.find_elements(By.CSS_SELECTOR, "tr.wyOal.aq4es.t_YUL.GAfu6")
                if len(new_items) == current_item_count and scroll_attempt > 5:  # 滚动5次后如果数量不再增加，可能到底了
                    print("滚动后条目数量未增加，可能已到达页面底部。")
                    # break # 可以选择在这里中断，或者继续尝试直到max_scroll_attempts

                scroll_attempt += 1
                if scroll_attempt >= max_scroll_attempts:
                    print(f"已达到最大滚动尝试次数 ({max_scroll_attempts})，当前条目数量: {current_item_count}。")

        except Exception as e:
            print(f"等待或滚动过程中发生错误: {str(e)}")

        # 生成文件名
        if html_file_name is None:
            parsed_url = urlparse(url)
            html_file_name = re.sub(r'[\\/*?:"<>|]', "_", parsed_url.netloc + parsed_url.path.replace('/', '_'))
            if not html_file_name.endswith('.html'):
                html_file_name += '.html'

        page_source = driver.page_source
        if b_save_webpage:
            # 确保保存路径存在
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            # 完整文件路径
            html_full_path = os.path.join(save_path, html_file_name)

            # 保存HTML页面
            with open(html_full_path, "w", encoding="utf-8") as file:
                file.write(page_source)
            print(f"HTML页面已保存到: {html_full_path}")

        # 开始分析网页内容
        soup = BeautifulSoup(page_source, 'html.parser')

        # 定位所有评级条目的表格行
        # 类名来自用户之前提供的HTML片段和脚本中的CSS选择器
        rating_rows = soup.select("tr.wyOal.aq4es.t_YUL.GAfu6")

        if not rating_rows:
            print("在HTML中未能找到评级条目。")
            return 0

        ratings_data = []
        for row in rating_rows:
            date_element = row.find('th', scope='row')
            rating_element = row.find('span', attrs={'data-test-id': 'card-rating'})

            if date_element and rating_element:
                date_str = date_element.get_text(strip=True)
                rating_str = rating_element.get_text(strip=True)
                ratings_data.append({'date': date_str, 'rating': rating_str})

        if not ratings_data:
            print("未能从HTML条目中解析出日期和评级数据。")
            return 0

        # HTML中的条目通常是日期倒序（最新在前），将其反转以得到正确的时序
        ratings_data.reverse()

        # 计算从最近一天开始的连续 "Strong Buy" 天数
        recent_strong_buy_streak = 0
        # 从列表末尾（最新日期）开始向前检查
        for i in range(len(ratings_data) - 1, -1, -1):
            entry = ratings_data[i]
            # print(f"检查倒序日期: {entry['date']}, 评级: {entry['rating']}") # 可选：打印每个条目以供调试
            if entry['rating'] == rating:
                recent_strong_buy_streak += 1
            else:
                # 一旦遇到非 Strong Buy，就停止计数，因为我们要的是从最近开始的连续天数
                break

        return recent_strong_buy_streak

    except Exception as e:
        print(f"发生错误: {str(e)}")
        return -1


if __name__ == "__main__":
    ticker_name = "EPR"
    # ticker_name = "BAP"

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    print("正在连接到Chrome浏览器...")
    driver = webdriver.Chrome(options=chrome_options)

    recent_strong_buy_streak = parse_ticker_rating_days(ticker_name, driver, True)
    print(f"从最近一天开始，连续 'Strong Buy' 评级的天数为: {recent_strong_buy_streak} 天。")

