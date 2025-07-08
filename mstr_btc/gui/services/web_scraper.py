"""
网页抓取服务模块 - 从网页获取BTC per share数据
"""

import re
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup


class WebScraper:
    """网页抓取服务"""
    
    def __init__(self, chrome_debug_port: int = 9222, timeout: int = 20):
        """
        初始化网页抓取器
        
        Args:
            chrome_debug_port: Chrome远程调试端口
            timeout: 页面加载超时时间
        """
        self.chrome_debug_port = chrome_debug_port
        self.timeout = timeout
        self.driver = None
        self.logger = logging.getLogger(__name__)
        
        # 目标网站URL
        self.target_url = (
            "https://strategytracker.com/mstr"
            "?charts=nav-multiplier%2Cperformance-comparison%2Cbitcoin-price%2Cnav-premium%2Creserve-chart"
            "&timeRange=year"
        )
        
        self.logger.info(f"网页抓取器初始化完成，目标URL: {self.target_url}")
    
    def connect_to_chrome(self) -> bool:
        """
        连接到Chrome浏览器
        
        Returns:
            是否成功连接
        """
        try:
            # 尝试连接到已运行的Chrome实例
            chrome_options = Options()
            chrome_options.add_experimental_option(
                "debuggerAddress", f"127.0.0.1:{self.chrome_debug_port}"
            )
            
            self.logger.info(f"正在连接到Chrome浏览器 (端口: {self.chrome_debug_port})...")
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 测试连接
            self.driver.execute_script("return document.readyState")
            
            self.logger.info("成功连接到Chrome浏览器")
            return True
            
        except WebDriverException as e:
            self.logger.error(f"连接Chrome浏览器失败: {e}")
            
            # 尝试启动新的Chrome实例
            try:
                self.logger.info("尝试启动新的Chrome浏览器实例...")
                
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--headless")  # 无头模式
                
                self.driver = webdriver.Chrome(options=chrome_options)
                
                self.logger.info("成功启动新的Chrome浏览器实例")
                return True
                
            except WebDriverException as e2:
                self.logger.error(f"启动Chrome浏览器失败: {e2}")
                return False
        
        except Exception as e:
            self.logger.error(f"连接Chrome浏览器时发生未知错误: {e}")
            return False
    
    def scrape_btc_per_share(self) -> Optional[float]:
        """
        抓取BTC per share数据
        
        Returns:
            BTC per share值，失败时返回None
        """
        if not self.driver:
            if not self.connect_to_chrome():
                return None
        
        try:
            # 访问目标网站
            self.logger.info(f"正在访问网站: {self.target_url}")
            self.driver.get(self.target_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, self.timeout)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            
            self.logger.info("页面加载完成")
            
            # 等待动态内容加载
            time.sleep(3)
            
            # 获取页面源码
            page_source = self.driver.page_source
            
            # 解析数据
            btc_per_share = self.parse_data(page_source)
            
            if btc_per_share is not None:
                self.logger.info(f"成功获取BTC per share: {btc_per_share}")
                return btc_per_share
            else:
                self.logger.warning("未能解析到BTC per share数据")
                return None
                
        except TimeoutException:
            self.logger.error("页面加载超时")
            return None
            
        except WebDriverException as e:
            self.logger.error(f"网页抓取失败: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"抓取BTC per share时发生未知错误: {e}")
            return None
    
    def parse_data(self, page_source: str) -> Optional[float]:
        """
        解析页面数据
        
        Args:
            page_source: 页面源码
            
        Returns:
            解析得到的BTC per share值
        """
        try:
            # 方法1: 使用Selenium直接查找元素
            if self.driver:
                try:
                    # 查找包含"BTC per Basic Share"的元素
                    elements = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), 'BTC per Basic Share')]"
                    )
                    
                    if elements:
                        # 获取父元素或相邻元素
                        for element in elements:
                            try:
                                parent = element.find_element(By.XPATH, "./..")
                                text = parent.text
                                
                                # 从文本中提取数值
                                match = re.search(r"([0-9.]+)", text)
                                if match:
                                    value = float(match.group(1))
                                    if self.validate_data(value):
                                        self.logger.debug(f"方法1成功解析: {value}")
                                        return value
                            except Exception:
                                continue
                                
                except Exception as e:
                    self.logger.debug(f"方法1解析失败: {e}")
            
            # 方法2: 使用BeautifulSoup解析
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 查找包含"BTC per Basic Share"的文本
            text_elements = soup.find_all(text=re.compile(r"BTC per Basic Share", re.IGNORECASE))
            
            for text_element in text_elements:
                try:
                    # 获取父元素
                    parent = text_element.parent
                    if parent:
                        # 在父元素中查找数值
                        parent_text = parent.get_text()
                        match = re.search(r"([0-9.]+)", parent_text)
                        if match:
                            value = float(match.group(1))
                            if self.validate_data(value):
                                self.logger.debug(f"方法2成功解析: {value}")
                                return value
                except Exception:
                    continue
            
            # 方法3: 正则表达式全文搜索
            if self.driver:
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    
                    # 查找BTC per Basic Share相关的数值
                    patterns = [
                        r"BTC per Basic Share:?\s*([0-9.]+)",
                        r"BTC per Share:?\s*([0-9.]+)",
                        r"(?:BTC|Bitcoin)\s*per\s*(?:Basic\s*)?Share:?\s*([0-9.]+)",
                        r"([0-9.]+)\s*BTC per (?:Basic\s*)?Share"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, body_text, re.IGNORECASE)
                        if match:
                            value = float(match.group(1))
                            if self.validate_data(value):
                                self.logger.debug(f"方法3成功解析: {value}")
                                return value
                                
                except Exception as e:
                    self.logger.debug(f"方法3解析失败: {e}")
            
            # 方法4: 查找特定的数值模式
            # 假设BTC per share在特定范围内
            all_numbers = re.findall(r"\b([0-9]*\.?[0-9]+)\b", page_source)
            
            for num_str in all_numbers:
                try:
                    value = float(num_str)
                    # BTC per share通常在0.001到0.01之间
                    if 0.001 <= value <= 0.01:
                        if self.validate_data(value):
                            self.logger.debug(f"方法4成功解析: {value}")
                            return value
                except ValueError:
                    continue
            
            self.logger.warning("所有解析方法都失败了")
            return None
            
        except Exception as e:
            self.logger.error(f"解析数据时发生错误: {e}")
            return None
    
    def validate_data(self, data: float) -> bool:
        """
        验证数据有效性
        
        Args:
            data: 待验证的数据
            
        Returns:
            数据是否有效
        """
        try:
            # 检查数据类型
            if not isinstance(data, (int, float)):
                return False
            
            # 检查数值范围（BTC per share通常在0.001到0.01之间）
            if not (0.0001 <= data <= 0.1):
                return False
            
            # 检查是否为有效数字
            if data != data:  # 检查NaN
                return False
            
            if data == float('inf') or data == float('-inf'):
                return False
            
            self.logger.debug(f"数据验证通过: {data}")
            return True
            
        except Exception as e:
            self.logger.error(f"数据验证失败: {e}")
            return False
    
    def get_page_screenshot(self, filename: str) -> bool:
        """
        获取页面截图
        
        Args:
            filename: 截图文件名
            
        Returns:
            是否成功保存截图
        """
        try:
            if self.driver:
                self.driver.save_screenshot(filename)
                self.logger.info(f"页面截图保存成功: {filename}")
                return True
            else:
                self.logger.error("WebDriver未初始化，无法保存截图")
                return False
                
        except Exception as e:
            self.logger.error(f"保存截图失败: {e}")
            return False
    
    def get_page_source(self) -> Optional[str]:
        """
        获取页面源码
        
        Returns:
            页面源码，失败时返回None
        """
        try:
            if self.driver:
                return self.driver.page_source
            else:
                self.logger.error("WebDriver未初始化")
                return None
                
        except Exception as e:
            self.logger.error(f"获取页面源码失败: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试连接和抓取功能
        
        Returns:
            测试是否成功
        """
        try:
            self.logger.info("开始测试连接和抓取功能...")
            
            # 测试连接
            if not self.connect_to_chrome():
                self.logger.error("连接测试失败")
                return False
            
            # 测试抓取
            result = self.scrape_btc_per_share()
            
            if result is not None:
                self.logger.info(f"抓取测试成功，获取到数据: {result}")
                return True
            else:
                self.logger.error("抓取测试失败")
                return False
                
        except Exception as e:
            self.logger.error(f"测试时发生错误: {e}")
            return False
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.driver:
                # 检查是否为远程调试连接
                if hasattr(self.driver, 'service') and self.driver.service:
                    # 只有非远程调试连接才需要quit
                    if self.chrome_debug_port != 9222:
                        self.driver.quit()
                        self.logger.info("Chrome浏览器已关闭")
                    else:
                        self.logger.info("远程调试连接，保持Chrome浏览器运行")
                else:
                    self.driver.quit()
                    self.logger.info("Chrome浏览器已关闭")
                    
                self.driver = None
                
        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


# 便捷函数
def get_btc_per_share() -> Optional[float]:
    """
    便捷函数：获取BTC per share数据
    
    Returns:
        BTC per share值，失败时返回None
    """
    with WebScraper() as scraper:
        return scraper.scrape_btc_per_share()


def test_scraper() -> bool:
    """
    便捷函数：测试抓取器功能
    
    Returns:
        测试是否成功
    """
    with WebScraper() as scraper:
        return scraper.test_connection()