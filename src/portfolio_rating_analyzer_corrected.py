#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合评级分析器 - 基于真实投资组合数据
只分析当前处于Hold和Buy评级的股票的连续评级天数
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

class CorrectedPortfolioRatingAnalyzer:
    def __init__(self):
        self.driver = None
        
        # 基于用户投资组合截图的真实数据
        self.target_stocks = [
            # Hold评级股票 (2.5-3.5) - 需要分析连续Hold天数
            {"symbol": "RCL", "rating": 3.47, "category": "Hold"},
            {"symbol": "TWLO", "rating": 3.42, "category": "Hold"},
            {"symbol": "MFC", "rating": 3.24, "category": "Hold"},
            
            # Buy评级股票 (3.5-4.5) - 需要分析连续Buy天数  
            {"symbol": "EXE", "rating": 4.23, "category": "Buy"},
            {"symbol": "REG", "rating": 3.93, "category": "Buy"},
        ]
        
        self.base_url = "https://seekingalpha.com/symbol/{}/ratings/quant-ratings"
        
    def connect_to_chrome(self) -> bool:
        """连接到远程调试模式的Chrome"""
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Chrome远程调试连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接Chrome失败: {e}")
            return False
    
    def analyze_stock_consecutive_days(self, symbol: str, target_category: str) -> Dict:
        """分析单只股票的连续评级天数"""
        try:
            url = self.base_url.format(symbol)
            logger.info(f"📊 访问 {symbol} 量化评分页面: {url}")
            
            self.driver.get(url)
            time.sleep(3)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except:
                logger.warning(f"{symbol}: 页面加载超时")
            
            # 滚动加载评级历史数据
            consecutive_days = self._scroll_and_analyze_rating_history(symbol, target_category)
            
            return {
                "Symbol": symbol,
                "Category": target_category,
                "ConsecutiveDays": consecutive_days,
                "Status": "Success" if consecutive_days > 0 else "No Data"
            }
            
        except Exception as e:
            logger.error(f"分析 {symbol} 失败: {e}")
            return {
                "Symbol": symbol,
                "Category": target_category,
                "ConsecutiveDays": 0,
                "Status": f"Error: {str(e)}"
            }
    
    def _scroll_and_analyze_rating_history(self, symbol: str, target_category: str) -> int:
        """滚动加载并分析评级历史，计算连续天数"""
        try:
            logger.info(f"🔄 开始滚动加载 {symbol} 的评级历史...")
            
            consecutive_days = 0
            previous_row_count = 0
            stable_count = 0
            max_stable_attempts = 5
            scroll_pause_time = 1.5
            
            while stable_count < max_stable_attempts:
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
                # 获取当前页面的评级历史数据
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                rating_rows = self._extract_rating_history_rows(soup)
                
                current_row_count = len(rating_rows)
                
                if current_row_count > previous_row_count:
                    logger.info(f"📈 {symbol}: 已加载 {current_row_count} 行评级历史")
                    previous_row_count = current_row_count
                    stable_count = 0
                else:
                    stable_count += 1
                    logger.info(f"📊 {symbol}: 数据稳定检查 {stable_count}/{max_stable_attempts}")
                
                # 如果已经有足够的数据（超过75行），可以开始分析
                if current_row_count >= 75:
                    break
            
            # 分析连续天数
            if rating_rows:
                logger.info(f"🔍 {symbol}: 找到 {len(rating_rows)} 行评级历史，开始分析...")
                
                # 显示前几行数据用于调试
                for i, row in enumerate(rating_rows[:5]):
                    logger.info(f"  行{i+1}: {row['date']} | {row['rating_text']} | {row['score']} | 类别: {row['category']}")
                
                consecutive_days = self._calculate_consecutive_days(rating_rows, target_category)
                logger.info(f"✅ {symbol}: 连续{target_category}天数 = {consecutive_days}天")
            else:
                logger.warning(f"⚠️ {symbol}: 未找到评级历史数据")
            
            return consecutive_days
            
        except Exception as e:
            logger.error(f"滚动分析 {symbol} 失败: {e}")
            return 0
    
    def _extract_rating_history_rows(self, soup) -> List[Dict]:
        """从页面中提取评级历史行数据"""
        try:
            rating_rows = []
            
            # 查找评级历史表格
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")
            
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                logger.info(f"表格 {table_idx+1}: 有 {len(rows)} 行")
                
                # 检查是否为评级历史表格（查找包含Date列的表头）
                if len(rows) > 0:
                    header_row = rows[0]
                    header_text = header_row.get_text().lower()
                    
                    if 'date' in header_text and ('quant rating' in header_text or 'rating' in header_text):
                        logger.info(f"找到评级历史表格，表格 {table_idx+1}")
                        
                        for row_idx, row in enumerate(rows[1:], 1):  # 跳过表头
                            cells = row.find_all(['td', 'th'])
                            
                            if len(cells) >= 4:  # 至少需要日期、价格、评级、评分列
                                # 根据截图调整列索引：Date, Price, Quant Rating, Quant Score
                                date_text = cells[0].get_text(strip=True) if cells[0] else ""
                                price_text = cells[1].get_text(strip=True) if cells[1] else ""
                                rating_text = cells[2].get_text(strip=True) if cells[2] else ""
                                score_text = cells[3].get_text(strip=True) if cells[3] else ""
                                
                                # 解析评级类别
                                category = self._parse_rating_category(rating_text, score_text)
                                
                                if date_text and category:
                                    rating_rows.append({
                                        "date": date_text,
                                        "price": price_text,
                                        "rating_text": rating_text,
                                        "score": score_text,
                                        "category": category
                                    })
                                    
                                    if row_idx <= 3:  # 显示前3行用于调试
                                        logger.info(f"  解析行 {row_idx}: {date_text} | {rating_text} | {score_text} | {category}")
            
            # 按日期排序（最新的在前）
            # 注意：SeekingAlpha的表格通常已经是最新在前的顺序
            logger.info(f"总共提取到 {len(rating_rows)} 行评级数据")
            return rating_rows
            
        except Exception as e:
            logger.error(f"提取评级历史失败: {e}")
            return []
    
    def _parse_rating_category(self, rating_text: str, score_text: str) -> Optional[str]:
        """解析评级类别"""
        try:
            # 优先从评级文本中直接提取（如截图中的"HOLD"）
            rating_lower = rating_text.lower().strip()
            
            if "strong buy" in rating_lower or "strongbuy" in rating_lower:
                return "StrongBuy"
            elif rating_lower == "hold":
                return "Hold"
            elif rating_lower == "buy":
                return "Buy" 
            elif "sell" in rating_lower:
                return "Sell"
            
            # 如果评级文本无法识别，尝试从评分数字推断
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            if score_match:
                score = float(score_match.group(1))
                
                if score >= 4.5:
                    return "StrongBuy"
                elif score >= 3.5:
                    return "Buy"
                elif score >= 2.5:
                    return "Hold"
                else:
                    return "Sell"
            
            # 如果都无法识别，记录调试信息
            logger.warning(f"无法解析评级: rating_text='{rating_text}', score_text='{score_text}'")
            return None
            
        except Exception as e:
            logger.error(f"解析评级类别失败: {e}")
            return None
    
    def _calculate_consecutive_days(self, rating_rows: List[Dict], target_category: str) -> int:
        """计算从最新日期开始的连续目标评级天数"""
        try:
            consecutive_days = 0
            
            # 从最新的评级开始检查
            for row in rating_rows:
                if row["category"] == target_category:
                    consecutive_days += 1
                else:
                    # 一旦遇到不同的评级，停止计数
                    break
            
            return consecutive_days
            
        except Exception as e:
            logger.error(f"计算连续天数失败: {e}")
            return 0
    
    def analyze_portfolio(self) -> List[Dict]:
        """分析投资组合中的目标股票"""
        logger.info("🚀 开始分析投资组合中的Hold和Buy股票")
        logger.info(f"📊 目标股票数量: {len(self.target_stocks)}")
        
        results = []
        
        # 连接Chrome
        if not self.connect_to_chrome():
            logger.error("无法连接到Chrome，分析终止")
            return []
        
        try:
            for i, stock in enumerate(self.target_stocks, 1):
                symbol = stock["symbol"]
                category = stock["category"]
                rating = stock["rating"]
                
                logger.info(f"📈 处理股票 {i}/{len(self.target_stocks)}: {symbol} ({rating}) - {category}")
                
                # 分析连续天数
                result = self.analyze_stock_consecutive_days(symbol, category)
                result["QuantRating"] = rating
                
                results.append(result)
                
                # 延时避免请求过快
                if i < len(self.target_stocks):
                    delay = 2.0
                    logger.info(f"⏱️ 延时 {delay}秒...")
                    time.sleep(delay)
            
            # 生成报告
            self._generate_report(results)
            
            return results
            
        except Exception as e:
            logger.error(f"分析过程中发生错误: {e}")
            return results
        
        finally:
            logger.info("🔚 分析完成，浏览器保持打开状态")
    
    def _generate_report(self, results: List[Dict]):
        """生成分析报告"""
        try:
            logger.info("=" * 60)
            logger.info("📊 投资组合Hold/Buy股票连续评级分析报告")
            logger.info("=" * 60)
            
            # 分类统计
            hold_stocks = [r for r in results if r["Category"] == "Hold" and r["ConsecutiveDays"] > 0]
            buy_stocks = [r for r in results if r["Category"] == "Buy" and r["ConsecutiveDays"] > 0]
            
            logger.info(f"📋 分析股票总数: {len(results)}")
            logger.info("")
            
            # Hold股票分析
            if hold_stocks:
                logger.info("🔄 Hold评级股票连续天数分析:")
                hold_stocks.sort(key=lambda x: x["ConsecutiveDays"], reverse=True)
                for stock in hold_stocks:
                    logger.info(f"   - {stock['Symbol']}: 连续Hold {stock['ConsecutiveDays']}天 ← 考虑止损")
                
                max_hold = max(hold_stocks, key=lambda x: x["ConsecutiveDays"])
                avg_hold = sum(s["ConsecutiveDays"] for s in hold_stocks) / len(hold_stocks)
                logger.info(f"   - 最长连续Hold: {max_hold['Symbol']} ({max_hold['ConsecutiveDays']}天)")
                logger.info(f"   - 平均连续Hold: {avg_hold:.1f}天")
            else:
                logger.info("🔄 Hold评级股票: 无有效数据")
            
            logger.info("")
            
            # Buy股票分析
            if buy_stocks:
                logger.info("📈 Buy评级股票连续天数分析:")
                buy_stocks.sort(key=lambda x: x["ConsecutiveDays"], reverse=True)
                for stock in buy_stocks:
                    logger.info(f"   - {stock['Symbol']}: 连续Buy {stock['ConsecutiveDays']}天 ← 考虑获利了结")
                
                max_buy = max(buy_stocks, key=lambda x: x["ConsecutiveDays"])
                avg_buy = sum(s["ConsecutiveDays"] for s in buy_stocks) / len(buy_stocks)
                logger.info(f"   - 最长连续Buy: {max_buy['Symbol']} ({max_buy['ConsecutiveDays']}天)")
                logger.info(f"   - 平均连续Buy: {avg_buy:.1f}天")
            else:
                logger.info("📈 Buy评级股票: 无有效数据")
            
            logger.info("=" * 60)
            
            # 保存到CSV
            self._save_to_csv(results)
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
    
    def _save_to_csv(self, results: List[Dict]):
        """保存结果到CSV文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_hold_buy_analysis_{timestamp}.csv"
            
            df = pd.DataFrame(results)
            df = df[["Symbol", "QuantRating", "Category", "ConsecutiveDays", "Status"]]
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"📁 分析结果已保存到: {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")

def main():
    """主函数"""
    try:
        analyzer = CorrectedPortfolioRatingAnalyzer()
        results = analyzer.analyze_portfolio()
        
        if results:
            logger.info("✅ 分析完成")
        else:
            logger.error("❌ 分析失败")
            
    except Exception as e:
        logger.error(f"主程序发生错误: {e}")

if __name__ == "__main__":
    main() 