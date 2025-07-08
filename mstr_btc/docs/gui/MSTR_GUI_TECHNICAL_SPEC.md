# MSTR/BTC溢价监控GUI应用技术规范

## 技术架构概述

### 系统架构图
```
┌─────────────────────────────────────────────────────┐
│                   GUI Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Display   │  │   Control   │  │   Chart     │ │
│  │   Widgets   │  │   Panel     │  │   Canvas    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                 Business Logic Layer                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Data      │  │   Monitor   │  │   Chart     │ │
│  │   Manager   │  │   Service   │  │   Service   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────┐
│                  Data Access Layer                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   API       │  │   Web       │  │   Config    │ │
│  │   Client    │  │   Scraper   │  │   Manager   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 技术栈选择

#### 核心技术
- **编程语言**: Python 3.8+
- **GUI框架**: Tkinter (内置库，无需额外安装)
- **图表库**: Matplotlib (强大的绘图功能)
- **数据结构**: Collections.deque (高效的时间序列存储)
- **多线程**: Threading (数据获取与UI分离)

#### 第三方库
```python
# 核心依赖
matplotlib>=3.5.0      # 图表绘制
requests>=2.25.0       # HTTP请求
beautifulsoup4>=4.9.0  # HTML解析
selenium>=4.0.0        # 网页自动化

# 可选依赖
pandas>=1.3.0          # 数据处理(用于CSV导出)
```

#### 选择理由
1. **Tkinter**: Python内置，跨平台，部署简单
2. **Matplotlib**: 功能强大，实时更新支持好
3. **轻量级**: 最小化依赖，提高稳定性
4. **兼容性**: 支持Windows/Linux/macOS

## 详细技术设计

### 1. 数据模型设计

#### PremiumData类
```python
from collections import deque
from datetime import datetime
from typing import Optional, List, Tuple
import threading

class PremiumData:
    """溢价数据管理类"""
    
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.mstr_prices = deque(maxlen=max_points)
        self.btc_prices = deque(maxlen=max_points)
        self.premiums = deque(maxlen=max_points)
        self.lock = threading.Lock()
        
    def add_data_point(self, timestamp: datetime, mstr_price: float, 
                      btc_price: float, premium: float) -> None:
        """添加新数据点"""
        with self.lock:
            self.timestamps.append(timestamp)
            self.mstr_prices.append(mstr_price)
            self.btc_prices.append(btc_price)
            self.premiums.append(premium)
    
    def get_latest_data(self) -> Optional[Tuple[datetime, float, float, float]]:
        """获取最新数据点"""
        with self.lock:
            if len(self.timestamps) == 0:
                return None
            return (self.timestamps[-1], self.mstr_prices[-1], 
                   self.btc_prices[-1], self.premiums[-1])
    
    def get_all_data(self) -> Tuple[List, List, List, List]:
        """获取所有数据点"""
        with self.lock:
            return (list(self.timestamps), list(self.mstr_prices),
                   list(self.btc_prices), list(self.premiums))
    
    def clear_data(self) -> None:
        """清空所有数据"""
        with self.lock:
            self.timestamps.clear()
            self.mstr_prices.clear()
            self.btc_prices.clear()
            self.premiums.clear()
```

### 2. API客户端设计

#### APIClient类
```python
import requests
import os
from typing import Optional
import logging

class APIClient:
    """API客户端统一管理"""
    
    def __init__(self):
        self.finnhub_api_key = os.environ.get(
            "FINNHUB_API_KEY", 
            "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g"
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MSTR-Monitor/1.0'
        })
        
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """获取股票价格"""
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_api_key}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                logging.error(f"API错误: {data['error']}")
                return None
                
            return data.get("c")  # 当前价格
            
        except requests.RequestException as e:
            logging.error(f"获取{symbol}价格失败: {e}")
            return None
        except Exception as e:
            logging.error(f"未知错误: {e}")
            return None
    
    def get_mstr_price(self) -> Optional[float]:
        """获取MSTR价格"""
        return self.get_ticker_price("MSTR")
    
    def get_btc_price(self) -> Optional[float]:
        """获取BTC价格"""
        return self.get_ticker_price("BINANCE:BTCUSDT")
