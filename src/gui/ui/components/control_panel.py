"""
控制面板组件 - 提供用户控制功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, Dict, Any
import logging
from datetime import datetime
from ...utils.helpers import format_duration


class ControlPanel:
    """控制面板"""
    
    def __init__(self, parent: tk.Widget):
        """
        初始化控制面板
        
        Args:
            parent: 父级组件
        """
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        
        # 回调函数
        self.callbacks = {
            'start_monitoring': None,
            'stop_monitoring': None,
            'clear_data': None,
            'open_settings': None,
            'export_data': None,
            'interval_changed': None,
            'timerange_changed': None
        }
        
        # 控制状态
        self.monitoring_state = False
        
        # 创建UI
        self.create_ui()
        
        self.logger.info("控制面板初始化完成")
    
    def create_ui(self) -> None:
        """创建用户界面"""
        # 主框架
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建按钮区域
        self.create_buttons()
        
        # 创建设置区域
        self.create_settings()
    
    def create_buttons(self) -> None:
        """创建控制按钮"""
        # 按钮框架
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 开始监控按钮
        self.start_button = ttk.Button(
            button_frame,
            text="开始监控",
            command=self._on_start_monitoring,
            width=12
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 停止监控按钮
        self.stop_button = ttk.Button(
            button_frame,
            text="停止监控",
            command=self._on_stop_monitoring,
            state=tk.DISABLED,
            width=12
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 清除数据按钮
        self.clear_button = ttk.Button(
            button_frame,
            text="清除数据",
            command=self._on_clear_data,
            width=12
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 设置按钮
        self.settings_button = ttk.Button(
            button_frame,
            text="设置",
            command=self._on_open_settings,
            width=12
        )
        self.settings_button.pack(side=tk.LEFT, padx=5)
        
        # 导出CSV按钮
        self.export_button = ttk.Button(
            button_frame,
            text="导出CSV",
            command=self._on_export_data,
            width=12
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # 分隔符
        separator = ttk.Separator(button_frame, orient='vertical')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 帮助按钮
        self.help_button = ttk.Button(
            button_frame,
            text="帮助",
            command=self._on_show_help,
            width=8
        )
        self.help_button.pack(side=tk.LEFT, padx=5)
    
    def create_settings(self) -> None:
        """创建设置控件"""
        # 设置框架
        settings_frame = ttk.Frame(self.frame)
        settings_frame.pack(fill=tk.X)
        
        # 更新间隔设置
        ttk.Label(settings_frame, text="更新间隔:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.interval_var = tk.StringVar(value="10秒")
        self.interval_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.interval_var,
            values=["5秒", "10秒", "15秒", "30秒", "60秒"],
            state="readonly",
            width=8
        )
        self.interval_combo.pack(side=tk.LEFT, padx=5)
        self.interval_combo.bind('<<ComboboxSelected>>', self._on_interval_change)
        
        # 显示时间范围设置
        ttk.Label(settings_frame, text="显示时间:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.timerange_var = tk.StringVar(value="1小时")
        self.timerange_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.timerange_var,
            values=["30分钟", "1小时", "2小时", "4小时", "8小时", "1天"],
            state="readonly",
            width=8
        )
        self.timerange_combo.pack(side=tk.LEFT, padx=5)
        self.timerange_combo.bind('<<ComboboxSelected>>', self._on_timerange_change)
        
        # 自动滚动设置
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(
            settings_frame,
            text="自动滚动",
            variable=self.auto_scroll_var,
            command=self._on_auto_scroll_change
        )
        self.auto_scroll_check.pack(side=tk.LEFT, padx=(20, 5))
        
        # 声音提醒设置
        self.sound_var = tk.BooleanVar(value=False)
        self.sound_check = ttk.Checkbutton(
            settings_frame,
            text="声音提醒",
            variable=self.sound_var,
            command=self._on_sound_change
        )
        self.sound_check.pack(side=tk.LEFT, padx=(20, 5))
        
        # 运行状态指示器
        self.status_indicator = ttk.Label(
            settings_frame,
            text="●",
            font=('Arial', 12),
            foreground='red'
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=5)
        
        self.status_text = ttk.Label(
            settings_frame,
            text="未运行",
            font=('Arial', 9)
        )
        self.status_text.pack(side=tk.RIGHT, padx=(0, 5))
    
    def set_callback(self, event: str, callback: Callable) -> None:
        """
        设置回调函数
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event] = callback
            self.logger.debug(f"设置回调函数: {event}")
        else:
            self.logger.warning(f"未知事件: {event}")
    
    def _on_start_monitoring(self) -> None:
        """开始监控按钮点击事件"""
        try:
            if self.callbacks['start_monitoring']:
                result = self.callbacks['start_monitoring']()
                if result:
                    self.set_monitoring_state(True)
                else:
                    messagebox.showerror("错误", "启动监控失败")
            else:
                messagebox.showwarning("警告", "监控功能未配置")
        except Exception as e:
            self.logger.error(f"启动监控时发生错误: {e}")
            messagebox.showerror("错误", f"启动监控时发生错误: {str(e)}")
    
    def _on_stop_monitoring(self) -> None:
        """停止监控按钮点击事件"""
        try:
            if self.callbacks['stop_monitoring']:
                self.callbacks['stop_monitoring']()
                self.set_monitoring_state(False)
            else:
                messagebox.showwarning("警告", "监控功能未配置")
        except Exception as e:
            self.logger.error(f"停止监控时发生错误: {e}")
            messagebox.showerror("错误", f"停止监控时发生错误: {str(e)}")
    
    def _on_clear_data(self) -> None:
        """清除数据按钮点击事件"""
        try:
            # 确认对话框
            if messagebox.askyesno("确认", "确定要清除所有数据吗？"):
                if self.callbacks['clear_data']:
                    self.callbacks['clear_data']()
                    messagebox.showinfo("成功", "数据已清除")
                else:
                    messagebox.showwarning("警告", "清除数据功能未配置")
        except Exception as e:
            self.logger.error(f"清除数据时发生错误: {e}")
            messagebox.showerror("错误", f"清除数据时发生错误: {str(e)}")
    
    def _on_open_settings(self) -> None:
        """设置按钮点击事件"""
        try:
            if self.callbacks['open_settings']:
                self.callbacks['open_settings']()
            else:
                messagebox.showwarning("警告", "设置功能未配置")
        except Exception as e:
            self.logger.error(f"打开设置时发生错误: {e}")
            messagebox.showerror("错误", f"打开设置时发生错误: {str(e)}")
    
    def _on_export_data(self) -> None:
        """导出数据按钮点击事件"""
        try:
            # 选择保存文件
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="导出数据"
            )
            
            if filename:
                if self.callbacks['export_data']:
                    result = self.callbacks['export_data'](filename)
                    if result:
                        messagebox.showinfo("成功", f"数据已导出到: {filename}")
                    else:
                        messagebox.showerror("错误", "导出数据失败")
                else:
                    messagebox.showwarning("警告", "导出功能未配置")
        except Exception as e:
            self.logger.error(f"导出数据时发生错误: {e}")
            messagebox.showerror("错误", f"导出数据时发生错误: {str(e)}")
    
    def _on_interval_change(self, event) -> None:
        """更新间隔变化事件"""
        try:
            interval_text = self.interval_var.get()
            interval_seconds = self._parse_interval(interval_text)
            
            if self.callbacks['interval_changed']:
                self.callbacks['interval_changed'](interval_seconds)
            
            self.logger.debug(f"更新间隔已更改: {interval_text} ({interval_seconds}秒)")
        except Exception as e:
            self.logger.error(f"更改更新间隔时发生错误: {e}")
    
    def _on_timerange_change(self, event) -> None:
        """时间范围变化事件"""
        try:
            timerange_text = self.timerange_var.get()
            timerange_seconds = self._parse_timerange(timerange_text)
            
            if self.callbacks['timerange_changed']:
                self.callbacks['timerange_changed'](timerange_seconds)
            
            self.logger.debug(f"时间范围已更改: {timerange_text} ({timerange_seconds}秒)")
        except Exception as e:
            self.logger.error(f"更改时间范围时发生错误: {e}")
    
    def _on_auto_scroll_change(self) -> None:
        """自动滚动变化事件"""
        enabled = self.auto_scroll_var.get()
        self.logger.debug(f"自动滚动: {'启用' if enabled else '禁用'}")
    
    def _on_sound_change(self) -> None:
        """声音提醒变化事件"""
        enabled = self.sound_var.get()
        self.logger.debug(f"声音提醒: {'启用' if enabled else '禁用'}")
    
    def _on_show_help(self) -> None:
        """显示帮助"""
        help_text = """
MSTR/BTC溢价监控帮助

主要功能：
• 开始监控：启动实时数据监控
• 停止监控：停止数据监控
• 清除数据：清空当前图表数据
• 设置：打开设置对话框
• 导出CSV：导出历史数据

设置选项：
• 更新间隔：设置数据更新频率
• 显示时间：设置图表显示的时间范围
• 自动滚动：自动滚动到最新数据
• 声音提醒：启用声音提醒功能

快捷键：
• Ctrl+S：开始/停止监控
• Ctrl+C：清除数据
• Ctrl+E：导出数据
• F1：显示帮助

注意事项：
• 确保Chrome浏览器以调试模式运行
• 需要有效的API密钥才能获取数据
• 数据仅在内存中存储，关闭应用后会丢失
        """
        
        messagebox.showinfo("帮助", help_text)
    
    def _parse_interval(self, interval_text: str) -> int:
        """
        解析更新间隔文本
        
        Args:
            interval_text: 间隔文本
            
        Returns:
            间隔秒数
        """
        mapping = {
            "5秒": 5,
            "10秒": 10,
            "15秒": 15,
            "30秒": 30,
            "60秒": 60
        }
        return mapping.get(interval_text, 10)
    
    def _parse_timerange(self, timerange_text: str) -> int:
        """
        解析时间范围文本
        
        Args:
            timerange_text: 时间范围文本
            
        Returns:
            时间范围秒数
        """
        mapping = {
            "30分钟": 30 * 60,
            "1小时": 60 * 60,
            "2小时": 2 * 60 * 60,
            "4小时": 4 * 60 * 60,
            "8小时": 8 * 60 * 60,
            "1天": 24 * 60 * 60
        }
        return mapping.get(timerange_text, 60 * 60)
    
    def set_monitoring_state(self, is_running: bool) -> None:
        """
        设置监控状态
        
        Args:
            is_running: 是否正在运行
        """
        self.monitoring_state = is_running
        
        if is_running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_indicator.config(foreground='green')
            self.status_text.config(text="运行中")
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_indicator.config(foreground='red')
            self.status_text.config(text="未运行")
    
    def get_current_settings(self) -> Dict[str, Any]:
        """
        获取当前设置
        
        Returns:
            设置字典
        """
        return {
            'interval': self._parse_interval(self.interval_var.get()),
            'timerange': self._parse_timerange(self.timerange_var.get()),
            'auto_scroll': self.auto_scroll_var.get(),
            'sound_enabled': self.sound_var.get(),
            'monitoring_state': self.monitoring_state
        }
    
    def set_settings(self, settings: Dict[str, Any]) -> None:
        """
        设置配置
        
        Args:
            settings: 设置字典
        """
        try:
            # 设置更新间隔
            if 'interval' in settings:
                interval_seconds = settings['interval']
                for text, seconds in [("5秒", 5), ("10秒", 10), ("15秒", 15), ("30秒", 30), ("60秒", 60)]:
                    if seconds == interval_seconds:
                        self.interval_var.set(text)
                        break
            
            # 设置时间范围
            if 'timerange' in settings:
                timerange_seconds = settings['timerange']
                for text, seconds in [("30分钟", 1800), ("1小时", 3600), ("2小时", 7200), 
                                     ("4小时", 14400), ("8小时", 28800), ("1天", 86400)]:
                    if seconds == timerange_seconds:
                        self.timerange_var.set(text)
                        break
            
            # 设置自动滚动
            if 'auto_scroll' in settings:
                self.auto_scroll_var.set(settings['auto_scroll'])
            
            # 设置声音提醒
            if 'sound_enabled' in settings:
                self.sound_var.set(settings['sound_enabled'])
            
            # 设置监控状态
            if 'monitoring_state' in settings:
                self.set_monitoring_state(settings['monitoring_state'])
            
            self.logger.debug("控制面板设置已更新")
            
        except Exception as e:
            self.logger.error(f"设置配置时发生错误: {e}")
    
    def enable_controls(self, enabled: bool = True) -> None:
        """
        启用/禁用控件
        
        Args:
            enabled: 是否启用
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        
        # 根据监控状态设置按钮
        if not self.monitoring_state:
            self.start_button.config(state=state)
        if self.monitoring_state:
            self.stop_button.config(state=state)
        
        self.clear_button.config(state=state)
        self.settings_button.config(state=state)
        self.export_button.config(state=state)
        self.help_button.config(state=state)
        
        # 设置组合框
        combo_state = "readonly" if enabled else "disabled"
        self.interval_combo.config(state=combo_state)
        self.timerange_combo.config(state=combo_state)
        
        # 设置复选框
        checkbox_state = tk.NORMAL if enabled else tk.DISABLED
        self.auto_scroll_check.config(state=checkbox_state)
        self.sound_check.config(state=checkbox_state)
    
    def setup_keyboard_shortcuts(self, root: tk.Tk) -> None:
        """
        设置键盘快捷键
        
        Args:
            root: 根窗口
        """
        root.bind('<Control-s>', lambda e: self._on_start_monitoring() if not self.monitoring_state else self._on_stop_monitoring())
        root.bind('<Control-c>', lambda e: self._on_clear_data())
        root.bind('<Control-e>', lambda e: self._on_export_data())
        root.bind('<F1>', lambda e: self._on_show_help())
        
        self.logger.debug("键盘快捷键已设置")


# 便捷函数
def create_control_panel(parent: tk.Widget) -> ControlPanel:
    """
    创建控制面板
    
    Args:
        parent: 父级组件
        
    Returns:
        控制面板实例
    """
    return ControlPanel(parent)