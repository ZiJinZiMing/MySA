#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SeekingAlpha投资组合在线爬虫
仅支持在线获取最新数据，删除本地HTML文件读取功能
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

    def scroll_and_load_all_data(self, max_scrolls=20, scroll_pause_time=1):
        """
        向下滚动页面并等待所有数据加载完成（改进版）
        
        Args:
            max_scrolls: 最大滚动次数
            scroll_pause_time: 每次滚动后的等待时间（秒）
        """
        try:
            logger.info("开始滚动页面加载所有数据...")
            
            # 获取初始表格行数
            initial_rows = self.driver.find_elements(By.XPATH, "//tbody[@data-test-id='table-body']//tr")
            last_row_count = len(initial_rows)
            logger.info(f"初始表格行数: {last_row_count}")
            
            # 获取初始页面高度
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            no_change_count = 0
            
            while scroll_count < max_scrolls:
                # 使用多种滚动方式
                if scroll_count % 3 == 0:
                    # 滚动到页面底部
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                elif scroll_count % 3 == 1:
                    # 向下滚动一个屏幕高度
                    self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                else:
                    # 平滑滚动到底部
                    self.driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
                
                # 等待新内容加载
                time.sleep(scroll_pause_time)
                
                # 检查表格行数变化
                try:
                    current_rows = self.driver.find_elements(By.XPATH, "//tbody[@data-test-id='table-body']//tr")
                    current_row_count = len(current_rows)
                    
                    if current_row_count > last_row_count:
                        logger.info(f"第 {scroll_count + 1} 次滚动：表格行数从 {last_row_count} 增加到 {current_row_count}")
                        last_row_count = current_row_count
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        logger.info(f"第 {scroll_count + 1} 次滚动：表格行数无变化 ({no_change_count}/5) - 当前 {current_row_count} 行")
                        
                        # 如果连续5次滚动都没有新行，则停止
                        if no_change_count >= 5:
                            logger.info("表格内容已完全加载")
                            break
                except Exception as e:
                    logger.warning(f"无法检查表格行数: {e}")
                    # 回退到页面高度检查
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        no_change_count += 1
                        logger.info(f"第 {scroll_count + 1} 次滚动：页面高度无变化 ({no_change_count}/5)")
                        if no_change_count >= 5:
                            logger.info("页面内容已完全加载")
                            break
                    else:
                        logger.info(f"第 {scroll_count + 1} 次滚动：页面高度从 {last_height} 增加到 {new_height}")
                        last_height = new_height
                        no_change_count = 0
                
                scroll_count += 1
            
            # 最后滚动到顶部
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # 最终统计
            try:
                final_rows = self.driver.find_elements(By.XPATH, "//tbody[@data-test-id='table-body']//tr")
                logger.info(f"滚动完成，最终发现 {len(final_rows)} 个表格行")
            except Exception as e:
                logger.warning(f"无法统计最终表格行数: {e}")
            
            logger.info("页面滚动和数据加载完成")
            
        except Exception as e:
            logger.error(f"页面滚动失败: {e}")

    def scrape_portfolio_data_improved(self) -> pd.DataFrame:
        """
        改进的投资组合数据爬取方法（包含页面滚动）- 适配新的HTML结构

        Returns:
            投资组合数据框
        """
        try:
            logger.info("开始爬取投资组合数据...")

            # 等待页面初始加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            
            # 滚动页面加载所有数据
            self.scroll_and_load_all_data()

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

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
                    stock_data = self._extract_stock_data_from_row_new(row)
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

            # 重新计算权重（确保一致性）
            df['calculated_weight'] = df['value'] / total_value

            return df

        except Exception as e:
            logger.error(f"数据爬取失败: {e}")
            return None
    
    def _extract_stock_data_from_row_new(self, row):
        """
        从HTML行中提取股票数据（新版本适配data-test-id结构）
        
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

    
    def calculate_equal_weight_rebalance(self, portfolio_df, min_trade_amount=None, cash_reserve_amount=None):
        """
        简化等权重再平衡算法
        
        Args:
            portfolio_df: 投资组合DataFrame
            min_trade_amount: 最小交易金额
            cash_reserve_amount: 预留现金金额（绝对值）
        
        Returns:
            再平衡指令DataFrame
        """
        try:
            # 获取默认配置
            config = self.get_simple_config()
            if min_trade_amount is None:
                min_trade_amount = config['min_trade_amount']
            if cash_reserve_amount is None:
                cash_reserve_amount = config['cash_reserve_amount']
            
            logger.info("开始计算简化等权重再平衡策略")
            logger.info(f"配置参数: 最小交易金额=${min_trade_amount}, 预留现金=${cash_reserve_amount}")
            
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return None
            
            # 1. 分离现金和股票数据
            cash_rows = portfolio_df[portfolio_df['symbol'] == 'CASH']
            stocks_df = portfolio_df[portfolio_df['symbol'] != 'CASH'].copy()
            
            if stocks_df.empty:
                logger.warning("没有股票数据")
                return None
            
            # 2. 计算总投资金额（包含现金管理）
            total_portfolio_value = portfolio_df['value'].sum()
            available_cash = cash_rows['value'].sum() if not cash_rows.empty else 0
            current_stock_value = stocks_df['value'].sum()
            
            # 总投资金额 = 投资组合总价值 - 预留现金
            total_investment_amount = total_portfolio_value - cash_reserve_amount
            
            logger.info(f"📊 投资组合总价值: ${total_portfolio_value:,.2f}")
            logger.info(f"💰 当前现金: ${available_cash:,.2f}")
            logger.info(f"📈 当前股票价值: ${current_stock_value:,.2f}")
            logger.info(f"🏦 预留现金: ${cash_reserve_amount:,.2f}")
            logger.info(f"🎯 总投资金额: ${total_investment_amount:,.2f}")
            logger.info(f"📊 股票数量: {len(stocks_df)}")
            
            # 3. 等权重计算：每只股票目标金额
            stock_count = len(stocks_df)
            target_amount_per_stock = total_investment_amount / stock_count
            
            logger.info(f"💰 每股目标金额: ${target_amount_per_stock:,.2f}")
            
            # 4. 计算每只股票的目标持股数（向上取整）
            stocks_df['target_shares'] = np.ceil(target_amount_per_stock / stocks_df['price'])
            stocks_df['target_value'] = stocks_df['target_shares'] * stocks_df['price']
            
            # 5. 生成买卖指令
            trades = []
            total_buy_amount = 0
            total_sell_amount = 0
            
            for _, stock in stocks_df.iterrows():
                current_shares = int(stock['shares'])
                target_shares = int(stock['target_shares'])
                share_diff = target_shares - current_shares
                trade_amount = abs(share_diff) * stock['price']
                
                # 只处理交易金额大于最小交易金额的操作
                if trade_amount >= min_trade_amount:
                    action = 'BUY' if share_diff > 0 else 'SELL'
                    
                    trades.append({
                        'symbol': stock['symbol'],
                        'action': action,
                        'shares': abs(share_diff),
                        'price': stock['price'],
                        'amount': trade_amount,
                        'current_shares': current_shares,
                        'target_shares': target_shares,
                        'current_value': stock['value'],
                        'target_value': stock['target_value'],
                        'reason': f'等权重调整 (${stock["value"]:.0f} → ${stock["target_value"]:.0f})'
                    })
                    
                    if action == 'BUY':
                        total_buy_amount += trade_amount
                    else:
                        total_sell_amount += trade_amount
                    
                    logger.info(f"  📈 {stock['symbol']}: {action} {abs(share_diff)} 股，${trade_amount:,.2f}")
            
            if not trades:
                logger.info("✅ 投资组合已接近等权重，无需再平衡")
                return None
            
            # 生成摘要
            logger.info(f"\n💰 === 简化等权重再平衡摘要 ===")
            logger.info(f"买入交易: {len([t for t in trades if t['action'] == 'BUY'])} 笔，总计 ${total_buy_amount:,.2f}")
            logger.info(f"卖出交易: {len([t for t in trades if t['action'] == 'SELL'])} 笔，总计 ${total_sell_amount:,.2f}")
            logger.info(f"净资金需求: ${total_buy_amount - total_sell_amount:,.2f}")
            
            return pd.DataFrame(trades)
            
        except Exception as e:
            logger.error(f"计算简化等权重再平衡失败: {e}")
            return None
    
    def get_simple_config(self):
        """
        获取简化配置参数（仅适用于简化等权重算法）
        
        Returns:
            dict: 简化配置字典
        """
        return {
            'min_trade_amount': 100,                   # 最小交易金额
            'cash_reserve_amount': 0,                  # 预留现金金额（绝对值）
        }
    

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
                
                # 策略B详细资金统计
                buy_amount = rebalance_df[rebalance_df['action'] == 'BUY']['amount'].sum()
                sell_amount = rebalance_df[rebalance_df['action'] == 'SELL']['amount'].sum()
                liquidate_amount = rebalance_df[rebalance_df['action'] == 'LIQUIDATE']['amount'].sum()
                
                # 计算现金相关数据
                cash_rows = portfolio_df[portfolio_df['symbol'] == 'CASH']
                current_cash = cash_rows['value'].sum() if not cash_rows.empty else 0
                
                # 预留现金计算（这里使用默认值，实际应该从算法中传递）
                target_cash_reserve = 2000.0  # 默认值，应该从参数传递
                
                # 资金流计算
                usable_cash = current_cash + liquidate_amount - target_cash_reserve
                total_funds_available = usable_cash + sell_amount
                net_cash_needed = buy_amount - sell_amount
                final_balance = total_funds_available - buy_amount
                
                report_lines.append(f"\n💰 策略B资金流详细统计:")
                report_lines.append(f"📊 资金来源:")
                report_lines.append(f"  • 当前现金: ${current_cash:,.2f}")
                report_lines.append(f"  • 清仓获得: ${liquidate_amount:,.2f}")
                report_lines.append(f"  • 卖出获得: ${sell_amount:,.2f}")
                report_lines.append(f"  • 总现金来源: ${current_cash + liquidate_amount + sell_amount:,.2f}")
                
                report_lines.append(f"\n📊 资金使用:")
                report_lines.append(f"  • 预留现金: ${target_cash_reserve:,.2f}")
                report_lines.append(f"  • 买入总额: ${buy_amount:,.2f}")
                report_lines.append(f"  • 总现金使用: ${target_cash_reserve + buy_amount:,.2f}")
                
                report_lines.append(f"\n📊 资金平衡:")
                report_lines.append(f"  • 可用于投资: ${usable_cash:,.2f}")
                report_lines.append(f"  • 总可用资金: ${total_funds_available:,.2f}")
                report_lines.append(f"  • 净现金需求: ${net_cash_needed:,.2f}")
                report_lines.append(f"  • 最终余额: ${final_balance:,.2f}")
                
                # 策略B验证
                if final_balance >= 0:
                    report_lines.append(f"\n✅ 策略B成功: 零净投入达成，余额 ${final_balance:,.2f}")
                    report_lines.append(f"💡 最终现金分布: ${target_cash_reserve:,.2f}(预留) + ${final_balance:,.2f}(余额) = ${target_cash_reserve + final_balance:,.2f}")
                else:
                    report_lines.append(f"\n⚠️ 策略B警告: 仍需额外投入 ${abs(final_balance):,.2f}")
                    
                # 传统计算对比（显示为什么会出现差异）
                traditional_shortage = net_cash_needed - (current_cash + liquidate_amount - target_cash_reserve)
                if traditional_shortage > 0:
                    report_lines.append(f"\n📝 传统计算显示: 资金不足 ${traditional_shortage:,.2f}")
                    report_lines.append(f"💡 差异原因: 传统计算未包含卖出获得资金 ${sell_amount:,.2f}")
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
    
    def scrape_portfolio_by_id(self, portfolio_id, save_html=True):
        """
        通过投资组合ID直接获取数据
        
        Args:
            portfolio_id: 投资组合ID
            save_html: 是否保存HTML文件
            
        Returns:
            投资组合数据DataFrame
        """
        try:
            if not self.driver:
                if not self.setup_driver():
                    return None
            
            # 构建URL
            portfolio_url = f"https://seekingalpha.com/account/portfolio/total_view?portfolioId={portfolio_id}"
            
            logger.info(f"正在访问投资组合: {portfolio_url}")
            self.driver.get(portfolio_url)
            
            # 等待页面初始加载
            time.sleep(3)
            
            # 检查是否需要登录
            if "login" in self.driver.current_url.lower():
                logger.warning("需要登录到SeekingAlpha账户")
                return None
            
            # 等待表格出现然后滚动加载所有数据
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table"))
                )
                # 滚动页面加载所有数据
                self.scroll_and_load_all_data()
            except Exception as e:
                logger.warning(f"页面滚动过程中出现问题: {e}")
            
            # 保存HTML文件
            if save_html:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_html_path = f"portfolio_data_{portfolio_id}_{timestamp}.html"
                standard_html_path = f"portfolio_data_{portfolio_id}.html"
                
                try:
                    with open(backup_html_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    with open(standard_html_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"页面HTML已保存: {backup_html_path}, {standard_html_path}")
                except Exception as e:
                    logger.error(f"保存HTML文件失败: {e}")
            
            # 爬取数据
            return self.scrape_portfolio_data_improved()
            
        except Exception as e:
            logger.error(f"通过ID获取投资组合数据失败: {e}")
            return None

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


def main(portfolio_id=None):
    """主函数 - 仅支持在线爬取"""
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=True)
    
    # 优先级：命令行参数 > 默认值
    if portfolio_id is None:
        portfolio_id = "64139349"  # 默认投资组合ID
    
    try:
        print(f"\n🌐 开始在线爬取投资组合 {portfolio_id}...")
        
        # 设置浏览器
        if not scraper.setup_driver():
            return

        # 导航到指定的投资组合页面
        portfolio_url = f"https://seekingalpha.com/account/portfolio/total_view?portfolioId={portfolio_id}"
        
        print(f"正在导航到: {portfolio_url}")
        scraper.driver.get(portfolio_url)
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(2)
        
        # 检查是否需要登录
        if "login" in scraper.driver.current_url.lower():
            print("⚠️ 需要登录到SeekingAlpha账户")
            print("请在浏览器中完成登录，然后按Enter继续...")
            input("按Enter继续爬取数据...")
            
            # 重新导航到投资组合页面
            scraper.driver.get(portfolio_url)
            time.sleep(5)

        # 滚动页面加载所有数据
        print("🔄 开始滚动页面加载所有投资组合数据...")
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            WebDriverWait(scraper.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            # scraper.scroll_and_load_all_data()
            print("✅ 页面滚动和数据加载完成")
        except Exception as e:
            print(f"⚠️ 页面滚动过程中出现问题: {e}")

        # 保存页面HTML用于后续分析
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_html_path = f"portfolio_data_{portfolio_id}_{timestamp}.html"
        
        try:
            with open(backup_html_path, 'w', encoding='utf-8') as f:
                f.write(scraper.driver.page_source)
            print(f"页面HTML已保存: {backup_html_path}")
        except Exception as e:
            print(f"保存HTML文件失败: {e}")

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
            
            # 计算简化等权重再平衡策略
            print("\n=== 🎯 开始计算简化等权重再平衡策略 ===")
            
            # 使用简化算法（使用默认配置）
            rebalance_df = scraper.calculate_equal_weight_rebalance(df)
            
            print("\n💡 简化算法说明:")
            print("- 等权重分配：每只股票获得相等的资金分配")
            print("- 向上取整：目标股数按向上取整原则计算")
            print("- 生成交易指令：比较当前持股与目标持股生成买卖操作")
            
            # 生成报告
            print("\n=== 📋 生成再平衡报告 ===")
            report = scraper.generate_rebalance_report(df, rebalance_df)
            print(report)

        else:
            print("❌ 数据获取失败")
            print("正在保存调试信息...")
            scraper.save_debug_info("debug_failed_scrape.html")

    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        scraper.close()




def quick_analyze_portfolio(portfolio_id, target_stock_count=30, target_cash_amount=None, 
                           target_cash_percentage=0.02, liquidate_symbols=None, exclude_symbols=None):
    """
    快速分析投资组合的便捷函数（分层处理策略）- 仅支持在线获取
    
    Args:
        portfolio_id: 投资组合ID
        target_stock_count: 目标股票数量 (默认30)
        target_cash_amount: 目标固定现金金额 (优先级高于百分比)
        target_cash_percentage: 目标现金比例 (默认2%)
        liquidate_symbols: 需要清仓的股票代码列表
        exclude_symbols: 排除的股票代码列表
        
    Returns:
        投资组合数据DataFrame和再平衡数据DataFrame
    """
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=False)
    
    try:
        # 在线获取数据
        print(f"在线获取投资组合数据: {portfolio_id}")
        df = scraper.scrape_portfolio_by_id(portfolio_id)
        
        if df is not None:
            # 计算简化等权重再平衡（使用默认配置）
            rebalance_df = scraper.calculate_equal_weight_rebalance(df)
            
            # 生成报告
            report = scraper.generate_rebalance_report(df, rebalance_df, save_to_file=True)
            print(report)
            
            return df, rebalance_df
        else:
            print("无法获取投资组合数据")
            return None, None
            
    except Exception as e:
        print(f"分析失败: {e}")
        return None, None
    finally:
        scraper.close()


if __name__ == "__main__":
    # 检查命令行参数
    import sys
    
    if len(sys.argv) > 1:
        # 第一个参数作为投资组合ID
        portfolio_id = sys.argv[1]
        print(f"使用指定的投资组合ID: {portfolio_id}")
        main(portfolio_id)
    else:
        main()