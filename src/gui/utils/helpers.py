"""
辅助函数模块 - 通用的辅助功能
"""

import time
import functools
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
import os
import sys
import threading


def format_price(price: float, currency: str = "USD") -> str:
    """
    格式化价格显示
    
    Args:
        price: 价格
        currency: 货币类型
        
    Returns:
        格式化的价格字符串
    """
    try:
        if currency == "USD":
            if price >= 1000:
                return f"${price:,.2f}"
            else:
                return f"${price:.2f}"
        else:
            return f"{price:.2f} {currency}"
    except Exception:
        return "N/A"


def format_premium(premium: float) -> str:
    """
    格式化溢价率显示
    
    Args:
        premium: 溢价率
        
    Returns:
        格式化的溢价率字符串
    """
    try:
        if premium >= 0:
            return f"+{premium:.2f}%"
        else:
            return f"{premium:.2f}%"
    except Exception:
        return "N/A"


def format_timestamp(timestamp: datetime, format_type: str = "default") -> str:
    """
    格式化时间戳显示
    
    Args:
        timestamp: 时间戳
        format_type: 格式类型
        
    Returns:
        格式化的时间字符串
    """
    try:
        if format_type == "default":
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "short":
            return timestamp.strftime("%H:%M:%S")
        elif format_type == "date":
            return timestamp.strftime("%Y-%m-%d")
        elif format_type == "time":
            return timestamp.strftime("%H:%M")
        elif format_type == "iso":
            return timestamp.isoformat()
        else:
            return timestamp.strftime(format_type)
    except Exception:
        return "N/A"


def format_duration(seconds: float) -> str:
    """
    格式化持续时间显示
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的持续时间字符串
    """
    try:
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
        else:
            days = seconds / 86400
            return f"{days:.1f}天"
    except Exception:
        return "N/A"


def format_number(number: Union[int, float], precision: int = 2) -> str:
    """
    格式化数字显示
    
    Args:
        number: 数字
        precision: 精度
        
    Returns:
        格式化的数字字符串
    """
    try:
        if isinstance(number, int):
            return f"{number:,}"
        else:
            return f"{number:,.{precision}f}"
    except Exception:
        return "N/A"


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化的文件大小字符串
    """
    try:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    except Exception:
        return "N/A"


def calculate_change_percentage(old_value: float, new_value: float) -> float:
    """
    计算变化百分比
    
    Args:
        old_value: 旧值
        new_value: 新值
        
    Returns:
        变化百分比
    """
    try:
        if old_value == 0:
            return 0.0
        return ((new_value - old_value) / old_value) * 100
    except Exception:
        return 0.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法运算
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 默认值
        
    Returns:
        除法结果
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    限制数值范围
    
    Args:
        value: 值
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        限制后的值
    """
    return max(min_val, min(value, max_val))


def get_time_ago(timestamp: datetime) -> str:
    """
    获取相对时间描述
    
    Args:
        timestamp: 时间戳
        
    Returns:
        相对时间描述
    """
    try:
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return "刚刚"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}分钟前"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}小时前"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days}天前"
    except Exception:
        return "未知"


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, 
                    backoff_factor: float = 2.0, 
                    exceptions: tuple = (Exception,)):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        sleep_time = delay * (backoff_factor ** attempt)
                        time.sleep(sleep_time)
                        
                        # 记录重试信息
                        logger = logging.getLogger(func.__module__)
                        logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次重试")
                    else:
                        # 最后一次尝试失败，抛出异常
                        logger = logging.getLogger(func.__module__)
                        logger.error(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败")
                        raise last_exception
                        
            return None
        
        return wrapper
    return decorator


def rate_limit(calls_per_second: float):
    """
    速率限制装饰器
    
    Args:
        calls_per_second: 每秒调用次数
        
    Returns:
        装饰器函数
    """
    min_interval = 1.0 / calls_per_second
    
    def decorator(func: Callable) -> Callable:
        last_called = [0.0]
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                elapsed = time.time() - last_called[0]
                left_to_wait = min_interval - elapsed
                
                if left_to_wait > 0:
                    time.sleep(left_to_wait)
                
                last_called[0] = time.time()
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def timeout(seconds: float):
    """
    超时装饰器
    
    Args:
        seconds: 超时时间
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)
            
            if thread.is_alive():
                # 超时
                logger = logging.getLogger(func.__module__)
                logger.error(f"函数 {func.__name__} 执行超时 ({seconds}秒)")
                raise TimeoutError(f"函数执行超时: {seconds}秒")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator


def memoize(maxsize: int = 128, ttl: Optional[float] = None):
    """
    记忆化装饰器
    
    Args:
        maxsize: 最大缓存大小
        ttl: 生存时间(秒)
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_info = {'hits': 0, 'misses': 0}
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))
            
            with lock:
                # 检查缓存
                if key in cache:
                    value, timestamp = cache[key]
                    
                    # 检查TTL
                    if ttl is None or time.time() - timestamp < ttl:
                        cache_info['hits'] += 1
                        return value
                    else:
                        # 缓存过期，删除
                        del cache[key]
                
                # 缓存未命中
                cache_info['misses'] += 1
                result = func(*args, **kwargs)
                
                # 保存到缓存
                cache[key] = (result, time.time())
                
                # 限制缓存大小
                if len(cache) > maxsize:
                    # 删除最旧的项
                    oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                    del cache[oldest_key]
                
                return result
        
        # 添加缓存信息方法
        def cache_info_func():
            return cache_info.copy()
        
        def clear_cache():
            with lock:
                cache.clear()
                cache_info['hits'] = 0
                cache_info['misses'] = 0
        
        wrapper.cache_info = cache_info_func
        wrapper.clear_cache = clear_cache
        
        return wrapper
    return decorator


