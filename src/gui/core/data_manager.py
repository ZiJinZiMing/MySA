"""
数据管理模块 - 管理溢价数据的存储、查询和导出
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
import threading
import csv
import os
import logging


class PremiumData:
    """溢价数据管理类"""
    
    def __init__(self, max_points: int = 1000):
        """
        初始化数据管理器
        
        Args:
            max_points: 最大存储数据点数量
        """
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.mstr_prices = deque(maxlen=max_points)
        self.btc_prices = deque(maxlen=max_points)
        self.premiums = deque(maxlen=max_points)
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
    def add_data_point(self, timestamp: datetime, mstr_price: float, 
                      btc_price: float, premium: float) -> None:
        """
        添加新数据点
        
        Args:
            timestamp: 时间戳
            mstr_price: MSTR价格
            btc_price: BTC价格
            premium: 溢价率
        """
        with self.lock:
            self.timestamps.append(timestamp)
            self.mstr_prices.append(mstr_price)
            self.btc_prices.append(btc_price)
            self.premiums.append(premium)
            
        self.logger.debug(f"添加数据点: {timestamp}, MSTR: {mstr_price}, BTC: {btc_price}, 溢价: {premium}%")
    
    def get_latest_data(self) -> Optional[Tuple[datetime, float, float, float]]:
        """
        获取最新数据点
        
        Returns:
            最新数据点的元组 (时间戳, MSTR价格, BTC价格, 溢价率)，如果没有数据则返回None
        """
        with self.lock:
            if len(self.timestamps) == 0:
                return None
            return (
                self.timestamps[-1], 
                self.mstr_prices[-1], 
                self.btc_prices[-1], 
                self.premiums[-1]
            )
    
    def get_all_data(self) -> Tuple[List[datetime], List[float], List[float], List[float]]:
        """
        获取所有数据点
        
        Returns:
            包含所有数据的元组 (时间戳列表, MSTR价格列表, BTC价格列表, 溢价率列表)
        """
        with self.lock:
            return (
                list(self.timestamps), 
                list(self.mstr_prices),
                list(self.btc_prices), 
                list(self.premiums)
            )
    
    def get_data_in_range(self, start_time: datetime, 
                         end_time: datetime) -> Tuple[List[datetime], List[float], List[float], List[float]]:
        """
        获取指定时间范围内的数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指定时间范围内的数据元组
        """
        with self.lock:
            filtered_timestamps = []
            filtered_mstr_prices = []
            filtered_btc_prices = []
            filtered_premiums = []
            
            for i, timestamp in enumerate(self.timestamps):
                if start_time <= timestamp <= end_time:
                    filtered_timestamps.append(timestamp)
                    filtered_mstr_prices.append(self.mstr_prices[i])
                    filtered_btc_prices.append(self.btc_prices[i])
                    filtered_premiums.append(self.premiums[i])
            
            return (filtered_timestamps, filtered_mstr_prices, 
                   filtered_btc_prices, filtered_premiums)
    
    def get_data_for_chart(self, time_range_seconds: int = 3600) -> Tuple[List[datetime], List[float]]:
        """
        获取用于图表显示的数据
        
        Args:
            time_range_seconds: 时间范围(秒)，默认1小时
            
        Returns:
            图表数据元组 (时间戳列表, 溢价率列表)
        """
        current_time = datetime.now()
        start_time = current_time - timedelta(seconds=time_range_seconds)
        
        timestamps, _, _, premiums = self.get_data_in_range(start_time, current_time)
        return timestamps, premiums
    
    def clear_data(self) -> None:
        """清空所有数据"""
        with self.lock:
            self.timestamps.clear()
            self.mstr_prices.clear()
            self.btc_prices.clear()
            self.premiums.clear()
        
        self.logger.info("已清空所有数据")
    
    def export_to_csv(self, filename: str) -> bool:
        """
        导出数据到CSV文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功导出
        """
        try:
            with self.lock:
                if len(self.timestamps) == 0:
                    self.logger.warning("没有数据可导出")
                    return False
                
                # 确保目录存在
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # 写入头部
                    writer.writerow(['时间戳', 'MSTR价格', 'BTC价格', '溢价率'])
                    
                    # 写入数据
                    for i in range(len(self.timestamps)):
                        writer.writerow([
                            self.timestamps[i].strftime('%Y-%m-%d %H:%M:%S'),
                            self.mstr_prices[i],
                            self.btc_prices[i],
                            self.premiums[i]
                        ])
                
                self.logger.info(f"成功导出数据到 {filename}")
                return True
                
        except Exception as e:
            self.logger.error(f"导出数据失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            if len(self.premiums) == 0:
                return {
                    'count': 0,
                    'latest_premium': None,
                    'max_premium': None,
                    'min_premium': None,
                    'avg_premium': None,
                    'latest_mstr_price': None,
                    'latest_btc_price': None,
                    'time_range': None
                }
            
            premiums_list = list(self.premiums)
            
            stats = {
                'count': len(premiums_list),
                'latest_premium': premiums_list[-1],
                'max_premium': max(premiums_list),
                'min_premium': min(premiums_list),
                'avg_premium': sum(premiums_list) / len(premiums_list),
                'latest_mstr_price': self.mstr_prices[-1],
                'latest_btc_price': self.btc_prices[-1],
                'time_range': (self.timestamps[0], self.timestamps[-1]) if len(self.timestamps) > 0 else None
            }
            
            return stats
    
    def get_data_count(self) -> int:
        """
        获取数据点数量
        
        Returns:
            数据点数量
        """
        with self.lock:
            return len(self.timestamps)
    
    def is_empty(self) -> bool:
        """
        检查是否为空
        
        Returns:
            是否为空
        """
        with self.lock:
            return len(self.timestamps) == 0
    
    def get_premium_change(self, minutes: int = 5) -> Optional[float]:
        """
        获取指定时间内的溢价变化
        
        Args:
            minutes: 时间间隔(分钟)
            
        Returns:
            溢价变化值，如果数据不足则返回None
        """
        with self.lock:
            if len(self.premiums) < 2:
                return None
            
            current_time = datetime.now()
            target_time = current_time - timedelta(minutes=minutes)
            
            # 找到最接近目标时间的数据点
            target_premium = None
            for i, timestamp in enumerate(self.timestamps):
                if timestamp >= target_time:
                    target_premium = self.premiums[i]
                    break
            
            if target_premium is None:
                return None
            
            return self.premiums[-1] - target_premium
    
    def cleanup_old_data(self, hours: int = 24) -> None:
        """
        清理超过指定时间的旧数据
        
        Args:
            hours: 保留数据的小时数
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            # 找到需要保留的数据起始位置
            start_index = 0
            for i, timestamp in enumerate(self.timestamps):
                if timestamp >= cutoff_time:
                    start_index = i
                    break
            
            # 如果需要清理数据
            if start_index > 0:
                # 创建新的deque来保存需要保留的数据
                new_timestamps = deque(list(self.timestamps)[start_index:], maxlen=self.max_points)
                new_mstr_prices = deque(list(self.mstr_prices)[start_index:], maxlen=self.max_points)
                new_btc_prices = deque(list(self.btc_prices)[start_index:], maxlen=self.max_points)
                new_premiums = deque(list(self.premiums)[start_index:], maxlen=self.max_points)
                
                self.timestamps = new_timestamps
                self.mstr_prices = new_mstr_prices
                self.btc_prices = new_btc_prices
                self.premiums = new_premiums
                
                self.logger.info(f"清理了 {start_index} 个过期数据点")