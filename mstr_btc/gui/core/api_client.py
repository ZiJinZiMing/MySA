"""
API客户端模块 - 统一管理所有外部API调用
"""

import requests
import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime


class APIClient:
    """API客户端统一管理"""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        """
        初始化API客户端
        
        Args:
            api_key: Finnhub API密钥
            timeout: 请求超时时间(秒)
        """
        self.finnhub_api_key = api_key or os.environ.get(
            "FINNHUB_API_KEY", 
            "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g"
        )
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # 创建会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MSTR-Monitor/1.0'
        })
        
        # 请求计数和限流
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 最小请求间隔(秒)
        
        self.logger.info(f"API客户端初始化完成，API Key: {self.finnhub_api_key[:10]}...")
    
    def _rate_limit(self) -> None:
        """实现请求速率限制"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict[str, Any] = None, 
                     max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            max_retries: 最大重试次数
            
        Returns:
            响应数据字典，失败时返回None
        """
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                self.request_count += 1
                self.logger.debug(f"发送请求: {url}, 尝试 {attempt + 1}/{max_retries}")
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # 检查API错误
                if isinstance(data, dict) and "error" in data:
                    self.logger.error(f"API错误: {data['error']}")
                    return None
                
                self.logger.debug(f"请求成功，响应数据: {str(data)[:100]}...")
                return data
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时，尝试 {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"连接错误，尝试 {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"HTTP错误: {e}")
                if e.response.status_code == 429:  # 请求过多
                    self.logger.warning("API请求限制，等待60秒")
                    time.sleep(60)
                    continue
                return None
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常: {e}")
                return None
                
            except ValueError as e:
                self.logger.error(f"JSON解析错误: {e}")
                return None
        
        self.logger.error(f"请求失败，已达到最大重试次数: {max_retries}")
        return None
    
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        获取股票价格 - 通用方法
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票价格，失败时返回None
        """
        url = "https://finnhub.io/api/v1/quote"
        params = {
            "symbol": symbol,
            "token": self.finnhub_api_key
        }
        
        data = self._make_request(url, params)
        
        if data is None:
            return None
        
        try:
            price = data.get("c")  # 当前价格
            if price is None or price == 0:
                self.logger.warning(f"获取到无效价格: {symbol} = {price}")
                return None
            
            self.logger.debug(f"获取价格成功: {symbol} = ${price}")
            return float(price)
            
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"解析价格数据失败: {e}")
            return None
    
    def get_mstr_price(self) -> Optional[float]:
        """
        获取MSTR价格
        
        Returns:
            MSTR价格，失败时返回None
        """
        return self.get_ticker_price("MSTR")
    
    def get_btc_price(self) -> Optional[float]:
        """
        获取BTC价格
        
        Returns:
            BTC价格，失败时返回None
        """
        # 尝试多个BTC价格源
        btc_symbols = ["BINANCE:BTCUSDT", "COINBASE:BTC-USD", "BTCUSD"]
        
        for symbol in btc_symbols:
            price = self.get_ticker_price(symbol)
            if price is not None:
                return price
        
        self.logger.error("无法从任何来源获取BTC价格")
        return None
    
    def get_price_change(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        获取价格变化信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            价格变化字典，包含当前价格、变化值、变化百分比
        """
        url = "https://finnhub.io/api/v1/quote"
        params = {
            "symbol": symbol,
            "token": self.finnhub_api_key
        }
        
        data = self._make_request(url, params)
        
        if data is None:
            return None
        
        try:
            current_price = data.get("c")
            previous_close = data.get("pc")
            
            if current_price is None or previous_close is None:
                return None
            
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
            
            return {
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent
            }
            
        except (KeyError, ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f"解析价格变化数据失败: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            # 测试一个简单的请求
            price = self.get_ticker_price("AAPL")
            if price is not None:
                self.logger.info("API连接测试成功")
                return True
            else:
                self.logger.error("API连接测试失败")
                return False
                
        except Exception as e:
            self.logger.error(f"API连接测试异常: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        获取API限制状态
        
        Returns:
            API限制状态字典
        """
        return {
            "request_count": self.request_count,
            "last_request_time": datetime.fromtimestamp(self.last_request_time),
            "api_key": self.finnhub_api_key[:10] + "...",
            "timeout": self.timeout,
            "min_request_interval": self.min_request_interval
        }
    
    def update_api_key(self, new_api_key: str) -> None:
        """
        更新API密钥
        
        Args:
            new_api_key: 新的API密钥
        """
        self.finnhub_api_key = new_api_key
        self.logger.info(f"API密钥已更新: {new_api_key[:10]}...")
    
    def set_timeout(self, timeout: int) -> None:
        """
        设置请求超时时间
        
        Args:
            timeout: 超时时间(秒)
        """
        self.timeout = timeout
        self.logger.info(f"请求超时时间设置为: {timeout}秒")
    
    def set_rate_limit(self, interval: float) -> None:
        """
        设置请求速率限制
        
        Args:
            interval: 最小请求间隔(秒)
        """
        self.min_request_interval = interval
        self.logger.info(f"请求速率限制设置为: {interval}秒")
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.request_count = 0
        self.last_request_time = 0
        self.logger.info("API统计信息已重置")
    
    def __del__(self):
        """析构函数，关闭会话"""
        if hasattr(self, 'session'):
            self.session.close()