```

### 3. 数据监控服务

#### MonitorService类
```python
import threading
import time
from datetime import datetime
from typing import Callable, Optional
import logging

class MonitorService:
    """数据监控服务"""
    
    def __init__(self, api_client: APIClient, data_manager: PremiumData):
        self.api_client = api_client
        self.data_manager = data_manager
        self.is_running = False
        self.monitor_thread = None
        self.update_interval = 10  # 秒
        self.btc_per_share = 0.00207973  # 默认值
        self.callbacks = []
        
    def add_callback(self, callback: Callable) -> None:
        """添加数据更新回调"""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable) -> None:
        """移除数据更新回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def set_btc_per_share(self, value: float) -> None:
        """设置BTC per share值"""
        self.btc_per_share = value
        
    def set_update_interval(self, interval: int) -> None:
        """设置更新间隔"""
        self.update_interval = max(1, interval)
    
    def calculate_premium(self, mstr_price: float, btc_price: float) -> float:
        """计算溢价率"""
        btc_value_per_share = self.btc_per_share * btc_price
        return (mstr_price / btc_value_per_share - 1) * 100
    
    def start_monitoring(self) -> bool:
        """开始监控"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logging.info("数据监控已启动")
        return True
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logging.info("数据监控已停止")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while self.is_running:
            try:
                # 获取价格数据
                mstr_price = self.api_client.get_mstr_price()
                btc_price = self.api_client.get_btc_price()
                
                if mstr_price is not None and btc_price is not None:
                    # 计算溢价率
                    premium = self.calculate_premium(mstr_price, btc_price)
                    
                    # 添加数据点
                    timestamp = datetime.now()
                    self.data_manager.add_data_point(
                        timestamp, mstr_price, btc_price, premium
                    )
                    
                    # 调用回调函数
                    for callback in self.callbacks:
                        try:
                            callback(timestamp, mstr_price, btc_price, premium)
                        except Exception as e:
                            logging.error(f"回调函数执行错误: {e}")
                
                # 等待下次更新
                time.sleep(self.update_interval)
                
            except Exception as e:
                logging.error(f"监控循环错误: {e}")
                time.sleep(5)  # 错误时短暂等待
```

### 4. 图表服务设计

#### ChartService类
```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from datetime import datetime, timedelta
import numpy as np

