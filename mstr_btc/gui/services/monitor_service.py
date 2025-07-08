"""
监控服务模块 - 管理数据获取和监控逻辑
"""

import threading
import time
import logging
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from ..core.api_client import APIClient
from ..core.data_manager import PremiumData
from .web_scraper import WebScraper


class MonitorService:
    """数据监控服务"""
    
    def __init__(self, api_client: APIClient, data_manager: PremiumData):
        """
        初始化监控服务
        
        Args:
            api_client: API客户端
            data_manager: 数据管理器
        """
        self.api_client = api_client
        self.data_manager = data_manager
        self.web_scraper = WebScraper()
        
        # 监控状态
        self.is_running = False
        self.is_paused = False
        self.monitor_thread = None
        
        # 监控参数
        self.update_interval = 10  # 更新间隔(秒)
        self.btc_per_share = 0.00207973  # BTC per share值
        self.auto_btc_per_share = True  # 是否自动获取BTC per share
        
        # 回调函数列表
        self.callbacks = []
        
        # 错误处理
        self.max_consecutive_errors = 5
        self.consecutive_errors = 0
        self.last_error_time = None
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None,
            'last_update_time': None,
            'uptime': 0
        }
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("监控服务初始化完成")
    
    def add_callback(self, callback: Callable) -> None:
        """
        添加数据更新回调函数
        
        Args:
            callback: 回调函数，签名为 callback(timestamp, mstr_price, btc_price, premium)
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self.logger.debug(f"添加回调函数: {callback.__name__}")
    
    def remove_callback(self, callback: Callable) -> None:
        """
        移除数据更新回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            self.logger.debug(f"移除回调函数: {callback.__name__}")
    
    def set_update_interval(self, interval: int) -> None:
        """
        设置更新间隔
        
        Args:
            interval: 更新间隔(秒)
        """
        if interval < 1:
            interval = 1
            
        self.update_interval = interval
        self.logger.info(f"更新间隔设置为: {interval}秒")
    
    def set_btc_per_share(self, value: float) -> None:
        """
        设置BTC per share值
        
        Args:
            value: BTC per share值
        """
        if value > 0:
            self.btc_per_share = value
            self.auto_btc_per_share = False
            self.logger.info(f"BTC per share设置为: {value}")
        else:
            self.logger.error(f"无效的BTC per share值: {value}")
    
    def enable_auto_btc_per_share(self, enabled: bool = True) -> None:
        """
        启用/禁用自动获取BTC per share
        
        Args:
            enabled: 是否启用
        """
        self.auto_btc_per_share = enabled
        self.logger.info(f"自动获取BTC per share: {'启用' if enabled else '禁用'}")
    
    def calculate_premium(self, mstr_price: float, btc_price: float) -> float:
        """
        计算溢价率
        
        Args:
            mstr_price: MSTR价格
            btc_price: BTC价格
            
        Returns:
            溢价率(百分比)
        """
        try:
            if self.btc_per_share <= 0:
                raise ValueError("BTC per share值无效")
                
            btc_value_per_share = self.btc_per_share * btc_price
            premium = (mstr_price / btc_value_per_share - 1) * 100
            
            return premium
            
        except (ZeroDivisionError, ValueError) as e:
            self.logger.error(f"计算溢价率失败: {e}")
            return 0.0
    
    def update_btc_per_share(self) -> bool:
        """
        更新BTC per share值
        
        Returns:
            是否成功更新
        """
        try:
            if not self.auto_btc_per_share:
                return True
                
            new_value = self.web_scraper.scrape_btc_per_share()
            
            if new_value is not None:
                old_value = self.btc_per_share
                self.btc_per_share = new_value
                
                self.logger.info(f"BTC per share更新: {old_value} -> {new_value}")
                
                # 如果变化超过5%，记录警告
                if abs(new_value - old_value) / old_value > 0.05:
                    self.logger.warning(f"BTC per share变化较大: {old_value} -> {new_value}")
                
                return True
            else:
                self.logger.warning("无法获取BTC per share，使用当前值")
                return False
                
        except Exception as e:
            self.logger.error(f"更新BTC per share失败: {e}")
            return False
    
    def fetch_data(self) -> Optional[Dict[str, Any]]:
        """
        获取一次数据
        
        Returns:
            数据字典，包含timestamp, mstr_price, btc_price, premium
        """
        try:
            self.stats['total_requests'] += 1
            
            # 获取价格数据
            mstr_price = self.api_client.get_mstr_price()
            btc_price = self.api_client.get_btc_price()
            
            if mstr_price is None or btc_price is None:
                self.logger.warning("无法获取价格数据")
                self.stats['failed_requests'] += 1
                return None
            
            # 计算溢价率
            premium = self.calculate_premium(mstr_price, btc_price)
            
            # 创建数据字典
            data = {
                'timestamp': datetime.now(),
                'mstr_price': mstr_price,
                'btc_price': btc_price,
                'premium': premium
            }
            
            self.stats['successful_requests'] += 1
            self.stats['last_update_time'] = data['timestamp']
            
            # 重置错误计数
            self.consecutive_errors = 0
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            self.stats['failed_requests'] += 1
            self.consecutive_errors += 1
            self.last_error_time = datetime.now()
            
            return None
    
    def start_monitoring(self) -> bool:
        """
        开始监控
        
        Returns:
            是否成功启动
        """
        if self.is_running:
            self.logger.warning("监控服务已在运行")
            return False
        
        try:
            # 初始化BTC per share
            if self.auto_btc_per_share:
                self.logger.info("正在获取BTC per share...")
                if not self.update_btc_per_share():
                    self.logger.warning("无法获取BTC per share，使用默认值")
            
            # 启动监控线程
            self.is_running = True
            self.is_paused = False
            self.consecutive_errors = 0
            self.stats['start_time'] = datetime.now()
            
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            self.logger.info("监控服务已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动监控服务失败: {e}")
            self.is_running = False
            return False
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        if not self.is_running:
            self.logger.warning("监控服务未在运行")
            return
        
        self.is_running = False
        self.is_paused = False
        
        # 等待线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            
            if self.monitor_thread.is_alive():
                self.logger.warning("监控线程未在超时时间内停止")
            else:
                self.logger.info("监控线程已停止")
        
        self.monitor_thread = None
        self.logger.info("监控服务已停止")
    
    def pause_monitoring(self) -> None:
        """暂停监控"""
        if self.is_running:
            self.is_paused = True
            self.logger.info("监控服务已暂停")
    
    def resume_monitoring(self) -> None:
        """恢复监控"""
        if self.is_running:
            self.is_paused = False
            self.logger.info("监控服务已恢复")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        self.logger.info("监控循环开始")
        
        while self.is_running:
            try:
                if self.is_paused:
                    time.sleep(1)
                    continue
                
                # 检查是否达到最大错误次数
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.logger.error(f"连续错误次数达到上限({self.max_consecutive_errors})，暂停监控")
                    self.pause_monitoring()
                    time.sleep(30)  # 等待30秒后尝试恢复
                    self.resume_monitoring()
                    continue
                
                # 获取数据
                data = self.fetch_data()
                
                if data is not None:
                    # 添加到数据管理器
                    self.data_manager.add_data_point(
                        data['timestamp'],
                        data['mstr_price'],
                        data['btc_price'],
                        data['premium']
                    )
                    
                    # 调用回调函数
                    self._call_callbacks(data)
                    
                    # 定期更新BTC per share（每小时一次）
                    if (self.auto_btc_per_share and 
                        self.stats['total_requests'] % (3600 // self.update_interval) == 0):
                        self.update_btc_per_share()
                
                # 等待下次更新
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环发生错误: {e}")
                self.consecutive_errors += 1
                time.sleep(5)  # 错误时短暂等待
        
        self.logger.info("监控循环结束")
    
    def _call_callbacks(self, data: Dict[str, Any]) -> None:
        """
        调用回调函数
        
        Args:
            data: 数据字典
        """
        for callback in self.callbacks:
            try:
                callback(
                    data['timestamp'],
                    data['mstr_price'],
                    data['btc_price'],
                    data['premium']
                )
            except Exception as e:
                self.logger.error(f"回调函数执行错误: {callback.__name__}: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        获取监控状态
        
        Returns:
            状态信息字典
        """
        status = {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'update_interval': self.update_interval,
            'btc_per_share': self.btc_per_share,
            'auto_btc_per_share': self.auto_btc_per_share,
            'consecutive_errors': self.consecutive_errors,
            'max_consecutive_errors': self.max_consecutive_errors,
            'callback_count': len(self.callbacks),
            'thread_alive': self.monitor_thread.is_alive() if self.monitor_thread else False
        }
        
        # 添加统计信息
        status.update(self.stats)
        
        # 计算运行时间
        if self.stats['start_time']:
            status['uptime'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # 计算成功率
        if self.stats['total_requests'] > 0:
            status['success_rate'] = (self.stats['successful_requests'] / self.stats['total_requests']) * 100
        else:
            status['success_rate'] = 0.0
        
        return status
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """
        获取最新数据
        
        Returns:
            最新数据字典
        """
        latest = self.data_manager.get_latest_data()
        
        if latest is None:
            return None
        
        return {
            'timestamp': latest[0],
            'mstr_price': latest[1],
            'btc_price': latest[2],
            'premium': latest[3]
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': datetime.now() if self.is_running else None,
            'last_update_time': None,
            'uptime': 0
        }
        
        self.consecutive_errors = 0
        self.last_error_time = None
        
        self.logger.info("统计信息已重置")
    
    def test_services(self) -> Dict[str, bool]:
        """
        测试相关服务
        
        Returns:
            测试结果字典
        """
        results = {}
        
        # 测试API客户端
        try:
            results['api_client'] = self.api_client.test_connection()
        except Exception as e:
            self.logger.error(f"API客户端测试失败: {e}")
            results['api_client'] = False
        
        # 测试网页抓取器
        try:
            results['web_scraper'] = self.web_scraper.test_connection()
        except Exception as e:
            self.logger.error(f"网页抓取器测试失败: {e}")
            results['web_scraper'] = False
        
        # 测试数据管理器
        try:
            test_data = self.data_manager.get_statistics()
            results['data_manager'] = isinstance(test_data, dict)
        except Exception as e:
            self.logger.error(f"数据管理器测试失败: {e}")
            results['data_manager'] = False
        
        return results
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止监控
            if self.is_running:
                self.stop_monitoring()
            
            # 清理网页抓取器
            if self.web_scraper:
                self.web_scraper.cleanup()
            
            # 清空回调函数
            self.callbacks.clear()
            
            self.logger.info("监控服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()