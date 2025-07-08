#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能说明:
    1. 从SeekingAlpha MyAlphaPicker页面获取股票筛选列表
    2. 提取股票的Symbol、Price、QuantRating、Sector&Industry等基础信息
    3. 访问每只股票的量化评分详细页面获取交易所信息和评级历史
    4. 支持限制处理股票数量(测试时只处理前N只股票)
    5. 使用Chrome远程调试架构，复用登录状态

简化改进:
    - 移除复杂的反爬虫机制
    - 保留进度管理功能
    - 简化延时逻辑
    - 移除图形化功能
"""

import os
import time
import logging
import pandas as pd
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, filename="stock_analysis_progress.json"):
        self.progress_file = filename
        
    def save_progress(self, processed_symbols: List[str], results: List[Dict]):
        """保存当前进度"""
        try:
            progress_data = {
                'timestamp': datetime.now().isoformat(),
                'processed_count': len(processed_symbols),
                'processed_symbols': processed_symbols,
                'results': results
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 进度已保存: {len(processed_symbols)}只股票")
            
        except Exception as e:
            logger.error(f"❌ 保存进度失败: {e}")
    
    def load_progress(self) -> Optional[Dict]:
        """加载之前的进度"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                
                logger.info(f"🔄 发现未完成任务: {progress['processed_count']}只股票已处理")
                return progress
                
        except Exception as e:
            logger.warning(f"加载进度失败: {e}")
        
        return None
    
    def cleanup(self):
        """清理进度文件"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                logger.info("🧹 进度文件已清理")
        except Exception as e:
            logger.warning(f"清理进度文件失败: {e}")


class SimplifiedStockAnalyzer:
    """简化的股票分析器"""
    
    def __init__(self, test_mode=False, max_stocks=None):
        """
        初始化分析器
        
        Args:
            test_mode: 是否为测试模式
            max_stocks: 最大处理股票数量，None表示处理全部
        """
        self.test_mode = test_mode
        self.max_stocks = max_stocks
        self.driver = None
        self.processed_count = 0
        
        # 进度管理
        self.progress_manager = ProgressManager()
        
        # URL配置
        self.my_alpha_picker_url = "https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker"
        self.quant_rating_url_template = "https://seekingalpha.com/symbol/{symbol}/ratings/quant-ratings"
        
        if max_stocks is None:
            logger.info(f"初始化简化股票分析器 - 处理模式: {'测试' if test_mode else '生产'}, 股票数: 全部")
        else:
            logger.info(f"初始化简化股票分析器 - 处理模式: {'测试' if test_mode else '生产'}, 最大股票数: {max_stocks}")
    
    def setup_driver(self) -> bool:
        """设置Chrome浏览器驱动"""
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Chrome远程调试连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ Chrome连接失败: {e}")
            return False
    
    def extract_my_alpha_picker_data(self) -> List[Dict]:
        """
        从MyAlphaPicker页面提取股票列表数据
        
        Returns:
            包含股票基础信息的列表
        """
        try:
            logger.info("🔍 正在访问MyAlphaPicker页面...")
            self.driver.get(self.my_alpha_picker_url)
            
            # 等待页面加载
            logger.info("等待页面加载...")
            time.sleep(2)
            
            # 检查页面是否需要登录
            if "login" in self.driver.current_url.lower():
                logger.warning("需要登录SeekingAlpha账户")
                return []
            
            # 尝试多种方式等待页面元素
            wait = WebDriverWait(self.driver, 15)
            
            # 尝试等待不同的表格元素
            table_selectors = [
                "[data-test-id='screener-table']",
                "table",
                ".screener-table",
                "[data-testid='screener-table']"
            ]
            
            table_found = False
            for selector in table_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    logger.info(f"找到表格元素: {selector}")
                    table_found = True
                    break
                except:
                    continue
            
            if not table_found:
                logger.warning("未找到表格元素，尝试解析整个页面")
            
            # 滚动加载全部股票（目标：312只）
            self._scroll_to_load_all_stocks()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 保存页面HTML用于调试
            debug_filename = f"debug_my_alpha_picker_{int(time.time())}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"已保存调试HTML: {debug_filename}")
            
            stocks_data = []
            
            # 尝试多种方式查找股票数据
            stock_rows = self._find_stock_rows(soup)
            
            if not stock_rows:
                logger.error("未找到任何股票行数据")
                return []
            
            logger.info(f"找到 {len(stock_rows)} 只股票")
            
            for i, row in enumerate(stock_rows):
                if self.max_stocks is not None and i >= self.max_stocks:
                    logger.info(f"达到处理限制: 仅处理前 {self.max_stocks} 只股票")
                    break
                
                try:
                    stock_data = self._extract_stock_basic_info(row)
                    if stock_data:
                        stocks_data.append(stock_data)
                        logger.info(f"✅ 提取股票基础信息: {stock_data['symbol']} - {stock_data['price']}")
                except Exception as e:
                    logger.warning(f"提取第 {i+1} 行股票信息失败: {e}")
                    continue
            
            logger.info(f"✅ 成功提取 {len(stocks_data)} 只股票的基础信息")
            return stocks_data
            
        except Exception as e:
            logger.error(f"❌ 提取MyAlphaPicker数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _scroll_to_load_all_stocks(self):
        """
        通过向下滚动加载全部股票数据（无限滚动）
        """
        try:
            logger.info("🔄 开始滚动加载全部股票数据...")
            
            previous_stock_count = 0
            stable_count = 0  # 连续多少次股票数量没有变化
            max_stable_attempts = 6  # 连续6次没变化就停止
            scroll_pause_time = 1.0  # 每次滚动后等待时间
            
            while stable_count < max_stable_attempts:
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # 等待内容加载
                time.sleep(scroll_pause_time)
                
                # 获取当前股票数量
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                current_stock_count = self._count_stocks_in_page(soup)
                
                if current_stock_count > previous_stock_count:
                    # 有新股票加载
                    new_stocks = current_stock_count - previous_stock_count
                    logger.info(f"📊 已加载 {current_stock_count} 只股票 (+{new_stocks} 新增)")
                    previous_stock_count = current_stock_count
                    stable_count = 0  # 重置稳定计数
                else:
                    # 股票数量没有变化
                    stable_count += 1
                    logger.info(f"🔄 滚动第 {stable_count}/{max_stable_attempts} 次，股票数量稳定在 {current_stock_count} 只")
                    
                    # 如果连续2次没有变化，尝试一些额外的滚动策略
                    if stable_count >= 2:
                        logger.info("🔧 尝试额外的滚动策略...")
                        # 多次小幅滚动
                        for i in range(5):
                            self.driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(0.2)
            
            # 最终统计
            final_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            final_count = self._count_stocks_in_page(final_soup)
            logger.info(f"✅ 滚动完成，最终加载 {final_count} 只股票")
            
        except Exception as e:
            logger.error(f"❌ 滚动加载股票失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _count_stocks_in_page(self, soup) -> int:
        """
        统计当前页面中的股票数量
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            股票数量
        """
        try:
            # 尝试多种方式计算股票数量
            stock_rows = self._find_stock_rows(soup)
            return len(stock_rows) if stock_rows else 0
            
        except Exception as e:
            logger.debug(f"统计股票数量失败: {e}")
            return 0
    
    def _find_stock_rows(self, soup):
        """查找股票行数据，使用多种方法"""
        try:
            # 方法1: 查找data-test-id属性的行
            rows = soup.find_all('tr', {'data-test-id': 'screener-table-row'})
            if rows:
                logger.info(f"方法1: 找到 {len(rows)} 行数据")
                return rows
            
            # 方法2: 查找表格中的所有行
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # 跳过表头
                if len(rows) > 0:
                    logger.info(f"方法2: 在表格中找到 {len(rows)} 行数据")
                    return rows
            
            # 方法3: 查找包含股票代码链接的行
            symbol_links = soup.find_all('a', href=re.compile(r'/symbol/[A-Z]+'))
            if symbol_links:
                rows = []
                for link in symbol_links:
                    # 找到包含这个链接的行
                    row = link.find_parent('tr')
                    if row and row not in rows:
                        rows.append(row)
                logger.info(f"方法3: 通过股票链接找到 {len(rows)} 行数据")
                return rows
            
            # 方法4: 查找包含价格信息的行
            price_elements = soup.find_all(text=re.compile(r'\$\d+\.\d+'))
            if price_elements:
                rows = []
                for price_elem in price_elements:
                    row = price_elem.find_parent('tr')
                    if row and row not in rows:
                        rows.append(row)
                logger.info(f"方法4: 通过价格信息找到 {len(rows)} 行数据")
                return rows
            
            logger.warning("所有方法都未找到股票行数据")
            return []
            
        except Exception as e:
            logger.error(f"查找股票行数据失败: {e}")
            return []
    
    def _extract_stock_basic_info(self, row) -> Optional[Dict]:
        """
        从表格行中提取股票基础信息，使用多种策略
        
        Args:
            row: BeautifulSoup行元素
            
        Returns:
            股票基础信息字典
        """
        try:
            stock_data = {}
            
            # 提取股票代码 (Symbol) - 多种方法
            symbol = self._extract_symbol(row)
            if not symbol:
                logger.warning("未找到股票代码，跳过此行")
                return None
            stock_data['symbol'] = symbol
            
            # 提取股票价格 (Price) - 多种方法
            stock_data['price'] = self._extract_price(row)
            
            # 提取量化评级 (QuantRating) - 多种方法
            stock_data['quant_rating'] = self._extract_quant_rating(row)
            
            # 提取行业信息 (Sector&Industry) - 多种方法
            stock_data['sector_industry'] = self._extract_sector_industry(row)
            
            # 提取市值 - 多种方法
            stock_data['market_cap'] = self._extract_market_cap(row)
            
            return stock_data
            
        except Exception as e:
            logger.error(f"提取股票基础信息失败: {e}")
            return None
    
    def _extract_symbol(self, row) -> Optional[str]:
        """提取股票代码"""
        try:
            # 方法1: 通过data-test-id='top-rated-ticker-name'
            symbol_element = row.find('span', {'data-test-id': 'top-rated-ticker-name'})
            if symbol_element:
                symbol_span = symbol_element.find('span')
                if symbol_span:
                    return symbol_span.get_text(strip=True)
            
            # 方法2: 查找股票链接
            symbol_links = row.find_all('a', href=re.compile(r'/symbol/([A-Z]+)'))
            if symbol_links:
                href = symbol_links[0].get('href', '')
                match = re.search(r'/symbol/([A-Z]+)', href)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"提取股票代码失败: {e}")
            return None
    
    def _extract_price(self, row) -> str:
        """提取股票价格"""
        try:
            # 通过data-test-id='portfolio-ticker-price-price'
            price_div = row.find('div', {'data-test-id': 'portfolio-ticker-price-price'})
            if price_div:
                price_span = price_div.find('span')
                if price_span:
                    return price_span.get_text(strip=True)
            
            return 'N/A'
            
        except Exception as e:
            logger.warning(f"提取价格失败: {e}")
            return 'N/A'
    
    def _extract_quant_rating(self, row) -> str:
        """提取量化评级"""
        try:
            # 通过data-test-id='quant-badge'
            quant_badge = row.find('span', {'data-test-id': 'quant-badge'})
            if quant_badge:
                # 获取完整文本，然后提取数值部分
                full_text = quant_badge.get_text(strip=True)
                # 使用正则表达式提取数值 (如 4.99)
                import re
                match = re.search(r'(\d+\.\d+)$', full_text)
                if match:
                    return match.group(1)
                else:
                    # 如果没有匹配到，返回完整文本
                    return full_text
            
            return 'N/A'
            
        except Exception as e:
            logger.warning(f"提取量化评级失败: {e}")
            return 'N/A'
    
    def _extract_sector_industry(self, row) -> str:
        """提取行业信息"""
        try:
            # 通过data-test-id='portfolio-ticker-price-sectorIndustry'
            sector_div = row.find('div', {'data-test-id': 'portfolio-ticker-price-sectorIndustry'})
            if sector_div:
                sector_span = sector_div.find('span')
                if sector_span:
                    return sector_span.get_text(strip=True)
            
            return 'N/A'
            
        except Exception as e:
            logger.warning(f"提取行业信息失败: {e}")
            return 'N/A'
    
    def _extract_market_cap(self, row) -> str:
        """提取市值"""
        try:
            # 通过data-test-id='portfolio-ticker-price-market_cap'
            cap_div = row.find('div', {'data-test-id': 'portfolio-ticker-price-market_cap'})
            if cap_div:
                cap_span = cap_div.find('span')
                if cap_span:
                    return cap_span.get_text(strip=True)
            
            return 'N/A'
            
        except Exception as e:
            logger.warning(f"提取市值失败: {e}")
            return 'N/A'
    
    def extract_stock_detailed_info(self, symbol: str) -> Dict:
        """
        从股票量化评分页面提取详细信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含交易所信息和评级历史的字典
        """
        try:
            quant_url = self.quant_rating_url_template.format(symbol=symbol)
            logger.info(f"🔍 正在访问 {symbol} 的量化评分页面...")
            
            self.driver.get(quant_url)
            time.sleep(3)  # 简化的固定延时
            
            # 获取连续Strong Buy评级天数
            consecutive_strong_buy_days = self._get_consecutive_strong_buy_days(symbol)
            
            # 获取交易所信息
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            detailed_info = {
                'symbol': symbol,
                'exchange': self._extract_exchange_info(soup),
                'consecutive_strong_buy_days': consecutive_strong_buy_days
            }
            
            logger.info(f"✅ 成功提取 {symbol} 的详细信息")
            return detailed_info
            
        except Exception as e:
            logger.error(f"❌ 提取 {symbol} 详细信息失败: {e}")
            return {
                'symbol': symbol,
                'exchange': 'Error',
                'consecutive_strong_buy_days': 0
            }
    
    def _extract_exchange_info(self, soup) -> str:
        """提取交易所信息"""
        try:
            # 查找包含交易所信息的元素
            exchange_patterns = [
                {'selector': 'span', 'text_contains': ['NASDAQ', 'NYSE', 'AMEX', 'OTCQX', 'OTC']},
                {'selector': 'div[data-test-id*="exchange"]'},
                {'selector': '.exchange-info'},
            ]
            
            for pattern in exchange_patterns:
                if 'text_contains' in pattern:
                    elements = soup.find_all(pattern['selector'])
                    for element in elements:
                        text = element.get_text(strip=True).upper()
                        for exchange in pattern['text_contains']:
                            if exchange in text:
                                # 特殊处理OTCQX
                                if 'OTCQX' in text or 'OTC' in text:
                                    return 'OTCQX'
                                return exchange
                else:
                    element = soup.select_one(pattern['selector'])
                    if element:
                        return element.get_text(strip=True)
            
            # 如果没有找到，尝试从页面文本中提取
            page_text = soup.get_text().upper()
            for exchange in ['OTCQX', 'NASDAQ', 'NYSE', 'AMEX']:
                if exchange in page_text:
                    return exchange
            
            return 'Unknown'
            
        except Exception as e:
            logger.warning(f"提取交易所信息失败: {e}")
            return 'Error'
    
    def _get_consecutive_strong_buy_days(self, symbol: str) -> int:
        """
        计算从最近交易日开始连续保持Strong Buy评级的天数
        
        Args:
            symbol: 股票代码
            
        Returns:
            连续Strong Buy的天数
        """
        try:
            logger.info(f"📊 开始计算 {symbol} 的连续Strong Buy天数...")
            
            # 等待页面完全加载
            wait = WebDriverWait(self.driver, 10)
            
            # 查找评级历史表格
            table_selector = "table"
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, table_selector)))
            
            # 先滚动加载完整的评级历史数据
            logger.info("开始滚动加载完整的评级历史数据...")
            self._scroll_to_load_rating_history()
            
            # 加载完成后，获取最终的评级数据并计算连续Strong Buy天数
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            consecutive_days = self._count_consecutive_strong_buy_from_table(soup)
            logger.info(f"数据加载完成，计算得出连续Strong Buy天数: {consecutive_days}")
            
            logger.info(f"✅ {symbol} 连续Strong Buy天数: {consecutive_days}")
            return consecutive_days
            
        except Exception as e:
            logger.error(f"❌ 计算连续Strong Buy天数失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _scroll_to_load_rating_history(self):
        """
        滚动页面加载完整的180个交易日评级历史数据
        """
        try:
            previous_row_count = 0
            stable_count = 0
            max_stable_attempts = 8  # 连续8次没变化就停止
            scroll_pause_time = 0.8  # 每次滚动后等待时间
            max_scrolls = 50  # 最多滚动50次
            scroll_count = 0
            target_days = 75  # 目标加载75个交易日
            
            logger.info(f"开始滚动加载评级历史数据，目标: {target_days}个交易日")
            
            while stable_count < max_stable_attempts and scroll_count < max_scrolls:
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
                # 检查当前数据行数
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                current_row_count = self._count_rating_rows(soup)
                
                if current_row_count > previous_row_count:
                    logger.info(f"已加载 {current_row_count} 条评级记录")
                    previous_row_count = current_row_count
                    stable_count = 0
                    
                    # 如果已经加载了足够的数据，可以提前停止
                    if current_row_count >= target_days:
                        logger.info(f"已加载 {current_row_count} 条记录，达到目标天数")
                        break
                else:
                    stable_count += 1
                    logger.info(f"数据未增加，稳定次数: {stable_count}/{max_stable_attempts}")
                
                scroll_count += 1
                
                # 备用滚动策略：多次小幅滚动
                if stable_count >= 3:
                    logger.info("尝试备用滚动策略...")
                    for i in range(3):
                        self.driver.execute_script("window.scrollBy(0, 800);")
                        time.sleep(0.3)
            
            final_count = self._count_rating_rows(BeautifulSoup(self.driver.page_source, 'html.parser'))
            logger.info(f"滚动完成，最终加载了 {final_count} 条评级记录")
            
        except Exception as e:
            logger.error(f"滚动加载评级历史失败: {e}")
    
    def _count_rating_rows(self, soup) -> int:
        """计算当前页面中评级历史的行数"""
        try:
            total_rows = 0
            
            # 查找所有表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                # 跳过表头，计算数据行
                data_rows = 0
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # 确保有足够的列
                        data_rows += 1
                
                if data_rows > total_rows:
                    total_rows = data_rows
            
            return total_rows
            
        except Exception as e:
            logger.error(f"计算评级行数失败: {e}")
            return 0
    
    def _count_consecutive_strong_buy_from_table(self, soup) -> int:
        """
        从当前页面表格中计算连续Strong Buy天数
        """
        try:
            consecutive_count = 0
            
            # 查找包含评级历史的表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # 跳过表头行，从最新的数据开始计数
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:  # 确保有足够的列：日期、价格、评级等
                        try:
                            # 提取评级（通常在第3列）
                            rating_cell = cells[2] if len(cells) > 2 else None
                            rating_text = 'N/A'
                            
                            if rating_cell:
                                # 查找评级文本，可能在span或其他元素中
                                rating_span = rating_cell.find('span')
                                if rating_span:
                                    rating_text = rating_span.get_text(strip=True)
                                else:
                                    rating_text = rating_cell.get_text(strip=True)
                            
                            # 检查是否为Strong Buy
                            if 'STRONG BUY' in rating_text.upper():
                                consecutive_count += 1
                            else:
                                # 一旦遇到非Strong Buy，就停止计数
                                break
                        
                        except Exception as e:
                            logger.warning(f"解析评级行失败: {e}")
                            break
                
                # 如果找到了数据，就返回结果
                if consecutive_count > 0:
                    break
            
            return consecutive_count
            
        except Exception as e:
            logger.error(f"从表格计算连续Strong Buy天数失败: {e}")
            return 0
    
    def analyze_stocks(self) -> List[Dict]:
        """
        分析股票的完整流程（简化版）
        
        Returns:
            包含完整分析数据的股票列表
        """
        try:
            if not self.setup_driver():
                return []
            
            # 1. 检查是否有未完成的任务
            progress = self.progress_manager.load_progress()
            
            if progress:
                processed_symbols = set(progress['processed_symbols'])
                complete_stocks_data = progress['results']
                logger.info(f"🔄 继续之前的任务，已处理 {len(processed_symbols)} 只股票")
                
                # 需要重新获取股票列表以获取剩余未处理的股票
                basic_stocks_data = self.extract_my_alpha_picker_data()
            else:
                processed_symbols = set()
                complete_stocks_data = []
                
                # 2. 获取MyAlphaPicker列表的基础数据（只访问一次）
                logger.info("=== 第一步：获取股票筛选列表 ===")
                basic_stocks_data = self.extract_my_alpha_picker_data()
                
                if not basic_stocks_data:
                    logger.error("未获取到任何股票数据")
                    return []
            
            # 3. 获取每只股票的详细信息（简化版）
            logger.info("=== 第二步：获取详细量化评分信息 ===")
            
            for i, stock in enumerate(basic_stocks_data):
                symbol = stock['symbol']
                
                # 跳过已处理的股票
                if symbol in processed_symbols:
                    continue
                
                try:
                    # 简化的固定延时
                    delay = 2.0
                    logger.info(f"📊 处理 {symbol} ({len(complete_stocks_data)+1}/{len(basic_stocks_data)}) - 延时{delay:.1f}秒")
                    time.sleep(delay)
                    
                    # 获取详细信息
                    detailed_info = self.extract_stock_detailed_info(symbol)
                    
                    # 合并基础信息和详细信息
                    complete_stock_data = {**stock, **detailed_info}
                    complete_stocks_data.append(complete_stock_data)
                    processed_symbols.add(symbol)
                    
                    # 每处理10只股票保存一次进度
                    if len(processed_symbols) % 10 == 0:
                        self.progress_manager.save_progress(
                            list(processed_symbols), 
                            complete_stocks_data
                        )
                    
                except KeyboardInterrupt:
                    logger.info("🛑 用户中断，保存当前进度...")
                    self.progress_manager.save_progress(
                        list(processed_symbols), 
                        complete_stocks_data
                    )
                    raise
                    
                except Exception as e:
                    logger.error(f"❌ 处理 {symbol} 失败: {e}")
                    continue
            
            # 4. 清理进度文件
            self.progress_manager.cleanup()
            
            logger.info(f"✅ 完成分析，共处理 {len(complete_stocks_data)} 只股票")
            return complete_stocks_data
            
        except KeyboardInterrupt:
            logger.info("用户中断分析")
            raise
        except Exception as e:
            logger.error(f"❌ 股票分析失败: {e}")
            return []
    
    def save_results_to_csv(self, stocks_data: List[Dict], filename: str = None):
        """保存分析结果到CSV文件（简化版）"""
        try:
            if not stocks_data:
                logger.warning("没有数据可保存")
                return
            
            if filename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"stock_analysis_simplified_{timestamp}.csv"
            
            # 准备CSV数据
            csv_data = []
            for stock in stocks_data:
                # 基础信息 + 连续Strong Buy天数
                row = {
                    'Symbol': stock.get('symbol', 'N/A'),
                    'Price': stock.get('price', 'N/A'),
                    'QuantRating': stock.get('quant_rating', 'N/A'),
                    'SectorIndustry': stock.get('sector_industry', 'N/A'),
                    'MarketCap': stock.get('market_cap', 'N/A'),
                    'Exchange': stock.get('exchange', 'N/A'),
                    'ConsecutiveStrongBuyDays': stock.get('consecutive_strong_buy_days', 0)
                }
                
                csv_data.append(row)
            
            # 保存到CSV
            df = pd.DataFrame(csv_data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 分析结果已保存到: {filename}")
            
            # 打印统计信息
            self._print_simple_summary(stocks_data)
            
        except Exception as e:
            logger.error(f"❌ 保存CSV文件失败: {e}")
    
    def _print_simple_summary(self, stocks_data: List[Dict]):
        """打印简化的分析摘要"""
        try:
            logger.info("\\n=== 📊 分析摘要 ===")
            logger.info(f"总处理股票数: {len(stocks_data)}")
            
            # 统计交易所分布
            exchanges = {}
            strong_buy_stats = []
            
            for stock in stocks_data:
                exchange = stock.get('exchange', 'Unknown')
                exchanges[exchange] = exchanges.get(exchange, 0) + 1
                
                # 收集连续Strong Buy天数
                consecutive_days = stock.get('consecutive_strong_buy_days', 0)
                strong_buy_stats.append(consecutive_days)
            
            logger.info("交易所分布:")
            for exchange, count in exchanges.items():
                logger.info(f"  {exchange}: {count} 只")
            
            # 统计连续Strong Buy天数
            if strong_buy_stats:
                max_days = max(strong_buy_stats)
                avg_days = sum(strong_buy_stats) / len(strong_buy_stats)
                stocks_with_strong_buy = len([d for d in strong_buy_stats if d > 0])
                
                logger.info("连续Strong Buy统计:")
                logger.info(f"  最长连续天数: {max_days} 天")
                logger.info(f"  平均连续天数: {avg_days:.1f} 天")
                logger.info(f"  有Strong Buy的股票: {stocks_with_strong_buy}/{len(stocks_data)} 只")
            
        except Exception as e:
            logger.warning(f"打印分析摘要失败: {e}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            # 注意：保持浏览器打开，不要关闭
            logger.info("分析完成，浏览器保持打开状态")


def main(test_mode=False, max_stocks=None):
    """主函数"""
    logger.info("🚀 启动简化股票分析器")
    
    analyzer = SimplifiedStockAnalyzer(test_mode=test_mode, max_stocks=max_stocks)
    
    try:
        # 执行股票分析
        stocks_data = analyzer.analyze_stocks()
        
        # 保存结果
        if stocks_data:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"my_alpha_picker_analysis_simplified_{timestamp}.csv"
            analyzer.save_results_to_csv(stocks_data, filename)
        else:
            logger.warning("未获取到任何股票数据")
        
    except KeyboardInterrupt:
        logger.info("用户中断分析")
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()


if __name__ == "__main__":
    # 生产模式：处理全部股票
    main(test_mode=False, max_stocks=None)