class ChartService:
    """图表服务"""
    
    def __init__(self, parent_frame: tk.Frame, data_manager: PremiumData):
        self.parent_frame = parent_frame
        self.data_manager = data_manager
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
        self.animation = None
        self.time_range = 3600  # 显示1小时数据
        
        self.setup_chart()
        self.setup_canvas()
    
    def setup_chart(self) -> None:
        """初始化图表"""
        self.ax.set_title("MSTR/BTC 溢价率实时走势", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("溢价率 (%)", fontsize=12)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor('#f8f9fa')
        
        # 设置图表样式
        self.fig.patch.set_facecolor('white')
        self.ax.tick_params(axis='both', which='major', labelsize=10)
        
    def setup_canvas(self) -> None:
        """设置画布"""
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def start_animation(self) -> None:
        """开始动画更新"""
        if self.animation is None:
            self.animation = FuncAnimation(
                self.fig, self.update_chart, 
                interval=1000, blit=False, cache_frame_data=False
            )
            self.canvas.draw()
    
    def stop_animation(self) -> None:
        """停止动画更新"""
        if self.animation:
            self.animation.event_source.stop()
            self.animation = None
    
    def update_chart(self, frame) -> None:
        """更新图表"""
        try:
            timestamps, _, _, premiums = self.data_manager.get_all_data()
            
            if len(timestamps) == 0:
                return
            
            # 过滤时间范围内的数据
            current_time = datetime.now()
            start_time = current_time - timedelta(seconds=self.time_range)
            
            filtered_data = [
                (t, p) for t, p in zip(timestamps, premiums) 
                if t >= start_time
            ]
            
            if len(filtered_data) == 0:
                return
            
            times, values = zip(*filtered_data)
            
            # 清空并重绘
            self.ax.clear()
            self.setup_chart()
            
            # 绘制折线图
            self.ax.plot(times, values, 'b-', linewidth=2, marker='o', 
                        markersize=3, alpha=0.8)
            
            # 设置x轴格式
            self.ax.tick_params(axis='x', rotation=45)
            
            # 添加最新数值标注
            if len(values) > 0:
                latest_value = values[-1]
                latest_time = times[-1]
                self.ax.annotate(f'{latest_value:.2f}%', 
                               xy=(latest_time, latest_value),
                               xytext=(10, 10), textcoords='offset points',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
                               arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
            
            # 调整布局
            self.fig.tight_layout()
            
        except Exception as e:
            logging.error(f"图表更新错误: {e}")
    
    def set_time_range(self, seconds: int) -> None:
        """设置时间范围"""
        self.time_range = max(60, seconds)
    
    def clear_chart(self) -> None:
        """清空图表"""
        self.ax.clear()
        self.setup_chart()
        self.canvas.draw()
```

### 5. 主GUI应用设计

#### MSTRMonitorGUI类结构
```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime

class MSTRMonitorGUI:
    """MSTR监控GUI主类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.data_manager = PremiumData()
        self.api_client = APIClient()
        self.monitor_service = MonitorService(self.api_client, self.data_manager)
        self.chart_service = None
        
        self.setup_logging()
        self.setup_ui()
        self.setup_services()
        
    def setup_logging(self) -> None:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('mstr_monitor.log'),
                logging.StreamHandler()
            ]
        )
    
    def setup_ui(self) -> None:
        """设置用户界面"""
        # 窗口配置
        self.root.title("MSTR/BTC 溢价监控")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 创建主要框架
        self.create_data_display_frame()
        self.create_chart_frame()
        self.create_control_frame()
        self.create_status_frame()
        
    def create_data_display_frame(self) -> None:
        """创建数据显示框架"""
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建数据卡片
        self.mstr_card = self.create_data_card(frame, "MSTR", "$0.00", "0.00%")
        self.btc_card = self.create_data_card(frame, "BTC", "$0.00", "0.00%")
        self.premium_card = self.create_data_card(frame, "溢价率", "0.00%", "正常")
        
    def create_data_card(self, parent, title, value, change) -> dict:
        """创建数据卡片"""
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        value_label = ttk.Label(frame, text=value, font=('Arial', 16, 'bold'))
        value_label.pack()
        
        change_label = ttk.Label(frame, text=change, font=('Arial', 10))
        change_label.pack()
        
        return {
            'frame': frame,
            'value_label': value_label,
            'change_label': change_label
        }
    
    def create_chart_frame(self) -> None:
        """创建图表框架"""
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chart_service = ChartService(frame, self.data_manager)
        
    def create_control_frame(self) -> None:
        """创建控制面板"""
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 控制按钮
        self.start_button = ttk.Button(frame, text="开始监控", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame, text="清除数据", command=self.clear_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="设置", command=self.open_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="导出CSV", command=self.export_data).pack(side=tk.LEFT, padx=5)
        
        # 参数设置
        ttk.Label(frame, text="更新间隔:").pack(side=tk.LEFT, padx=(20, 5))
        self.interval_var = tk.StringVar(value="10秒")
        interval_combo = ttk.Combobox(frame, textvariable=self.interval_var, 
                                     values=["5秒", "10秒", "30秒", "60秒"], 
                                     state="readonly", width=8)
        interval_combo.pack(side=tk.LEFT, padx=5)
        interval_combo.bind('<<ComboboxSelected>>', self.on_interval_change)
        
        ttk.Label(frame, text="显示时间:").pack(side=tk.LEFT, padx=(20, 5))
        self.timerange_var = tk.StringVar(value="1小时")
        timerange_combo = ttk.Combobox(frame, textvariable=self.timerange_var,
                                      values=["30分钟", "1小时", "4小时", "1天"],
                                      state="readonly", width=8)
        timerange_combo.pack(side=tk.LEFT, padx=5)
        timerange_combo.bind('<<ComboboxSelected>>', self.on_timerange_change)
        
    def create_status_frame(self) -> None:
        """创建状态栏"""
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(frame, text="状态: 未连接")
        self.status_label.pack(side=tk.LEFT)
        
        self.update_time_label = ttk.Label(frame, text="最后更新: --")
        self.update_time_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.data_count_label = ttk.Label(frame, text="数据点: 0")
        self.data_count_label.pack(side=tk.LEFT, padx=(20, 0))
```

### 6. 线程安全设计

#### 线程模型
```
Main Thread (GUI)
├── Data Update Thread (监控服务)
│   ├── API请求 (定时执行)
│   ├── 数据计算 (溢价率计算)
│   └── 数据存储 (线程安全)
├── Chart Update Thread (图表服务)
│   ├── 数据读取 (线程安全)
│   ├── 图表绘制 (matplotlib)
│   └── UI更新 (tkinter.after)
└── User Event Thread (用户交互)
    ├── 按钮点击处理
    ├── 参数设置
    └── 数据导出
```

#### 线程安全策略
1. **数据访问**: 使用threading.Lock保护共享数据
2. **UI更新**: 使用tkinter.after确保主线程更新UI
3. **异常处理**: 各线程独立处理异常，避免崩溃
4. **资源清理**: 应用关闭时正确停止所有线程

### 7. 错误处理机制

#### 异常分类处理
```python
class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_api_error(error: Exception) -> None:
        """处理API错误"""
        logging.error(f"API错误: {error}")
        # 更新状态显示
        # 启用重试机制
        
    @staticmethod
    def handle_network_error(error: Exception) -> None:
        """处理网络错误"""
        logging.error(f"网络错误: {error}")
        # 显示连接状态
        # 自动重连
        
    @staticmethod
    def handle_data_error(error: Exception) -> None:
        """处理数据错误"""
        logging.error(f"数据错误: {error}")
        # 跳过错误数据
        # 继续监控
        
    @staticmethod
    def handle_ui_error(error: Exception) -> None:
        """处理UI错误"""
        logging.error(f"UI错误: {error}")
        # 显示错误消息
        # 恢复界面状态
```

### 8. 性能优化策略

#### 内存优化
- 使用deque限制数据点数量
- 定期清理过期数据
- 避免大量临时对象创建

#### CPU优化
- 数据获取与UI更新分离
- 图表更新采用差量更新
- 合理设置更新频率

#### 网络优化
- 连接池复用
- 请求超时设置
- 智能重试机制

### 9. 配置管理

#### 配置文件结构
```json
{
    "api": {
        "finnhub_api_key": "your_api_key",
        "request_timeout": 10,
        "retry_count": 3
    },
    "monitor": {
        "default_interval": 10,
        "max_data_points": 1000,
        "btc_per_share": 0.00207973
    },
    "ui": {
        "window_width": 1000,
        "window_height": 700,
        "default_time_range": 3600
    },
    "chart": {
        "line_color": "blue",
        "line_width": 2,
        "grid_alpha": 0.3
    }
}
```

#### 配置管理器
```python
import json
import os
from typing import Dict, Any

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"配置加载失败: {e}")
        
        return self.get_default_config()
    
    def save_config(self) -> None:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"配置保存失败: {e}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api": {
                "finnhub_api_key": "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g",
                "request_timeout": 10,
                "retry_count": 3
            },
            "monitor": {
                "default_interval": 10,
                "max_data_points": 1000,
                "btc_per_share": 0.00207973
            },
            "ui": {
                "window_width": 1000,
                "window_height": 700,
                "default_time_range": 3600
            },
            "chart": {
                "line_color": "blue",
                "line_width": 2,
                "grid_alpha": 0.3
            }
        }
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
```

这个技术规范提供了MSTR/BTC溢价监控GUI应用的详细技术实现方案，确保代码结构清晰、功能完整、性能优良。