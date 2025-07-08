"""
主窗口模块 - 管理主应用程序窗口和布局
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# 导入核心模块
from ..core.data_manager import PremiumData
from ..core.api_client import APIClient
from ..core.config_manager import ConfigManager

# 导入服务模块
from ..services.monitor_service import MonitorService
from ..services.chart_service import ChartService
from ..services.web_scraper import WebScraper

# 导入UI组件
from .components.data_cards import DataCardManager
from .components.control_panel import ControlPanel
from .components.status_bar import StatusBar, StatusBarManager

# 导入对话框
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.export_dialog import ExportDialog

# 导入工具
from ..utils.logger import setup_logger
from ..utils.helpers import get_app_data_dir


class MSTRMonitorGUI:
    """MSTR监控GUI主类"""
    
    def __init__(self):
        """初始化GUI应用"""
        # 设置日志
        self.logger = setup_logger("MSTRMonitorGUI")
        self.logger.info("MSTR监控GUI应用启动")
        
        # 初始化配置
        self.config_manager = ConfigManager()
        
        # 初始化数据管理器
        self.data_manager = PremiumData(
            max_points=self.config_manager.get('monitor.max_data_points', 1000)
        )
        
        # 初始化API客户端
        self.api_client = APIClient(
            api_key=self.config_manager.get('api.finnhub_api_key'),
            timeout=self.config_manager.get('api.request_timeout', 10)
        )
        
        # 初始化监控服务
        self.monitor_service = MonitorService(self.api_client, self.data_manager)
        
        # 初始化Web抓取器
        self.web_scraper = WebScraper()
        
        # 图表服务 (稍后初始化)
        self.chart_service = None
        
        # UI组件
        self.root = None
        self.data_cards = None
        self.control_panel = None
        self.status_bar = None
        self.status_bar_manager = None
        
        # 对话框
        self.settings_dialog = None
        self.export_dialog = None
        
        # 应用状态
        self.is_running = False
        
        # 设置UI
        self.setup_ui()
        
        # 设置服务
        self.setup_services()
        
        self.logger.info("MSTR监控GUI应用初始化完成")
    
    def setup_ui(self) -> None:
        """设置用户界面"""
        # 创建根窗口
        self.root = tk.Tk()
        self.root.title("MSTR/BTC 溢价监控")
        
        # 设置窗口大小和位置
        width = self.config_manager.get('ui.window_width', 1000)
        height = self.config_manager.get('ui.window_height', 700)
        x = self.config_manager.get('ui.window_x', 100)
        y = self.config_manager.get('ui.window_y', 100)
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 600)
        
        # 设置图标和样式
        self.root.configure(bg='#f0f0f0')
        
        # 创建主框架
        self.create_main_frame()
        
        # 创建数据显示区域
        self.create_data_display_frame()
        
        # 创建图表框架
        self.create_chart_frame()
        
        # 创建控制面板
        self.create_control_frame()
        
        # 创建状态栏
        self.create_status_frame()
        
        # 设置键盘快捷键
        self.setup_keyboard_shortcuts()
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.logger.debug("用户界面设置完成")
    
    def create_main_frame(self) -> None:
        """创建主框架"""
        # 标题框架
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = ttk.Label(
            title_frame,
            text="MSTR/BTC 溢价监控",
            font=('Arial', 18, 'bold')
        )
        title_label.pack(pady=5)
        
        # 添加分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)
    
    def create_data_display_frame(self) -> None:
        """创建数据显示框架"""
        # 数据卡片管理器
        self.data_cards = DataCardManager(self.root)
        
        # 添加分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)
    
    def create_chart_frame(self) -> None:
        """创建图表框架"""
        # 图表容器框架
        chart_container = ttk.Frame(self.root)
        chart_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 图表标题
        chart_title = ttk.Label(
            chart_container,
            text="溢价走势图表",
            font=('Arial', 14, 'bold')
        )
        chart_title.pack(pady=(0, 5))
        
        # 图表框架
        self.chart_frame = ttk.Frame(chart_container)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初始化图表服务
        chart_config = {
            'line_color': self.config_manager.get('chart.line_color', '#1f77b4'),
            'line_width': self.config_manager.get('chart.line_width', 2),
            'grid_alpha': self.config_manager.get('chart.grid_alpha', 0.3),
            'animation_interval': self.config_manager.get('chart.animation_interval', 1000),
            'background_color': self.config_manager.get('chart.background_color', '#f8f9fa')
        }
        
        self.chart_service = ChartService(self.chart_frame, self.data_manager, chart_config)
        
        # 添加分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)
    
    def create_control_frame(self) -> None:
        """创建控制面板"""
        self.control_panel = ControlPanel(self.root)
        
        # 设置控制面板回调
        self.control_panel.set_callback('start_monitoring', self.start_monitoring)
        self.control_panel.set_callback('stop_monitoring', self.stop_monitoring)
        self.control_panel.set_callback('clear_data', self.clear_data)
        self.control_panel.set_callback('open_settings', self.open_settings)
        self.control_panel.set_callback('export_data', self.export_data)
        self.control_panel.set_callback('interval_changed', self.on_interval_changed)
        self.control_panel.set_callback('timerange_changed', self.on_timerange_changed)
        
        # 设置快捷键
        self.control_panel.setup_keyboard_shortcuts(self.root)
        
        # 添加分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=5)
    
    def create_status_frame(self) -> None:
        """创建状态栏"""
        self.status_bar = StatusBar(self.root)
        self.status_bar_manager = StatusBarManager(self.status_bar)
    
    def setup_services(self) -> None:
        """设置服务"""
        # 设置监控服务回调
        self.monitor_service.add_callback(self.on_data_updated)
        
        # 设置监控参数
        self.monitor_service.set_update_interval(
            self.config_manager.get('monitor.default_interval', 10)
        )
        
        # 设置BTC per share
        btc_per_share = self.config_manager.get('monitor.btc_per_share', 0.00207973)
        self.monitor_service.set_btc_per_share(btc_per_share)
        
        # 启用自动获取BTC per share
        self.monitor_service.enable_auto_btc_per_share(True)
        
        # 设置图表时间范围
        self.chart_service.set_time_range(
            self.config_manager.get('ui.default_time_range', 3600)
        )
        
        self.logger.debug("服务设置完成")
    
    def setup_keyboard_shortcuts(self) -> None:
        """设置键盘快捷键"""
        # 基本快捷键已在control_panel中设置
        
        # 额外快捷键
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-r>', lambda e: self.refresh_data())
        self.root.bind('<F5>', lambda e: self.refresh_data())
        self.root.bind('<Escape>', lambda e: self.root.focus_set())
        
        self.logger.debug("键盘快捷键设置完成")
    
    def start_monitoring(self) -> bool:
        """
        开始监控
        
        Returns:
            是否成功启动
        """
        try:
            self.logger.info("开始监控")
            
            # 测试服务
            test_results = self.monitor_service.test_services()
            
            if not test_results.get('api_client', False):
                messagebox.showerror("错误", "API客户端连接失败，请检查网络连接和API密钥")
                return False
            
            # 启动监控服务
            if self.monitor_service.start_monitoring():
                # 启动图表动画
                self.chart_service.start_animation()
                
                # 更新状态
                self.status_bar.set_monitoring_status(True)
                self.is_running = True
                
                # 显示成功消息
                self.status_bar.show_message("监控已启动", 2000)
                
                self.logger.info("监控已启动")
                return True
            else:
                messagebox.showerror("错误", "启动监控失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动监控时发生错误: {e}")
            messagebox.showerror("错误", f"启动监控时发生错误: {str(e)}")
            return False
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        try:
            self.logger.info("停止监控")
            
            # 停止监控服务
            self.monitor_service.stop_monitoring()
            
            # 停止图表动画
            self.chart_service.stop_animation()
            
            # 更新状态
            self.status_bar.set_monitoring_status(False)
            self.is_running = False
            
            # 显示停止消息
            self.status_bar.show_message("监控已停止", 2000)
            
            self.logger.info("监控已停止")
            
        except Exception as e:
            self.logger.error(f"停止监控时发生错误: {e}")
            messagebox.showerror("错误", f"停止监控时发生错误: {str(e)}")
    
    def clear_data(self) -> None:
        """清除数据"""
        try:
            self.logger.info("清除数据")
            
            # 清除数据管理器中的数据
            self.data_manager.clear_data()
            
            # 清除图表
            self.chart_service.clear_chart()
            
            # 清除数据卡片
            self.data_cards.clear_all_data()
            
            # 重置状态栏
            self.status_bar.set_data_count(0)
            self.status_bar.reset_error_count()
            
            # 显示清除消息
            self.status_bar.show_message("数据已清除", 2000)
            
            self.logger.info("数据已清除")
            
        except Exception as e:
            self.logger.error(f"清除数据时发生错误: {e}")
            messagebox.showerror("错误", f"清除数据时发生错误: {str(e)}")
    
    def open_settings(self) -> None:
        """打开设置对话框"""
        try:
            if self.settings_dialog is None:
                self.settings_dialog = SettingsDialog(self.root, self.config_manager)
                
                # 设置回调
                self.settings_dialog.set_callback('settings_changed', self.on_settings_changed)
            
            self.settings_dialog.show()
            
        except Exception as e:
            self.logger.error(f"打开设置对话框时发生错误: {e}")
            messagebox.showerror("错误", f"打开设置对话框时发生错误: {str(e)}")
    
    def export_data(self, filename: str) -> bool:
        """
        导出数据
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功导出
        """
        try:
            self.logger.info(f"导出数据到: {filename}")
            
            # 导出数据
            result = self.data_manager.export_to_csv(filename)
            
            if result:
                self.status_bar.show_message("数据导出成功", 3000)
                self.logger.info("数据导出成功")
                return True
            else:
                self.logger.error("数据导出失败")
                return False
                
        except Exception as e:
            self.logger.error(f"导出数据时发生错误: {e}")
            return False
    
    def on_data_updated(self, timestamp: datetime, mstr_price: float, 
                       btc_price: float, premium: float) -> None:
        """
        数据更新回调
        
        Args:
            timestamp: 时间戳
            mstr_price: MSTR价格
            btc_price: BTC价格
            premium: 溢价率
        """
        try:
            # 更新数据卡片
            self.data_cards.update_all_data(timestamp, mstr_price, btc_price, premium)
            
            # 更新状态栏
            self.status_bar_manager.update_from_data_manager(self.data_manager)
            self.status_bar_manager.update_from_monitor_service(self.monitor_service)
            
            self.logger.debug(f"数据已更新: {timestamp}, MSTR: {mstr_price}, BTC: {btc_price}, 溢价: {premium:.2f}%")
            
        except Exception as e:
            self.logger.error(f"更新数据时发生错误: {e}")
            self.status_bar.increment_error_count()
    
    def on_interval_changed(self, interval: int) -> None:
        """
        更新间隔变化回调
        
        Args:
            interval: 新的间隔时间(秒)
        """
        try:
            self.monitor_service.set_update_interval(interval)
            self.config_manager.set('monitor.default_interval', interval)
            self.config_manager.save_config()
            
            self.logger.info(f"更新间隔已更改为: {interval}秒")
            
        except Exception as e:
            self.logger.error(f"更改更新间隔时发生错误: {e}")
    
    def on_timerange_changed(self, timerange: int) -> None:
        """
        时间范围变化回调
        
        Args:
            timerange: 新的时间范围(秒)
        """
        try:
            self.chart_service.set_time_range(timerange)
            self.config_manager.set('ui.default_time_range', timerange)
            self.config_manager.save_config()
            
            self.logger.info(f"时间范围已更改为: {timerange}秒")
            
        except Exception as e:
            self.logger.error(f"更改时间范围时发生错误: {e}")
    
    def on_settings_changed(self, settings: Dict[str, Any]) -> None:
        """
        设置变化回调
        
        Args:
            settings: 设置字典
        """
        try:
            self.logger.info("设置已更改")
            
            # 更新API客户端
            if 'api' in settings:
                api_settings = settings['api']
                if 'finnhub_api_key' in api_settings:
                    self.api_client.update_api_key(api_settings['finnhub_api_key'])
                if 'request_timeout' in api_settings:
                    self.api_client.set_timeout(api_settings['request_timeout'])
            
            # 更新监控服务
            if 'monitor' in settings:
                monitor_settings = settings['monitor']
                if 'default_interval' in monitor_settings:
                    self.monitor_service.set_update_interval(monitor_settings['default_interval'])
                if 'btc_per_share' in monitor_settings:
                    self.monitor_service.set_btc_per_share(monitor_settings['btc_per_share'])
            
            # 更新图表
            if 'chart' in settings:
                chart_settings = settings['chart']
                self.chart_service.set_chart_style(chart_settings)
            
            # 更新UI
            if 'ui' in settings:
                ui_settings = settings['ui']
                if 'default_time_range' in ui_settings:
                    self.chart_service.set_time_range(ui_settings['default_time_range'])
            
            self.logger.info("设置更新完成")
            
        except Exception as e:
            self.logger.error(f"更新设置时发生错误: {e}")
    
    def refresh_data(self) -> None:
        """刷新数据"""
        try:
            if self.is_running:
                # 强制更新一次数据
                data = self.monitor_service.fetch_data()
                if data:
                    self.on_data_updated(
                        data['timestamp'],
                        data['mstr_price'],
                        data['btc_price'],
                        data['premium']
                    )
            
            self.logger.debug("数据已刷新")
            
        except Exception as e:
            self.logger.error(f"刷新数据时发生错误: {e}")
    
    def on_closing(self) -> None:
        """窗口关闭事件"""
        try:
            self.logger.info("正在关闭应用程序")
            
            # 保存窗口位置和大小
            geometry = self.root.geometry()
            width, height, x, y = geometry.replace('+', 'x').split('x')
            
            self.config_manager.set('ui.window_width', int(width))
            self.config_manager.set('ui.window_height', int(height))
            self.config_manager.set('ui.window_x', int(x))
            self.config_manager.set('ui.window_y', int(y))
            self.config_manager.save_config()
            
            # 停止监控
            if self.is_running:
                self.stop_monitoring()
            
            # 清理资源
            self.cleanup()
            
            # 关闭窗口
            self.root.destroy()
            
            self.logger.info("应用程序已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭应用程序时发生错误: {e}")
            # 强制关闭
            self.root.destroy()
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清理监控服务
            if self.monitor_service:
                self.monitor_service.cleanup()
            
            # 清理图表服务
            if self.chart_service:
                self.chart_service.cleanup()
            
            # 清理Web抓取器
            if self.web_scraper:
                self.web_scraper.cleanup()
            
            self.logger.debug("资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")
    
    def run(self) -> None:
        """运行应用程序"""
        try:
            self.logger.info("启动GUI主循环")
            
            # 显示窗口
            self.root.deiconify()
            
            # 运行主循环
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"运行应用程序时发生错误: {e}")
            raise
    
    def get_app_info(self) -> Dict[str, Any]:
        """
        获取应用程序信息
        
        Returns:
            应用程序信息字典
        """
        return {
            'name': 'MSTR/BTC溢价监控',
            'version': '1.0.0',
            'is_running': self.is_running,
            'data_count': self.data_manager.get_data_count(),
            'monitor_status': self.monitor_service.get_monitoring_status(),
            'chart_stats': self.chart_service.get_chart_statistics(),
            'config_summary': self.config_manager.get_config_summary()
        }