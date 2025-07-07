#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强股票分析器 - Enhanced Stock Analyzer

功能说明:
    1. 从SeekingAlpha MyAlphaPicker页面获取股票筛选列表
    2. 提取股票的Symbol、Price、QuantRating、Sector&Industry等基础信息
    3. 访问每只股票的量化评分详细页面获取交易所信息和评级历史
    4. 支持限制处理股票数量(测试时只处理前5只股票)
    5. 使用Chrome远程调试架构，复用登录状态

主要改进:
    - 清晰的功能分离和模块化设计
    - 结构化的数据提取和存储
    - 完善的错误处理和进度跟踪
    - 支持测试模式(仅处理前N只股票)
"""

import os
import time
import random
import logging
import pandas as pd
from typing import List, Dict, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from collections import deque
import json
# from multi_format_exporter import MultiFormatExporter  # 不再需要多格式导出

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AntiCrawlerManager:
    """反爬虫管理器"""
    
    def __init__(self):
        self.request_times = deque()     # 请求时间戳队列
        self.max_requests = 80           # SeekingAlpha限制
        self.reset_interval = 120        # 2分钟重置窗口(秒)
        self.batch_delay_threshold = 40  # 每40次增加延时
        self.current_requests = 0
        self.start_time = datetime.now()
        
        # 机器人检测相关
        self.bot_detection_count = 0     # 检测到机器人验证的次数
        self.adaptive_mode = False       # 是否启用自适应模式
        self.base_delay_multiplier = 1.0 # 延时倍数
        
        logger.info("🛡️ 反爬虫管理器已初始化 - 限制: 80次/2分钟")
    
    def record_request(self):
        """记录一次请求"""
        current_time = datetime.now()
        self.request_times.append(current_time)
        self.current_requests += 1
        
        # 检查是否需要批次延时
        if self.current_requests % self.batch_delay_threshold == 0 and self.current_requests > 0:
            batch_delay = random.uniform(10, 20)
            logger.info(f"🛡️ 达到{self.current_requests}次请求，批次延时: {batch_delay:.1f}秒")
            time.sleep(batch_delay)
    
    def detect_bot_verification(self, driver) -> bool:
        """
        检测当前页面是否触发了机器人验证
        
        Args:
            driver: Selenium WebDriver实例
            
        Returns:
            是否检测到机器人验证
        """
        try:
            # 获取当前页面标题和URL
            current_url = driver.current_url.lower()
            page_title = driver.title.lower()
            
            # 检测常见的机器人验证指标
            bot_indicators = [
                # URL指标
                'captcha' in current_url,
                'verify' in current_url,
                'challenge' in current_url,
                'robot' in current_url,
                'security' in current_url,
                
                # 标题指标
                'verify' in page_title,
                'security' in page_title,
                'access denied' in page_title,
                'blocked' in page_title,
                'captcha' in page_title,
                'human verification' in page_title,
            ]
            
            # 检测页面内容指标
            try:
                page_source = driver.page_source.lower()
                content_indicators = [
                    'please verify you are human' in page_source,
                    'captcha' in page_source,
                    'access denied' in page_source,
                    'blocked' in page_source,
                    'security check' in page_source,
                    'verify you are not a robot' in page_source,
                    'cloudflare' in page_source and 'checking' in page_source,
                    'just a moment' in page_source and 'verifying' in page_source,
                ]
                bot_indicators.extend(content_indicators)
            except:
                # 如果无法获取页面源码，跳过内容检测
                pass
            
            # 检测特定元素
            try:
                # 常见的验证码或机器人检测元素
                verification_selectors = [
                    "[id*='captcha']",
                    "[class*='captcha']",
                    "[id*='challenge']",
                    "[class*='challenge']",
                    "[id*='verify']",
                    "[class*='verify']",
                    "iframe[src*='captcha']",
                    "iframe[src*='recaptcha']",
                ]
                
                for selector in verification_selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        bot_indicators.append(True)
                        break
                        
            except Exception:
                # 如果元素查找失败，跳过
                pass
            
            # 如果任何指标为True，则检测到机器人验证
            detected = any(bot_indicators)
            
            if detected:
                self.bot_detection_count += 1
                logger.warning(f"🤖 检测到机器人验证！(第{self.bot_detection_count}次)")
                logger.warning(f"   URL: {current_url}")
                logger.warning(f"   标题: {page_title}")
                
                # 保存验证页面截图用于调试
                try:
                    timestamp = int(time.time())
                    screenshot_path = f"bot_detection_screenshot_{timestamp}.png"
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"📸 已保存验证页面截图: {screenshot_path}")
                except:
                    pass
            
            return detected
            
        except Exception as e:
            logger.warning(f"机器人检测失败: {e}")
            return False
    
    def handle_bot_detection(self):
        """处理机器人检测触发后的算法调整"""
        try:
            # 启用自适应模式
            self.adaptive_mode = True
            
            # 根据检测次数调整参数
            if self.bot_detection_count == 1:
                # 第一次检测：降低请求频率
                self.base_delay_multiplier = 2.0
                self.max_requests = 40  # 降低到40次
                self.batch_delay_threshold = 20  # 每20次延时
                logger.info("🔧 算法调整 Level 1: 延时x2, 限制40次, 每20次批次延时")
                
            elif self.bot_detection_count == 2:
                # 第二次检测：进一步降低频率
                self.base_delay_multiplier = 3.0
                self.max_requests = 20  # 降低到20次
                self.batch_delay_threshold = 10  # 每10次延时
                logger.info("🔧 算法调整 Level 2: 延时x3, 限制20次, 每10次批次延时")
                
            elif self.bot_detection_count >= 3:
                # 第三次及以上：极保守模式
                self.base_delay_multiplier = 5.0
                self.max_requests = 10  # 降低到10次
                self.batch_delay_threshold = 5   # 每5次延时
                logger.info("🔧 算法调整 Level 3: 延时x5, 限制10次, 每5次批次延时")
            
            # 立即等待一段时间
            wait_time = 300 + (self.bot_detection_count * 120)  # 5-15分钟
            logger.warning(f"⏳ 机器人检测触发，等待 {wait_time//60} 分钟...")
            time.sleep(wait_time)
            
            # 重置请求计数
            self.current_requests = 0
            self.request_times.clear()
            
            logger.info("✅ 等待完成，算法已调整，继续执行")
            
        except Exception as e:
            logger.error(f"处理机器人检测失败: {e}")
    
    def get_smart_delay(self) -> float:
        """获取智能延时时间（自适应版本）"""
        # 基础延时计算
        if self.current_requests <= 200:
            base_delay = random.uniform(1.5, 3.0)  # 基础延时
        elif self.current_requests <= 400:
            base_delay = random.uniform(3.0, 5.0)  # 中等延时
        elif self.current_requests <= 600:
            base_delay = random.uniform(5.0, 8.0)  # 较长延时
        else:
            base_delay = random.uniform(8.0, 12.0) # 临界延时
        
        # 应用自适应倍数
        adjusted_delay = base_delay * self.base_delay_multiplier
        
        # 如果处于自适应模式，额外增加随机延时
        if self.adaptive_mode:
            extra_delay = random.uniform(2.0, 8.0)
            adjusted_delay += extra_delay
        
        return adjusted_delay
    
    def check_and_reset(self):
        """检查请求数量并在必要时重置"""
        if self.current_requests >= self.max_requests:
            logger.warning(f"⚠️ 达到{self.max_requests}次请求限制，等待2分钟重置...")
            time.sleep(self.reset_interval)
            self.current_requests = 0
            self.request_times.clear()
            logger.info("✅ 请求计数器已重置")
    
    def get_status(self) -> str:
        """获取当前状态信息"""
        elapsed = datetime.now() - self.start_time
        status = f"请求数: {self.current_requests}/{self.max_requests}, 运行时间: {elapsed}"
        
        if self.adaptive_mode:
            status += f", 自适应模式: x{self.base_delay_multiplier:.1f}, 检测次数: {self.bot_detection_count}"
        
        return status


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, filename="stock_analysis_progress.json"):
        self.progress_file = filename
        
    def save_progress(self, processed_symbols: List[str], results: List[Dict], request_count: int):
        """保存当前进度"""
        try:
            progress_data = {
                'timestamp': datetime.now().isoformat(),
                'processed_count': len(processed_symbols),
                'processed_symbols': processed_symbols,
                'results': results,
                'request_count': request_count
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


class EnhancedStockAnalyzer:
    """增强的股票分析器"""
    
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
        
        # 反爬虫和进度管理
        self.anti_crawler = AntiCrawlerManager()
        self.progress_manager = ProgressManager()
        
        # URL配置
        self.my_alpha_picker_url = "https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker"
        self.quant_rating_url_template = "https://seekingalpha.com/symbol/{symbol}/ratings/quant-ratings"
        
        if max_stocks is None:
            logger.info(f"初始化增强股票分析器 - 处理模式: {'测试' if test_mode else '生产'}, 股票数: 全部")
        else:
            logger.info(f"初始化增强股票分析器 - 处理模式: {'测试' if test_mode else '生产'}, 最大股票数: {max_stocks}")
    
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
            time.sleep(1)
            
            # 检查页面是否需要登录
            if "login" in self.driver.current_url.lower():
                logger.warning("需要登录SeekingAlpha账户")
                return []
            

            # # 检测是否触发机器人验证
            # if hasattr(self, 'anti_crawler') and self.anti_crawler.detect_bot_verification(self.driver):
            #     logger.warning("🤖 MyAlphaPicker页面触发机器人验证")
            #     self.anti_crawler.handle_bot_detection()
            #     # 重新尝试访问
            #     return self.extract_my_alpha_picker_data()
            

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
            scroll_pause_time = 0.5  # 每次滚动后等待时间（给页面充分时间加载）
            
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
                        
                        # 策略1: 多次小幅滚动
                        for i in range(5):
                            self.driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(0.1)
                        
                        # # 策略2: 按键滚动
                        # try:
                        #     from selenium.webdriver.common.keys import Keys
                        #     body = self.driver.find_element(By.TAG_NAME, "body")
                        #     body.send_keys(Keys.END)
                        #     time.sleep(1)
                        #     body.send_keys(Keys.PAGE_DOWN)
                        #     time.sleep(1)
                        # except:
                        #     pass
                        
                        # # 策略3: 尝试滚动表格容器
                        # try:
                        #     table_selectors = [
                        #         "[data-test-id='screener-table']",
                        #         ".screener-table", 
                        #         "table",
                        #         "[data-testid='screener-table']"
                        #     ]
                            
                        #     for selector in table_selectors:
                        #         try:
                        #             element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        #             self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
                        #             time.sleep(1)
                        #             break
                        #         except:
                        #             continue
                        # except:
                        #     pass
                        
                        # # 增加等待时间，给页面更多时间加载
                        # time.sleep(2)
            
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
            
            # 不需要公司名称字段
            
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
            time.sleep(3)  # 等待页面加载
            
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
    
    def _extract_rating_history(self, soup) -> List[Dict]:
        """提取评级历史"""
        try:
            rating_history = []
            
            # 查找评级历史表格
            tables = soup.find_all('table')
            
            for table in tables:
                # 检查是否为评级历史表格
                headers = table.find_all('th')
                header_texts = [th.get_text(strip=True).lower() for th in headers]
                
                if any('date' in header and 'rating' in header_texts for header in header_texts):
                    # 找到评级历史表格
                    rows = table.find_all('tr')[1:]  # 跳过表头
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            date_text = cells[0].get_text(strip=True)
                            rating_text = cells[1].get_text(strip=True)
                            
                            # 提取分数（如果有）
                            score = None
                            if len(cells) >= 3:
                                score_text = cells[2].get_text(strip=True)
                                score = self._extract_score(score_text)
                            
                            rating_history.append({
                                'date': date_text,
                                'rating': rating_text,
                                'score': score
                            })
            
            # 如果表格方法失败，尝试其他方法
            if not rating_history:
                rating_history = self._extract_rating_history_alternative(soup)
            
            logger.info(f"提取到 {len(rating_history)} 条评级历史记录")
            return rating_history
            
        except Exception as e:
            logger.warning(f"提取评级历史失败: {e}")
            return []
    
    def _extract_rating_history_alternative(self, soup) -> List[Dict]:
        """备用方法提取评级历史"""
        try:
            rating_history = []
            
            # 查找包含日期和评级的元素
            date_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}')
            rating_pattern = re.compile(r'(Strong Buy|Buy|Hold|Sell|Strong Sell)', re.IGNORECASE)
            
            # 遍历所有文本元素
            text_elements = soup.find_all(text=True)
            
            for i, text in enumerate(text_elements):
                date_match = date_pattern.search(text)
                if date_match:
                    # 在附近查找评级
                    context_range = 5  # 前后5个元素的范围
                    start_idx = max(0, i - context_range)
                    end_idx = min(len(text_elements), i + context_range + 1)
                    
                    for j in range(start_idx, end_idx):
                        rating_match = rating_pattern.search(text_elements[j])
                        if rating_match:
                            rating_history.append({
                                'date': date_match.group(),
                                'rating': rating_match.group(),
                                'score': None
                            })
                            break
            
            return rating_history
            
        except Exception as e:
            logger.warning(f"备用评级历史提取失败: {e}")
            return []
    
    def _extract_score(self, score_text: str) -> Optional[float]:
        """从文本中提取数值分数"""
        try:
            # 移除非数字字符，保留小数点
            clean_text = re.sub(r'[^\d.]', '', score_text)
            if clean_text:
                return float(clean_text)
            return None
        except:
            return None
    
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
            
            # 先滚动加载完整的180天评级历史数据
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
            scroll_pause_time = 0.5  # 每次滚动后等待时间
            max_scrolls = 50  # 最多滚动50次，确保加载180天数据
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
        """
        计算当前页面中评级历史的行数
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            评级历史行数
        """
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
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            连续Strong Buy的天数
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
    
    def _found_rating_change_point(self, soup) -> bool:
        """
        检查是否找到了评级变化点（从Strong Buy变为其他评级）
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            是否找到评级变化点
        """
        try:
            # 查找包含评级历史的表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                found_strong_buy = False
                
                # 跳过表头行
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        try:
                            # 提取评级
                            rating_cell = cells[2] if len(cells) > 2 else None
                            rating_text = 'N/A'
                            
                            if rating_cell:
                                rating_span = rating_cell.find('span')
                                if rating_span:
                                    rating_text = rating_span.get_text(strip=True)
                                else:
                                    rating_text = rating_cell.get_text(strip=True)
                            
                            if 'STRONG BUY' in rating_text.upper():
                                found_strong_buy = True
                            elif found_strong_buy:
                                # 已经找到Strong Buy，现在遇到其他评级，说明找到变化点
                                return True
                        
                        except Exception:
                            continue
                
                # 如果在这个表格中找到了数据，就结束
                if found_strong_buy:
                    break
            
            return False
            
        except Exception as e:
            logger.error(f"检查评级变化点失败: {e}")
            return False
    
    def _extract_rating_history_from_table(self, soup) -> List[Dict]:
        """
        从表格中提取评级历史数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            评级历史列表
        """
        try:
            rating_history = []
            
            # 查找包含评级历史的表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # 跳过表头行
                for i, row in enumerate(rows[1:], 1):
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:  # 确保有足够的列：日期、评级、分数等
                        try:
                            # 提取日期
                            date_cell = cells[0]
                            date_text = date_cell.get_text(strip=True)
                            
                            # 提取价格
                            price_cell = cells[1] if len(cells) > 1 else None
                            price_text = price_cell.get_text(strip=True) if price_cell else 'N/A'
                            
                            # 提取评级
                            rating_cell = cells[2] if len(cells) > 2 else None
                            rating_text = 'N/A'
                            if rating_cell:
                                # 查找评级文本，可能在span或其他元素中
                                rating_span = rating_cell.find('span')
                                if rating_span:
                                    rating_text = rating_span.get_text(strip=True)
                                else:
                                    rating_text = rating_cell.get_text(strip=True)
                            
                            # 提取分数
                            score_cell = cells[3] if len(cells) > 3 else None
                            score_text = 'N/A'
                            if score_cell:
                                score_span = score_cell.find('span')
                                if score_span:
                                    score_text = score_span.get_text(strip=True)
                                else:
                                    score_text = score_cell.get_text(strip=True)
                            
                            # 清理和验证数据
                            if date_text and self._is_valid_date(date_text):
                                rating_history.append({
                                    'date': date_text,
                                    'price': price_text,
                                    'rating': rating_text,
                                    'score': score_text,
                                    'row_index': i
                                })
                        
                        except Exception as e:
                            logger.warning(f"解析第 {i} 行数据失败: {e}")
                            continue
            
            return rating_history
            
        except Exception as e:
            logger.error(f"从表格提取评级历史失败: {e}")
            return []
    
    def _is_valid_date(self, date_text: str) -> bool:
        """验证日期格式是否有效"""
        try:
            # 检查常见的日期格式
            date_patterns = [
                r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
                r'^\d{1,2}/\d{1,2}/\d{4}$',  # M/D/YYYY
                r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            ]
            
            for pattern in date_patterns:
                if re.match(pattern, date_text.strip()):
                    return True
            
            return False
        except:
            return False
    
    def _calculate_rating_consistency(self, rating_history: List[Dict]) -> List[Dict]:
        """
        计算每个交易日的连续评级天数
        
        Args:
            rating_history: 评级历史列表
            
        Returns:
            包含连续评级天数的评级历史列表
        """
        try:
            if not rating_history:
                return []
            
            # 按日期排序（最新的在前）
            sorted_history = sorted(rating_history, 
                                  key=lambda x: self._parse_date(x['date']), 
                                  reverse=True)
            
            # 计算连续评级天数
            for i, record in enumerate(sorted_history):
                current_rating = record['rating']
                consecutive_days = 1
                
                # 向后查找相同评级的连续天数
                for j in range(i + 1, len(sorted_history)):
                    if sorted_history[j]['rating'] == current_rating:
                        consecutive_days += 1
                    else:
                        break
                
                record['consecutive_days'] = consecutive_days
                record['position_from_latest'] = i + 1
            
            logger.info(f"✅ 完成 {len(sorted_history)} 条记录的连续评级天数计算")
            return sorted_history
            
        except Exception as e:
            logger.error(f"计算连续评级天数失败: {e}")
            return rating_history
    
    def _parse_date(self, date_str: str):
        """解析日期字符串为可比较的格式"""
        try:
            from datetime import datetime
            
            # 尝试不同的日期格式
            date_formats = [
                '%m/%d/%Y',    # MM/DD/YYYY
                '%m/%d/%y',    # MM/DD/YY
                '%Y-%m-%d',    # YYYY-MM-DD
                '%d/%m/%Y',    # DD/MM/YYYY
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            # 如果所有格式都失败，返回一个默认值
            return datetime.min
            
        except Exception:
            return datetime.min
    
    def _analyze_rating_consistency(self, rating_history: List[Dict]) -> Dict:
        """
        分析评级一致性和连续性
        
        Args:
            rating_history: 评级历史列表
            
        Returns:
            评级分析结果字典
        """
        try:
            if not rating_history:
                return {}
            
            # 统计评级分布
            rating_counts = {}
            total_days = len(rating_history)
            
            for record in rating_history:
                rating = record.get('rating', 'Unknown')
                rating_counts[rating] = rating_counts.get(rating, 0) + 1
            
            # 计算最长连续评级
            max_consecutive = 0
            current_consecutive = 1
            current_rating = rating_history[0].get('rating') if rating_history else None
            
            for i in range(1, len(rating_history)):
                if rating_history[i].get('rating') == current_rating:
                    current_consecutive += 1
                else:
                    max_consecutive = max(max_consecutive, current_consecutive)
                    current_consecutive = 1
                    current_rating = rating_history[i].get('rating')
            
            max_consecutive = max(max_consecutive, current_consecutive)
            
            # 当前评级连续天数
            current_rating_streak = rating_history[0].get('consecutive_days', 0) if rating_history else 0
            
            analysis = {
                'total_days': total_days,
                'rating_distribution': rating_counts,
                'max_consecutive_days': max_consecutive,
                'current_rating': current_rating,
                'current_rating_streak': current_rating_streak,
                'most_common_rating': max(rating_counts, key=rating_counts.get) if rating_counts else 'Unknown'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析评级一致性失败: {e}")
            return {}
    
    def _clean_numeric_value(self, value_text: str) -> str:
        """清理数值文本"""
        if not value_text:
            return 'N/A'
        
        # 移除货币符号和多余空格
        cleaned = re.sub(r'[$\s]', '', value_text.strip())
        return cleaned if cleaned else 'N/A'
    
    def analyze_stocks(self) -> List[Dict]:
        """
        分析股票的完整流程（带反爬虫保护）
        
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
                self.anti_crawler.current_requests = progress.get('request_count', 0)
                logger.info(f"🔄 继续之前的任务，已处理 {len(processed_symbols)} 只股票")
                
                # 需要重新获取股票列表以获取剩余未处理的股票
                basic_stocks_data = self.extract_my_alpha_picker_data()
                self.anti_crawler.record_request()  # 记录MyAlphaPicker访问
            else:
                processed_symbols = set()
                complete_stocks_data = []
                
                # 2. 获取MyAlphaPicker列表的基础数据（只访问一次）
                logger.info("=== 第一步：获取股票筛选列表 ===")
                basic_stocks_data = self.extract_my_alpha_picker_data()
                self.anti_crawler.record_request()  # 记录MyAlphaPicker访问
                
                if not basic_stocks_data:
                    logger.error("未获取到任何股票数据")
                    return []
            
            # 3. 获取每只股票的详细信息（带反爬虫保护）
            logger.info("=== 第二步：获取详细量化评分信息 ===")
            
            for i, stock in enumerate(basic_stocks_data):
                symbol = stock['symbol']
                
                # 跳过已处理的股票
                if symbol in processed_symbols:
                    continue
                
                try:
                    # 检查请求限制并在必要时重置
                    self.anti_crawler.check_and_reset()
                    
                    # 智能延时
                    delay = self.anti_crawler.get_smart_delay()
                    status = self.anti_crawler.get_status()
                    logger.info(f"📊 处理 {symbol} ({len(complete_stocks_data)+1}/{len(basic_stocks_data)}) - 延时{delay:.1f}秒 [{status}]")
                    time.sleep(delay)
                    
                    # 获取详细信息
                    detailed_info = self.extract_stock_detailed_info(symbol)
                    self.anti_crawler.record_request()  # 记录详情页面访问
                    
                    # # 检测是否触发机器人验证
                    # if self.anti_crawler.detect_bot_verification(self.driver):
                    #     # 处理机器人检测
                    #     self.anti_crawler.handle_bot_detection()
                    #     
                    #     # 保存当前进度
                    #     self.progress_manager.save_progress(
                    #         list(processed_symbols), 
                    #         complete_stocks_data, 
                    #         self.anti_crawler.current_requests
                    #     )
                    #     
                    #     # 重新尝试当前股票
                    #     logger.info(f"🔄 重新尝试处理 {symbol}...")
                    #     continue
                    
                    # 合并基础信息和详细信息
                    complete_stock_data = {**stock, **detailed_info}
                    complete_stocks_data.append(complete_stock_data)
                    processed_symbols.add(symbol)
                    
                    # 每处理10只股票保存一次进度
                    if len(processed_symbols) % 10 == 0:
                        self.progress_manager.save_progress(
                            list(processed_symbols), 
                            complete_stocks_data, 
                            self.anti_crawler.current_requests
                        )
                    
                except KeyboardInterrupt:
                    logger.info("🛑 用户中断，保存当前进度...")
                    self.progress_manager.save_progress(
                        list(processed_symbols), 
                        complete_stocks_data, 
                        self.anti_crawler.current_requests
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
                filename = f"stock_analysis_with_strong_buy_days_{timestamp}.csv"
            
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
    
    def _save_detailed_rating_history(self, stocks_data: List[Dict], main_filename: str):
        """保存详细的评级历史到单独的CSV文件"""
        try:
            # 创建详细评级历史文件名
            base_name = main_filename.replace('.csv', '')
            detailed_filename = f"{base_name}_detailed_history.csv"
            
            detailed_data = []
            
            for stock in stocks_data:
                symbol = stock.get('symbol', 'Unknown')
                rating_history = stock.get('rating_history', [])
                
                for record in rating_history:
                    detailed_data.append({
                        'Symbol': symbol,
                        'Date': record.get('date', 'N/A'),
                        'Price': record.get('price', 'N/A'),
                        'Rating': record.get('rating', 'N/A'),
                        'Score': record.get('score', 'N/A'),
                        'ConsecutiveDays': record.get('consecutive_days', 'N/A'),
                        'PositionFromLatest': record.get('position_from_latest', 'N/A')
                    })
            
            if detailed_data:
                df_detailed = pd.DataFrame(detailed_data)
                df_detailed.to_csv(detailed_filename, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 详细评级历史已保存到: {detailed_filename}")
            
        except Exception as e:
            logger.error(f"❌ 保存详细评级历史失败: {e}")
    
    def _print_analysis_summary(self, stocks_data: List[Dict]):
        """打印分析摘要"""
        try:
            logger.info("\n=== 📊 分析摘要 ===")
            logger.info(f"总处理股票数: {len(stocks_data)}")
            
            # 统计交易所分布
            exchanges = {}
            for stock in stocks_data:
                exchange = stock.get('exchange', 'Unknown')
                exchanges[exchange] = exchanges.get(exchange, 0) + 1
            
            logger.info("交易所分布:")
            for exchange, count in exchanges.items():
                logger.info(f"  {exchange}: {count} 只")
            
            # 统计评级分布
            latest_ratings = {}
            for stock in stocks_data:
                rating_history = stock.get('rating_history', [])
                if rating_history:
                    latest_rating = rating_history[-1].get('rating', 'Unknown')
                    latest_ratings[latest_rating] = latest_ratings.get(latest_rating, 0) + 1
            
            if latest_ratings:
                logger.info("最新评级分布:")
                for rating, count in latest_ratings.items():
                    logger.info(f"  {rating}: {count} 只")
            
        except Exception as e:
            logger.warning(f"打印分析摘要失败: {e}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            # 注意：保持浏览器打开，不要关闭
            logger.info("分析完成，浏览器保持打开状态")


def main(test_mode=False, max_stocks=None):
    """主函数"""
    logger.info("🚀 启动增强股票分析器")
    
    analyzer = EnhancedStockAnalyzer(test_mode=test_mode, max_stocks=max_stocks)
    
    try:
        # 执行股票分析
        stocks_data = analyzer.analyze_stocks()
        
        # 保存结果
        if stocks_data:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"my_alpha_picker_analysis_{timestamp}.csv"
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