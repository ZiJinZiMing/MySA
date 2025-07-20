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

    
    def calculate_equal_weight_rebalance(self, portfolio_df, config=None):
        """
        计算等权重再平衡策略（分层处理策略）
        
        Args:
            portfolio_df: 投资组合DataFrame
            config: 配置字典，包含所有再平衡参数
            
        Returns:
            再平衡指令DataFrame
        """
        try:
            # 使用默认配置
            if config is None:
                config = self.get_default_config()
            
            logger.info("开始计算等权重再平衡策略（分层处理策略）")
            
            if portfolio_df is None or portfolio_df.empty:
                logger.error("投资组合数据为空")
                return None
            
            # 初始化参数
            exclude_symbols = config.get('exclude_symbols', [])
            liquidate_symbols = config.get('liquidate_symbols', [])
            
            # ===== 第一阶段：基础数据准备 =====
            cash_rows = portfolio_df[portfolio_df['symbol'] == 'CASH']
            stock_rows = portfolio_df[portfolio_df['symbol'] != 'CASH'].copy()
            
            total_portfolio_value = portfolio_df['value'].sum()
            available_cash = cash_rows['value'].sum() if not cash_rows.empty else 0
            
            logger.info(f"📊 投资组合总价值: ${total_portfolio_value:,.2f}")
            logger.info(f"💰 当前现金: ${available_cash:,.2f}")
            
            # ===== 第二阶段：处理清仓和排除 =====
            liquidation_proceeds = 0
            liquidated_stocks = pd.DataFrame()
            if liquidate_symbols:
                liquidation_mask = stock_rows['symbol'].isin(liquidate_symbols)
                liquidated_stocks = stock_rows[liquidation_mask].copy()
                liquidation_proceeds = liquidated_stocks['value'].sum()
                stock_rows = stock_rows[~liquidation_mask]
                logger.info(f"🔥 清仓股票: {liquidate_symbols}")
                logger.info(f"🔥 清仓获得资金: ${liquidation_proceeds:,.2f}")
            
            if exclude_symbols:
                exclude_mask = stock_rows['symbol'].isin(exclude_symbols)
                stock_rows = stock_rows[~exclude_mask]
                logger.info(f"⏭️ 排除股票: {exclude_symbols}")
            
            # ===== 第三阶段：计算目标股票数量 =====
            # 根据实际数据计算目标股票数量，而不是使用配置参数
            target_stock_count = len(stock_rows)
            logger.info(f"🎯 目标股票数量: {target_stock_count} (根据实际数据计算)")
            
            # ===== 第四阶段：计算预留现金 =====
            target_cash_reserve = self._calculate_target_cash_reserve(total_portfolio_value, config)
            logger.info(f"🏦 预留现金: ${target_cash_reserve:,.2f}")
            
            # ===== 第五阶段：分层处理再平衡 =====
            total_available_funds = available_cash + liquidation_proceeds - target_cash_reserve
            
            if total_available_funds <= 0:
                logger.warning("⚠️ 可用资金不足，无法进行再平衡")
                return self._create_liquidation_only_df(liquidated_stocks) if not liquidated_stocks.empty else None
            
            # 计算目标权重和偏离度
            target_weight = 1.0 / target_stock_count
            target_value_per_stock = total_portfolio_value * target_weight
            
            stock_rows['target_value'] = target_value_per_stock
            stock_rows['deviation'] = (stock_rows['value'] - target_value_per_stock) / total_portfolio_value
            stock_rows['abs_deviation'] = abs(stock_rows['deviation'])
            
            # 执行分层处理
            trades, remaining_funds = self._execute_tiered_rebalancing(
                stock_rows, total_available_funds, target_value_per_stock, 
                total_portfolio_value, config
            )
            
            # 添加清仓指令
            if not liquidated_stocks.empty:
                for _, stock in liquidated_stocks.iterrows():
                    trades.append({
                        'symbol': stock['symbol'],
                        'action': 'LIQUIDATE',
                        'shares': int(stock['shares']),
                        'price': stock['price'],
                        'amount': stock['value'],
                        'current_value': stock['value'],
                        'target_value': 0,
                        'difference': -stock['value'],
                        'current_weight': stock['value'] / total_portfolio_value,
                        'target_weight': 0,
                        'priority': 'LIQUIDATION',
                        'reason': '清仓'
                    })
            
            if not trades:
                logger.info("✅ 投资组合已接近等权重，无需再平衡")
                return None
            
            # 生成最终报告
            self._log_rebalancing_summary(trades, total_available_funds, remaining_funds)
            
            return pd.DataFrame(trades)
            
        except Exception as e:
            logger.error(f"计算等权重再平衡失败: {e}")
            return None
    
    def get_default_config(self):
        """
        获取默认配置参数
        
        Returns:
            dict: 默认配置字典
        """
        return {
            # 基础配置
            'target_stock_count': 30,                  # 目标股票数量
            'exclude_symbols': ['CASH'],               # 排除的股票代码
            'liquidate_symbols': [],                   # 需要清仓的股票代码
            
            # 现金管理
            'target_cash_amount': None,                # 目标固定现金金额 (优先级高)
            'target_cash_percentage': 0.02,            # 目标现金比例 (2%)
            'min_cash_reserve': 1000,                  # 最小现金储备
            
            # 偏离度阈值
            'deviation_thresholds': {
                'critical': 0.02,                      # 临界偏离 (2%)
                'severe': 0.015,                       # 严重偏离 (1.5%)
                'moderate': 0.01,                      # 中等偏离 (1%)
                'minor': 0.005,                        # 轻微偏离 (0.5%)
                'target_range': 0.003                  # 目标范围 (±0.3%)
            },
            
            # 分层处理配置
            'tier_allocation': {
                'tier1_budget_ratio': 0.6,             # 第一层预算比例 (60%)
                'tier2_budget_ratio': 0.3,             # 第二层预算比例 (30%)
                'tier3_budget_ratio': 0.1,             # 第三层预算比例 (10%)
                'max_single_stock_ratio': 0.15,        # 单只股票最大资金比例 (15%)
                'tier1_target_improvement': 0.7,       # 第一层目标改善比例 (70%)
                'tier2_target_improvement': 0.5,       # 第二层目标改善比例 (50%)
                'tier3_target_improvement': 0.3        # 第三层目标改善比例 (30%)
            },
            
            # 交易约束
            'trading_constraints': {
                'min_trade_amount': 100,               # 最小交易金额
                'min_shares_per_trade': 1,             # 最小交易股数
                'max_position_change': 0.5,            # 单次最大仓位变化 (50%)
                'overweight_sell_threshold': 0.015,    # 超配卖出阈值 (1.5%)
                'underweight_buy_threshold': -0.005    # 低配买入阈值 (-0.5%)
            },
            
            # 风险控制
            'risk_management': {
                'max_trades_per_session': 50,          # 单次最大交易数
                'emergency_cash_ratio': 0.05,          # 紧急现金比例 (5%)
                'concentration_limit': 0.1,            # 单只股票最大权重 (10%)
                'liquidity_buffer': 0.02               # 流动性缓冲 (2%)
            }
        }
    
    def _calculate_target_cash_reserve(self, total_portfolio_value, config):
        """
        计算目标现金储备
        
        Args:
            total_portfolio_value: 投资组合总价值
            config: 配置字典
            
        Returns:
            float: 目标现金储备金额
        """
        target_cash_amount = config.get('target_cash_amount')
        if target_cash_amount is not None:
            return target_cash_amount
        
        target_cash_percentage = config.get('target_cash_percentage', 0.02)
        calculated_reserve = total_portfolio_value * target_cash_percentage
        
        min_cash_reserve = config.get('min_cash_reserve', 1000)
        return max(calculated_reserve, min_cash_reserve)
    
    def _execute_tiered_rebalancing(self, stock_rows, available_funds, target_value_per_stock, 
                                   total_portfolio_value, config):
        """
        执行分层再平衡策略
        
        Args:
            stock_rows: 股票数据DataFrame
            available_funds: 可用资金
            target_value_per_stock: 目标每股价值
            total_portfolio_value: 投资组合总价值
            config: 配置字典
            
        Returns:
            tuple: (交易列表, 剩余资金)
        """
        trades = []
        remaining_funds = available_funds
        
        # 获取配置
        thresholds = config.get('deviation_thresholds')
        tier_config = config.get('tier_allocation')
        
        # 第一步：处理超配股票，增加可用资金
        overweight_proceeds = self._handle_overweight_stocks(
            stock_rows, target_value_per_stock, total_portfolio_value, 
            thresholds, config, trades
        )
        remaining_funds += overweight_proceeds
        
        logger.info(f"💰 超配卖出获得资金: ${overweight_proceeds:,.2f}")
        logger.info(f"💰 更新后可用资金: ${remaining_funds:,.2f}")
        
        # 第二步：分层处理不足权重的股票
        underweight_stocks = stock_rows[stock_rows['deviation'] < -thresholds['minor']].copy()
        
        if underweight_stocks.empty:
            logger.info("✅ 没有需要补仓的股票")
            return trades, remaining_funds
        
        # 计算资金覆盖率
        total_shortage = (underweight_stocks['target_value'] - underweight_stocks['value']).sum()
        coverage_ratio = remaining_funds / total_shortage if total_shortage > 0 else 1.0
        
        logger.info(f"📊 === 分层处理分析 ===")
        logger.info(f"不足权重股票数量: {len(underweight_stocks)}")
        logger.info(f"总资金缺口: ${total_shortage:,.2f}")
        logger.info(f"资金覆盖率: {coverage_ratio:.2%}")
        
        # 执行分层处理
        if coverage_ratio < 0.2:
            logger.info("🚨 策略：集中火力解决最严重问题")
            remaining_funds = self._tier1_critical_focus(
                underweight_stocks, remaining_funds, target_value_per_stock, 
                total_portfolio_value, config, trades
            )
        elif coverage_ratio < 0.6:
            logger.info("⚠️ 策略：分层处理不同程度的不足")
            remaining_funds = self._execute_full_tiered_strategy(
                underweight_stocks, remaining_funds, target_value_per_stock, 
                total_portfolio_value, config, trades
            )
        else:
            logger.info("✅ 策略：全面改善权重平衡")
            remaining_funds = self._comprehensive_rebalancing(
                underweight_stocks, remaining_funds, target_value_per_stock, 
                total_portfolio_value, config, trades
            )
        
        return trades, remaining_funds
    
    def _handle_overweight_stocks(self, stock_rows, target_value_per_stock, total_portfolio_value, 
                                 thresholds, config, trades):
        """
        处理超配股票，通过卖出增加可用资金
        
        Args:
            stock_rows: 股票数据DataFrame
            target_value_per_stock: 目标每股价值
            total_portfolio_value: 投资组合总价值
            thresholds: 偏离度阈值
            config: 配置字典
            trades: 交易列表
            
        Returns:
            float: 卖出获得的资金
        """
        sell_threshold = config.get('trading_constraints', {}).get('overweight_sell_threshold', 0.015)
        overweight_stocks = stock_rows[stock_rows['deviation'] > sell_threshold]
        
        total_proceeds = 0
        
        if overweight_stocks.empty:
            return total_proceeds
        
        logger.info(f"🔍 发现 {len(overweight_stocks)} 只超配股票")
        
        for _, stock in overweight_stocks.iterrows():
            excess_value = stock['value'] - target_value_per_stock
            shares_to_sell = int(excess_value / stock['price'])
            
            if shares_to_sell > 0:
                sell_amount = shares_to_sell * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'SELL',
                    'shares': shares_to_sell,
                    'price': stock['price'],
                    'amount': sell_amount,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': -excess_value,
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'OVERWEIGHT_REDUCTION',
                    'reason': f'超配{stock["deviation"]:.2%}'
                })
                
                total_proceeds += sell_amount
                logger.info(f"  📉 {stock['symbol']}: 卖出 {shares_to_sell} 股，获得 ${sell_amount:,.2f}")
        
        return total_proceeds
    
    def _tier1_critical_focus(self, underweight_stocks, available_funds, target_value_per_stock, 
                             total_portfolio_value, config, trades):
        """
        第一层：集中处理最严重的问题
        
        Args:
            underweight_stocks: 不足权重股票DataFrame
            available_funds: 可用资金
            target_value_per_stock: 目标每股价值
            total_portfolio_value: 投资组合总价值
            config: 配置字典
            trades: 交易列表
            
        Returns:
            float: 剩余资金
        """
        thresholds = config.get('deviation_thresholds')
        tier_config = config.get('tier_allocation')
        
        # 只处理最严重的前5只股票
        critical_stocks = underweight_stocks[
            underweight_stocks['deviation'] < -thresholds['critical']
        ].sort_values('deviation').head(5)
        
        remaining_funds = available_funds
        
        logger.info(f"🎯 第一层：集中处理 {len(critical_stocks)} 只最严重股票")
        
        for _, stock in critical_stocks.iterrows():
            if remaining_funds < stock['price']:
                break
            
            # 目标：让这只股票达到可接受的水平
            target_improvement = tier_config.get('tier1_target_improvement', 0.7)
            needed_improvement = (target_value_per_stock - stock['value']) * target_improvement
            
            max_investment = min(
                needed_improvement,
                remaining_funds * 0.8,  # 最多用80%资金
                remaining_funds - config.get('min_cash_reserve', 1000)
            )
            
            if max_investment > stock['price']:
                shares = int(max_investment / stock['price'])
                cost = shares * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'BUY',
                    'shares': shares,
                    'price': stock['price'],
                    'amount': cost,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': target_value_per_stock - stock['value'],
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'TIER1_CRITICAL',
                    'reason': f'严重不足{stock["deviation"]:.2%}'
                })
                
                remaining_funds -= cost
                logger.info(f"  🎯 {stock['symbol']}: 集中投资 {shares} 股，${cost:,.2f}")
        
        return remaining_funds
    
    def _execute_full_tiered_strategy(self, underweight_stocks, available_funds, target_value_per_stock, 
                                     total_portfolio_value, config, trades):
        """
        执行完整的分层策略
        
        Args:
            underweight_stocks: 不足权重股票DataFrame
            available_funds: 可用资金
            target_value_per_stock: 目标每股价值
            total_portfolio_value: 投资组合总价值
            config: 配置字典
            trades: 交易列表
            
        Returns:
            float: 剩余资金
        """
        thresholds = config.get('deviation_thresholds')
        tier_config = config.get('tier_allocation')
        
        # 股票分层
        tier1_stocks = underweight_stocks[underweight_stocks['deviation'] < -thresholds['critical']]
        tier2_stocks = underweight_stocks[
            (underweight_stocks['deviation'] >= -thresholds['critical']) &
            (underweight_stocks['deviation'] < -thresholds['severe'])
        ]
        tier3_stocks = underweight_stocks[
            (underweight_stocks['deviation'] >= -thresholds['severe']) &
            (underweight_stocks['deviation'] < -thresholds['minor'])
        ]
        
        remaining_funds = available_funds
        
        # 第一层：临界不足股票 (60%资金)
        tier1_budget = available_funds * tier_config.get('tier1_budget_ratio', 0.6)
        remaining_funds = self._process_tier1_stocks(
            tier1_stocks, tier1_budget, remaining_funds, target_value_per_stock, 
            total_portfolio_value, config, trades
        )
        
        # 第二层：严重不足股票 (30%资金)
        tier2_budget = min(
            available_funds * tier_config.get('tier2_budget_ratio', 0.3),
            remaining_funds
        )
        remaining_funds = self._process_tier2_stocks(
            tier2_stocks, tier2_budget, remaining_funds, target_value_per_stock, 
            total_portfolio_value, config, trades
        )
        
        # 第三层：中等不足股票 (剩余资金)
        remaining_funds = self._process_tier3_stocks(
            tier3_stocks, remaining_funds, target_value_per_stock, 
            total_portfolio_value, config, trades
        )
        
        return remaining_funds
    
    def _process_tier1_stocks(self, tier1_stocks, tier1_budget, remaining_funds, target_value_per_stock, 
                             total_portfolio_value, config, trades):
        """
        处理第一层股票：临界不足股票
        """
        if tier1_stocks.empty:
            return remaining_funds
        
        tier_config = config.get('tier_allocation')
        logger.info(f"🎯 第一层处理：{len(tier1_stocks)} 只临界不足股票，预算 ${tier1_budget:,.2f}")
        
        for _, stock in tier1_stocks.sort_values('deviation').iterrows():
            if remaining_funds < stock['price'] or tier1_budget < stock['price']:
                break
            
            # 目标：让这些股票达到严重不足水平
            target_improvement = tier_config.get('tier1_target_improvement', 0.7)
            needed_improvement = (target_value_per_stock - stock['value']) * target_improvement
            
            max_investment = min(
                needed_improvement,
                tier1_budget / max(1, len(tier1_stocks)),
                remaining_funds * tier_config.get('max_single_stock_ratio', 0.15)
            )
            
            if max_investment > stock['price']:
                shares = int(max_investment / stock['price'])
                cost = shares * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'BUY',
                    'shares': shares,
                    'price': stock['price'],
                    'amount': cost,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': target_value_per_stock - stock['value'],
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'TIER1_CRITICAL',
                    'reason': f'临界不足{stock["deviation"]:.2%}'
                })
                
                remaining_funds -= cost
                tier1_budget -= cost
                
                new_deviation = (stock['value'] + cost - target_value_per_stock) / total_portfolio_value
                logger.info(f"  📈 {stock['symbol']}: 买入 {shares} 股 (${cost:,.2f}), "
                           f"改善 {stock['deviation']:.2%} → {new_deviation:.2%}")
        
        return remaining_funds
    
    def _process_tier2_stocks(self, tier2_stocks, tier2_budget, remaining_funds, target_value_per_stock, 
                             total_portfolio_value, config, trades):
        """
        处理第二层股票：严重不足股票
        """
        if tier2_stocks.empty:
            return remaining_funds
        
        tier_config = config.get('tier_allocation')
        logger.info(f"🎯 第二层处理：{len(tier2_stocks)} 只严重不足股票，预算 ${tier2_budget:,.2f}")
        
        for _, stock in tier2_stocks.sort_values('deviation').iterrows():
            if remaining_funds < stock['price'] or tier2_budget < stock['price']:
                break
            
            target_improvement = tier_config.get('tier2_target_improvement', 0.5)
            needed_improvement = (target_value_per_stock - stock['value']) * target_improvement
            
            max_investment = min(
                needed_improvement,
                tier2_budget / max(1, len(tier2_stocks)),
                remaining_funds * 0.1  # 第二层单股最多10%资金
            )
            
            if max_investment > stock['price']:
                shares = int(max_investment / stock['price'])
                cost = shares * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'BUY',
                    'shares': shares,
                    'price': stock['price'],
                    'amount': cost,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': target_value_per_stock - stock['value'],
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'TIER2_SEVERE',
                    'reason': f'严重不足{stock["deviation"]:.2%}'
                })
                
                remaining_funds -= cost
                tier2_budget -= cost
                logger.info(f"  📈 {stock['symbol']}: 买入 {shares} 股 (${cost:,.2f})")
        
        return remaining_funds
    
    def _process_tier3_stocks(self, tier3_stocks, remaining_funds, target_value_per_stock, 
                             total_portfolio_value, config, trades):
        """
        处理第三层股票：中等不足股票
        """
        if tier3_stocks.empty:
            return remaining_funds
        
        tier_config = config.get('tier_allocation')
        logger.info(f"🎯 第三层处理：{len(tier3_stocks)} 只中等不足股票，预算 ${remaining_funds:,.2f}")
        
        for _, stock in tier3_stocks.sort_values('deviation').iterrows():
            if remaining_funds < stock['price'] * 10:  # 至少要能买10股
                break
            
            target_improvement = tier_config.get('tier3_target_improvement', 0.3)
            needed_improvement = (target_value_per_stock - stock['value']) * target_improvement
            
            max_investment = min(
                needed_improvement,
                remaining_funds * 0.5  # 第三层单股最多50%剩余资金
            )
            
            if max_investment > stock['price']:
                shares = int(max_investment / stock['price'])
                cost = shares * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'BUY',
                    'shares': shares,
                    'price': stock['price'],
                    'amount': cost,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': target_value_per_stock - stock['value'],
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'TIER3_MODERATE',
                    'reason': f'中等不足{stock["deviation"]:.2%}'
                })
                
                remaining_funds -= cost
                logger.info(f"  📈 {stock['symbol']}: 买入 {shares} 股 (${cost:,.2f})")
        
        return remaining_funds
    
    def _comprehensive_rebalancing(self, underweight_stocks, available_funds, target_value_per_stock, 
                                  total_portfolio_value, config, trades):
        """
        全面改善权重平衡
        """
        logger.info(f"✅ 全面改善：{len(underweight_stocks)} 只不足权重股票")
        
        remaining_funds = available_funds
        
        for _, stock in underweight_stocks.sort_values('deviation').iterrows():
            if remaining_funds < stock['price']:
                break
            
            # 尽可能接近目标权重
            needed_investment = target_value_per_stock - stock['value']
            max_investment = min(
                needed_investment,
                remaining_funds * 0.8 / len(underweight_stocks),  # 平均分配
                remaining_funds * 0.1  # 单股最多10%
            )
            
            if max_investment > stock['price']:
                shares = int(max_investment / stock['price'])
                cost = shares * stock['price']
                
                trades.append({
                    'symbol': stock['symbol'],
                    'action': 'BUY',
                    'shares': shares,
                    'price': stock['price'],
                    'amount': cost,
                    'current_value': stock['value'],
                    'target_value': target_value_per_stock,
                    'difference': target_value_per_stock - stock['value'],
                    'current_weight': stock['value'] / total_portfolio_value,
                    'target_weight': target_value_per_stock / total_portfolio_value,
                    'priority': 'COMPREHENSIVE',
                    'reason': f'全面改善{stock["deviation"]:.2%}'
                })
                
                remaining_funds -= cost
                logger.info(f"  📈 {stock['symbol']}: 买入 {shares} 股 (${cost:,.2f})")
        
        return remaining_funds
    
    def _log_rebalancing_summary(self, trades, total_available_funds, remaining_funds):
        """
        记录再平衡摘要
        """
        if not trades:
            return
        
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        liquidate_trades = [t for t in trades if t['action'] == 'LIQUIDATE']
        
        total_buy_amount = sum(t['amount'] for t in buy_trades)
        total_sell_amount = sum(t['amount'] for t in sell_trades)
        total_liquidate_amount = sum(t['amount'] for t in liquidate_trades)
        
        logger.info(f"\n💰 === 分层再平衡摘要 ===")
        logger.info(f"总可用资金: ${total_available_funds:,.2f}")
        logger.info(f"买入交易: {len(buy_trades)} 笔，总计 ${total_buy_amount:,.2f}")
        logger.info(f"卖出交易: {len(sell_trades)} 笔，总计 ${total_sell_amount:,.2f}")
        logger.info(f"清仓交易: {len(liquidate_trades)} 笔，总计 ${total_liquidate_amount:,.2f}")
        logger.info(f"剩余现金: ${remaining_funds:,.2f}")
        logger.info(f"资金利用率: {(total_available_funds - remaining_funds) / total_available_funds:.2%}")
        
        # 按优先级统计
        priority_stats = {}
        for trade in trades:
            priority = trade.get('priority', 'UNKNOWN')
            if priority not in priority_stats:
                priority_stats[priority] = {'count': 0, 'amount': 0}
            priority_stats[priority]['count'] += 1
            priority_stats[priority]['amount'] += trade['amount']
        
        logger.info(f"\n📊 === 优先级统计 ===")
        for priority, stats in priority_stats.items():
            logger.info(f"{priority}: {stats['count']} 笔交易，${stats['amount']:,.2f}")
    
    def _create_liquidation_only_df(self, liquidated_stocks):
        """创建仅包含清仓指令的DataFrame"""
        liquidation_actions = []
        for _, stock in liquidated_stocks.iterrows():
            liquidation_actions.append({
                'symbol': stock['symbol'],
                'action': 'LIQUIDATE',
                'shares': int(stock['shares']),
                'price': stock['price'],
                'amount': stock['value'],
                'current_value': stock['value'],
                'target_value': 0,
                'difference': -stock['value'],
                'current_weight': stock['weight'] if 'weight' in stock else 0,
                'target_weight': 0,
                'priority': 'LIQUIDATION',
                'reason': '清仓'
            })
        return pd.DataFrame(liquidation_actions)
    
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
            time.sleep(5)
            
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
            scraper.scroll_and_load_all_data()
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
            
            # 计算等权重再平衡（分层处理策略）
            print("\n=== 🎯 开始计算等权重再平衡（分层处理策略）===")
            
            # 创建配置
            config = {
                'target_stock_count': 30,
                'target_cash_amount': 200,
                'liquidate_symbols': ['OKTA', 'INTA'],
                'exclude_symbols': ['CASH'],
                'deviation_thresholds': {
                    'critical': 0.02,
                    'severe': 0.015,
                    'moderate': 0.01,
                    'minor': 0.005,
                    'target_range': 0.003
                },
                'tier_allocation': {
                    'tier1_budget_ratio': 0.6,
                    'tier2_budget_ratio': 0.3,
                    'tier3_budget_ratio': 0.1,
                    'max_single_stock_ratio': 0.15,
                    'tier1_target_improvement': 0.7,
                    'tier2_target_improvement': 0.5,
                    'tier3_target_improvement': 0.3
                }
            }
            
            rebalance_df = scraper.calculate_equal_weight_rebalance(df, config)
            
            print("\n💡 分层处理策略说明:")
            print("- 第一层(60%资金): 处理偏离>2%的临界不足股票")
            print("- 第二层(30%资金): 处理偏离1.5%-2%的严重不足股票")
            print("- 第三层(10%资金): 处理偏离0.5%-1.5%的中等不足股票")
            print("- 超配股票: 自动卖出偏离>1.5%的股票")
            print("- 资金智能分配: 根据资金覆盖率选择最优策略")
            
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
            # 创建配置
            config = {
                'target_stock_count': target_stock_count,
                'target_cash_amount': target_cash_amount,
                'target_cash_percentage': target_cash_percentage,
                'liquidate_symbols': liquidate_symbols or [],
                'exclude_symbols': exclude_symbols or ['CASH']
            }
            
            # 计算分层再平衡
            rebalance_df = scraper.calculate_equal_weight_rebalance(df, config)
            
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