"""
状态栏组件 - 显示应用状态信息
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from ...utils.helpers import format_timestamp, format_duration


class StatusBar:
    """状态栏组件"""
    
    def __init__(self, parent: tk.Widget):
        """
        初始化状态栏
        
        Args:
            parent: 父级组件
        """
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        
        # 状态信息
        self.connection_status = "未连接"
        self.last_update_time = None
        self.data_count = 0
        self.error_count = 0
        self.uptime_start = None
        
        # 创建UI
        self.create_ui()
        
        self.logger.info("状态栏初始化完成")
    
    def create_ui(self) -> None:
        """创建用户界面"""
        # 主框架
        self.frame = ttk.Frame(self.parent, relief=tk.SUNKEN)
        self.frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 分隔线
        separator = ttk.Separator(self.frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(0, 2))
        
        # 状态内容框架
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 连接状态
        self.connection_frame = ttk.Frame(content_frame)
        self.connection_frame.pack(side=tk.LEFT)
        
        self.connection_indicator = ttk.Label(
            self.connection_frame,
            text="●",
            font=('Arial', 10),
            foreground='red'
        )
        self.connection_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        self.connection_label = ttk.Label(
            self.connection_frame,
            text="连接状态: 未连接",
            font=('Arial', 9)
        )
        self.connection_label.pack(side=tk.LEFT)
        
        # 分隔符
        ttk.Separator(content_frame, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )
        
        # 最后更新时间
        self.update_time_label = ttk.Label(
            content_frame,
            text="最后更新: --",
            font=('Arial', 9)
        )
        self.update_time_label.pack(side=tk.LEFT, padx=5)
        
        # 分隔符
        ttk.Separator(content_frame, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )
        
        # 数据点数量
        self.data_count_label = ttk.Label(
            content_frame,
            text="数据点: 0",
            font=('Arial', 9)
        )
        self.data_count_label.pack(side=tk.LEFT, padx=5)
        
        # 分隔符
        ttk.Separator(content_frame, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )
        
        # 错误计数
        self.error_count_label = ttk.Label(
            content_frame,
            text="错误: 0",
            font=('Arial', 9)
        )
        self.error_count_label.pack(side=tk.LEFT, padx=5)
        
        # 运行时间 (右侧)
        self.uptime_label = ttk.Label(
            content_frame,
            text="运行时间: --",
            font=('Arial', 9)
        )
        self.uptime_label.pack(side=tk.RIGHT, padx=5)
        
        # 分隔符
        ttk.Separator(content_frame, orient='vertical').pack(
            side=tk.RIGHT, fill=tk.Y, padx=10
        )
        
        # 内存使用情况
        self.memory_label = ttk.Label(
            content_frame,
            text="内存: --",
            font=('Arial', 9)
        )
        self.memory_label.pack(side=tk.RIGHT, padx=5)
        
        # 分隔符
        ttk.Separator(content_frame, orient='vertical').pack(
            side=tk.RIGHT, fill=tk.Y, padx=10
        )
        
        # API请求状态
        self.api_status_label = ttk.Label(
            content_frame,
            text="API: --",
            font=('Arial', 9)
        )
        self.api_status_label.pack(side=tk.RIGHT, padx=5)
    
    def set_connection_status(self, status: str, is_connected: bool = True) -> None:
        """
        设置连接状态
        
        Args:
            status: 状态文本
            is_connected: 是否已连接
        """
        try:
            self.connection_status = status
            self.connection_label.config(text=f"连接状态: {status}")
            
            # 更新指示器颜色
            if is_connected:
                self.connection_indicator.config(foreground='green')
            else:
                self.connection_indicator.config(foreground='red')
            
            self.logger.debug(f"连接状态已更新: {status}")
            
        except Exception as e:
            self.logger.error(f"设置连接状态时发生错误: {e}")
    
    def set_last_update_time(self, timestamp: Optional[datetime] = None) -> None:
        """
        设置最后更新时间
        
        Args:
            timestamp: 时间戳，如果为None则使用当前时间
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            self.last_update_time = timestamp
            time_str = format_timestamp(timestamp, "short")
            self.update_time_label.config(text=f"最后更新: {time_str}")
            
        except Exception as e:
            self.logger.error(f"设置最后更新时间时发生错误: {e}")
    
    def set_data_count(self, count: int) -> None:
        """
        设置数据点数量
        
        Args:
            count: 数据点数量
        """
        try:
            self.data_count = count
            self.data_count_label.config(text=f"数据点: {count}")
            
        except Exception as e:
            self.logger.error(f"设置数据点数量时发生错误: {e}")
    
    def set_error_count(self, count: int) -> None:
        """
        设置错误计数
        
        Args:
            count: 错误数量
        """
        try:
            self.error_count = count
            
            # 根据错误数量设置颜色
            if count == 0:
                color = 'green'
            elif count < 5:
                color = 'orange'
            else:
                color = 'red'
            
            self.error_count_label.config(
                text=f"错误: {count}",
                foreground=color
            )
            
        except Exception as e:
            self.logger.error(f"设置错误计数时发生错误: {e}")
    
    def increment_error_count(self) -> None:
        """增加错误计数"""
        self.set_error_count(self.error_count + 1)
    
    def reset_error_count(self) -> None:
        """重置错误计数"""
        self.set_error_count(0)
    
    def set_uptime_start(self, start_time: Optional[datetime] = None) -> None:
        """
        设置运行时间开始时间
        
        Args:
            start_time: 开始时间，如果为None则使用当前时间
        """
        if start_time is None:
            start_time = datetime.now()
        
        self.uptime_start = start_time
        self.logger.debug(f"运行时间开始: {start_time}")
    
    def update_uptime(self) -> None:
        """更新运行时间显示"""
        try:
            if self.uptime_start is None:
                self.uptime_label.config(text="运行时间: --")
                return
            
            current_time = datetime.now()
            uptime_seconds = (current_time - self.uptime_start).total_seconds()
            uptime_str = format_duration(uptime_seconds)
            
            self.uptime_label.config(text=f"运行时间: {uptime_str}")
            
        except Exception as e:
            self.logger.error(f"更新运行时间时发生错误: {e}")
    
    def set_memory_usage(self, usage_mb: float) -> None:
        """
        设置内存使用情况
        
        Args:
            usage_mb: 内存使用量(MB)
        """
        try:
            if usage_mb < 100:
                color = 'green'
            elif usage_mb < 200:
                color = 'orange'
            else:
                color = 'red'
            
            self.memory_label.config(
                text=f"内存: {usage_mb:.1f}MB",
                foreground=color
            )
            
        except Exception as e:
            self.logger.error(f"设置内存使用情况时发生错误: {e}")
    
    def set_api_status(self, status: str, success_rate: Optional[float] = None) -> None:
        """
        设置API状态
        
        Args:
            status: 状态文本
            success_rate: 成功率(0-100)
        """
        try:
            if success_rate is not None:
                status_text = f"API: {status} ({success_rate:.1f}%)"
                
                # 根据成功率设置颜色
                if success_rate >= 95:
                    color = 'green'
                elif success_rate >= 80:
                    color = 'orange'
                else:
                    color = 'red'
            else:
                status_text = f"API: {status}"
                color = 'black'
            
            self.api_status_label.config(
                text=status_text,
                foreground=color
            )
            
        except Exception as e:
            self.logger.error(f"设置API状态时发生错误: {e}")
    
    def update_all_status(self, status_info: Dict[str, Any]) -> None:
        """
        更新所有状态信息
        
        Args:
            status_info: 状态信息字典
        """
        try:
            # 连接状态
            if 'connection_status' in status_info:
                self.set_connection_status(
                    status_info['connection_status'],
                    status_info.get('is_connected', False)
                )
            
            # 最后更新时间
            if 'last_update_time' in status_info:
                self.set_last_update_time(status_info['last_update_time'])
            
            # 数据点数量
            if 'data_count' in status_info:
                self.set_data_count(status_info['data_count'])
            
            # 错误计数
            if 'error_count' in status_info:
                self.set_error_count(status_info['error_count'])
            
            # 内存使用
            if 'memory_usage' in status_info:
                self.set_memory_usage(status_info['memory_usage'])
            
            # API状态
            if 'api_status' in status_info:
                self.set_api_status(
                    status_info['api_status'],
                    status_info.get('api_success_rate')
                )
            
            # 更新运行时间
            self.update_uptime()
            
        except Exception as e:
            self.logger.error(f"更新所有状态时发生错误: {e}")
    
    def get_memory_usage(self) -> float:
        """
        获取当前内存使用情况
        
        Returns:
            内存使用量(MB)
        """
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # 转换为MB
            
        except ImportError:
            return 0.0
        except Exception as e:
            self.logger.error(f"获取内存使用情况时发生错误: {e}")
            return 0.0
    
    def start_auto_update(self, interval: int = 5000) -> None:
        """
        启动自动更新
        
        Args:
            interval: 更新间隔(毫秒)
        """
        try:
            # 更新内存使用情况
            memory_usage = self.get_memory_usage()
            if memory_usage > 0:
                self.set_memory_usage(memory_usage)
            
            # 更新运行时间
            self.update_uptime()
            
            # 安排下次更新
            self.parent.after(interval, lambda: self.start_auto_update(interval))
            
        except Exception as e:
            self.logger.error(f"自动更新时发生错误: {e}")
    
    def clear_all_status(self) -> None:
        """清空所有状态"""
        self.set_connection_status("未连接", False)
        self.set_last_update_time(None)
        self.set_data_count(0)
        self.reset_error_count()
        self.set_memory_usage(0)
        self.set_api_status("未连接")
        self.uptime_start = None
        self.uptime_label.config(text="运行时间: --")
        self.update_time_label.config(text="最后更新: --")
    
    def set_monitoring_status(self, is_monitoring: bool) -> None:
        """
        设置监控状态
        
        Args:
            is_monitoring: 是否正在监控
        """
        if is_monitoring:
            self.set_connection_status("监控中", True)
            if self.uptime_start is None:
                self.set_uptime_start()
        else:
            self.set_connection_status("已停止", False)
    
    def show_message(self, message: str, duration: int = 3000) -> None:
        """
        在状态栏显示临时消息
        
        Args:
            message: 消息内容
            duration: 显示时长(毫秒)
        """
        try:
            # 保存当前状态
            original_text = self.connection_label.cget('text')
            original_color = self.connection_indicator.cget('foreground')
            
            # 显示消息
            self.connection_label.config(text=message)
            self.connection_indicator.config(foreground='blue')
            
            # 定时恢复原状态
            def restore_status():
                self.connection_label.config(text=original_text)
                self.connection_indicator.config(foreground=original_color)
            
            self.parent.after(duration, restore_status)
            
        except Exception as e:
            self.logger.error(f"显示消息时发生错误: {e}")
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取当前状态信息
        
        Returns:
            状态信息字典
        """
        return {
            'connection_status': self.connection_status,
            'last_update_time': self.last_update_time,
            'data_count': self.data_count,
            'error_count': self.error_count,
            'uptime_start': self.uptime_start,
            'memory_usage': self.get_memory_usage()
        }


class StatusBarManager:
    """状态栏管理器"""
    
    def __init__(self, status_bar: StatusBar):
        """
        初始化状态栏管理器
        
        Args:
            status_bar: 状态栏实例
        """
        self.status_bar = status_bar
        self.logger = logging.getLogger(__name__)
        
        # 启动自动更新
        self.status_bar.start_auto_update()
        
        self.logger.info("状态栏管理器初始化完成")
    
    def update_from_monitor_service(self, monitor_service) -> None:
        """
        从监控服务更新状态
        
        Args:
            monitor_service: 监控服务实例
        """
        try:
            status = monitor_service.get_monitoring_status()
            
            # 更新连接状态
            if status.get('is_running', False):
                self.status_bar.set_connection_status("监控中", True)
            else:
                self.status_bar.set_connection_status("已停止", False)
            
            # 更新数据统计
            self.status_bar.set_error_count(status.get('consecutive_errors', 0))
            
            # 更新API状态
            total_requests = status.get('total_requests', 0)
            if total_requests > 0:
                success_rate = (status.get('successful_requests', 0) / total_requests) * 100
                self.status_bar.set_api_status("正常", success_rate)
            else:
                self.status_bar.set_api_status("未请求")
            
            # 更新最后更新时间
            if status.get('last_update_time'):
                self.status_bar.set_last_update_time(status['last_update_time'])
            
        except Exception as e:
            self.logger.error(f"从监控服务更新状态时发生错误: {e}")
    
    def update_from_data_manager(self, data_manager) -> None:
        """
        从数据管理器更新状态
        
        Args:
            data_manager: 数据管理器实例
        """
        try:
            # 更新数据点数量
            count = data_manager.get_data_count()
            self.status_bar.set_data_count(count)
            
            # 更新最后更新时间
            latest_data = data_manager.get_latest_data()
            if latest_data:
                self.status_bar.set_last_update_time(latest_data[0])
            
        except Exception as e:
            self.logger.error(f"从数据管理器更新状态时发生错误: {e}")


# 便捷函数
def create_status_bar(parent: tk.Widget) -> StatusBar:
    """
    创建状态栏
    
    Args:
        parent: 父级组件
        
    Returns:
        状态栏实例
    """
    return StatusBar(parent)


def create_status_bar_manager(status_bar: StatusBar) -> StatusBarManager:
    """
    创建状态栏管理器
    
    Args:
        status_bar: 状态栏实例
        
    Returns:
        状态栏管理器实例
    """
    return StatusBarManager(status_bar)