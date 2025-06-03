#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: parse_portfolio.py
功能描述: 
    本脚本用于自动化获取并分析 SeekingAlpha 网站上用户投资组合的股票信息。
    
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

注意事项:
    - 脚本通过debuggerAddress连接到已打开的Chrome浏览器
    - 支持键盘中断(Ctrl+C)，中断时会保存已收集的数据
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from common_func import connect_parse_portfolio_picker_list

if __name__ == "__main__":
    # 投资组合和观察列表的URL
    holdings_url = "https://seekingalpha.com/account/portfolio/summary?portfolioId=63326124"
    
    # 保存路径
    current_save_path = "." 
    
    try:
        # 连接到已打开的Chrome浏览器
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # 获取并分析持仓组合数据
        print(f"\n正在获取持仓组合数据: {holdings_url}")
        holdings_tickers = connect_parse_portfolio_picker_list(
            holdings_url, 
            driver, 
            b_save_webpage_csv=True, 
            save_path=current_save_path,
        )
        print(f"已获取 {len(holdings_tickers)} 个持仓股票信息")
   
        
    except KeyboardInterrupt:
        print("\n脚本被用户中断。")
    
    except Exception as e:
        print(f"\n处理过程中发生意外错误: {e}")
    
    finally:
        if driver:
            print("\n脚本执行完毕或被中断。浏览器状态由用户控制。") 