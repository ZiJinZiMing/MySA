#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: parse_picker_rating.py
功能描述: 
    本模块负责获取并分析 SeekingAlpha 网站上特定股票的 Quant Ratings 历史数据。
    作为 parse_top_quant.py 的辅助模块使用。

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
    2. 可被 parse_top_quant.py 导入并调用其功能
    
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
def parse_ticker_rating_days(ticker_name, driver=None, b_save_webpage=False, rating_list=["Strong Buy"], save_path="./picker_rating", html_file_name=None, desired_item_count=250):
    """
    连接到已打开的Chrome浏览器，获取网页内容，可选保存网页。
    
    参数:
        ticker_name (str): 股票代码
        driver (WebDriver, optional): Selenium WebDriver对象
        b_save_webpage (bool): 是否保存网页
        rating_list (list): 评级数组，匹配规则是数组中包含的评级即为符合标准，不区分大小写
        save_path (str): 保存网页的路径
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
            max_scroll_attempts = 30  # 最多尝试滚动15次，避免无限循环
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
                time.sleep(0.3)  # 等待0.5秒让新内容加载

                # 检查是否有新的内容加载，或者是否到达页面底部且无法再加载
                new_items = driver.find_elements(By.CSS_SELECTOR, "tr.wyOal.aq4es.t_YUL.GAfu6")
                if len(new_items) == current_item_count and scroll_attempt > 10:  # 滚动10次后如果数量不再增加，可能到底了
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

        # 计算从最近一天开始的连续匹配评级天数
        recent_rating_streak = 0
        # 从列表末尾（最新日期）开始向前检查
        for i in range(len(ratings_data) - 1, -1, -1):
            entry = ratings_data[i]
            # 检查当前评级是否在rating_list中（不区分大小写）
            is_matched = False
            for r in rating_list:
                if entry['rating'].lower() == r.lower():
                    is_matched = True
                    break
                    
            if is_matched:
                recent_rating_streak += 1
            else:
                # 一旦遇到不符合条件的评级，就停止计数
                break

        return recent_rating_streak

    except Exception as e:
        print(f"发生错误: {str(e)}")
        return -1


def connect_parse_screener_picker_list(url, driver, b_save_webpage_csv=False, save_path=".", html_file_name=None):
    """
    连接到已打开的Chrome浏览器，下载 MyAlphaPicker 列表网页，确保滚动到底部并等待。
    现在返回包含ticker_name和三种评级信息的完整股票数据。
    """

    try:
        if driver is None:
            # 连接到已打开的Chrome浏览器
            print("driver不能为空")
            return None

            
        print(f"正在打开picker列表网页: {url}")
        driver.get(url)

        print("等待picker列表页面初步加载完成...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='top-rated-ticker-name']"))
            )
            print("特定元素 data-test-id='top-rated-ticker-name' 已定位。")
        except Exception as e:
            print(f"等待特定元素 data-test-id='top-rated-ticker-name' 超时或未找到，将尝试继续执行。错误: {str(e)}")

        # 循环滚动到底部以加载所有ticker
        print("开始滚动页面以确保所有ticker加载...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts_for_list = 15  # 针对列表页的滚动次数上限
        consecutive_no_change_attempts = 0

        while scroll_attempts < max_scroll_attempts_for_list:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # 等待新内容加载
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                consecutive_no_change_attempts += 1
                print(f"页面高度未改变，连续未变次数: {consecutive_no_change_attempts}")
                if consecutive_no_change_attempts >= 3:  # 如果连续3次高度不变，认为已到底部
                    print("页面高度连续多次未变，认为已到达底部。")
                    break
            else:
                consecutive_no_change_attempts = 0  # 高度变化，重置计数器
                print(f"页面已滚动，新高度: {new_height}")
            last_height = new_height
            scroll_attempts += 1
            if scroll_attempts >= max_scroll_attempts_for_list:
                print(f"已达到列表页最大滚动尝试次数 ({max_scroll_attempts_for_list})。")

        print("滚动完成，额外等待3秒确保所有内容渲染完毕...")
        time.sleep(3)

        page_source = driver.page_source

        if html_file_name is None:
            parsed_url = urlparse(url)
            html_file_name = re.sub(r'[\\/*?:"<>|]', "_", parsed_url.netloc + parsed_url.path.replace('/', '_'))
            if not html_file_name.endswith('.html'):
                html_file_name += '.html'


        if b_save_webpage_csv:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            html_full_path = os.path.join(save_path, html_file_name)
            with open(html_full_path, "w", encoding="utf-8") as file:
                file.write(page_source)
            print(f"Picker列表HTML页面已保存到: {html_full_path}")
        else:
            print("SAVE_WEBPAGES 为 False，跳过保存 Picker列表HTML页面。")

        # 使用Selenium直接从浏览器中提取数据
        stocks_data = []
        
        # 查找所有包含ticker的元素
        ticker_elements = driver.find_elements(By.XPATH, "//span[@data-test-id='top-rated-ticker-name']")
        
        for ticker_element in ticker_elements:
            stock_data = {}
            inner_span = ticker_element.find_element(By.XPATH, ".//span")
            if inner_span:
                ticker = inner_span.text.strip()
                if ticker:
                    stock_data['ticker'] = ticker
                    print(f"找到股票: {ticker}")
                    
                    # 获取包含此ticker的行
                    try:
                        row = ticker_element.find_element(By.XPATH, "./ancestor::tr")
                        
                        # 在同一行中查找评级信息
                        try:
                            # 查找Quant Rating
                            quant_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/quant-ratings')]")
                            quant_badge = quant_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                            sr_only = quant_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                            
                            rating_text = sr_only.text.strip()
                            # 处理大小写不敏感的前缀移除
                            if rating_text.upper().startswith("RATING: "):
                                rating_value = rating_text[8:]  # 移除"Rating: "前缀
                            else:
                                rating_value = rating_text
                            
                            full_text = quant_badge.text.strip()
                            score_text = full_text.replace(rating_text, '').strip()
                            
                            stock_data['quant_rating'] = rating_value
                            stock_data['quant_score'] = score_text
                        except Exception as e:
                            stock_data['quant_rating'] = 'N/A'
                            stock_data['quant_score'] = 'N/A'
                        
                        try:
                            # 查找Author Rating
                            author_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/author-ratings')]")
                            author_badge = author_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                            sr_only = author_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                            
                            rating_text = sr_only.text.strip()
                            # 处理大小写不敏感的前缀移除
                            if rating_text.upper().startswith("RATING: "):
                                rating_value = rating_text[8:]  # 移除"Rating: "前缀
                            else:
                                rating_value = rating_text
                            
                            full_text = author_badge.text.strip()
                            score_text = full_text.replace(rating_text, '').strip()
                            
                            stock_data['author_rating'] = rating_value
                            stock_data['author_score'] = score_text
                        except Exception as e:
                            stock_data['author_rating'] = 'N/A'
                            stock_data['author_score'] = 'N/A'
                        
                        try:
                            # 查找Sell-Side Rating
                            sell_side_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/sell-side-ratings')]")
                            sell_side_badge = sell_side_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                            sr_only = sell_side_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                            
                            rating_text = sr_only.text.strip()
                            # 处理大小写不敏感的前缀移除
                            if rating_text.upper().startswith("RATING: "):
                                rating_value = rating_text[8:]  # 移除"Rating: "前缀
                            else:
                                rating_value = rating_text
                            
                            full_text = sell_side_badge.text.strip()
                            score_text = full_text.replace(rating_text, '').strip()
                            
                            stock_data['sell_side_rating'] = rating_value
                            stock_data['sell_side_score'] = score_text
                        except Exception as e:
                            stock_data['sell_side_rating'] = 'N/A'
                            stock_data['sell_side_score'] = 'N/A'
                    except Exception as e:
                        # 若无法找到行或评级，设置为N/A
                        stock_data['quant_rating'] = 'N/A'
                        stock_data['quant_score'] = 'N/A'
                        stock_data['author_rating'] = 'N/A'
                        stock_data['author_score'] = 'N/A'
                        stock_data['sell_side_rating'] = 'N/A'
                        stock_data['sell_side_score'] = 'N/A'
                    
                    stocks_data.append(stock_data)

        if not stocks_data:
            print("未能在找到的元素中提取到有效的股票数据，或提取的数据为空。")
            return []

        print(f"\n总共提取到 {len(stocks_data)} 个股票数据")
        
        # 显示前5个股票的详细信息
        for i, stock in enumerate(stocks_data[:5]):
            ticker = stock.get('ticker', 'N/A')
            quant_rating = stock.get('quant_rating', 'N/A')
            quant_score = stock.get('quant_score', 'N/A')
            author_rating = stock.get('author_rating', 'N/A')
            author_score = stock.get('author_score', 'N/A')
            sell_side_rating = stock.get('sell_side_rating', 'N/A')
            sell_side_score = stock.get('sell_side_score', 'N/A')
            
            print(f"股票 {i+1}: {ticker}")
            print(f"  Quant Rating: {quant_rating}, Score: {quant_score}")
            print(f"  Author Rating: {author_rating}, Score: {author_score}")
            print(f"  Sell-Side Rating: {sell_side_rating}, Score: {sell_side_score}")

        if b_save_webpage_csv:
            try:
                df = pd.DataFrame(stocks_data)
                base_name = "my_alpha_screener_picker"
                csv_filename = f"{base_name}_data.csv"
                csv_full_path = os.path.join(save_path, csv_filename)
                
                # 确保所有列都存在，即使某些股票可能没有这些评级
                required_columns = [
                    'ticker', 
                    'quant_rating', 'quant_score', 
                    'author_rating', 'author_score', 
                    'sell_side_rating', 'sell_side_score'
                ]
                
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = 'N/A'  # 添加缺失的列
                
                # 重新排序列，使ticker列在最前面，然后是各种评级
                columns_order = [col for col in required_columns if col in df.columns]
                other_columns = [col for col in df.columns if col not in required_columns]
                df = df[columns_order + other_columns]
                
                df.to_csv(csv_full_path, index=False, encoding='utf-8', header=True)
                print(f"\n股票数据已成功保存到: {csv_full_path}")
            except Exception as e:
                print(f"保存股票数据到CSV时发生错误: {str(e)}")

        # 只返回完整的股票数据，上层代码可以按需从中提取ticker列表
        return stocks_data


    except Exception as e:
        print(f"下载picker列表页面时发生错误: {str(e)}")
        if driver:
            pass
        return []




def connect_parse_portfolio_picker_list(url, driver, b_save_webpage_csv=False, save_path=".", html_file_name=None):
    """
    连接到已打开的Chrome浏览器，下载 投资组合 列表网页，确保滚动到底部并等待。
    提取股票代码(ticker_name)和三种不同类型的评级信息(quant、author、sell-side)。
    """

    try:
        if driver is None:
            # 连接到已打开的Chrome浏览器
            print("driver不能为空")
            return None

            
        print(f"正在打开picker列表网页: {url}")
        driver.get(url)

        print("等待picker列表页面初步加载完成...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='portfolio-ticker-name']"))
            )
            print("特定元素 data-test-id='portfolio-ticker-name' 已定位。")
        except Exception as e:
            print(f"等待特定元素 data-test-id='portfolio-ticker-name' 超时或未找到，将尝试继续执行。错误: {str(e)}")

        # 获取页面源码
        page_source = driver.page_source

        if html_file_name is None:
            parsed_url = urlparse(url)
            html_file_name = re.sub(r'[\\/*?:"<>|]', "_", parsed_url.netloc + parsed_url.path.replace('/', '_'))
            if not html_file_name.endswith('.html'):
                html_file_name += '.html'

        if b_save_webpage_csv:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            html_full_path = os.path.join(save_path, html_file_name)
            with open(html_full_path, "w", encoding="utf-8") as file:
                file.write(page_source)
            print(f"Picker列表HTML页面已保存到: {html_full_path}")
        else:
            print("SAVE_WEBPAGES 为 False，跳过保存 Picker列表HTML页面。")

        # 使用Selenium直接从浏览器中提取数据
        stocks_data = []
        
        # 查找所有包含ticker的行
        ticker_elements = driver.find_elements(By.XPATH, "//span[@data-test-id='portfolio-ticker-name']")
        
        for ticker_element in ticker_elements:
            stock_data = {}
            ticker = ticker_element.text.strip()
            stock_data['ticker'] = ticker
            
            # 获取包含此ticker的行
            row = ticker_element.find_element(By.XPATH, "./ancestor::tr")
            
            # 在同一行中查找评级信息
            try:
                # 查找Quant Rating
                quant_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/quant-ratings')]")
                quant_badge = quant_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                sr_only = quant_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                
                rating_text = sr_only.text.strip()
                # 处理大小写不敏感的前缀移除
                if rating_text.upper().startswith("RATING: "):
                    rating_value = rating_text[8:]  # 移除"Rating: "前缀
                else:
                    rating_value = rating_text
                
                full_text = quant_badge.text.strip()
                score_text = full_text.replace(rating_text, '').strip()
                
                stock_data['quant_rating'] = rating_value
                stock_data['quant_score'] = score_text
            except Exception as e:
                stock_data['quant_rating'] = 'N/A'
                stock_data['quant_score'] = 'N/A'
            
            try:
                # 查找Author Rating
                author_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/author-ratings')]")
                author_badge = author_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                sr_only = author_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                
                rating_text = sr_only.text.strip()
                # 处理大小写不敏感的前缀移除
                if rating_text.upper().startswith("RATING: "):
                    rating_value = rating_text[8:]  # 移除"Rating: "前缀
                else:
                    rating_value = rating_text
                
                full_text = author_badge.text.strip()
                score_text = full_text.replace(rating_text, '').strip()
                
                stock_data['author_rating'] = rating_value
                stock_data['author_score'] = score_text
            except Exception as e:
                stock_data['author_rating'] = 'N/A'
                stock_data['author_score'] = 'N/A'
            
            try:
                # 查找Sell-Side Rating
                sell_side_link = row.find_element(By.XPATH, ".//a[contains(@href, '/ratings/sell-side-ratings')]")
                sell_side_badge = sell_side_link.find_element(By.XPATH, ".//span[@data-test-id='quant-badge']")
                sr_only = sell_side_badge.find_element(By.XPATH, ".//span[@class='sr-only']")
                
                rating_text = sr_only.text.strip()
                # 处理大小写不敏感的前缀移除
                if rating_text.upper().startswith("RATING: "):
                    rating_value = rating_text[8:]  # 移除"Rating: "前缀
                else:
                    rating_value = rating_text
                
                full_text = sell_side_badge.text.strip()
                score_text = full_text.replace(rating_text, '').strip()
                
                stock_data['sell_side_rating'] = rating_value
                stock_data['sell_side_score'] = score_text
            except Exception as e:
                stock_data['sell_side_rating'] = 'N/A'
                stock_data['sell_side_score'] = 'N/A'
            
            stocks_data.append(stock_data)

        if not stocks_data:
            print("未能在找到的元素中提取到有效的股票数据，或提取的数据为空。")
            return []

        print(f"\n总共提取到 {len(stocks_data)} 个股票数据")
        for i, stock in enumerate(stocks_data[:5]):
            ticker = stock.get('ticker', 'N/A')
            quant_rating = stock.get('quant_rating', 'N/A')
            quant_score = stock.get('quant_score', 'N/A')
            author_rating = stock.get('author_rating', 'N/A')
            author_score = stock.get('author_score', 'N/A')
            sell_side_rating = stock.get('sell_side_rating', 'N/A')
            sell_side_score = stock.get('sell_side_score', 'N/A')
            
            print(f"股票 {i+1}: {ticker}")
            print(f"  Quant Rating: {quant_rating}, Score: {quant_score}")
            print(f"  Author Rating: {author_rating}, Score: {author_score}")
            print(f"  Sell-Side Rating: {sell_side_rating}, Score: {sell_side_score}")

        if b_save_webpage_csv:
            try:
                df = pd.DataFrame(stocks_data)
                
 
                # 从URL中提取portfolioId作为文件名的一部分
                portfolio_id_match = re.search(r'portfolioId=(\d+)', url)
                portfolio_id = portfolio_id_match.group(1) if portfolio_id_match else "unknown"
                base_name = f"portfolio_{portfolio_id}"
                
                csv_filename = f"{html_file_name}_data.csv"
                csv_full_path = os.path.join(save_path, csv_filename)
                
                # 确保所有列都存在，即使某些股票可能没有这些评级
                required_columns = [
                    'ticker', 
                    'quant_rating', 'quant_score', 
                    'author_rating', 'author_score', 
                    'sell_side_rating', 'sell_side_score'
                ]
                
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = 'N/A'  # 添加缺失的列
                
                # 重新排序列，使ticker列在最前面，然后是各种评级
                columns_order = [col for col in required_columns if col in df.columns]
                other_columns = [col for col in df.columns if col not in required_columns]
                df = df[columns_order + other_columns]
                
                df.to_csv(csv_full_path, index=False, encoding='utf-8', header=True)
                print(f"\n股票数据已成功保存到: {csv_full_path}")
            except Exception as e:
                print(f"保存股票数据到CSV时发生错误: {str(e)}")

        return stocks_data


    except Exception as e:
        print(f"下载picker列表页面时发生错误: {str(e)}")
        if driver:
            pass
        return [], []



if __name__ == "__main__":
    ticker_name = "EPR"
    # ticker_name = "BAP"

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    print("正在连接到Chrome浏览器...")
    driver = webdriver.Chrome(options=chrome_options)



    # recent_strong_buy_streak = parse_ticker_rating_days(ticker_name, driver, True)
    # print(f"从最近一天开始，连续 'Strong Buy' 评级的天数为: {recent_strong_buy_streak} 天。")

    # url = "https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker"
    # pickers = connect_parse_screener_picker_list(url, driver=driver, b_save_webpage_csv=True)
    # print(pickers)


    url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124"
    pickers = connect_parse_portfolio_picker_list(url, driver=driver, b_save_webpage_csv=True)
    print(pickers)


