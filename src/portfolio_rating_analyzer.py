#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合评级分析器 - Portfolio Rating Analyzer

功能说明:
    1. 从SeekingAlpha投资组合页面获取持仓股票列表
    2. 访问每只股票的量化评分详细页面获取评级历史
    3. 计算每只股票连续Hold天数和连续Buy天数
    4. 生成详细的分析报告

基于 enhanced_stock_analyzer_simplified.py 的逻辑改进
"""

import os
import time
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
from datetime import datetime
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PortfolioProgressManager:
    """投资组合分析进度管理器"""
    
    def __init__(self, filename="portfolio_rating_progress.json"):
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


class PortfolioRatingAnalyzer:
    """投资组合评级分析器"""
    
    def __init__(self, portfolio_url: str, test_mode=False):
        """
        初始化分析器
        
        Args:
            portfolio_url: 投资组合URL
            test_mode: 是否为测试模式
        """
        self.portfolio_url = portfolio_url
        self.test_mode = test_mode
        self.driver = None
        
        # 进度管理
        self.progress_manager = PortfolioProgressManager()
        
        # URL模板
        self.quant_rating_url_template = "https://seekingalpha.com/symbol/{symbol}/ratings/quant-ratings"
        
        logger.info(f"初始化投资组合评级分析器 - 处理模式: {'测试' if test_mode else '生产'}")
        logger.info(f"投资组合URL: {portfolio_url}")
    
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
    
    def extract_portfolio_stocks(self) -> List[Dict]:
        """
        从投资组合页面提取需要分析的股票数据（仅Hold和Buy）
        
        Returns:
            需要分析的股票数据列表
        """
        try:
            logger.info("🔍 正在访问投资组合页面...")
            self.driver.get(self.portfolio_url)
            
            # 等待页面加载更长时间
            time.sleep(8)
            
            # 检查是否需要登录
            if "login" in self.driver.current_url.lower():
                logger.warning("需要登录SeekingAlpha账户")
                return []
            
            # 尝试等待动态内容加载
            wait = WebDriverWait(self.driver, 30)
            
            # 尝试等待股票数据加载
            logger.info("等待动态内容加载...")
            try:
                # 等待包含股票链接的元素
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/symbol/']")))
                logger.info("找到股票链接元素")
            except:
                logger.warning("未找到股票链接，继续尝试其他方法")
            
            # 等待JavaScript渲染和页面完全加载
            logger.info("等待页面完全加载...")
            
            # 检查页面状态
            logger.info(f"当前页面URL: {self.driver.current_url}")
            logger.info(f"页面标题: {self.driver.title}")
            
            # 使用显式等待来等待页面内容加载
            logger.info("等待页面内容加载...")
            max_wait_time = 60  # 最多等待60秒
            start_time = time.time()
            
            while (time.time() - start_time) < max_wait_time:
                # 检查页面是否有基本的内容结构
                if self.driver.execute_script("return document.body && document.body.children.length > 5"):
                    logger.info("页面基本结构已加载")
                    break
                    
                logger.info(f"页面仍在加载中... ({int(time.time() - start_time)}s)")
                time.sleep(5)
            
            # 等待额外时间让动态内容加载
            time.sleep(10)
            
            # 尝试页面交互来确保数据加载
            logger.info("尝试页面交互来触发数据加载...")
            
            # 滚动页面
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(3)
                
                # 尝试点击页面来激活
                self.driver.execute_script("document.body.click();")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"页面交互失败: {e}")
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 保存页面HTML用于调试
            debug_filename = f"debug_portfolio_{int(time.time())}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"已保存调试HTML: {debug_filename}")
            
            # 提取股票代码和评分信息
            stocks_data = self._extract_portfolio_stocks_with_ratings(soup)
            
            if not stocks_data:
                logger.error("未能提取到任何股票数据")
                return []
            
            # 按评级分类统计
            rating_stats = {}
            for stock in stocks_data:
                category = stock['rating_category']
                if category not in rating_stats:
                    rating_stats[category] = []
                rating_stats[category].append(stock['symbol'])
            
            # 打印统计信息
            logger.info("📊 投资组合评级分布:")
            for category, symbols in rating_stats.items():
                logger.info(f"  {category}: {len(symbols)}只 - {symbols[:5]}{'...' if len(symbols) > 5 else ''}")
            
            # 过滤出需要分析的股票（只有Hold和Buy）
            target_stocks = [stock for stock in stocks_data 
                           if stock['rating_category'] in ['Hold', 'Buy']]
            
            logger.info(f"🎯 需要分析连续天数的股票: {len(target_stocks)}只")
            for stock in target_stocks:
                logger.info(f"  {stock['symbol']} ({stock['rating_category']}: {stock['rating_score']})")
            
            logger.info(f"✅ 跳过StrongBuy股票: {len(rating_stats.get('StrongBuy', []))}只，提高处理效率")
            
            return target_stocks
            
        except Exception as e:
            logger.error(f"❌ 提取投资组合股票失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    def _extract_portfolio_stocks_with_ratings(self, soup) -> List[Dict]:
        """从投资组合页面提取股票代码和QuantRating评分"""
        try:
            stocks_data = []
            
            # 查找投资组合表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                if len(rows) > 1:  # 确保有数据行
                    header_row = rows[0]
                    header_text = header_row.get_text().lower()
                    
                    # 检查是否是投资组合表格
                    if any(keyword in header_text for keyword in ['symbol', 'quant rating', 'weight', 'value']):
                        logger.info("找到投资组合表格，开始解析股票和评分...")
                        
                        for row in rows[1:]:  # 跳过表头
                            cells = row.find_all(['td', 'th'])
                            
                            if len(cells) >= 3:  # 确保有足够的列
                                # 提取股票代码（通常在第一列）
                                symbol_cell = cells[0]
                                symbol_link = symbol_cell.find('a', href=re.compile(r'/symbol/([A-Z]+)'))
                                
                                if symbol_link:
                                    href = symbol_link.get('href', '')
                                    symbol_match = re.search(r'/symbol/([A-Z]+)', href)
                                    if symbol_match:
                                        symbol = symbol_match.group(1)
                                        
                                        # 查找QuantRating评分（通常在后面的列中）
                                        rating_score = None
                                        for cell in cells:
                                            # 查找带有评分样式的元素
                                            rating_elements = cell.find_all(['span', 'div'], 
                                                                          class_=re.compile(r'rating|score'))
                                            
                                            for elem in rating_elements:
                                                text = elem.get_text(strip=True)
                                                # 尝试解析数字评分
                                                try:
                                                    score = float(text)
                                                    if 0 <= score <= 5:  # QuantRating范围
                                                        rating_score = score
                                                        break
                                                except (ValueError, TypeError):
                                                    continue
                                            
                                            if rating_score is not None:
                                                break
                                        
                                        # 如果没找到评分，尝试从纯文本中提取
                                        if rating_score is None:
                                            for cell in cells:
                                                text = cell.get_text(strip=True)
                                                # 查找形如 "4.66" 的评分
                                                score_match = re.search(r'\b(\d+\.\d{1,2})\b', text)
                                                if score_match:
                                                    try:
                                                        score = float(score_match.group(1))
                                                        if 0 <= score <= 5:
                                                            rating_score = score
                                                            break
                                                    except (ValueError, TypeError):
                                                        continue
                                        
                                        # 确定评级类别
                                        rating_category = self._get_rating_category(rating_score)
                                        
                                        stocks_data.append({
                                            'symbol': symbol,
                                            'rating_score': rating_score,
                                            'rating_category': rating_category
                                        })
                        
                        # 如果找到了数据，退出表格循环
                        if stocks_data:
                            break
            
            logger.info(f"从投资组合中提取到 {len(stocks_data)} 只股票及其评分")
            return stocks_data
            
        except Exception as e:
            logger.error(f"提取股票数据失败: {e}")
            return []
    
    def _get_rating_category(self, score: Optional[float]) -> str:
        """根据QuantRating评分确定评级类别"""
        if score is None:
            return "Unknown"
        elif score >= 4.5:
            return "StrongBuy"
        elif score >= 3.5:
            return "Buy" 
        elif score >= 2.5:
            return "Hold"
        else:
            return "Sell"
    
    def _extract_stock_symbols_fallback(self, soup) -> List[str]:
        """备用的股票代码提取方法，更宽泛的搜索"""
        try:
            symbols = []
            
            # 方法1: 搜索所有包含'/symbol/'的链接
            symbol_links = soup.find_all('a', href=re.compile(r'/symbol/([A-Z]+)'))
            for link in symbol_links:
                href = link.get('href', '')
                match = re.search(r'/symbol/([A-Z]+)', href)
                if match:
                    symbol = match.group(1)
                    if symbol not in symbols and len(symbol) <= 5:  # 股票代码通常不超过5个字符
                        symbols.append(symbol)
            
            # 方法2: 在页面文本中查找可能的股票代码模式
            text_content = soup.get_text()
            # 查找独立的大写字母组合（2-5个字符）
            potential_symbols = re.findall(r'\b([A-Z]{2,5})\b', text_content)
            
            for symbol in potential_symbols:
                if symbol not in symbols and symbol not in [
                    'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF', 'SEK', 'NOK', 'DKK',
                    'API', 'FAQ', 'URL', 'HTML', 'CSS', 'JSON', 'XML', 'HTTP', 'HTTPS',
                    'COVID', 'NYSE', 'NASDAQ', 'ETF', 'IPO', 'CEO', 'CFO', 'CTO',
                    'TOTAL', 'CASH', 'ALL', 'NEW', 'OLD', 'BEST', 'TOP', 'VIEW'
                ]:
                    symbols.append(symbol)
            
            # 限制结果数量，避免过多误报
            symbols = symbols[:100]  # 最多100个
            
            logger.info(f"备用方法提取到 {len(symbols)} 个可能的股票代码: {symbols[:20]}{'...' if len(symbols) > 20 else ''}")
            return symbols
            
        except Exception as e:
            logger.error(f"备用股票代码提取失败: {e}")
            return []
    
    def analyze_stock_rating_history(self, symbol: str) -> Dict:
        """
        分析单只股票的评级历史，计算连续Hold和Buy天数
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含连续评级天数的字典
        """
        try:
            quant_url = self.quant_rating_url_template.format(symbol=symbol)
            logger.info(f"🔍 正在访问 {symbol} 的量化评分页面...")
            
            self.driver.get(quant_url)
            time.sleep(3)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
            
            # 滚动加载完整的评级历史数据
            logger.info("开始滚动加载完整的评级历史数据...")
            self._scroll_to_load_rating_history()
            
            # 解析评级历史并计算连续天数
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            consecutive_hold, consecutive_buy = self._calculate_consecutive_ratings(soup)
            
            result = {
                'symbol': symbol,
                'consecutive_hold_days': consecutive_hold,
                'consecutive_buy_days': consecutive_buy,
                'current_rating': self._get_current_rating(soup)
            }
            
            logger.info(f"✅ {symbol} - Hold: {consecutive_hold}天, Buy: {consecutive_buy}天")
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析 {symbol} 评级历史失败: {e}")
            return {
                'symbol': symbol,
                'consecutive_hold_days': 0,
                'consecutive_buy_days': 0,
                'current_rating': 'Error'
            }
    
    def _scroll_to_load_rating_history(self):
        """滚动页面加载完整的评级历史数据（复用原脚本逻辑）"""
        try:
            previous_row_count = 0
            stable_count = 0
            max_stable_attempts = 8
            scroll_pause_time = 0.8
            max_scrolls = 50
            scroll_count = 0
            target_days = 75
            
            logger.info(f"开始滚动加载评级历史数据，目标: {target_days}个交易日")
            
            while stable_count < max_stable_attempts and scroll_count < max_scrolls:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                current_row_count = self._count_rating_rows(soup)
                
                if current_row_count > previous_row_count:
                    logger.info(f"已加载 {current_row_count} 条评级记录")
                    previous_row_count = current_row_count
                    stable_count = 0
                    
                    if current_row_count >= target_days:
                        logger.info(f"已加载 {current_row_count} 条记录，达到目标天数")
                        break
                else:
                    stable_count += 1
                    logger.info(f"数据未增加，稳定次数: {stable_count}/{max_stable_attempts}")
                
                scroll_count += 1
                
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
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                data_rows = 0
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        data_rows += 1
                
                if data_rows > total_rows:
                    total_rows = data_rows
            
            return total_rows
            
        except Exception as e:
            logger.error(f"计算评级行数失败: {e}")
            return 0
    
    def _calculate_consecutive_ratings(self, soup) -> Tuple[int, int]:
        """
        计算连续Hold天数和连续Buy天数
        
        Returns:
            (consecutive_hold_days, consecutive_buy_days)
        """
        try:
            consecutive_hold = 0
            consecutive_buy = 0
            
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # 从最新的数据开始计数Hold天数
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        try:
                            rating_cell = cells[2] if len(cells) > 2 else None
                            rating_text = self._extract_rating_text(rating_cell)
                            
                            if self._is_hold_rating(rating_text):
                                consecutive_hold += 1
                            else:
                                break  # 遇到非Hold就停止
                        except Exception as e:
                            logger.warning(f"解析Hold评级行失败: {e}")
                            break
                
                # 重新遍历计算Buy天数
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        try:
                            rating_cell = cells[2] if len(cells) > 2 else None
                            rating_text = self._extract_rating_text(rating_cell)
                            
                            if self._is_buy_rating(rating_text):
                                consecutive_buy += 1
                            else:
                                break  # 遇到非Buy就停止
                        except Exception as e:
                            logger.warning(f"解析Buy评级行失败: {e}")
                            break
                
                # 如果找到了数据，就返回结果
                if consecutive_hold > 0 or consecutive_buy > 0:
                    break
            
            return consecutive_hold, consecutive_buy
            
        except Exception as e:
            logger.error(f"计算连续评级天数失败: {e}")
            return 0, 0
    
    def _extract_rating_text(self, rating_cell) -> str:
        """提取评级文本"""
        if not rating_cell:
            return 'N/A'
        
        # 查找评级文本，可能在span或其他元素中
        rating_span = rating_cell.find('span')
        if rating_span:
            return rating_span.get_text(strip=True)
        else:
            return rating_cell.get_text(strip=True)
    
    def _is_hold_rating(self, rating_text: str) -> bool:
        """判断是否为Hold评级"""
        rating_text = rating_text.strip().upper()
        hold_patterns = ['HOLD', 'NEUTRAL']
        return any(pattern in rating_text for pattern in hold_patterns)
    
    def _is_buy_rating(self, rating_text: str) -> bool:
        """判断是否为Buy评级（包括Strong Buy）"""
        rating_text = rating_text.strip().upper()
        buy_patterns = ['BUY', 'STRONG BUY', 'STRONG-BUY', 'STRONGBUY']
        return any(pattern in rating_text for pattern in buy_patterns)
    
    def _get_current_rating(self, soup) -> str:
        """获取当前最新评级"""
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:  # 确保有数据行
                    first_data_row = rows[1]  # 第一行数据（最新）
                    cells = first_data_row.find_all(['td', 'th'])
                    
                    if len(cells) >= 3:
                        rating_cell = cells[2]
                        return self._extract_rating_text(rating_cell)
            
            return 'N/A'
            
        except Exception as e:
            logger.warning(f"获取当前评级失败: {e}")
            return 'N/A'
    
    def analyze_portfolio(self) -> List[Dict]:
        """
        分析整个投资组合的评级历史
        
        Returns:
            包含所有股票评级分析的列表
        """
        try:
            if not self.setup_driver():
                return []
            
            # 检查是否有未完成的任务
            progress = self.progress_manager.load_progress()
            
            if progress:
                processed_symbols = set(progress['processed_symbols'])
                complete_results = progress['results']
                logger.info(f"🔄 继续之前的任务，已处理 {len(processed_symbols)} 只股票")
                
                # 重新获取投资组合股票列表
                target_stocks = self.extract_portfolio_stocks()
            else:
                processed_symbols = set()
                complete_results = []
                
                # 获取投资组合股票列表
                logger.info("=== 第一步：获取投资组合股票列表 ===")
                target_stocks = self.extract_portfolio_stocks()
                
                if not target_stocks:
                    logger.error("未获取到任何需要分析的股票（Hold/Buy）")
                    return []
            
            # 分析每只股票的评级历史
            logger.info("=== 第二步：分析每只股票的评级历史 ===")
            
            for i, stock_data in enumerate(target_stocks):
                symbol = stock_data['symbol']
                
                # 跳过已处理的股票
                if symbol in processed_symbols:
                    continue
                
                try:
                    # 固定延时
                    delay = 2.0
                    logger.info(f"📊 处理 {symbol} ({stock_data['rating_category']}: {stock_data['rating_score']}) - "
                             f"({len(complete_results)+1}/{len(target_stocks)}) - 延时{delay:.1f}秒")
                    time.sleep(delay)
                    
                    # 分析股票评级历史
                    result = self.analyze_stock_rating_history(symbol)
                    
                    # 添加当前的评级信息到结果中
                    result['current_rating_score'] = stock_data['rating_score']
                    result['current_rating_category'] = stock_data['rating_category']
                    
                    complete_results.append(result)
                    processed_symbols.add(symbol)
                    
                    # 每处理5只股票保存一次进度
                    if len(processed_symbols) % 5 == 0:
                        self.progress_manager.save_progress(
                            list(processed_symbols), 
                            complete_results
                        )
                    
                except KeyboardInterrupt:
                    logger.info("🛑 用户中断，保存当前进度...")
                    self.progress_manager.save_progress(
                        list(processed_symbols), 
                        complete_results
                    )
                    raise
                    
                except Exception as e:
                    logger.error(f"❌ 处理 {symbol} 失败: {e}")
                    continue
            
            # 清理进度文件
            self.progress_manager.cleanup()
            
            logger.info(f"✅ 完成分析，共处理 {len(complete_results)} 只股票")
            return complete_results
            
        except KeyboardInterrupt:
            logger.info("用户中断分析")
            raise
        except Exception as e:
            logger.error(f"❌ 投资组合分析失败: {e}")
            return []
    
    def save_results_to_csv(self, results: List[Dict], filename: str = None):
        """保存分析结果到CSV文件"""
        try:
            if not results:
                logger.warning("没有数据可保存")
                return
            
            if filename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_rating_analysis_{timestamp}.csv"
            
            # 准备CSV数据
            csv_data = []
            for result in results:
                row = {
                    'Symbol': result.get('symbol', 'N/A'),
                    'CurrentRating': result.get('current_rating', 'N/A'),
                    'ConsecutiveHoldDays': result.get('consecutive_hold_days', 0),
                    'ConsecutiveBuyDays': result.get('consecutive_buy_days', 0)
                }
                csv_data.append(row)
            
            # 保存到CSV
            df = pd.DataFrame(csv_data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 分析结果已保存到: {filename}")
            
            # 打印统计摘要
            self._print_analysis_summary(results)
            
        except Exception as e:
            logger.error(f"❌ 保存CSV文件失败: {e}")
    
    def _print_analysis_summary(self, results: List[Dict]):
        """打印分析摘要"""
        try:
            logger.info("\n=== 📊 投资组合评级分析摘要 ===")
            logger.info(f"总分析股票数: {len(results)}")
            
            # 统计当前评级分布
            current_ratings = {}
            hold_stats = []
            buy_stats = []
            
            for result in results:
                rating = result.get('current_rating', 'Unknown')
                current_ratings[rating] = current_ratings.get(rating, 0) + 1
                
                hold_days = result.get('consecutive_hold_days', 0)
                buy_days = result.get('consecutive_buy_days', 0)
                
                if hold_days > 0:
                    hold_stats.append(hold_days)
                if buy_days > 0:
                    buy_stats.append(buy_days)
            
            logger.info("当前评级分布:")
            for rating, count in current_ratings.items():
                logger.info(f"  {rating}: {count} 只")
            
            # 统计连续Hold天数
            if hold_stats:
                max_hold = max(hold_stats)
                avg_hold = sum(hold_stats) / len(hold_stats)
                logger.info("连续Hold统计:")
                logger.info(f"  有Hold评级的股票: {len(hold_stats)}/{len(results)} 只")
                logger.info(f"  最长连续Hold天数: {max_hold} 天")
                logger.info(f"  平均连续Hold天数: {avg_hold:.1f} 天")
            
            # 统计连续Buy天数
            if buy_stats:
                max_buy = max(buy_stats)
                avg_buy = sum(buy_stats) / len(buy_stats)
                logger.info("连续Buy统计:")
                logger.info(f"  有Buy评级的股票: {len(buy_stats)}/{len(results)} 只")
                logger.info(f"  最长连续Buy天数: {max_buy} 天")
                logger.info(f"  平均连续Buy天数: {avg_buy:.1f} 天")
            
        except Exception as e:
            logger.warning(f"打印分析摘要失败: {e}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            logger.info("分析完成，浏览器保持打开状态")


def main():
    """主函数"""
    logger.info("🚀 启动投资组合评级分析器")
    
    # 投资组合URL
    portfolio_url = "https://seekingalpha.com/account/portfolio/total_view?portfolioId=64139349"
    
    analyzer = PortfolioRatingAnalyzer(portfolio_url, test_mode=False)
    
    try:
        # 执行投资组合分析
        results = analyzer.analyze_portfolio()
        
        # 保存结果
        if results:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_rating_analysis_{timestamp}.csv"
            analyzer.save_results_to_csv(results, filename)
        else:
            logger.warning("未获取到任何分析结果")
        
    except KeyboardInterrupt:
        logger.info("用户中断分析")
    except Exception as e:
        logger.error(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()


if __name__ == "__main__":
    main() 