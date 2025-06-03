#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接从HTML文件提取评级信息的脚本
"""

from bs4 import BeautifulSoup
import pandas as pd
import re

# 打开HTML文件
html_file = 'portfolio_holdings.html'
print(f"正在分析文件: {html_file}")

with open(html_file, 'r', encoding='utf-8') as file:
    html_content = file.read()

# 解析HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 直接查找所有ticker名称
ticker_spans = soup.find_all('span', attrs={'data-test-id': 'portfolio-ticker-name'})
print(f"找到 {len(ticker_spans)} 个ticker名称")

# 直接查找所有评级标签
quant_badges = soup.find_all('span', attrs={'data-test-id': 'quant-badge'})
print(f"找到 {len(quant_badges)} 个评级标签")

# 直接查找所有sr-only评级文本
sr_only_spans = soup.find_all('span', class_='sr-only')
print(f"找到 {len(sr_only_spans)} 个sr-only评级文本")

# 直接查找所有评级链接
rating_links = soup.find_all('a', attrs={'data-test-id': 'conditional-link'})
print(f"找到 {len(rating_links)} 个评级链接")

# 检查评级链接的href属性
rating_types = {
    'quant': 0,
    'author': 0,
    'sell_side': 0,
    'other': 0
}

for link in rating_links:
    href = link.get('href', '')
    if '/ratings/quant-ratings' in href:
        rating_types['quant'] += 1
    elif '/ratings/author-ratings' in href:
        rating_types['author'] += 1
    elif '/ratings/sell-side-ratings' in href:
        rating_types['sell_side'] += 1
    else:
        rating_types['other'] += 1

print("\n评级链接类型统计:")
for rating_type, count in rating_types.items():
    print(f"  {rating_type}: {count}")

# 检查前5个评级标签的内容
print("\n前5个评级标签的内容:")
for i, badge in enumerate(quant_badges[:5]):
    print(f"\n评级标签 {i+1}:")
    print(f"  完整HTML: {badge}")
    print(f"  文本内容: {badge.text.strip()}")
    
    sr_only = badge.find('span', class_='sr-only')
    if sr_only:
        print(f"  sr-only文本: {sr_only.text.strip()}")
        print(f"  可能的分数: {badge.text.replace(sr_only.text, '').strip()}")
    else:
        print("  未找到sr-only元素")

# 尝试查找表格行并分析结构
rows = soup.find_all('tr')
print(f"\n找到 {len(rows)} 个表格行")

# 检查前5个包含ticker的行
ticker_rows = []
for row in rows:
    if row.find('span', attrs={'data-test-id': 'portfolio-ticker-name'}):
        ticker_rows.append(row)

print(f"找到 {len(ticker_rows)} 个包含ticker的行")

for i, row in enumerate(ticker_rows[:5]):
    ticker_span = row.find('span', attrs={'data-test-id': 'portfolio-ticker-name'})
    ticker = ticker_span.text.strip() if ticker_span else "未知"
    
    print(f"\n行 {i+1}, Ticker: {ticker}")
    print(f"  行的子元素数量: {len(list(row.children))}")
    
    # 查找该行中的所有td元素
    tds = row.find_all('td')
    print(f"  td元素数量: {len(tds)}")
    
    # 查找该行中的所有评级链接
    links = row.find_all('a', attrs={'data-test-id': 'conditional-link'})
    print(f"  评级链接数量: {len(links)}")
    
    for j, link in enumerate(links):
        href = link.get('href', '')
        if '/ratings/' in href:
            rating_type = "未知"
            if '/ratings/quant-ratings' in href:
                rating_type = "Quant"
            elif '/ratings/author-ratings' in href:
                rating_type = "Author"
            elif '/ratings/sell-side-ratings' in href:
                rating_type = "Sell-Side"
                
            print(f"    链接 {j+1}: {rating_type}, href={href}")
            
            badge = link.find('span', attrs={'data-test-id': 'quant-badge'})
            if badge:
                sr_only = badge.find('span', class_='sr-only')
                if sr_only:
                    print(f"      评级文本: {sr_only.text.strip()}")
                    print(f"      完整文本: {badge.text.strip()}")
                else:
                    print(f"      完整文本: {badge.text.strip()}")
            else:
                print("      未找到评级标签") 