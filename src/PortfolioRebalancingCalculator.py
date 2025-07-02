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
import os
from typing import Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import logging
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib.font_manager import FontProperties

logger = logging.getLogger(__name__)


class FixedSeekingAlphaScraper:
    """修复后的SeekingAlpha投资组合爬虫"""

    def __init__(self, use_existing_browser=True, debug_mode=True):
        self.use_existing_browser = use_existing_browser
        self.debug_mode = debug_mode
        self.driver = None
        
        # 配置matplotlib中文支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 设置seaborn样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")

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

    def parse_local_html_file(self, html_file_path):
        """
        解析本地HTML文件获取投资组合数据
        
        Args:
            html_file_path: 本地HTML文件路径
            
        Returns:
            投资组合数据DataFrame
        """
        try:
            logger.info(f"开始解析本地HTML文件: {html_file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(html_file_path):
                logger.error(f"文件不存在: {html_file_path}")
                return None
                
            # 读取HTML文件
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找投资组合表格
            table_body = soup.find('tbody', {'data-test-id': 'table-body'})
            if not table_body:
                logger.error("未找到投资组合表格")
                return None
                
            portfolio_data = []
            
            # 查找所有股票行
            stock_rows = table_body.find_all('tr', class_='wyOal')
            logger.info(f"找到 {len(stock_rows)} 只股票")
            
            for row_idx, row in enumerate(stock_rows):
                try:
                    stock_data = self._extract_stock_data_from_row(row)
                    if stock_data:
                        portfolio_data.append(stock_data)
                        if self.debug_mode:
                            logger.debug(f"✓ 提取成功: {stock_data['symbol']} - ${stock_data['price']} × {stock_data['shares']} = ${stock_data['value']:.2f}")
                except Exception as e:
                    if self.debug_mode:
                        logger.debug(f"处理第 {row_idx + 1} 行时出错: {e}")
                    continue
                    
            if not portfolio_data:
                logger.warning("未能提取到有效的投资组合数据")
                return None
                
            df = pd.DataFrame(portfolio_data)
            
            # 数据验证和统计
            logger.info(f"成功提取 {len(df)} 条投资组合记录")
            total_value = df['value'].sum()
            logger.info(f"投资组合总价值: ${total_value:,.2f}")
            
            # 重新计算权重（确保一致性）
            df['calculated_weight'] = df['value'] / total_value
            
            return df
            
        except Exception as e:
            logger.error(f"解析本地HTML文件失败: {e}")
            return None
    
    def _extract_stock_data_from_row(self, row):
        """
        从HTML行中提取股票数据
        
        Args:
            row: BeautifulSoup行元素
            
        Returns:
            股票数据字典或None
        """
        try:
            # 提取股票代码
            symbol_element = row.find('span', {'data-test-id': 'portfolio-ticker-name'})
            if not symbol_element:
                return None
            symbol = symbol_element.get_text(strip=True)
            
            # 检查是否是现金项目
            if symbol.upper() in ['CASH', 'CURRENCY']:
                # 对于现金项目，处理方式不同
                weight_element = row.find('div', {'data-test-id': 'portfolio-ticker-price-weight'})
                weight = None
                if weight_element:
                    weight_text = weight_element.find('span').get_text(strip=True)
                    if weight_text.endswith('%'):
                        weight = float(weight_text.replace('%', '')) / 100
                
                # 提取现金价值
                value_element = row.find('div', {'data-test-id': 'portfolio-ticker-price-value'})
                if not value_element:
                    return None
                value_text = value_element.find('span').get_text(strip=True)
                value = float(value_text.replace(',', ''))
                
                return {
                    'symbol': 'CASH',
                    'price': 1.0,  # 现金价格固定为1
                    'shares': value,  # 现金数量等于价值
                    'weight': weight,
                    'value': value,
                    'calculated_value': value
                }
            
            # 提取价格
            price_element = row.find('div', {'data-test-id': 'portfolio-ticker-price-price'})
            if not price_element:
                return None
            price_text = price_element.find('span').get_text(strip=True)
            price = float(price_text.replace(',', ''))
            
            # 提取股数
            shares_element = row.find('span', {'data-test-id': 'share-value'})
            if not shares_element:
                return None
            shares_text = shares_element.get_text(strip=True)
            shares = float(shares_text.replace(',', ''))
            
            # 提取权重
            weight_element = row.find('div', {'data-test-id': 'portfolio-ticker-price-weight'})
            weight = None
            if weight_element:
                weight_text = weight_element.find('span').get_text(strip=True)
                if weight_text.endswith('%'):
                    weight = float(weight_text.replace('%', '')) / 100
            
            # 提取价值
            value_element = row.find('div', {'data-test-id': 'portfolio-ticker-price-value'})
            if not value_element:
                return None
            value_text = value_element.find('span').get_text(strip=True)
            value = float(value_text.replace(',', ''))
            
            # 验证数据一致性
            calculated_value = price * shares
            if abs(calculated_value - value) > 0.1:  # 允许小幅误差
                logger.warning(f"{symbol}: 计算价值 {calculated_value:.2f} 与显示价值 {value:.2f} 不一致")
            
            return {
                'symbol': symbol,
                'price': price,
                'shares': shares,
                'weight': weight,
                'value': value,
                'calculated_value': calculated_value
            }
            
        except Exception as e:
            if self.debug_mode:
                logger.debug(f"提取股票数据失败: {e}")
            return None
    
    def calculate_equal_weight_rebalance(self, portfolio_df, target_cash_percentage=0.0, exclude_symbols=None):
        """
        计算等权重再平衡策略
        
        Args:
            portfolio_df: 投资组合DataFrame
            target_cash_percentage: 目标现金比例 (0.0-1.0)
            exclude_symbols: 排除的股票代码列表
            
        Returns:
            再平衡指令DataFrame
        """
        try:
            logger.info("开始计算等权重再平衡策略")
            
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return None
            
            # 分离现金和股票
            cash_rows = portfolio_df[portfolio_df['symbol'] == 'CASH']
            stock_rows = portfolio_df[portfolio_df['symbol'] != 'CASH']
            
            # 过滤排除的股票
            if exclude_symbols:
                stock_rows = stock_rows[~stock_rows['symbol'].isin(exclude_symbols)]
                logger.info(f"排除股票: {exclude_symbols}")
            
            # 计算总资产价值（包括现金）
            total_portfolio_value = portfolio_df['value'].sum()
            available_cash = cash_rows['value'].sum() if not cash_rows.empty else 0
            stock_value = stock_rows['value'].sum()
            
            logger.info(f"投资组合总价值: ${total_portfolio_value:,.2f}")
            logger.info(f"可用现金: ${available_cash:,.2f}")
            logger.info(f"股票总价值: ${stock_value:,.2f}")
            
            # 计算可投资总金额（总资产减去目标现金保留）
            target_cash_reserve = total_portfolio_value * target_cash_percentage
            investable_total = total_portfolio_value - target_cash_reserve
            
            logger.info(f"目标现金保留: ${target_cash_reserve:,.2f} ({target_cash_percentage:.1%})")
            logger.info(f"可投资总金额: ${investable_total:,.2f}")
            
            # 计算等权重目标分配
            num_stocks = len(stock_rows)
            if num_stocks == 0:
                logger.warning("没有股票可以投资")
                return None
                
            target_value_per_stock = investable_total / num_stocks
            
            logger.info(f"股票数量: {num_stocks}")
            logger.info(f"每只股票目标价值: ${target_value_per_stock:,.2f}")
            logger.info(f"等权重比例: {1/num_stocks:.2%}")
            
            # 计算再平衡指令
            rebalance_actions = []
            total_buy_needed = 0
            total_sell_available = 0
            
            for _, stock in stock_rows.iterrows():
                current_value = stock['value']
                target_value = target_value_per_stock
                difference = target_value - current_value
                
                # 计算需要买卖的股数
                if abs(difference) > 1.0:  # 只处理差异大于$1的情况
                    if difference > 0:
                        # 需要买入
                        shares_to_buy = difference / stock['price']
                        action = 'BUY'
                        shares = int(shares_to_buy)  # 向下取整
                        actual_amount = shares * stock['price']
                        total_buy_needed += actual_amount
                    else:
                        # 需要卖出
                        shares_to_sell = abs(difference) / stock['price']
                        action = 'SELL'
                        shares = int(shares_to_sell)  # 向下取整
                        actual_amount = shares * stock['price']
                        total_sell_available += actual_amount
                    
                    if shares > 0:  # 只记录有效交易
                        rebalance_actions.append({
                            'symbol': stock['symbol'],
                            'action': action,
                            'shares': shares,
                            'price': stock['price'],
                            'amount': actual_amount,
                            'current_value': current_value,
                            'target_value': target_value,
                            'difference': difference,
                            'current_weight': current_value / total_portfolio_value,
                            'target_weight': target_value / total_portfolio_value
                        })
            
            if not rebalance_actions:
                logger.info("投资组合已接近等权重，无需再平衡")
                return None
                
            rebalance_df = pd.DataFrame(rebalance_actions)
            
            # 计算现金使用情况
            net_cash_needed = total_buy_needed - total_sell_available
            cash_after_rebalance = available_cash - net_cash_needed
            
            logger.info(f"\n=== 再平衡统计 ===")
            logger.info(f"需要买入总额: ${total_buy_needed:,.2f}")
            logger.info(f"可卖出总额: ${total_sell_available:,.2f}")
            logger.info(f"净现金需求: ${net_cash_needed:,.2f}")
            logger.info(f"剩余现金: ${cash_after_rebalance:,.2f}")
            
            # 检查现金是否充足
            if net_cash_needed > available_cash:
                logger.warning(f"现金不足！需要 ${net_cash_needed:,.2f}，但只有 ${available_cash:,.2f}")
                logger.info("建议减少买入金额或增加卖出金额")
            
            return rebalance_df
            
        except Exception as e:
            logger.error(f"计算等权重再平衡失败: {e}")
            return None
    
    def generate_rebalance_report(self, portfolio_df, rebalance_df, save_to_file=True):
        """
        生成再平衡报告
        
        Args:
            portfolio_df: 投资组合DataFrame
            rebalance_df: 再平衡指令DataFrame
            save_to_file: 是否保存到文件
            
        Returns:
            报告字符串
        """
        try:
            if portfolio_df is None or portfolio_df.empty:
                return "无投资组合数据"
                
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("投资组合等权重再平衡报告")
            report_lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("=" * 80)
            
            # 当前投资组合概览
            total_value = portfolio_df['value'].sum()
            report_lines.append(f"\n📊 当前投资组合概览:")
            report_lines.append(f"总价值: ${total_value:,.2f}")
            report_lines.append(f"股票数量: {len(portfolio_df)}")
            report_lines.append(f"平均每股价值: ${total_value/len(portfolio_df):,.2f}")
            
            # 当前持仓详情
            report_lines.append(f"\n📋 当前持仓详情:")
            report_lines.append(f"{'股票代码':<8} {'价格':<8} {'股数':<8} {'价值':<12} {'权重':<8}")
            report_lines.append("-" * 50)
            
            for _, stock in portfolio_df.iterrows():
                weight = stock['value'] / total_value
                report_lines.append(
                    f"{stock['symbol']:<8} "
                    f"${stock['price']:<7.2f} "
                    f"{stock['shares']:<8.0f} "
                    f"${stock['value']:<11.2f} "
                    f"{weight:<7.1%}"
                )
            
            # 再平衡指令
            if rebalance_df is not None and not rebalance_df.empty:
                report_lines.append(f"\n🔄 再平衡交易指令:")
                report_lines.append(f"{'股票代码':<8} {'操作':<6} {'股数':<8} {'金额':<12} {'当前权重':<8} {'目标权重':<8}")
                report_lines.append("-" * 60)
                
                for _, action in rebalance_df.iterrows():
                    report_lines.append(
                        f"{action['symbol']:<8} "
                        f"{action['action']:<6} "
                        f"{action['shares']:<8.0f} "
                        f"${action['amount']:<11.2f} "
                        f"{action['current_weight']:<7.1%} "
                        f"{action['target_weight']:<7.1%}"
                    )
                
                # 交易统计
                buy_amount = rebalance_df[rebalance_df['action'] == 'BUY']['amount'].sum()
                sell_amount = rebalance_df[rebalance_df['action'] == 'SELL']['amount'].sum()
                
                report_lines.append(f"\n💰 交易统计:")
                report_lines.append(f"买入总额: ${buy_amount:,.2f}")
                report_lines.append(f"卖出总额: ${sell_amount:,.2f}")
                report_lines.append(f"净现金需求: ${buy_amount - sell_amount:,.2f}")
            else:
                report_lines.append(f"\n✅ 投资组合已接近等权重，无需再平衡")
            
            report_lines.append("\n" + "=" * 80)
            
            report = "\n".join(report_lines)
            
            if save_to_file:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_rebalance_report_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                logger.info(f"报告已保存到: {filename}")
            
            return report
            
        except Exception as e:
            logger.error(f"生成再平衡报告失败: {e}")
            return f"生成报告失败: {e}"
    
    def visualize_portfolio_weights(self, portfolio_df, save_charts=True, show_charts=False):
        """
        创建投资组合权重分布饼图
        
        Args:
            portfolio_df: 投资组合DataFrame
            save_charts: 是否保存图表
            show_charts: 是否显示图表
            
        Returns:
            图表文件路径列表
        """
        try:
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return []
                
            saved_files = []
            
            # 计算权重
            total_value = portfolio_df['value'].sum()
            portfolio_df = portfolio_df.copy()
            portfolio_df['weight'] = portfolio_df['value'] / total_value
            
            # 创建饼图
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 左侧：详细饼图（所有股票）
            colors = plt.cm.Set3(np.linspace(0, 1, len(portfolio_df)))
            wedges, texts, autotexts = ax1.pie(
                portfolio_df['weight'], 
                labels=portfolio_df['symbol'],
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 8}
            )
            ax1.set_title('投资组合权重分布 (详细)', fontsize=14, fontweight='bold')
            
            # 右侧：简化饼图（合并小权重）
            threshold = 0.02  # 2%以下合并
            large_positions = portfolio_df[portfolio_df['weight'] >= threshold].copy()
            small_positions = portfolio_df[portfolio_df['weight'] < threshold]
            
            if not small_positions.empty:
                small_total = small_positions['weight'].sum()
                other_row = pd.DataFrame({
                    'symbol': ['其他'],
                    'weight': [small_total],
                    'value': [small_positions['value'].sum()]
                })
                simplified_df = pd.concat([large_positions, other_row], ignore_index=True)
            else:
                simplified_df = large_positions.copy()
            
            colors2 = plt.cm.Set2(np.linspace(0, 1, len(simplified_df)))
            wedges2, texts2, autotexts2 = ax2.pie(
                simplified_df['weight'], 
                labels=simplified_df['symbol'],
                autopct='%1.1f%%',
                startangle=90,
                colors=colors2,
                textprops={'fontsize': 10}
            )
            ax2.set_title('投资组合权重分布 (简化)', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
            if save_charts:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_weights_pie_{timestamp}.png"
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                saved_files.append(filename)
                logger.info(f"权重分布饼图已保存: {filename}")
                
            if show_charts:
                plt.show()
            else:
                plt.close()
                
            return saved_files
            
        except Exception as e:
            logger.error(f"创建权重分布图失败: {e}")
            return []
    
    def visualize_rebalance_comparison(self, portfolio_df, rebalance_df, save_charts=True, show_charts=False):
        """
        创建再平衡前后对比柱状图
        
        Args:
            portfolio_df: 投资组合DataFrame
            rebalance_df: 再平衡指令DataFrame
            save_charts: 是否保存图表
            show_charts: 是否显示图表
            
        Returns:
            图表文件路径列表
        """
        try:
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return []
                
            saved_files = []
            
            # 计算当前权重
            total_value = portfolio_df['value'].sum()
            current_weights = {}
            for _, stock in portfolio_df.iterrows():
                if stock['symbol'] != 'CASH':
                    current_weights[stock['symbol']] = stock['value'] / total_value
            
            # 创建目标权重（等权重）
            num_stocks = len([s for s in portfolio_df['symbol'] if s != 'CASH'])
            target_weight = 1.0 / num_stocks if num_stocks > 0 else 0
            
            # 准备数据
            symbols = list(current_weights.keys())
            current_weights_list = [current_weights[s] for s in symbols]
            target_weights_list = [target_weight] * len(symbols)
            
            # 创建对比图
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 子图1：权重对比柱状图
            x_pos = np.arange(len(symbols))
            width = 0.35
            
            bars1 = ax1.bar(x_pos - width/2, current_weights_list, width, 
                           label='当前权重', color='skyblue', alpha=0.8)
            bars2 = ax1.bar(x_pos + width/2, target_weights_list, width,
                           label='目标权重', color='lightcoral', alpha=0.8)
            
            ax1.set_xlabel('股票代码')
            ax1.set_ylabel('权重')
            ax1.set_title('再平衡前后权重对比', fontweight='bold')
            ax1.set_xticks(x_pos)
            ax1.set_xticklabels(symbols, rotation=45)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar in bars1:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1%}', ha='center', va='bottom', fontsize=8)
            for bar in bars2:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1%}', ha='center', va='bottom', fontsize=8)
            
            # 子图2：权重偏差图
            deviations = [current_weights_list[i] - target_weights_list[i] for i in range(len(symbols))]
            colors = ['red' if d < 0 else 'green' for d in deviations]
            
            bars3 = ax2.bar(symbols, deviations, color=colors, alpha=0.7)
            ax2.set_xlabel('股票代码')
            ax2.set_ylabel('权重偏差')
            ax2.set_title('当前权重偏差 (正值=超配，负值=低配)', fontweight='bold')
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar in bars3:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1%}', ha='center', va='bottom' if height >= 0 else 'top', 
                        fontsize=8)
            
            # 子图3：交易金额分布（如果有再平衡数据）
            if rebalance_df is not None and not rebalance_df.empty:
                buy_data = rebalance_df[rebalance_df['action'] == 'BUY']
                sell_data = rebalance_df[rebalance_df['action'] == 'SELL']
                
                # 合并买卖数据用于显示
                all_symbols = set(buy_data['symbol'].tolist() + sell_data['symbol'].tolist())
                trade_amounts = {}
                
                for symbol in all_symbols:
                    buy_amount = buy_data[buy_data['symbol'] == symbol]['amount'].sum()
                    sell_amount = sell_data[sell_data['symbol'] == symbol]['amount'].sum()
                    net_amount = buy_amount - sell_amount  # 正值=净买入，负值=净卖出
                    trade_amounts[symbol] = net_amount
                
                trade_symbols = list(trade_amounts.keys())
                trade_values = list(trade_amounts.values())
                trade_colors = ['green' if v > 0 else 'red' for v in trade_values]
                
                bars4 = ax3.bar(trade_symbols, trade_values, color=trade_colors, alpha=0.7)
                ax3.set_xlabel('股票代码')
                ax3.set_ylabel('净交易金额 ($)')
                ax3.set_title('净交易金额分布 (正值=净买入，负值=净卖出)', fontweight='bold')
                ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax3.tick_params(axis='x', rotation=45)
                ax3.grid(True, alpha=0.3)
                
                # 添加数值标签
                for bar in bars4:
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height,
                            f'${height:,.0f}', ha='center', 
                            va='bottom' if height >= 0 else 'top', fontsize=8)
            else:
                ax3.text(0.5, 0.5, '无再平衡交易数据', ha='center', va='center', 
                        transform=ax3.transAxes, fontsize=14)
                ax3.set_title('交易金额分布', fontweight='bold')
            
            # 子图4：投资组合价值分布
            values = [portfolio_df[portfolio_df['symbol'] == s]['value'].iloc[0] for s in symbols]
            
            # 使用颜色映射
            colors4 = plt.cm.viridis(np.linspace(0, 1, len(symbols)))
            bars5 = ax4.bar(symbols, values, color=colors4, alpha=0.8)
            ax4.set_xlabel('股票代码')
            ax4.set_ylabel('投资价值 ($)')
            ax4.set_title('各股票投资价值分布', fontweight='bold')
            ax4.tick_params(axis='x', rotation=45)
            ax4.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar in bars5:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'${height:,.0f}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            
            if save_charts:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"rebalance_comparison_{timestamp}.png"
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                saved_files.append(filename)
                logger.info(f"再平衡对比图已保存: {filename}")
                
            if show_charts:
                plt.show()
            else:
                plt.close()
                
            return saved_files
            
        except Exception as e:
            logger.error(f"创建再平衡对比图失败: {e}")
            return []
    
    def visualize_trade_distribution(self, rebalance_df, save_charts=True, show_charts=False):
        """
        创建交易金额分布可视化
        
        Args:
            rebalance_df: 再平衡指令DataFrame
            save_charts: 是否保存图表
            show_charts: 是否显示图表
            
        Returns:
            图表文件路径列表
        """
        try:
            if rebalance_df is None or rebalance_df.empty:
                logger.warning("无再平衡交易数据")
                return []
                
            saved_files = []
            
            # 创建图表
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 子图1：买入vs卖出总额对比
            buy_total = rebalance_df[rebalance_df['action'] == 'BUY']['amount'].sum()
            sell_total = rebalance_df[rebalance_df['action'] == 'SELL']['amount'].sum()
            
            categories = ['买入总额', '卖出总额']
            amounts = [buy_total, sell_total]
            colors1 = ['green', 'red']
            
            bars1 = ax1.bar(categories, amounts, color=colors1, alpha=0.7)
            ax1.set_ylabel('金额 ($)')
            ax1.set_title('买入vs卖出总额对比', fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar in bars1:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'${height:,.0f}', ha='center', va='bottom', fontsize=10)
            
            # 添加净现金需求
            net_cash = buy_total - sell_total
            ax1.text(0.5, 0.95, f'净现金需求: ${net_cash:,.0f}', 
                    transform=ax1.transAxes, ha='center', va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # 子图2：各股票交易金额分布
            buy_data = rebalance_df[rebalance_df['action'] == 'BUY']
            sell_data = rebalance_df[rebalance_df['action'] == 'SELL']
            
            # 合并数据
            all_symbols = set(rebalance_df['symbol'].unique())
            trade_data = []
            
            for symbol in all_symbols:
                buy_amount = buy_data[buy_data['symbol'] == symbol]['amount'].sum()
                sell_amount = sell_data[sell_data['symbol'] == symbol]['amount'].sum()
                trade_data.append({
                    'symbol': symbol,
                    'buy_amount': buy_amount,
                    'sell_amount': sell_amount
                })
            
            trade_df = pd.DataFrame(trade_data)
            
            # 创建堆叠柱状图
            x_pos = np.arange(len(trade_df))
            
            bars2_buy = ax2.bar(x_pos, trade_df['buy_amount'], label='买入', 
                              color='green', alpha=0.7)
            bars2_sell = ax2.bar(x_pos, -trade_df['sell_amount'], label='卖出', 
                               color='red', alpha=0.7)
            
            ax2.set_xlabel('股票代码')
            ax2.set_ylabel('交易金额 ($)')
            ax2.set_title('各股票买入卖出金额分布', fontweight='bold')
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(trade_df['symbol'], rotation=45)
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 子图3：交易股数分布
            symbols = rebalance_df['symbol'].unique()
            shares_data = []
            
            for symbol in symbols:
                symbol_data = rebalance_df[rebalance_df['symbol'] == symbol]
                buy_shares = symbol_data[symbol_data['action'] == 'BUY']['shares'].sum()
                sell_shares = symbol_data[symbol_data['action'] == 'SELL']['shares'].sum()
                shares_data.append({
                    'symbol': symbol,
                    'buy_shares': buy_shares,
                    'sell_shares': sell_shares
                })
            
            shares_df = pd.DataFrame(shares_data)
            x_pos2 = np.arange(len(shares_df))
            
            bars3_buy = ax3.bar(x_pos2, shares_df['buy_shares'], label='买入股数', 
                              color='lightgreen', alpha=0.7)
            bars3_sell = ax3.bar(x_pos2, -shares_df['sell_shares'], label='卖出股数', 
                               color='lightcoral', alpha=0.7)
            
            ax3.set_xlabel('股票代码')
            ax3.set_ylabel('股数')
            ax3.set_title('各股票买入卖出股数分布', fontweight='bold')
            ax3.set_xticks(x_pos2)
            ax3.set_xticklabels(shares_df['symbol'], rotation=45)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 子图4：交易行为分析饼图
            action_counts = rebalance_df['action'].value_counts()
            action_amounts = rebalance_df.groupby('action')['amount'].sum()
            
            # 创建双饼图
            fig2, (ax4_left, ax4_right) = plt.subplots(1, 2, figsize=(10, 5))
            
            # 交易次数分布
            colors4 = ['green', 'red']
            wedges1, texts1, autotexts1 = ax4_left.pie(
                action_counts.values, 
                labels=action_counts.index,
                autopct='%1.0f次',
                colors=colors4,
                startangle=90
            )
            ax4_left.set_title('交易次数分布', fontweight='bold')
            
            # 交易金额分布
            wedges2, texts2, autotexts2 = ax4_right.pie(
                action_amounts.values, 
                labels=action_amounts.index,
                autopct=lambda pct: f'${action_amounts.sum()*pct/100:,.0f}',
                colors=colors4,
                startangle=90
            )
            ax4_right.set_title('交易金额分布', fontweight='bold')
            
            # 将双饼图放在ax4位置
            ax4.remove()  # 移除原来的ax4
            plt.sca(ax4_left.figure.axes[0])  # 设置当前轴
            
            # 统计信息文本框
            stats_text = f"""
交易统计摘要:
• 总买入金额: ${buy_total:,.0f}
• 总卖出金额: ${sell_total:,.0f}
• 净现金需求: ${net_cash:,.0f}
• 买入交易数: {len(buy_data)}
• 卖出交易数: {len(sell_data)}
• 涉及股票数: {len(all_symbols)}
            """
            
            # 在主图上添加统计信息
            fig.text(0.7, 0.25, stats_text.strip(), fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
                    verticalalignment='top')
            
            plt.tight_layout()
            
            if save_charts:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"trade_distribution_{timestamp}.png"
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                saved_files.append(filename)
                logger.info(f"交易分布图已保存: {filename}")
                
            if show_charts:
                plt.show()
            else:
                plt.close()
                
            return saved_files
            
        except Exception as e:
            logger.error(f"创建交易分布图失败: {e}")
            return []
    
    def create_comprehensive_dashboard(self, portfolio_df, rebalance_df, save_charts=True, show_charts=False):
        """
        创建综合可视化仪表板
        
        Args:
            portfolio_df: 投资组合DataFrame
            rebalance_df: 再平衡指令DataFrame
            save_charts: 是否保存图表
            show_charts: 是否显示图表
            
        Returns:
            图表文件路径列表
        """
        try:
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return []
                
            saved_files = []
            
            # 设置图表布局 - 3x3网格
            fig = plt.figure(figsize=(20, 15))
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
            
            # 计算基础数据
            total_value = portfolio_df['value'].sum()
            portfolio_df_copy = portfolio_df.copy()
            portfolio_df_copy['weight'] = portfolio_df_copy['value'] / total_value
            
            # 过滤掉现金项目用于股票分析
            stocks_df = portfolio_df_copy[portfolio_df_copy['symbol'] != 'CASH']
            cash_df = portfolio_df_copy[portfolio_df_copy['symbol'] == 'CASH']
            
            # 1. 投资组合概览 (左上)
            ax1 = fig.add_subplot(gs[0, 0])
            
            # 创建概览信息
            overview_text = f"""
📊 投资组合概览
━━━━━━━━━━━━━━━━━━━━
💰 总价值: ${total_value:,.0f}
📈 股票数量: {len(stocks_df)}
💵 现金: ${cash_df['value'].sum() if not cash_df.empty else 0:,.0f}
📊 平均持仓: ${total_value/len(portfolio_df):,.0f}
━━━━━━━━━━━━━━━━━━━━
🎯 等权重目标: {1/len(stocks_df):.1%}
📉 最大偏差: {abs(stocks_df['weight'] - 1/len(stocks_df)).max():.1%}
            """
            
            ax1.text(0.05, 0.95, overview_text.strip(), transform=ax1.transAxes,
                    fontsize=11, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
            ax1.set_xlim(0, 1)
            ax1.set_ylim(0, 1)
            ax1.axis('off')
            
            # 2. 权重分布饼图 (中上)
            ax2 = fig.add_subplot(gs[0, 1])
            
            # 简化版饼图（合并小权重）
            threshold = 0.03  # 3%以下合并
            large_positions = stocks_df[stocks_df['weight'] >= threshold].copy()
            small_positions = stocks_df[stocks_df['weight'] < threshold]
            
            if not small_positions.empty:
                small_total = small_positions['weight'].sum()
                other_row = pd.DataFrame({
                    'symbol': ['其他'],
                    'weight': [small_total],
                    'value': [small_positions['value'].sum()]
                })
                pie_df = pd.concat([large_positions[['symbol', 'weight', 'value']], other_row], ignore_index=True)
            else:
                pie_df = large_positions[['symbol', 'weight', 'value']].copy()
            
            wedges, texts, autotexts = ax2.pie(
                pie_df['weight'], 
                labels=pie_df['symbol'],
                autopct='%1.1f%%',
                startangle=90,
                colors=plt.cm.Set3(np.linspace(0, 1, len(pie_df)))
            )
            ax2.set_title('投资组合权重分布', fontweight='bold', fontsize=12)
            
            # 3. 权重偏差分析 (右上)
            ax3 = fig.add_subplot(gs[0, 2])
            
            target_weight = 1.0 / len(stocks_df)
            deviations = stocks_df['weight'] - target_weight
            colors = ['red' if d < 0 else 'green' for d in deviations]
            
            bars = ax3.barh(stocks_df['symbol'], deviations, color=colors, alpha=0.7)
            ax3.set_xlabel('权重偏差')
            ax3.set_title('权重偏差分析', fontweight='bold', fontsize=12)
            ax3.axvline(x=0, color='black', linestyle='-', alpha=0.3)
            ax3.grid(True, alpha=0.3)
            
            # 4. 当前持仓价值 (左中)
            ax4 = fig.add_subplot(gs[1, 0])
            
            # 排序显示前10大持仓
            top_stocks = stocks_df.nlargest(10, 'value')
            colors4 = plt.cm.viridis(np.linspace(0, 1, len(top_stocks)))
            
            bars4 = ax4.barh(top_stocks['symbol'], top_stocks['value'], color=colors4)
            ax4.set_xlabel('持仓价值 ($)')
            ax4.set_title('Top 10 持仓价值', fontweight='bold', fontsize=12)
            ax4.grid(True, alpha=0.3)
            
            # 添加数值标签
            for bar in bars4:
                width = bar.get_width()
                ax4.text(width, bar.get_y() + bar.get_height()/2,
                        f'${width:,.0f}', ha='left', va='center', fontsize=8)
            
            # 5. 再平衡交易概览 (中中)
            ax5 = fig.add_subplot(gs[1, 1])
            
            if rebalance_df is not None and not rebalance_df.empty:
                # 买卖总额对比
                buy_total = rebalance_df[rebalance_df['action'] == 'BUY']['amount'].sum()
                sell_total = rebalance_df[rebalance_df['action'] == 'SELL']['amount'].sum()
                net_cash = buy_total - sell_total
                
                categories = ['买入', '卖出']
                amounts = [buy_total, sell_total]
                colors5 = ['green', 'red']
                
                bars5 = ax5.bar(categories, amounts, color=colors5, alpha=0.7)
                ax5.set_ylabel('金额 ($)')
                ax5.set_title('再平衡交易总额', fontweight='bold', fontsize=12)
                
                # 添加数值标签
                for bar in bars5:
                    height = bar.get_height()
                    ax5.text(bar.get_x() + bar.get_width()/2., height,
                            f'${height:,.0f}', ha='center', va='bottom', fontsize=9)
                
                # 添加净现金需求
                ax5.text(0.5, 0.85, f'净现金需求: ${net_cash:,.0f}', 
                        transform=ax5.transAxes, ha='center',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
            else:
                ax5.text(0.5, 0.5, '无再平衡数据', ha='center', va='center', 
                        transform=ax5.transAxes, fontsize=14)
                ax5.set_title('再平衡交易总额', fontweight='bold', fontsize=12)
            
            # 6. 风险分析 (右中)
            ax6 = fig.add_subplot(gs[1, 2])
            
            # 集中度分析
            weights_sorted = stocks_df['weight'].sort_values(ascending=False)
            top5_concentration = weights_sorted.head(5).sum()
            top10_concentration = weights_sorted.head(min(10, len(weights_sorted))).sum()
            
            # 赫芬达尔指数 (衡量集中度)
            hhi = (stocks_df['weight'] ** 2).sum()
            diversification_score = 1 - hhi
            
            risk_metrics = {
                'Top 5 集中度': f'{top5_concentration:.1%}',
                'Top 10 集中度': f'{top10_concentration:.1%}',
                '多元化分数': f'{diversification_score:.3f}',
                'HHI指数': f'{hhi:.3f}',
                '有效股票数': f'{1/hhi:.1f}'
            }
            
            risk_text = "🎯 风险指标\n" + "━"*20 + "\n"
            for metric, value in risk_metrics.items():
                risk_text += f"{metric}: {value}\n"
            
            ax6.text(0.05, 0.95, risk_text, transform=ax6.transAxes,
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.8))
            ax6.set_xlim(0, 1)
            ax6.set_ylim(0, 1)
            ax6.axis('off')
            
            # 7. 交易明细 (下排左)
            ax7 = fig.add_subplot(gs[2, 0])
            
            if rebalance_df is not None and not rebalance_df.empty:
                # 显示前10个交易
                top_trades = rebalance_df.nlargest(10, 'amount')
                
                trade_colors = ['green' if action == 'BUY' else 'red' 
                               for action in top_trades['action']]
                
                bars7 = ax7.barh(range(len(top_trades)), top_trades['amount'], 
                                color=trade_colors, alpha=0.7)
                ax7.set_yticks(range(len(top_trades)))
                ax7.set_yticklabels([f"{row['symbol']} ({row['action']})" 
                                    for _, row in top_trades.iterrows()])
                ax7.set_xlabel('交易金额 ($)')
                ax7.set_title('Top 10 交易明细', fontweight='bold', fontsize=12)
                ax7.grid(True, alpha=0.3)
            else:
                ax7.text(0.5, 0.5, '无交易数据', ha='center', va='center', 
                        transform=ax7.transAxes, fontsize=14)
                ax7.set_title('交易明细', fontweight='bold', fontsize=12)
            
            # 8. 权重热力图 (下排中)
            ax8 = fig.add_subplot(gs[2, 1])
            
            # 创建权重矩阵用于热力图
            symbols = stocks_df['symbol'].tolist()[:15]  # 最多显示15只股票
            current_weights = stocks_df['weight'].tolist()[:15]
            target_weights = [target_weight] * len(symbols)
            
            # 创建矩阵
            weight_matrix = np.array([current_weights, target_weights])
            
            im = ax8.imshow(weight_matrix, cmap='RdYlGn', aspect='auto')
            ax8.set_xticks(range(len(symbols)))
            ax8.set_xticklabels(symbols, rotation=45, ha='right')
            ax8.set_yticks([0, 1])
            ax8.set_yticklabels(['当前权重', '目标权重'])
            ax8.set_title('权重热力图', fontweight='bold', fontsize=12)
            
            # 添加颜色条
            cbar = plt.colorbar(im, ax=ax8, shrink=0.8)
            cbar.set_label('权重', rotation=270, labelpad=15)
            
            # 9. 统计总结 (下排右)
            ax9 = fig.add_subplot(gs[2, 2])
            
            # 综合统计
            stats_text = f"""
📈 投资组合统计
━━━━━━━━━━━━━━━━━━━━
股票总数: {len(stocks_df)}
总投资: ${total_value:,.0f}
平均权重: {1/len(stocks_df):.2%}
权重标准差: {stocks_df['weight'].std():.2%}
━━━━━━━━━━━━━━━━━━━━
🔄 再平衡统计
"""
            
            if rebalance_df is not None and not rebalance_df.empty:
                num_buy = len(rebalance_df[rebalance_df['action'] == 'BUY'])
                num_sell = len(rebalance_df[rebalance_df['action'] == 'SELL'])
                total_trades = len(rebalance_df)
                
                stats_text += f"""需要调整: {total_trades} 笔
买入交易: {num_buy} 笔
卖出交易: {num_sell} 笔
调整股票: {len(rebalance_df['symbol'].unique())} 只"""
            else:
                stats_text += "无需调整"
            
            ax9.text(0.05, 0.95, stats_text, transform=ax9.transAxes,
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8))
            ax9.set_xlim(0, 1)
            ax9.set_ylim(0, 1)
            ax9.axis('off')
            
            # 添加主标题
            fig.suptitle('投资组合再平衡分析仪表板', fontsize=16, fontweight='bold', y=0.98)
            
            if save_charts:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_dashboard_{timestamp}.png"
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                saved_files.append(filename)
                logger.info(f"综合仪表板已保存: {filename}")
                
            if show_charts:
                plt.show()
            else:
                plt.close()
                
            return saved_files
            
        except Exception as e:
            logger.error(f"创建综合仪表板失败: {e}")
            return []
    
    def generate_all_visualizations(self, portfolio_df, rebalance_df, save_charts=True, show_charts=False):
        """
        生成所有可视化图表的便捷方法
        
        Args:
            portfolio_df: 投资组合DataFrame
            rebalance_df: 再平衡指令DataFrame  
            save_charts: 是否保存图表
            show_charts: 是否显示图表
            
        Returns:
            所有生成的图表文件路径列表
        """
        try:
            logger.info("开始生成所有可视化图表...")
            all_files = []
            
            # 1. 权重分布饼图
            files1 = self.visualize_portfolio_weights(portfolio_df, save_charts, show_charts)
            all_files.extend(files1)
            
            # 2. 再平衡对比图
            files2 = self.visualize_rebalance_comparison(portfolio_df, rebalance_df, save_charts, show_charts)
            all_files.extend(files2)
            
            # 3. 交易分布图
            if rebalance_df is not None and not rebalance_df.empty:
                files3 = self.visualize_trade_distribution(rebalance_df, save_charts, show_charts)
                all_files.extend(files3)
            
            # 4. 综合仪表板
            files4 = self.create_comprehensive_dashboard(portfolio_df, rebalance_df, save_charts, show_charts)
            all_files.extend(files4)
            
            logger.info(f"已生成 {len(all_files)} 个可视化图表: {all_files}")
            return all_files
            
        except Exception as e:
            logger.error(f"生成可视化图表失败: {e}")
            return []
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


def main():
    """主函数示例 - 支持本地HTML文件和在线爬取"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=True)
    
    # 检查是否有本地HTML文件
    html_file_path = "portfolio_data_20250629_225241.html"
    
    try:
        if os.path.exists(html_file_path):
            print(f"\n🔍 发现本地HTML文件: {html_file_path}")
            print("正在解析本地文件...")
            
            # 解析本地HTML文件
            df = scraper.parse_local_html_file(html_file_path)
            
        else:
            print("\n🌐 未找到本地HTML文件，开始在线爬取...")
            
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
            print("\n=== 📊 投资组合数据 ===")
            print(f"成功提取 {len(df)} 条记录")
            print("\n前10条数据:")
            print(df.head(10).to_string())

            # 保存到CSV
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            csv_file = f"portfolio_data_{timestamp}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n数据已保存到: {csv_file}")
            
            # 计算等权重再平衡
            print("\n=== 🎯 开始计算等权重再平衡 ===")
            rebalance_df = scraper.calculate_equal_weight_rebalance(
                df, 
                target_cash_percentage=0.05,  # 保留5%现金
                exclude_symbols=['CASH']  # 排除现金项目
            )
            
            # 生成报告
            print("\n=== 📋 生成再平衡报告 ===")
            report = scraper.generate_rebalance_report(df, rebalance_df)
            print(report)
            
            # 生成可视化图表
            print("\n=== 📊 生成可视化图表 ===")
            chart_files = scraper.generate_all_visualizations(df, rebalance_df, save_charts=True, show_charts=False)
            if chart_files:
                print(f"✅ 已生成 {len(chart_files)} 个可视化图表:")
                for file in chart_files:
                    print(f"   📈 {file}")
            else:
                print("⚠️ 未生成可视化图表")

        else:
            print("❌ 数据获取失败")
            if not os.path.exists(html_file_path):
                print("正在保存调试信息...")
                scraper.save_debug_info("debug_failed_scrape.html")

    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        scraper.close()


def analyze_html_file(html_file_path):
    """独立的HTML文件分析函数"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scraper = FixedSeekingAlphaScraper(debug_mode=True)
    
    try:
        print(f"\n🔍 分析HTML文件: {html_file_path}")
        
        # 解析本地HTML文件
        df = scraper.parse_local_html_file(html_file_path)
        
        if df is not None:
            print("\n=== 📊 投资组合数据 ===")
            print(f"成功提取 {len(df)} 条记录")
            print(df.to_string())
            
            # 计算等权重再平衡
            print("\n=== 🎯 计算等权重再平衡 ===")
            rebalance_df = scraper.calculate_equal_weight_rebalance(
                df, 
                target_cash_percentage=0.0,  # 不保留现金
                exclude_symbols=[]  # 不排除任何股票
            )
            
            # 生成报告
            print("\n=== 📋 再平衡报告 ===")
            report = scraper.generate_rebalance_report(df, rebalance_df)
            print(report)
            
            # 生成可视化图表
            print("\n=== 📊 生成可视化图表 ===")
            chart_files = scraper.generate_all_visualizations(df, rebalance_df, save_charts=True, show_charts=False)
            if chart_files:
                print(f"✅ 已生成 {len(chart_files)} 个可视化图表:")
                for file in chart_files:
                    print(f"   📈 {file}")
            else:
                print("⚠️ 未生成可视化图表")
            
            return df, rebalance_df
        else:
            print("❌ 数据解析失败")
            return None, None
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    # 检查命令行参数
    import sys
    
    if len(sys.argv) > 1:
        html_file_path = sys.argv[1]
        print(f"使用指定的HTML文件: {html_file_path}")
        analyze_html_file(html_file_path)
    else:
        main()