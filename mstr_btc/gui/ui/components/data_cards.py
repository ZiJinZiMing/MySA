"""
数据显示卡片组件 - 显示实时价格和溢价数据
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any
import logging
from datetime import datetime
from ...utils.helpers import format_price, format_premium, calculate_change_percentage


class DataCard:
    """数据显示卡片基类"""
    
    def __init__(self, parent: tk.Widget, title: str, width: int = 200, height: int = 100):
        """
        初始化数据卡片
        
        Args:
            parent: 父级组件
            title: 卡片标题
            width: 卡片宽度
            height: 卡片高度
        """
        self.parent = parent
        self.title = title
        self.width = width
        self.height = height
        self.logger = logging.getLogger(__name__)
        
        # 数据状态
        self.current_value = None
        self.previous_value = None
        self.last_update_time = None
        
        # 颜色配置
        self.colors = {
            'normal': '#f8f9fa',
            'positive': '#d4edda',
            'negative': '#f8d7da',
            'warning': '#fff3cd',
            'error': '#f8d7da',
            'text_normal': '#333333',
            'text_positive': '#155724',
            'text_negative': '#721c24',
            'text_warning': '#856404',
            'text_error': '#721c24'
        }
        
        # 创建UI
        self.create_ui()
        
        self.logger.debug(f"数据卡片创建完成: {title}")
    
    def create_ui(self) -> None:
        """创建用户界面"""
        # 主框架
        self.frame = ttk.LabelFrame(
            self.parent,
            text=self.title,
            padding=10,
            width=self.width,
            height=self.height
        )
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.frame.pack_propagate(False)
        
        # 创建内容区域
        self.content_frame = ttk.Frame(self.frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 主数值标签
        self.value_label = ttk.Label(
            self.content_frame,
            text="--",
            font=('Arial', 16, 'bold'),
            anchor='center'
        )
        self.value_label.pack(pady=(0, 5))
        
        # 变化标签
        self.change_label = ttk.Label(
            self.content_frame,
            text="--",
            font=('Arial', 10),
            anchor='center'
        )
        self.change_label.pack(pady=(0, 5))
        
        # 状态标签
        self.status_label = ttk.Label(
            self.content_frame,
            text="未连接",
            font=('Arial', 9),
            anchor='center',
            foreground='gray'
        )
        self.status_label.pack()
        
        # 最后更新时间标签
        self.time_label = ttk.Label(
            self.content_frame,
            text="",
            font=('Arial', 8),
            anchor='center',
            foreground='gray'
        )
        self.time_label.pack(side=tk.BOTTOM)
    
    def update_value(self, value: float, change: Optional[float] = None) -> None:
        """
        更新数值显示
        
        Args:
            value: 新数值
            change: 变化值
        """
        try:
            # 保存之前的值
            self.previous_value = self.current_value
            self.current_value = value
            self.last_update_time = datetime.now()
            
            # 格式化数值
            formatted_value = self.format_value(value)
            self.value_label.config(text=formatted_value)
            
            # 计算变化
            if change is None and self.previous_value is not None:
                change = calculate_change_percentage(self.previous_value, value)
            
            # 更新变化显示
            if change is not None:
                change_text = f"{change:+.2f}%"
                change_color = self.get_change_color(change)
                
                self.change_label.config(
                    text=change_text,
                    foreground=change_color
                )
            else:
                self.change_label.config(text="--", foreground='gray')
            
            # 更新背景颜色
            self.update_background_color(value, change)
            
            # 更新状态
            self.set_status("正常", "normal")
            
            # 更新时间
            time_text = self.last_update_time.strftime("%H:%M:%S")
            self.time_label.config(text=time_text)
            
        except Exception as e:
            self.logger.error(f"更新数值时发生错误: {e}")
            self.set_status("错误", "error")
    
    def format_value(self, value: float) -> str:
        """
        格式化数值显示
        
        Args:
            value: 数值
            
        Returns:
            格式化后的字符串
        """
        return f"{value:.2f}"
    
    def get_change_color(self, change: float) -> str:
        """
        获取变化颜色
        
        Args:
            change: 变化值
            
        Returns:
            颜色字符串
        """
        if change > 0:
            return self.colors['text_positive']
        elif change < 0:
            return self.colors['text_negative']
        else:
            return self.colors['text_normal']
    
    def update_background_color(self, value: float, change: Optional[float]) -> None:
        """
        更新背景颜色
        
        Args:
            value: 当前值
            change: 变化值
        """
        # 基类使用默认颜色
        pass
    
    def set_status(self, status: str, status_type: str = "normal") -> None:
        """
        设置状态指示
        
        Args:
            status: 状态文本
            status_type: 状态类型
        """
        try:
            color = self.colors.get(f'text_{status_type}', self.colors['text_normal'])
            self.status_label.config(text=status, foreground=color)
        except Exception as e:
            self.logger.error(f"设置状态时发生错误: {e}")
    
    def clear_data(self) -> None:
        """清空数据"""
        self.current_value = None
        self.previous_value = None
        self.last_update_time = None
        
        self.value_label.config(text="--")
        self.change_label.config(text="--", foreground='gray')
        self.status_label.config(text="未连接", foreground='gray')
        self.time_label.config(text="")
    
    def get_current_value(self) -> Optional[float]:
        """获取当前值"""
        return self.current_value
    
    def get_last_update_time(self) -> Optional[datetime]:
        """获取最后更新时间"""
        return self.last_update_time


class MSTRCard(DataCard):
    """MSTR价格卡片"""
    
    def __init__(self, parent: tk.Widget):
        super().__init__(parent, "MSTR价格", width=200, height=120)
    
    def format_value(self, value: float) -> str:
        """格式化MSTR价格"""
        return format_price(value)
    
    def update_background_color(self, value: float, change: Optional[float]) -> None:
        """更新背景颜色"""
        if change is not None:
            if change > 2:
                color = self.colors['positive']
            elif change < -2:
                color = self.colors['negative']
            else:
                color = self.colors['normal']
            
            # 注意：ttk.LabelFrame不支持直接设置背景色
            # 这里可以通过样式或其他方式实现
            pass


class BTCCard(DataCard):
    """BTC价格卡片"""
    
    def __init__(self, parent: tk.Widget):
        super().__init__(parent, "BTC价格", width=200, height=120)
    
    def format_value(self, value: float) -> str:
        """格式化BTC价格"""
        return format_price(value)
    
    def update_background_color(self, value: float, change: Optional[float]) -> None:
        """更新背景颜色"""
        if change is not None:
            if change > 3:
                color = self.colors['positive']
            elif change < -3:
                color = self.colors['negative']
            else:
                color = self.colors['normal']
            
            pass


class PremiumCard(DataCard):
    """溢价率卡片"""
    
    def __init__(self, parent: tk.Widget):
        super().__init__(parent, "溢价率", width=200, height=120)
    
    def format_value(self, value: float) -> str:
        """格式化溢价率"""
        return format_premium(value)
    
    def update_background_color(self, value: float, change: Optional[float]) -> None:
        """更新背景颜色"""
        if value > 50:
            color = self.colors['warning']
        elif value < -10:
            color = self.colors['negative']
        elif value > 25:
            color = self.colors['positive']
        else:
            color = self.colors['normal']
        
        pass
    
    def get_change_color(self, change: float) -> str:
        """获取溢价率变化颜色"""
        if abs(change) > 5:  # 溢价率变化超过5%时使用警告色
            return self.colors['text_warning']
        elif change > 0:
            return self.colors['text_positive']
        elif change < 0:
            return self.colors['text_negative']
        else:
            return self.colors['text_normal']


class DataCardManager:
    """数据卡片管理器"""
    
    def __init__(self, parent: tk.Widget):
        """
        初始化数据卡片管理器
        
        Args:
            parent: 父级组件
        """
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        
        # 创建容器框架
        self.container = ttk.Frame(parent)
        self.container.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建卡片
        self.mstr_card = MSTRCard(self.container)
        self.btc_card = BTCCard(self.container)
        self.premium_card = PremiumCard(self.container)
        
        # 卡片字典
        self.cards = {
            'mstr': self.mstr_card,
            'btc': self.btc_card,
            'premium': self.premium_card
        }
        
        self.logger.info("数据卡片管理器初始化完成")
    
    def update_mstr_data(self, price: float, change: Optional[float] = None) -> None:
        """
        更新MSTR数据
        
        Args:
            price: MSTR价格
            change: 变化百分比
        """
        self.mstr_card.update_value(price, change)
    
    def update_btc_data(self, price: float, change: Optional[float] = None) -> None:
        """
        更新BTC数据
        
        Args:
            price: BTC价格
            change: 变化百分比
        """
        self.btc_card.update_value(price, change)
    
    def update_premium_data(self, premium: float, change: Optional[float] = None) -> None:
        """
        更新溢价率数据
        
        Args:
            premium: 溢价率
            change: 变化值
        """
        self.premium_card.update_value(premium, change)
    
    def update_all_data(self, timestamp: datetime, mstr_price: float, 
                       btc_price: float, premium: float) -> None:
        """
        更新所有数据
        
        Args:
            timestamp: 时间戳
            mstr_price: MSTR价格
            btc_price: BTC价格
            premium: 溢价率
        """
        try:
            # 更新MSTR数据
            self.update_mstr_data(mstr_price)
            
            # 更新BTC数据
            self.update_btc_data(btc_price)
            
            # 更新溢价率数据
            self.update_premium_data(premium)
            
            self.logger.debug(f"所有数据卡片已更新: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"更新所有数据时发生错误: {e}")
            self.set_all_status("错误", "error")
    
    def set_all_status(self, status: str, status_type: str = "normal") -> None:
        """
        设置所有卡片状态
        
        Args:
            status: 状态文本
            status_type: 状态类型
        """
        for card in self.cards.values():
            card.set_status(status, status_type)
    
    def clear_all_data(self) -> None:
        """清空所有数据"""
        for card in self.cards.values():
            card.clear_data()
    
    def get_card(self, card_type: str) -> Optional[DataCard]:
        """
        获取指定类型的卡片
        
        Args:
            card_type: 卡片类型 ('mstr', 'btc', 'premium')
            
        Returns:
            数据卡片对象
        """
        return self.cards.get(card_type)
    
    def get_all_values(self) -> Dict[str, Optional[float]]:
        """
        获取所有卡片的当前值
        
        Returns:
            所有卡片值的字典
        """
        return {
            'mstr': self.mstr_card.get_current_value(),
            'btc': self.btc_card.get_current_value(),
            'premium': self.premium_card.get_current_value()
        }
    
    def get_last_update_times(self) -> Dict[str, Optional[datetime]]:
        """
        获取所有卡片的最后更新时间
        
        Returns:
            所有卡片更新时间的字典
        """
        return {
            'mstr': self.mstr_card.get_last_update_time(),
            'btc': self.btc_card.get_last_update_time(),
            'premium': self.premium_card.get_last_update_time()
        }
    
    def set_error_status(self, message: str = "连接错误") -> None:
        """设置错误状态"""
        self.set_all_status(message, "error")
    
    def set_loading_status(self, message: str = "加载中...") -> None:
        """设置加载状态"""
        self.set_all_status(message, "warning")
    
    def set_normal_status(self, message: str = "正常") -> None:
        """设置正常状态"""
        self.set_all_status(message, "normal")


# 便捷函数
def create_data_cards(parent: tk.Widget) -> DataCardManager:
    """
    创建数据卡片管理器
    
    Args:
        parent: 父级组件
        
    Returns:
        数据卡片管理器实例
    """
    return DataCardManager(parent)