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