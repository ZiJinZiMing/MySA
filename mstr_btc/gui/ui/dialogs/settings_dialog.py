"""
设置对话框 - 应用程序设置界面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, Callable
import logging
from ...core.config_manager import ConfigManager
from ...utils.validators import validate_api_key, validate_config


class SettingsDialog:
    """设置对话框"""
    
    def __init__(self, parent: tk.Widget, config_manager: ConfigManager):
        """
        初始化设置对话框
        
        Args:
            parent: 父窗口
            config_manager: 配置管理器
        """
        self.parent = parent
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 对话框窗口
        self.dialog = None
        
        # 变量
        self.variables = {}
        
        # 回调函数
        self.callback = None
        
        # 原始配置备份
        self.original_config = None
        
        self.logger.info("设置对话框初始化完成")
    
    def show(self) -> None:
        """显示对话框"""
        if self.dialog is not None:
            # 如果对话框已存在，激活它
            self.dialog.lift()
            self.dialog.focus_set()
            return
        
        # 创建新对话框
        self.create_dialog()
        
        # 加载当前配置
        self.load_config()
        
        # 显示对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.focus_set()
        
        # 居中显示
        self.center_dialog()
        
        self.logger.debug("设置对话框已显示")
    
    def create_dialog(self) -> None:
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("设置")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        
        # 设置对话框关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # 创建笔记本控件
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个选项卡
        self.create_api_tab()
        self.create_monitor_tab()
        self.create_ui_tab()
        self.create_chart_tab()
        self.create_alerts_tab()
        
        # 创建按钮框架
        self.create_button_frame()
    
    def create_api_tab(self) -> None:
        """创建API设置选项卡"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="API设置")
        
        # API密钥
        ttk.Label(frame, text="Finnhub API密钥:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['api_key'] = tk.StringVar()
        api_key_entry = ttk.Entry(frame, textvariable=self.variables['api_key'], width=40, show="*")
        api_key_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 显示/隐藏密钥按钮
        def toggle_api_key_visibility():
            if api_key_entry.cget('show') == '*':
                api_key_entry.config(show='')
                show_button.config(text="隐藏")
            else:
                api_key_entry.config(show='*')
                show_button.config(text="显示")
        
        show_button = ttk.Button(frame, text="显示", command=toggle_api_key_visibility, width=6)
        show_button.grid(row=0, column=2, padx=5, pady=5)
        
        # 测试连接按钮
        test_button = ttk.Button(frame, text="测试连接", command=self.test_api_connection)
        test_button.grid(row=0, column=3, padx=5, pady=5)
        
        # 请求超时
        ttk.Label(frame, text="请求超时(秒):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['request_timeout'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['request_timeout'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 重试次数
        ttk.Label(frame, text="重试次数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['retry_count'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['retry_count'], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 重试延迟
        ttk.Label(frame, text="重试延迟(秒):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['retry_delay'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['retry_delay'], width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 速率限制
        ttk.Label(frame, text="请求间隔(秒):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['rate_limit_interval'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['rate_limit_interval'], width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 说明文本
        info_text = """
API设置说明:
• API密钥：获取Finnhub免费API密钥访问 https://finnhub.io
• 请求超时：API请求的超时时间，建议5-30秒
• 重试次数：请求失败时的重试次数，建议1-5次
• 重试延迟：重试之间的等待时间，建议0.5-3秒
• 请求间隔：两次请求之间的最小间隔，建议0.5-2秒
        """
        
        info_label = ttk.Label(frame, text=info_text, font=('Arial', 9), foreground='gray')
        info_label.grid(row=5, column=0, columnspan=4, sticky=tk.W, padx=5, pady=10)
    
    def create_monitor_tab(self) -> None:
        """创建监控设置选项卡"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="监控设置")
        
        # 默认更新间隔
        ttk.Label(frame, text="默认更新间隔(秒):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['default_interval'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['default_interval'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 最大数据点
        ttk.Label(frame, text="最大数据点:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['max_data_points'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['max_data_points'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # BTC per share
        ttk.Label(frame, text="BTC per Share:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['btc_per_share'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['btc_per_share'], width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 自动获取BTC per share
        self.variables['auto_btc_per_share'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="自动获取BTC per Share", variable=self.variables['auto_btc_per_share']).grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 自动开始监控
        self.variables['auto_start'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启动时自动开始监控", variable=self.variables['auto_start']).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 自动清理时间
        ttk.Label(frame, text="自动清理时间(小时):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['auto_cleanup_hours'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['auto_cleanup_hours'], width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
    
    def create_ui_tab(self) -> None:
        """创建UI设置选项卡"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="界面设置")
        
        # 窗口大小
        ttk.Label(frame, text="窗口宽度:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['window_width'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['window_width'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(frame, text="窗口高度:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['window_height'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['window_height'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 默认时间范围
        ttk.Label(frame, text="默认时间范围:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['default_time_range'] = tk.StringVar()
        time_range_combo = ttk.Combobox(frame, textvariable=self.variables['default_time_range'], 
                                       values=["30分钟", "1小时", "2小时", "4小时", "8小时", "1天"], 
                                       state="readonly", width=10)
        time_range_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 主题
        ttk.Label(frame, text="主题:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['theme'] = tk.StringVar()
        theme_combo = ttk.Combobox(frame, textvariable=self.variables['theme'], 
                                  values=["default", "dark", "light"], 
                                  state="readonly", width=10)
        theme_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 字体大小
        ttk.Label(frame, text="字体大小:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['font_size'] = tk.StringVar()
        font_size_combo = ttk.Combobox(frame, textvariable=self.variables['font_size'], 
                                      values=["8", "9", "10", "11", "12", "14", "16"], 
                                      state="readonly", width=10)
        font_size_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 其他选项
        self.variables['always_on_top'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="窗口置顶", variable=self.variables['always_on_top']).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        self.variables['minimize_to_tray'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="最小化到系统托盘", variable=self.variables['minimize_to_tray']).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
    
    def create_chart_tab(self) -> None:
        """创建图表设置选项卡"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="图表设置")
        
        # 线条颜色
        ttk.Label(frame, text="线条颜色:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['line_color'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['line_color'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 线条宽度
        ttk.Label(frame, text="线条宽度:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['line_width'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['line_width'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 网格透明度
        ttk.Label(frame, text="网格透明度:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['grid_alpha'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['grid_alpha'], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 动画间隔
        ttk.Label(frame, text="动画间隔(毫秒):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['animation_interval'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['animation_interval'], width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 背景颜色
        ttk.Label(frame, text="背景颜色:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['background_color'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['background_color'], width=10).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 显示选项
        self.variables['show_grid'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="显示网格", variable=self.variables['show_grid']).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        self.variables['show_legend'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="显示图例", variable=self.variables['show_legend']).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
    
    def create_alerts_tab(self) -> None:
        """创建告警设置选项卡"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="告警设置")
        
        # 启用告警
        self.variables['alerts_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用告警", variable=self.variables['alerts_enabled']).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 高溢价阈值
        ttk.Label(frame, text="高溢价阈值(%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['high_premium_threshold'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['high_premium_threshold'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 低溢价阈值
        ttk.Label(frame, text="低溢价阈值(%):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['low_premium_threshold'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['low_premium_threshold'], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 价格变化阈值
        ttk.Label(frame, text="价格变化阈值(%):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['price_change_threshold'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.variables['price_change_threshold'], width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 声音提醒
        self.variables['sound_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用声音提醒", variable=self.variables['sound_enabled']).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 声音音量
        ttk.Label(frame, text="声音音量:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.variables['sound_volume'] = tk.StringVar()
        volume_scale = ttk.Scale(frame, from_=0, to=1, orient=tk.HORIZONTAL, length=200)
        volume_scale.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 绑定音量滑块
        def on_volume_change(value):
            self.variables['sound_volume'].set(f"{float(value):.1f}")
        
        volume_scale.config(command=on_volume_change)
        
        # 音量标签
        volume_label = ttk.Label(frame, textvariable=self.variables['sound_volume'])
        volume_label.grid(row=5, column=2, sticky=tk.W, padx=5, pady=5)
    
    def create_button_frame(self) -> None:
        """创建按钮框架"""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 确定按钮
        ttk.Button(button_frame, text="确定", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        
        # 取消按钮
        ttk.Button(button_frame, text="取消", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # 应用按钮
        ttk.Button(button_frame, text="应用", command=self.on_apply).pack(side=tk.RIGHT, padx=5)
        
        # 重置按钮
        ttk.Button(button_frame, text="重置", command=self.on_reset).pack(side=tk.LEFT, padx=5)
        
        # 导入按钮
        ttk.Button(button_frame, text="导入", command=self.on_import).pack(side=tk.LEFT, padx=5)
        
        # 导出按钮
        ttk.Button(button_frame, text="导出", command=self.on_export).pack(side=tk.LEFT, padx=5)
    
    def load_config(self) -> None:
        """加载配置到界面"""
        try:
            # 备份原始配置
            self.original_config = self.config_manager.config.copy()
            
            # API设置
            self.variables['api_key'].set(self.config_manager.get('api.finnhub_api_key', ''))
            self.variables['request_timeout'].set(str(self.config_manager.get('api.request_timeout', 10)))
            self.variables['retry_count'].set(str(self.config_manager.get('api.retry_count', 3)))
            self.variables['retry_delay'].set(str(self.config_manager.get('api.retry_delay', 1.0)))
            self.variables['rate_limit_interval'].set(str(self.config_manager.get('api.rate_limit_interval', 0.5)))
            
            # 监控设置
            self.variables['default_interval'].set(str(self.config_manager.get('monitor.default_interval', 10)))
            self.variables['max_data_points'].set(str(self.config_manager.get('monitor.max_data_points', 1000)))
            self.variables['btc_per_share'].set(str(self.config_manager.get('monitor.btc_per_share', 0.00207973)))
            self.variables['auto_start'].set(self.config_manager.get('monitor.auto_start', False))
            self.variables['auto_cleanup_hours'].set(str(self.config_manager.get('monitor.auto_cleanup_hours', 24)))
            
            # UI设置
            self.variables['window_width'].set(str(self.config_manager.get('ui.window_width', 1000)))
            self.variables['window_height'].set(str(self.config_manager.get('ui.window_height', 700)))
            
            # 时间范围映射
            time_range_map = {
                1800: "30分钟", 3600: "1小时", 7200: "2小时", 
                14400: "4小时", 28800: "8小时", 86400: "1天"
            }
            time_range_seconds = self.config_manager.get('ui.default_time_range', 3600)
            self.variables['default_time_range'].set(time_range_map.get(time_range_seconds, "1小时"))
            
            self.variables['theme'].set(self.config_manager.get('ui.theme', 'default'))
            self.variables['font_size'].set(str(self.config_manager.get('ui.font_size', 10)))
            self.variables['always_on_top'].set(self.config_manager.get('ui.always_on_top', False))
            self.variables['minimize_to_tray'].set(self.config_manager.get('ui.minimize_to_tray', False))
            
            # 图表设置
            self.variables['line_color'].set(self.config_manager.get('chart.line_color', '#1f77b4'))
            self.variables['line_width'].set(str(self.config_manager.get('chart.line_width', 2)))
            self.variables['grid_alpha'].set(str(self.config_manager.get('chart.grid_alpha', 0.3)))
            self.variables['animation_interval'].set(str(self.config_manager.get('chart.animation_interval', 1000)))
            self.variables['background_color'].set(self.config_manager.get('chart.background_color', '#f8f9fa'))
            self.variables['show_grid'].set(self.config_manager.get('chart.show_grid', True))
            self.variables['show_legend'].set(self.config_manager.get('chart.show_legend', True))
            
            # 告警设置
            self.variables['alerts_enabled'].set(self.config_manager.get('alerts.enabled', False))
            self.variables['high_premium_threshold'].set(str(self.config_manager.get('alerts.high_premium_threshold', 50.0)))
            self.variables['low_premium_threshold'].set(str(self.config_manager.get('alerts.low_premium_threshold', -10.0)))
            self.variables['price_change_threshold'].set(str(self.config_manager.get('alerts.price_change_threshold', 5.0)))
            self.variables['sound_enabled'].set(self.config_manager.get('alerts.sound_enabled', True))
            self.variables['sound_volume'].set(str(self.config_manager.get('alerts.sound_volume', 0.5)))
            
            self.logger.debug("配置已加载到界面")
            
        except Exception as e:
            self.logger.error(f"加载配置时发生错误: {e}")
            messagebox.showerror("错误", f"加载配置时发生错误: {str(e)}")
    
    def save_config(self) -> Dict[str, Any]:
        """保存配置"""
        try:
            # 构建新配置
            new_config = {}
            
            # API设置
            new_config['api'] = {
                'finnhub_api_key': self.variables['api_key'].get(),
                'request_timeout': int(self.variables['request_timeout'].get()),
                'retry_count': int(self.variables['retry_count'].get()),
                'retry_delay': float(self.variables['retry_delay'].get()),
                'rate_limit_interval': float(self.variables['rate_limit_interval'].get())
            }
            
            # 监控设置
            new_config['monitor'] = {
                'default_interval': int(self.variables['default_interval'].get()),
                'max_data_points': int(self.variables['max_data_points'].get()),
                'btc_per_share': float(self.variables['btc_per_share'].get()),
                'auto_start': self.variables['auto_start'].get(),
                'auto_cleanup_hours': int(self.variables['auto_cleanup_hours'].get())
            }
            
            # UI设置
            time_range_map = {
                "30分钟": 1800, "1小时": 3600, "2小时": 7200, 
                "4小时": 14400, "8小时": 28800, "1天": 86400
            }
            
            new_config['ui'] = {
                'window_width': int(self.variables['window_width'].get()),
                'window_height': int(self.variables['window_height'].get()),
                'default_time_range': time_range_map.get(self.variables['default_time_range'].get(), 3600),
                'theme': self.variables['theme'].get(),
                'font_size': int(self.variables['font_size'].get()),
                'always_on_top': self.variables['always_on_top'].get(),
                'minimize_to_tray': self.variables['minimize_to_tray'].get()
            }
            
            # 图表设置
            new_config['chart'] = {
                'line_color': self.variables['line_color'].get(),
                'line_width': int(self.variables['line_width'].get()),
                'grid_alpha': float(self.variables['grid_alpha'].get()),
                'animation_interval': int(self.variables['animation_interval'].get()),
                'background_color': self.variables['background_color'].get(),
                'show_grid': self.variables['show_grid'].get(),
                'show_legend': self.variables['show_legend'].get()
            }
            
            # 告警设置
            new_config['alerts'] = {
                'enabled': self.variables['alerts_enabled'].get(),
                'high_premium_threshold': float(self.variables['high_premium_threshold'].get()),
                'low_premium_threshold': float(self.variables['low_premium_threshold'].get()),
                'price_change_threshold': float(self.variables['price_change_threshold'].get()),
                'sound_enabled': self.variables['sound_enabled'].get(),
                'sound_volume': float(self.variables['sound_volume'].get())
            }
            
            # 验证配置
            is_valid, errors = validate_config(new_config)
            if not is_valid:
                messagebox.showerror("配置错误", "配置验证失败:\\n" + "\\n".join(errors))
                return None
            
            # 更新配置管理器
            self.config_manager.update_config(new_config)
            
            self.logger.info("配置已保存")
            return new_config
            
        except ValueError as e:
            messagebox.showerror("输入错误", f"请检查输入值的格式: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"保存配置时发生错误: {e}")
            messagebox.showerror("错误", f"保存配置时发生错误: {str(e)}")
            return None
    
    def test_api_connection(self) -> None:
        """测试API连接"""
        try:
            api_key = self.variables['api_key'].get()
            
            if not validate_api_key(api_key):
                messagebox.showerror("错误", "API密钥格式无效")
                return
            
            # 创建临时API客户端测试
            from ...core.api_client import APIClient
            temp_client = APIClient(api_key)
            
            if temp_client.test_connection():
                messagebox.showinfo("成功", "API连接测试成功！")
            else:
                messagebox.showerror("失败", "API连接测试失败，请检查密钥和网络连接")
                
        except Exception as e:
            self.logger.error(f"测试API连接时发生错误: {e}")
            messagebox.showerror("错误", f"测试API连接时发生错误: {str(e)}")
    
    def on_ok(self) -> None:
        """确定按钮点击"""
        new_config = self.save_config()
        if new_config is not None:
            # 调用回调函数
            if self.callback:
                self.callback(new_config)
            
            self.close_dialog()
    
    def on_cancel(self) -> None:
        """取消按钮点击"""
        # 恢复原始配置
        if self.original_config:
            self.config_manager.config = self.original_config.copy()
        
        self.close_dialog()
    
    def on_apply(self) -> None:
        """应用按钮点击"""
        new_config = self.save_config()
        if new_config is not None:
            # 调用回调函数
            if self.callback:
                self.callback(new_config)
            
            messagebox.showinfo("成功", "设置已应用")
    
    def on_reset(self) -> None:
        """重置按钮点击"""
        if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            self.config_manager.reset_to_default()
            self.load_config()
            messagebox.showinfo("成功", "设置已重置为默认值")
    
    def on_import(self) -> None:
        """导入按钮点击"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            if self.config_manager.import_config(filename):
                self.load_config()
                messagebox.showinfo("成功", "配置导入成功")
            else:
                messagebox.showerror("错误", "配置导入失败")
    
    def on_export(self) -> None:
        """导出按钮点击"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            if self.config_manager.export_config(filename):
                messagebox.showinfo("成功", "配置导出成功")
            else:
                messagebox.showerror("错误", "配置导出失败")
    
    def center_dialog(self) -> None:
        """居中显示对话框"""
        self.dialog.update_idletasks()
        
        # 获取对话框大小
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        
        # 获取父窗口位置和大小
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def close_dialog(self) -> None:
        """关闭对话框"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
    
    def set_callback(self, callback: Callable) -> None:
        """设置回调函数"""
        self.callback = callback