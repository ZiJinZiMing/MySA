#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用于分析HTML结构并提取评级信息的脚本
"""

from bs4 import BeautifulSoup
import re

# 打开HTML文件
html_file = 'seekingalpha.com_account_portfolio_summary.html'
print(f"正在分析文件: {html_file}")

with open(html_file, 'r', encoding='utf-8') as file:
    html_content = file.read()

# 解析HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 查找表格行
rows = soup.find_all('tr')
print(f"找到 {len(rows)} 个表格行")

# 查找ticker和评级相关元素
ticker_found = False
ratings_found = 0

for i, row in enumerate(rows):
    ticker_name_span = row.find('span', attrs={'data-test-id': 'portfolio-ticker-name'})
    if ticker_name_span:
        ticker = ticker_name_span.text.strip()
        ticker_found = True
        
        print(f"\n发现股票 {ticker} 在第 {i} 行")
        
        # 在同一行中查找评级链接
        rating_links = row.find_all('a', attrs={'data-test-id': 'conditional-link'})
        print(f"  在该行中找到 {len(rating_links)} 个可能的评级链接")
        
        for link in rating_links:
            href = link.get('href', '')
            if '/ratings/' in href:
                ratings_found += 1
                
                # 确定评级类型
                rating_type = "未知"
                if '/ratings/quant-ratings' in href:
                    rating_type = "Quant Rating"
                elif '/ratings/author-ratings' in href:
                    rating_type = "Author Rating"
                elif '/ratings/sell-side-ratings' in href:
                    rating_type = "Sell-Side Rating"
                
                print(f"  评级链接 {ratings_found}: {rating_type}, href={href}")
                
                # 查找评级标签
                badge = link.find('span', attrs={'data-test-id': 'quant-badge'})
                if badge:
                    sr_only = badge.find('span', class_='sr-only')
                    if sr_only:
                        rating_text = sr_only.text.strip()
                        full_text = badge.text.strip()
                        score_text = full_text.replace(rating_text, '').strip()
                        
                        print(f"    评级文本: {rating_text}")
                        print(f"    评级分数: {score_text}")
                        print(f"    完整文本: {full_text}")
                    else:
                        print(f"    未找到sr-only span，完整文本: {badge.text.strip()}")
                else:
                    print("    未找到评级标签")
        
        # 只显示前5个ticker的信息
        if ratings_found >= 15:  # 5个股票，每个股票3个评级
            print("\n已显示5个股票的评级信息，终止分析...")
            break

if not ticker_found:
    print("未找到任何股票代码")
    
print(f"\n总计找到 {ratings_found} 个评级信息") 