def get_app_data_dir(app_name: str = "MSTRMonitor") -> str:
    """
    获取应用数据目录
    
    Args:
        app_name: 应用名称
        
    Returns:
        应用数据目录路径
    """
    try:
        if sys.platform == "win32":
            base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        elif sys.platform == "darwin":  # macOS
            base_dir = os.path.expanduser("~/Library/Application Support")
        else:  # Linux
            base_dir = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        
        app_dir = os.path.join(base_dir, app_name)
        os.makedirs(app_dir, exist_ok=True)
        
        return app_dir
    except Exception:
        # 回退到当前目录
        return os.getcwd()


def get_temp_dir(app_name: str = "MSTRMonitor") -> str:
    """
    获取临时目录
    
    Args:
        app_name: 应用名称
        
    Returns:
        临时目录路径
    """
    try:
        import tempfile
        
        temp_dir = os.path.join(tempfile.gettempdir(), app_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        return temp_dir
    except Exception:
        return os.getcwd()


def ensure_dir(path: str) -> bool:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        是否成功创建或已存在
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    try:
        # 替换不安全字符
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 255:
            filename = filename[:255]
        
        # 移除开头和结尾的空格和点
        filename = filename.strip(' .')
        
        # 避免空文件名
        if not filename:
            filename = "unnamed"
        
        return filename
    except Exception:
        return "unnamed"


def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    
    Returns:
        系统信息字典
    """
    try:
        import platform
        
        info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
        
        # 获取内存信息
        try:
            import psutil
            info['memory_total'] = psutil.virtual_memory().total
            info['memory_available'] = psutil.virtual_memory().available
            info['cpu_count'] = psutil.cpu_count()
        except ImportError:
            pass
        
        return info
    except Exception:
        return {}


def generate_unique_id() -> str:
    """
    生成唯一ID
    
    Returns:
        唯一ID字符串
    """
    try:
        import uuid
        return str(uuid.uuid4())
    except Exception:
        # 回退方案
        import random
        return str(int(time.time() * 1000000) + random.randint(0, 999999))


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    展平嵌套字典
    
    Args:
        d: 嵌套字典
        separator: 分隔符
        
    Returns:
        展平后的字典
    """
    def _flatten(obj, prefix=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                yield from _flatten(value, new_key)
        else:
            yield prefix, obj
    
    return dict(_flatten(d))


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 原始列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    获取嵌套字典中的值
    
    Args:
        data: 字典数据
        key_path: 键路径，用点号分隔
        default: 默认值
        
    Returns:
        获取到的值
    """
    try:
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            value = value[key]
        
        return value
    except (KeyError, TypeError):
        return default


def set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    设置嵌套字典中的值
    
    Args:
        data: 字典数据
        key_path: 键路径，用点号分隔
        value: 要设置的值
    """
    keys = key_path.split('.')
    target = data
    
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]
    
    target[keys[-1]] = value


class SingletonMeta(type):
    """单例元类"""
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.logger.debug(f"{self.name} 耗时: {elapsed:.3f}秒")
    
    def elapsed(self) -> float:
        """获取已消耗时间"""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0


# 常用的便捷函数
def now() -> datetime:
    """获取当前时间"""
    return datetime.now()


def today() -> datetime:
    """获取今天的日期"""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def yesterday() -> datetime:
    """获取昨天的日期"""
    return today() - timedelta(days=1)


def tomorrow() -> datetime:
    """获取明天的日期"""
    return today() + timedelta(days=1)


def is_business_day(date: datetime) -> bool:
    """判断是否为工作日"""
    return date.weekday() < 5  # 0-4 为周一到周五


def next_business_day(date: datetime) -> datetime:
    """获取下一个工作日"""
    next_day = date + timedelta(days=1)
    while not is_business_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix