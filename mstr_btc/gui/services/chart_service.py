"""
图表服务模块 - 管理实时图表显示和更新
"""

import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.dates import DateFormatter, HourLocator, MinuteLocator
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List, Tuple
from ..core.data_manager import PremiumData


class ChartService:
    """图表服务"""
    
    def __init__(self, parent_frame: tk.Frame, data_manager: PremiumData, 
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化图表服务
        
        Args:
            parent_frame: 父级框架
            data_manager: 数据管理器
            config: 图表配置
        """
        self.parent_frame = parent_frame
        self.data_manager = data_manager
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.config = {
            'line_color': '#1f77b4',
            'line_width': 2,
            'grid_alpha': 0.3,
            'animation_interval': 1000,
            'background_color': '#f8f9fa',
            'show_grid': True,
            'show_legend': True,
            'figure_size': (12, 6),
            'dpi': 100
        }
        
        # 更新配置
        if config:
            self.config.update(config)
        
        # 图表状态
        self.time_range = 3600  # 显示1小时数据
        self.is_animated = False
        self.animation = None
        self.last_update_time = None
        
        # 创建图表
        self.fig, self.ax = plt.subplots(
            figsize=self.config['figure_size'],
            dpi=self.config['dpi']
        )
        
        # 图表组件
        self.canvas = None
        self.toolbar = None
        self.line = None
        self.annotation = None
        
        # 初始化图表
        self.setup_chart()
        self.setup_canvas()
        
        self.logger.info("图表服务初始化完成")
    
    def setup_chart(self) -> None:
        """初始化图表"""
        try:
            # 设置标题和标签
            self.ax.set_title("MSTR/BTC 溢价率实时走势", fontsize=14, fontweight='bold', pad=20)
            self.ax.set_xlabel("时间", fontsize=12)
            self.ax.set_ylabel("溢价率 (%)", fontsize=12)
            
            # 设置网格
            if self.config['show_grid']:
                self.ax.grid(True, alpha=self.config['grid_alpha'])
            
            # 设置背景颜色
            self.ax.set_facecolor(self.config['background_color'])
            self.fig.patch.set_facecolor('white')
            
            # 设置刻度标签
            self.ax.tick_params(axis='both', which='major', labelsize=10)
            
            # 设置Y轴格式
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
            
            # 设置X轴日期格式
            self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            self.ax.xaxis.set_major_locator(MinuteLocator(interval=15))
            self.ax.xaxis.set_minor_locator(MinuteLocator(interval=5))
            
            # 旋转X轴标签
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
            
            # 初始化空的折线图
            self.line, = self.ax.plot([], [], 
                                     color=self.config['line_color'], 
                                     linewidth=self.config['line_width'],
                                     marker='o', markersize=3, alpha=0.8)
            
            # 设置图例
            if self.config['show_legend']:
                self.ax.legend(['溢价率'], loc='upper right')
            
            # 调整布局
            self.fig.tight_layout()
            
            self.logger.debug("图表设置完成")
            
        except Exception as e:
            self.logger.error(f"设置图表时发生错误: {e}")
    
    def setup_canvas(self) -> None:
        """设置画布"""
        try:
            # 创建画布
            self.canvas = FigureCanvasTkAgg(self.fig, self.parent_frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # 创建工具栏
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.parent_frame)
            self.toolbar.update()
            
            # 绑定事件
            self.canvas.mpl_connect('button_press_event', self._on_click)
            self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
            
            self.logger.debug("画布设置完成")
            
        except Exception as e:
            self.logger.error(f"设置画布时发生错误: {e}")
    
    def start_animation(self) -> None:
        """开始动画更新"""
        if self.is_animated:
            self.logger.warning("动画已在运行")
            return
        
        try:
            self.animation = FuncAnimation(
                self.fig, 
                self.update_chart,
                interval=self.config['animation_interval'],
                blit=False,
                cache_frame_data=False
            )
            
            self.is_animated = True
            self.canvas.draw()
            
            self.logger.info("图表动画已启动")
            
        except Exception as e:
            self.logger.error(f"启动动画时发生错误: {e}")
    
    def stop_animation(self) -> None:
        """停止动画更新"""
        if not self.is_animated:
            self.logger.warning("动画未在运行")
            return
        
        try:
            if self.animation:
                self.animation.event_source.stop()
                self.animation = None
            
            self.is_animated = False
            
            self.logger.info("图表动画已停止")
            
        except Exception as e:
            self.logger.error(f"停止动画时发生错误: {e}")
    
    def update_chart(self, frame=None) -> None:
        """
        更新图表数据
        
        Args:
            frame: 动画帧(由FuncAnimation自动传递)
        """
        try:
            # 获取数据
            timestamps, premiums = self.data_manager.get_data_for_chart(self.time_range)
            
            if len(timestamps) == 0:
                return
            
            # 更新线条数据
            self.line.set_data(timestamps, premiums)
            
            # 调整坐标轴范围
            self._adjust_axes(timestamps, premiums)
            
            # 更新最新数值标注
            self._update_annotation(timestamps, premiums)
            
            # 更新时间戳
            self.last_update_time = datetime.now()
            
            # 重绘画布
            if not self.is_animated:
                self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"更新图表时发生错误: {e}")
    
    def _adjust_axes(self, timestamps: List[datetime], premiums: List[float]) -> None:
        """
        调整坐标轴范围
        
        Args:
            timestamps: 时间戳列表
            premiums: 溢价率列表
        """
        try:
            if len(timestamps) == 0 or len(premiums) == 0:
                return
            
            # 设置X轴范围
            current_time = datetime.now()
            start_time = current_time - timedelta(seconds=self.time_range)
            self.ax.set_xlim(start_time, current_time)
            
            # 设置Y轴范围
            if len(premiums) > 0:
                min_premium = min(premiums)
                max_premium = max(premiums)
                
                # 添加一些边距
                y_range = max_premium - min_premium
                margin = max(y_range * 0.1, 5)  # 至少5%的边距
                
                self.ax.set_ylim(min_premium - margin, max_premium + margin)
            
            # 更新X轴标签
            self._update_time_labels()
            
        except Exception as e:
            self.logger.error(f"调整坐标轴时发生错误: {e}")
    
    def _update_time_labels(self) -> None:
        """更新时间标签"""
        try:
            if self.time_range <= 3600:  # 1小时内，显示分钟
                self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(MinuteLocator(interval=15))
                self.ax.xaxis.set_minor_locator(MinuteLocator(interval=5))
            elif self.time_range <= 14400:  # 4小时内，显示小时和分钟
                self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
                self.ax.xaxis.set_major_locator(HourLocator(interval=1))
                self.ax.xaxis.set_minor_locator(MinuteLocator(interval=30))
            else:  # 超过4小时，显示小时
                self.ax.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M'))
                self.ax.xaxis.set_major_locator(HourLocator(interval=2))
                self.ax.xaxis.set_minor_locator(HourLocator(interval=1))
            
        except Exception as e:
            self.logger.error(f"更新时间标签时发生错误: {e}")
    
    def _update_annotation(self, timestamps: List[datetime], premiums: List[float]) -> None:
        """
        更新最新数值标注
        
        Args:
            timestamps: 时间戳列表
            premiums: 溢价率列表
        """
        try:
            if len(timestamps) == 0 or len(premiums) == 0:
                return
            
            # 移除旧的标注
            if self.annotation:
                self.annotation.remove()
                self.annotation = None
            
            # 添加新的标注
            latest_time = timestamps[-1]
            latest_premium = premiums[-1]
            
            # 选择颜色
            color = 'red' if latest_premium < 0 else 'green'
            
            self.annotation = self.ax.annotate(
                f'{latest_premium:.2f}%',
                xy=(latest_time, latest_premium),
                xytext=(10, 10),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                fontsize=10,
                color='white',
                fontweight='bold'
            )
            
        except Exception as e:
            self.logger.error(f"更新标注时发生错误: {e}")
    
    def set_time_range(self, seconds: int) -> None:
        """
        设置时间范围
        
        Args:
            seconds: 时间范围(秒)
        """
        if seconds < 60:
            seconds = 60
        
        self.time_range = seconds
        self.logger.info(f"图表时间范围设置为: {seconds}秒")
        
        # 立即更新图表
        self.update_chart()
    
    def set_chart_style(self, style: Dict[str, Any]) -> None:
        """
        设置图表样式
        
        Args:
            style: 样式字典
        """
        try:
            # 更新配置
            self.config.update(style)
            
            # 应用新样式
            if 'line_color' in style:
                self.line.set_color(style['line_color'])
            
            if 'line_width' in style:
                self.line.set_linewidth(style['line_width'])
            
            if 'background_color' in style:
                self.ax.set_facecolor(style['background_color'])
            
            if 'grid_alpha' in style:
                self.ax.grid(True, alpha=style['grid_alpha'])
            
            # 重绘
            self.canvas.draw()
            
            self.logger.info("图表样式已更新")
            
        except Exception as e:
            self.logger.error(f"设置图表样式时发生错误: {e}")
    
    def clear_chart(self) -> None:
        """清空图表"""
        try:
            # 清空线条数据
            self.line.set_data([], [])
            
            # 移除标注
            if self.annotation:
                self.annotation.remove()
                self.annotation = None
            
            # 重置坐标轴
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            
            # 重绘
            self.canvas.draw()
            
            self.logger.info("图表已清空")
            
        except Exception as e:
            self.logger.error(f"清空图表时发生错误: {e}")
    
    def export_chart(self, filename: str, dpi: int = 300) -> bool:
        """
        导出图表图片
        
        Args:
            filename: 文件名
            dpi: 分辨率
            
        Returns:
            是否成功导出
        """
        try:
            # 临时调整大小以获得更好的导出效果
            original_size = self.fig.get_size_inches()
            self.fig.set_size_inches(12, 8)
            
            # 保存图片
            self.fig.savefig(filename, dpi=dpi, bbox_inches='tight', 
                            facecolor='white', edgecolor='none')
            
            # 恢复原始大小
            self.fig.set_size_inches(original_size)
            
            self.logger.info(f"图表导出成功: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出图表时发生错误: {e}")
            return False
    
    def get_chart_statistics(self) -> Dict[str, Any]:
        """
        获取图表统计信息
        
        Returns:
            统计信息字典
        """
        try:
            data_stats = self.data_manager.get_statistics()
            
            return {
                'time_range': self.time_range,
                'time_range_display': self._format_time_range(self.time_range),
                'is_animated': self.is_animated,
                'animation_interval': self.config['animation_interval'],
                'last_update_time': self.last_update_time,
                'data_points': data_stats.get('count', 0),
                'latest_premium': data_stats.get('latest_premium'),
                'max_premium': data_stats.get('max_premium'),
                'min_premium': data_stats.get('min_premium'),
                'avg_premium': data_stats.get('avg_premium')
            }
            
        except Exception as e:
            self.logger.error(f"获取图表统计时发生错误: {e}")
            return {}
    
    def _format_time_range(self, seconds: int) -> str:
        """
        格式化时间范围显示
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间范围字符串
        """
        if seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时"
        else:
            return f"{seconds // 86400}天"
    
    def _on_click(self, event) -> None:
        """
        鼠标点击事件处理
        
        Args:
            event: 鼠标事件
        """
        try:
            if event.inaxes == self.ax and event.button == 1:  # 左键点击
                # 获取点击位置的数据
                if hasattr(event, 'xdata') and hasattr(event, 'ydata'):
                    if event.xdata is not None and event.ydata is not None:
                        click_time = mdates.num2date(event.xdata)
                        click_premium = event.ydata
                        
                        self.logger.debug(f"图表点击: 时间={click_time}, 溢价率={click_premium:.2f}%")
        
        except Exception as e:
            self.logger.error(f"处理点击事件时发生错误: {e}")
    
    def _on_mouse_move(self, event) -> None:
        """
        鼠标移动事件处理
        
        Args:
            event: 鼠标事件
        """
        try:
            if event.inaxes == self.ax:
                # 这里可以添加鼠标悬停显示数据的功能
                pass
        
        except Exception as e:
            self.logger.error(f"处理鼠标移动事件时发生错误: {e}")
    
    def add_horizontal_line(self, y_value: float, color: str = 'red', 
                           linestyle: str = '--', label: str = None) -> None:
        """
        添加水平参考线
        
        Args:
            y_value: Y轴值
            color: 线条颜色
            linestyle: 线条样式
            label: 标签
        """
        try:
            self.ax.axhline(y=y_value, color=color, linestyle=linestyle, 
                           alpha=0.7, label=label)
            
            if label and self.config['show_legend']:
                self.ax.legend()
            
            self.canvas.draw()
            
            self.logger.debug(f"添加水平线: y={y_value}, 颜色={color}")
            
        except Exception as e:
            self.logger.error(f"添加水平线时发生错误: {e}")
    
    def remove_horizontal_lines(self) -> None:
        """移除所有水平参考线"""
        try:
            # 移除所有水平线
            for line in self.ax.get_lines():
                if line != self.line:  # 保留主数据线
                    line.remove()
            
            self.canvas.draw()
            
            self.logger.debug("已移除所有水平参考线")
            
        except Exception as e:
            self.logger.error(f"移除水平线时发生错误: {e}")
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止动画
            if self.is_animated:
                self.stop_animation()
            
            # 清理matplotlib资源
            if self.fig:
                plt.close(self.fig)
            
            self.logger.info("图表服务资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源时发生错误: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()