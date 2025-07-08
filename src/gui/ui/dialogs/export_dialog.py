"""
导出对话框 - 数据导出功能界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime, timedelta
from ...core.data_manager import PremiumData
from ...utils.helpers import format_timestamp, get_app_data_dir


class ExportDialog:
    """导出对话框"""
    
    def __init__(self, parent: tk.Widget, data_manager: PremiumData):
        """
        初始化导出对话框
        
        Args:
            parent: 父窗口
            data_manager: 数据管理器
        """
        self.parent = parent
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        
        # 对话框窗口
        self.dialog = None
        
        # 导出选项变量
        self.export_vars = {}
        
        # 回调函数
        self.callback = None
        
        self.logger.info("导出对话框初始化完成")
    
    def show(self) -> None:
        """显示对话框"""
        if self.dialog is not None:
            # 如果对话框已存在，激活它
            self.dialog.lift()
            self.dialog.focus_set()
            return
        
        # 创建新对话框
        self.create_dialog()
        
        # 初始化选项
        self.initialize_options()
        
        # 显示对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.focus_set()
        
        # 居中显示
        self.center_dialog()
        
        self.logger.debug("导出对话框已显示")
    
    def create_dialog(self) -> None:
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("导出数据")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        # 设置对话框关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # 创建主框架
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个区域
        self.create_file_selection_frame(main_frame)
        self.create_data_options_frame(main_frame)
        self.create_time_range_frame(main_frame)
        self.create_format_options_frame(main_frame)
        self.create_preview_frame(main_frame)
        self.create_button_frame(main_frame)
    
    def create_file_selection_frame(self, parent: tk.Widget) -> None:
        """创建文件选择框架"""
        frame = ttk.LabelFrame(parent, text="文件设置", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文件名
        ttk.Label(frame, text="文件名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.export_vars['filename'] = tk.StringVar()
        default_filename = f"mstr_premium_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.export_vars['filename'].set(default_filename)
        
        filename_entry = ttk.Entry(frame, textvariable=self.export_vars['filename'], width=30)
        filename_entry.grid(row=0, column=1, padx=5)
        
        # 浏览按钮
        ttk.Button(frame, text="浏览", command=self.browse_file).grid(row=0, column=2, padx=5)
        
        # 保存位置
        ttk.Label(frame, text="保存位置:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        
        self.export_vars['directory'] = tk.StringVar()
        default_dir = get_app_data_dir()
        self.export_vars['directory'].set(default_dir)
        
        dir_entry = ttk.Entry(frame, textvariable=self.export_vars['directory'], width=30)
        dir_entry.grid(row=1, column=1, padx=5, pady=(10, 0))
        
        # 浏览文件夹按钮
        ttk.Button(frame, text="浏览", command=self.browse_directory).grid(row=1, column=2, padx=5, pady=(10, 0))
    
    def create_data_options_frame(self, parent: tk.Widget) -> None:
        """创建数据选项框架"""
        frame = ttk.LabelFrame(parent, text="数据选项", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 包含字段
        ttk.Label(frame, text="包含字段:").grid(row=0, column=0, sticky=tk.NW, padx=(0, 10))
        
        fields_frame = ttk.Frame(frame)
        fields_frame.grid(row=0, column=1, sticky=tk.W)
        
        # 字段选择
        self.export_vars['include_timestamp'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(fields_frame, text="时间戳", variable=self.export_vars['include_timestamp']).grid(row=0, column=0, sticky=tk.W)
        
        self.export_vars['include_mstr_price'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(fields_frame, text="MSTR价格", variable=self.export_vars['include_mstr_price']).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.export_vars['include_btc_price'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(fields_frame, text="BTC价格", variable=self.export_vars['include_btc_price']).grid(row=1, column=0, sticky=tk.W)
        
        self.export_vars['include_premium'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(fields_frame, text="溢价率", variable=self.export_vars['include_premium']).grid(row=1, column=1, sticky=tk.W, padx=(20, 0))
        
        # 数据排序
        ttk.Label(frame, text="排序方式:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        self.export_vars['sort_order'] = tk.StringVar(value="时间升序")
        sort_combo = ttk.Combobox(frame, textvariable=self.export_vars['sort_order'], 
                                 values=["时间升序", "时间降序"], 
                                 state="readonly", width=15)
        sort_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
    
    def create_time_range_frame(self, parent: tk.Widget) -> None:
        """创建时间范围框架"""
        frame = ttk.LabelFrame(parent, text="时间范围", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 时间范围选择
        self.export_vars['time_range'] = tk.StringVar(value="全部数据")
        
        ttk.Radiobutton(frame, text="全部数据", variable=self.export_vars['time_range'], 
                       value="全部数据").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(frame, text="最近1小时", variable=self.export_vars['time_range'], 
                       value="最近1小时").grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        ttk.Radiobutton(frame, text="最近24小时", variable=self.export_vars['time_range'], 
                       value="最近24小时").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        
        ttk.Radiobutton(frame, text="自定义范围", variable=self.export_vars['time_range'], 
                       value="自定义范围").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        # 自定义时间范围
        custom_frame = ttk.Frame(frame)
        custom_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(10, 0))
        
        ttk.Label(custom_frame, text="从:").grid(row=0, column=0, sticky=tk.W)
        
        self.export_vars['start_time'] = tk.StringVar()
        start_entry = ttk.Entry(custom_frame, textvariable=self.export_vars['start_time'], width=16)
        start_entry.grid(row=0, column=1, padx=(5, 10))
        
        ttk.Label(custom_frame, text="到:").grid(row=0, column=2, sticky=tk.W)
        
        self.export_vars['end_time'] = tk.StringVar()
        end_entry = ttk.Entry(custom_frame, textvariable=self.export_vars['end_time'], width=16)
        end_entry.grid(row=0, column=3, padx=(5, 0))
        
        # 时间格式说明
        ttk.Label(custom_frame, text="格式: YYYY-MM-DD HH:MM:SS", 
                 font=('Arial', 8), foreground='gray').grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(2, 0))
    
    def create_format_options_frame(self, parent: tk.Widget) -> None:
        """创建格式选项框架"""
        frame = ttk.LabelFrame(parent, text="格式选项", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文件格式
        ttk.Label(frame, text="文件格式:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.export_vars['file_format'] = tk.StringVar(value="CSV")
        format_combo = ttk.Combobox(frame, textvariable=self.export_vars['file_format'], 
                                   values=["CSV", "JSON", "Excel"], 
                                   state="readonly", width=10)
        format_combo.grid(row=0, column=1, sticky=tk.W)
        
        # CSV选项
        csv_frame = ttk.Frame(frame)
        csv_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(csv_frame, text="CSV选项:").grid(row=0, column=0, sticky=tk.W)
        
        self.export_vars['csv_delimiter'] = tk.StringVar(value=",")
        ttk.Label(csv_frame, text="分隔符:").grid(row=0, column=1, sticky=tk.W, padx=(20, 5))
        delimiter_combo = ttk.Combobox(csv_frame, textvariable=self.export_vars['csv_delimiter'], 
                                      values=[",", ";", "\t"], 
                                      state="readonly", width=8)
        delimiter_combo.grid(row=0, column=2, sticky=tk.W)
        
        self.export_vars['include_headers'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(csv_frame, text="包含标题行", 
                       variable=self.export_vars['include_headers']).grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        
        # 数值格式
        ttk.Label(frame, text="数值格式:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        self.export_vars['decimal_places'] = tk.StringVar(value="2")
        decimal_combo = ttk.Combobox(frame, textvariable=self.export_vars['decimal_places'], 
                                    values=["2", "3", "4", "6"], 
                                    state="readonly", width=8)
        decimal_combo.grid(row=2, column=1, sticky=tk.W, pady=(10, 0))
    
    def create_preview_frame(self, parent: tk.Widget) -> None:
        """创建预览框架"""
        frame = ttk.LabelFrame(parent, text="预览", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 预览文本
        self.preview_text = tk.Text(frame, height=6, width=60, font=('Courier', 9))
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.config(yscrollcommand=scrollbar.set)
        
        # 预览按钮
        ttk.Button(frame, text="预览数据", command=self.preview_data).pack(pady=(10, 0))
    
    def create_button_frame(self, parent: tk.Widget) -> None:
        """创建按钮框架"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(10, 0))
        
        # 导出按钮
        ttk.Button(frame, text="导出", command=self.on_export).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 取消按钮
        ttk.Button(frame, text="取消", command=self.on_cancel).pack(side=tk.RIGHT)
        
        # 帮助按钮
        ttk.Button(frame, text="帮助", command=self.show_help).pack(side=tk.LEFT)
    
    def initialize_options(self) -> None:
        """初始化选项"""
        try:
            # 设置默认时间范围
            now = datetime.now()
            start_time = now - timedelta(hours=1)
            
            self.export_vars['start_time'].set(start_time.strftime('%Y-%m-%d %H:%M:%S'))
            self.export_vars['end_time'].set(now.strftime('%Y-%m-%d %H:%M:%S'))
            
            # 更新预览
            self.preview_data()
            
        except Exception as e:
            self.logger.error(f"初始化选项时发生错误: {e}")
    
    def browse_file(self) -> None:
        """浏览文件"""
        try:
            filename = filedialog.asksaveasfilename(
                title="选择导出文件",
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("JSON files", "*.json"),
                    ("Excel files", "*.xlsx"),
                    ("All files", "*.*")
                ]
            )
            
            if filename:
                # 分离目录和文件名
                directory = os.path.dirname(filename)
                basename = os.path.basename(filename)
                
                self.export_vars['directory'].set(directory)
                
                # 移除扩展名
                name_without_ext = os.path.splitext(basename)[0]
                self.export_vars['filename'].set(name_without_ext)
                
        except Exception as e:
            self.logger.error(f"浏览文件时发生错误: {e}")
            messagebox.showerror("错误", f"浏览文件时发生错误: {str(e)}")
    
    def browse_directory(self) -> None:
        """浏览目录"""
        try:
            directory = filedialog.askdirectory(
                title="选择保存目录",
                initialdir=self.export_vars['directory'].get()
            )
            
            if directory:
                self.export_vars['directory'].set(directory)
                
        except Exception as e:
            self.logger.error(f"浏览目录时发生错误: {e}")
            messagebox.showerror("错误", f"浏览目录时发生错误: {str(e)}")
    
    def preview_data(self) -> None:
        """预览数据"""
        try:
            # 获取数据
            data = self.get_filtered_data()
            
            if not data:
                self.preview_text.delete(1.0, tk.END)
                self.preview_text.insert(tk.END, "没有可导出的数据")
                return
            
            # 生成预览
            preview_lines = []
            
            # 添加标题行
            if self.export_vars['include_headers'].get():
                headers = []
                if self.export_vars['include_timestamp'].get():
                    headers.append("时间戳")
                if self.export_vars['include_mstr_price'].get():
                    headers.append("MSTR价格")
                if self.export_vars['include_btc_price'].get():
                    headers.append("BTC价格")
                if self.export_vars['include_premium'].get():
                    headers.append("溢价率")
                
                delimiter = self.export_vars['csv_delimiter'].get()
                preview_lines.append(delimiter.join(headers))
            
            # 添加数据行（最多显示5行）
            decimal_places = int(self.export_vars['decimal_places'].get())
            for i, (timestamp, mstr_price, btc_price, premium) in enumerate(data[:5]):
                row = []
                
                if self.export_vars['include_timestamp'].get():
                    row.append(format_timestamp(timestamp))
                if self.export_vars['include_mstr_price'].get():
                    row.append(f"{mstr_price:.{decimal_places}f}")
                if self.export_vars['include_btc_price'].get():
                    row.append(f"{btc_price:.{decimal_places}f}")
                if self.export_vars['include_premium'].get():
                    row.append(f"{premium:.{decimal_places}f}")
                
                delimiter = self.export_vars['csv_delimiter'].get()
                preview_lines.append(delimiter.join(row))
            
            # 如果有更多数据，添加提示
            if len(data) > 5:
                preview_lines.append(f"... 还有 {len(data) - 5} 行数据")
            
            # 显示预览
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "\n".join(preview_lines))
            
            # 添加统计信息
            stats = f"\n\n统计信息:\n总数据点: {len(data)}\n"
            if data:
                stats += f"时间范围: {format_timestamp(data[0][0])} 至 {format_timestamp(data[-1][0])}"
            
            self.preview_text.insert(tk.END, stats)
            
        except Exception as e:
            self.logger.error(f"预览数据时发生错误: {e}")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"预览失败: {str(e)}")
    
    def get_filtered_data(self) -> list:
        """获取过滤后的数据"""
        try:
            # 获取所有数据
            all_data = self.data_manager.get_all_data()
            
            if not all_data:
                return []
            
            # 时间范围过滤
            time_range = self.export_vars['time_range'].get()
            now = datetime.now()
            
            if time_range == "最近1小时":
                start_time = now - timedelta(hours=1)
                filtered_data = [d for d in all_data if d[0] >= start_time]
            elif time_range == "最近24小时":
                start_time = now - timedelta(hours=24)
                filtered_data = [d for d in all_data if d[0] >= start_time]
            elif time_range == "自定义范围":
                try:
                    start_str = self.export_vars['start_time'].get()
                    end_str = self.export_vars['end_time'].get()
                    
                    start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
                    
                    filtered_data = [d for d in all_data if start_time <= d[0] <= end_time]
                except ValueError:
                    messagebox.showerror("错误", "时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
                    return []
            else:  # 全部数据
                filtered_data = all_data
            
            # 排序
            sort_order = self.export_vars['sort_order'].get()
            if sort_order == "时间降序":
                filtered_data.sort(key=lambda x: x[0], reverse=True)
            else:  # 时间升序
                filtered_data.sort(key=lambda x: x[0])
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"获取过滤数据时发生错误: {e}")
            return []
    
    def on_export(self) -> None:
        """导出按钮点击"""
        try:
            # 验证输入
            if not self.validate_inputs():
                return
            
            # 获取数据
            data = self.get_filtered_data()
            
            if not data:
                messagebox.showwarning("警告", "没有可导出的数据")
                return
            
            # 构建文件路径
            filename = self.export_vars['filename'].get()
            directory = self.export_vars['directory'].get()
            file_format = self.export_vars['file_format'].get()
            
            if file_format == "CSV":
                extension = ".csv"
            elif file_format == "JSON":
                extension = ".json"
            elif file_format == "Excel":
                extension = ".xlsx"
            else:
                extension = ".csv"
            
            if not filename.endswith(extension):
                filename += extension
            
            filepath = os.path.join(directory, filename)
            
            # 导出数据
            success = self.export_data(data, filepath)
            
            if success:
                messagebox.showinfo("成功", f"数据已成功导出到:\n{filepath}")
                
                # 调用回调函数
                if self.callback:
                    self.callback(filepath)
                
                self.close_dialog()
            else:
                messagebox.showerror("错误", "导出失败")
                
        except Exception as e:
            self.logger.error(f"导出时发生错误: {e}")
            messagebox.showerror("错误", f"导出时发生错误: {str(e)}")
    
    def validate_inputs(self) -> bool:
        """验证输入"""
        try:
            # 验证文件名
            filename = self.export_vars['filename'].get().strip()
            if not filename:
                messagebox.showerror("错误", "请输入文件名")
                return False
            
            # 验证目录
            directory = self.export_vars['directory'].get().strip()
            if not directory:
                messagebox.showerror("错误", "请选择保存目录")
                return False
            
            if not os.path.exists(directory):
                messagebox.showerror("错误", "保存目录不存在")
                return False
            
            # 验证字段选择
            if not any([
                self.export_vars['include_timestamp'].get(),
                self.export_vars['include_mstr_price'].get(),
                self.export_vars['include_btc_price'].get(),
                self.export_vars['include_premium'].get()
            ]):
                messagebox.showerror("错误", "请至少选择一个字段")
                return False
            
            # 验证自定义时间范围
            if self.export_vars['time_range'].get() == "自定义范围":
                try:
                    start_str = self.export_vars['start_time'].get()
                    end_str = self.export_vars['end_time'].get()
                    
                    start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
                    
                    if start_time >= end_time:
                        messagebox.showerror("错误", "开始时间必须早于结束时间")
                        return False
                        
                except ValueError:
                    messagebox.showerror("错误", "时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS 格式")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证输入时发生错误: {e}")
            return False
    
    def export_data(self, data: list, filepath: str) -> bool:
        """导出数据到文件"""
        try:
            file_format = self.export_vars['file_format'].get()
            
            if file_format == "CSV":
                return self.export_to_csv(data, filepath)
            elif file_format == "JSON":
                return self.export_to_json(data, filepath)
            elif file_format == "Excel":
                return self.export_to_excel(data, filepath)
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"导出数据时发生错误: {e}")
            return False
    
    def export_to_csv(self, data: list, filepath: str) -> bool:
        """导出为CSV格式"""
        try:
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as file:
                delimiter = self.export_vars['csv_delimiter'].get()
                writer = csv.writer(file, delimiter=delimiter)
                
                # 写入标题行
                if self.export_vars['include_headers'].get():
                    headers = []
                    if self.export_vars['include_timestamp'].get():
                        headers.append("时间戳")
                    if self.export_vars['include_mstr_price'].get():
                        headers.append("MSTR价格")
                    if self.export_vars['include_btc_price'].get():
                        headers.append("BTC价格")
                    if self.export_vars['include_premium'].get():
                        headers.append("溢价率")
                    
                    writer.writerow(headers)
                
                # 写入数据行
                decimal_places = int(self.export_vars['decimal_places'].get())
                for timestamp, mstr_price, btc_price, premium in data:
                    row = []
                    
                    if self.export_vars['include_timestamp'].get():
                        row.append(format_timestamp(timestamp))
                    if self.export_vars['include_mstr_price'].get():
                        row.append(f"{mstr_price:.{decimal_places}f}")
                    if self.export_vars['include_btc_price'].get():
                        row.append(f"{btc_price:.{decimal_places}f}")
                    if self.export_vars['include_premium'].get():
                        row.append(f"{premium:.{decimal_places}f}")
                    
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出CSV时发生错误: {e}")
            return False
    
    def export_to_json(self, data: list, filepath: str) -> bool:
        """导出为JSON格式"""
        try:
            import json
            
            # 构建JSON数据
            json_data = []
            decimal_places = int(self.export_vars['decimal_places'].get())
            
            for timestamp, mstr_price, btc_price, premium in data:
                record = {}
                
                if self.export_vars['include_timestamp'].get():
                    record['timestamp'] = format_timestamp(timestamp)
                if self.export_vars['include_mstr_price'].get():
                    record['mstr_price'] = round(mstr_price, decimal_places)
                if self.export_vars['include_btc_price'].get():
                    record['btc_price'] = round(btc_price, decimal_places)
                if self.export_vars['include_premium'].get():
                    record['premium'] = round(premium, decimal_places)
                
                json_data.append(record)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(json_data, file, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出JSON时发生错误: {e}")
            return False
    
    def export_to_excel(self, data: list, filepath: str) -> bool:
        """导出为Excel格式"""
        try:
            try:
                import pandas as pd
            except ImportError:
                messagebox.showerror("错误", "需要安装pandas库才能导出Excel格式")
                return False
            
            # 构建DataFrame
            df_data = {}
            decimal_places = int(self.export_vars['decimal_places'].get())
            
            if self.export_vars['include_timestamp'].get():
                df_data['时间戳'] = [format_timestamp(d[0]) for d in data]
            if self.export_vars['include_mstr_price'].get():
                df_data['MSTR价格'] = [round(d[1], decimal_places) for d in data]
            if self.export_vars['include_btc_price'].get():
                df_data['BTC价格'] = [round(d[2], decimal_places) for d in data]
            if self.export_vars['include_premium'].get():
                df_data['溢价率'] = [round(d[3], decimal_places) for d in data]
            
            df = pd.DataFrame(df_data)
            
            # 写入Excel文件
            df.to_excel(filepath, index=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出Excel时发生错误: {e}")
            return False
    
    def show_help(self) -> None:
        """显示帮助信息"""
        help_text = """
数据导出帮助

文件设置:
• 文件名: 导出文件的名称（不包含扩展名）
• 保存位置: 文件保存的目录

数据选项:
• 包含字段: 选择要导出的数据字段
• 排序方式: 选择数据的排序方式

时间范围:
• 全部数据: 导出所有可用数据
• 最近1小时/24小时: 导出最近时间段的数据
• 自定义范围: 指定具体的时间范围

格式选项:
• 文件格式: 选择导出格式（CSV、JSON、Excel）
• CSV选项: 设置CSV分隔符和是否包含标题行
• 数值格式: 设置数值的小数位数

注意事项:
• Excel格式需要安装pandas库
• 自定义时间范围使用格式: YYYY-MM-DD HH:MM:SS
• 预览功能可以查看导出数据的样本
        """
        
        messagebox.showinfo("帮助", help_text)
    
    def on_cancel(self) -> None:
        """取消按钮点击"""
        self.close_dialog()
    
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