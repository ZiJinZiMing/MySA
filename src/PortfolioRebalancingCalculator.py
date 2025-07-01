#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的SeekingAlpha投资组合爬虫
解决股票代码解析错误和数据提取问题
"""

import pandas as pd
import numpy as np
import re
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging

logger = logging.getLogger(__name__)


class FixedSeekingAlphaScraper:
    """修复后的SeekingAlpha投资组合爬虫"""

    def __init__(self, use_existing_browser=True, debug_mode=True):
        self.use_existing_browser = use_existing_browser
        self.debug_mode = debug_mode
        self.driver = None

    def setup_driver(self):
        """设置浏览器驱动"""
        chrome_options = Options()

        if self.use_existing_browser:
            # 连接到现有浏览器实例
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        else:
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✓ 浏览器驱动设置成功")
            return True
        except Exception as e:
            logger.error(f"浏览器驱动设置失败: {e}")
            return False

    def clean_symbol_from_element(self, element) -> str:
        """
        从HTML元素中提取并清理股票代码

        Args:
            element: BeautifulSoup元素

        Returns:
            清理后的股票代码
        """
        # 尝试多种方式提取股票代码
        symbol = None

        # 方法1: 从文本内容提取
        text = element.get_text(strip=True)
        if text:
            # 移除SOURCE部分
            if '#SOURCE=' in text:
                symbol = text.split('#SOURCE=')[0]
            else:
                symbol = text

        # 方法2: 从href属性提取
        if not symbol:
            links = element.find_all('a')
            for link in links:
                href = link.get('href', '')
                if '/symbol/' in href:
                    # 从URL中提取股票代码
                    match = re.search(r'/symbol/([A-Z]+)', href)
                    if match:
                        symbol = match.group(1)
                        break

        # 方法3: 从data属性提取
        if not symbol:
            for attr in ['data-symbol', 'data-ticker', 'symbol']:
                attr_value = element.get(attr)
                if attr_value:
                    symbol = attr_value
                    break

        # 清理股票代码
        if symbol:
            # 移除特殊字符和URL编码
            symbol = re.sub(r'[^A-Za-z0-9.-]', '', symbol.strip().upper())
            # 移除数字后缀（如果存在）
            symbol = re.sub(r'\d+$', '', symbol)

            # 验证股票代码格式
            if len(symbol) >= 1 and len(symbol) <= 5 and symbol.isalpha():
                return symbol

        return None

    def extract_numeric_value(self, element, field_type="price") -> float:
        """
        从HTML元素中提取数值

        Args:
            element: BeautifulSoup元素
            field_type: 字段类型 (price, shares, weight, value)

        Returns:
            提取的数值或None
        """
        if not element:
            return None

        text = element.get_text(strip=True)

        if not text or text in ['-', '--', 'N/A', '']:
            return None

        try:
            # 移除货币符号、逗号、百分号等
            clean_text = re.sub(r'[$,%\s]', '', text)

            # 处理百分比
            if field_type == "weight" and '%' in text:
                clean_text = re.sub(r'%', '', clean_text)
                value = float(clean_text) / 100  # 转换为小数
            else:
                # 处理负号
                if text.startswith('-') or text.startswith('('):
                    clean_text = '-' + re.sub(r'[^\d.]', '', clean_text)

                value = float(clean_text)

            # 合理性检查
            if field_type == "price" and (value < 0 or value > 10000):
                return None
            elif field_type == "shares" and (value < 0 or value > 1000000):
                return None
            elif field_type == "weight" and (value < 0 or value > 1):
                return None
            elif field_type == "value" and value < 0:
                return None

            return value

        except (ValueError, AttributeError):
            if self.debug_mode:
                logger.debug(f"无法解析 {field_type} 值: '{text}'")
            return None

    def analyze_table_structure(self, table) -> Dict:
        """
        分析表格结构，自动识别列位置

        Args:
            table: BeautifulSoup表格元素

        Returns:
            列位置映射字典
        """
        logger.info("正在分析表格结构...")

        # 查找表头
        headers = []
        header_row = table.find('tr')
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
            headers = [cell.get_text(strip=True).lower() for cell in header_cells]

        logger.info(f"表头: {headers}")

        # 定义列匹配模式
        column_patterns = {
            'symbol': ['symbol', 'ticker', 'stock', 'name', 'company'],
            'price': ['price', 'last', 'current', '$'],
            'shares': ['shares', 'quantity', 'qty', 'position', 'amount'],
            'weight': ['weight', '%', 'allocation', 'percent'],
            'value': ['value', 'market value', 'position value', 'total']
        }

        column_map = {}

        # 自动匹配列位置
        for col_type, patterns in column_patterns.items():
            for i, header in enumerate(headers):
                if any(pattern in header for pattern in patterns):
                    column_map[col_type] = i
                    break

        logger.info(f"列映射: {column_map}")

        # 如果无法识别所有列，尝试基于位置的默认映射
        if len(column_map) < 4:
            logger.warning("无法识别所有列，使用默认位置映射")
            column_map = {
                'symbol': 0,
                'price': 1,
                'shares': 2,
                'weight': 3,
                'value': 4
            }

        return column_map

    def scrape_portfolio_data_improved(self) -> pd.DataFrame:
        """
        改进的投资组合数据爬取方法

        Returns:
            投资组合数据框
        """
        try:
            logger.info("开始爬取投资组合数据...")

            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # 查找所有表格
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")

            portfolio_data = []

            for table_idx, table in enumerate(tables):
                logger.info(f"处理表格 {table_idx + 1}")

                # 分析表格结构
                column_map = self.analyze_table_structure(table)

                # 获取数据行
                rows = table.find_all('tr')[1:]  # 跳过表头

                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])

                    if len(cells) < 3:  # 至少需要3列数据
                        continue

                    try:
                        # 提取股票代码
                        symbol_cell = cells[column_map.get('symbol', 0)]
                        symbol = self.clean_symbol_from_element(symbol_cell)

                        if not symbol or symbol.upper() in ['TOTAL', 'CASH']:
                            continue

                        # 提取价格
                        price_idx = column_map.get('price', 1)
                        price = None
                        if price_idx < len(cells):
                            price = self.extract_numeric_value(cells[price_idx], "price")

                        # 提取股数
                        shares_idx = column_map.get('shares', 2)
                        shares = None
                        if shares_idx < len(cells):
                            shares = self.extract_numeric_value(cells[shares_idx], "shares")

                        # 提取权重
                        weight_idx = column_map.get('weight', 3)
                        weight = None
                        if weight_idx < len(cells):
                            weight = self.extract_numeric_value(cells[weight_idx], "weight")

                        # 提取或计算市值
                        value_idx = column_map.get('value', 4)
                        value = None
                        if value_idx < len(cells):
                            value = self.extract_numeric_value(cells[value_idx], "value")

                        # 如果没有市值，尝试计算
                        if not value and price and shares:
                            value = price * shares

                        # 验证数据完整性
                        if symbol and price and shares and value:
                            portfolio_data.append({
                                'symbol': symbol,
                                'price': price,
                                'shares': shares,
                                'weight': weight,
                                'value': value,
                                'table_source': table_idx + 1,
                                'row_source': row_idx + 1
                            })

                            if self.debug_mode:
                                logger.debug(f"✓ 提取成功: {symbol} - ${price} × {shares} = ${value:.2f}")
                        else:
                            if self.debug_mode:
                                logger.debug(f"✗ 数据不完整: symbol={symbol}, price={price}, shares={shares}, value={value}")

                    except Exception as e:
                        if self.debug_mode:
                            logger.debug(f"处理行 {row_idx + 1} 时出错: {e}")
                        continue

            if not portfolio_data:
                logger.warning("未能提取到有效的投资组合数据")
                return None

            df = pd.DataFrame(portfolio_data)

            # 数据验证和清理
            logger.info(f"成功提取 {len(df)} 条投资组合记录")

            # 移除重复项
            before_dedup = len(df)
            df = df.drop_duplicates(subset=['symbol']).reset_index(drop=True)
            after_dedup = len(df)

            if before_dedup != after_dedup:
                logger.info(f"移除 {before_dedup - after_dedup} 条重复记录")

            # 计算总市值
            total_value = df['value'].sum()
            logger.info(f"投资组合总价值: ${total_value:,.2f}")

            # 重新计算权重（如果权重数据不完整）
            missing_weights = df['weight'].isna().sum()
            if missing_weights > 0:
                logger.info(f"有 {missing_weights} 个股票权重缺失，重新计算权重")
                df['weight'] = df['value'] / total_value

            return df

        except Exception as e:
            logger.error(f"数据爬取失败: {e}")
            return None

    def save_debug_info(self, filename="debug_portfolio_page.html"):
        """保存调试信息"""
        if not self.driver:
            return

        try:
            # 保存页面源码
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)

            # 保存页面截图
            screenshot_file = filename.replace('.html', '_screenshot.png')
            self.driver.save_screenshot(screenshot_file)

            logger.info(f"调试信息已保存: {filename}, {screenshot_file}")

        except Exception as e:
            logger.error(f"保存调试信息失败: {e}")

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


def main():
    """主函数示例"""
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=True)

    try:
        # 设置浏览器
        if not scraper.setup_driver():
            return

        # 导航到投资组合页面 (需要手动先登录)
        portfolio_url = "https://seekingalpha.com/account/portfolio"

        print("请在浏览器中手动导航到您的投资组合页面，然后按Enter继续...")
        input("按Enter继续爬取数据...")

        # 爬取数据
        df = scraper.scrape_portfolio_data_improved()

        if df is not None:
            print("\n=== 爬取结果 ===")
            print(f"成功提取 {len(df)} 条记录")
            print("\n前10条数据:")
            print(df.head(10).to_string())

            # 保存到CSV
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            csv_file = f"portfolio_data_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n数据已保存到: {csv_file}")

            # 保存调试信息
            debug_file = f"debug_portfolio_{timestamp}.html"
            scraper.save_debug_info(debug_file)

        else:
            print("数据爬取失败，正在保存调试信息...")
            scraper.save_debug_info("debug_failed_scrape.html")

    except Exception as e:
        print(f"程序执行出错: {e}")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()