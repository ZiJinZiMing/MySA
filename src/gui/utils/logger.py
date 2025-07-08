"""
日志工具模块 - 统一的日志管理
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
import functools


def setup_logger(name: str, level: str = "INFO", 
                config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        config: 日志配置字典
        
    Returns:
        配置好的日志器
    """
    # 默认配置
    default_config = {
        "level": level,
        "file_handler": True,
        "console_handler": True,
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
        "log_dir": "logs",
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S"
    }
    
    # 合并配置
    if config:
        default_config.update(config)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, default_config["level"].upper()))
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        default_config["log_format"],
        default_config["date_format"]
    )
    
    # 添加文件处理器
    if default_config["file_handler"]:
        # 确保日志目录存在
        log_dir = default_config["log_dir"]
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志文件路径
        log_file = os.path.join(log_dir, f"{name}.log")
        
        # 创建轮转文件处理器
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=default_config["max_file_size"],
            backupCount=default_config["backup_count"],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 添加控制台处理器
    if default_config["console_handler"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def log_api_call(func):
    """
    API调用日志装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # 记录API调用开始
        logger.debug(f"API调用开始: {func.__name__}")
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            
            # 记录API调用成功
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.debug(f"API调用成功: {func.__name__}, 耗时: {duration:.2f}秒")
            
            return result
            
        except Exception as e:
            # 记录API调用失败
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"API调用失败: {func.__name__}, 耗时: {duration:.2f}秒, 错误: {e}")
            raise
    
    return wrapper


def log_error(func):
    """
    错误日志装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {func.__name__} 发生错误: {e}", exc_info=True)
            raise
    
    return wrapper


def log_performance(func):
    """
    性能日志装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 记录性能信息
            if duration > 1.0:  # 超过1秒的调用记录为警告
                logger.warning(f"函数 {func.__name__} 执行时间较长: {duration:.2f}秒")
            else:
                logger.debug(f"函数 {func.__name__} 执行完成, 耗时: {duration:.2f}秒")
            
            return result
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"函数 {func.__name__} 执行失败, 耗时: {duration:.2f}秒, 错误: {e}")
            raise
    
    return wrapper


class LogHandler:
    """日志处理器类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化日志处理器
        
        Args:
            config: 日志配置
        """
        self.config = config
        self.logger = setup_logger("LogHandler", config.get("level", "INFO"))
    
    def format_message(self, level: str, message: str, context: Optional[Dict] = None) -> str:
        """
        格式化日志消息
        
        Args:
            level: 日志级别
            message: 消息内容
            context: 上下文信息
            
        Returns:
            格式化后的消息
        """
        if context:
            context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
            return f"{message} | {context_str}"
        return message
    
    def log_system_info(self) -> None:
        """记录系统信息"""
        import platform
        import psutil
        
        system_info = {
            "系统": platform.system(),
            "版本": platform.version(),
            "架构": platform.architecture()[0],
            "处理器": platform.processor(),
            "内存": f"{psutil.virtual_memory().total / (1024**3):.1f}GB",
            "Python版本": platform.python_version()
        }
        
        for key, value in system_info.items():
            self.logger.info(f"系统信息 - {key}: {value}")
    
    def log_application_start(self, app_name: str, version: str) -> None:
        """
        记录应用启动信息
        
        Args:
            app_name: 应用名称
            version: 应用版本
        """
        self.logger.info(f"应用启动: {app_name} v{version}")
        self.logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_system_info()
    
    def log_application_stop(self, app_name: str) -> None:
        """
        记录应用停止信息
        
        Args:
            app_name: 应用名称
        """
        self.logger.info(f"应用停止: {app_name}")
        self.logger.info(f"停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def log_data_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """
        记录数据操作
        
        Args:
            operation: 操作类型
            details: 操作详情
        """
        message = f"数据操作: {operation}"
        formatted_message = self.format_message("INFO", message, details)
        self.logger.info(formatted_message)
    
    def log_user_action(self, action: str, user_id: str = "default") -> None:
        """
        记录用户操作
        
        Args:
            action: 用户操作
            user_id: 用户ID
        """
        context = {
            "用户": user_id,
            "时间": datetime.now().strftime('%H:%M:%S')
        }
        message = f"用户操作: {action}"
        formatted_message = self.format_message("INFO", message, context)
        self.logger.info(formatted_message)
    
    def log_configuration_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        记录配置更改
        
        Args:
            key: 配置键
            old_value: 旧值
            new_value: 新值
        """
        context = {
            "配置项": key,
            "旧值": str(old_value),
            "新值": str(new_value)
        }
        message = "配置更改"
        formatted_message = self.format_message("INFO", message, context)
        self.logger.info(formatted_message)
    
    def log_network_request(self, url: str, method: str, status_code: int, 
                          response_time: float) -> None:
        """
        记录网络请求
        
        Args:
            url: 请求URL
            method: 请求方法
            status_code: 状态码
            response_time: 响应时间
        """
        context = {
            "URL": url,
            "方法": method,
            "状态码": status_code,
            "响应时间": f"{response_time:.2f}秒"
        }
        message = "网络请求"
        formatted_message = self.format_message("DEBUG", message, context)
        
        if status_code >= 400:
            self.logger.error(formatted_message)
        elif response_time > 5.0:
            self.logger.warning(formatted_message)
        else:
            self.logger.debug(formatted_message)
    
    def log_exception(self, exception: Exception, context: Optional[Dict] = None) -> None:
        """
        记录异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
        """
        message = f"异常: {type(exception).__name__}: {str(exception)}"
        formatted_message = self.format_message("ERROR", message, context)
        self.logger.error(formatted_message, exc_info=True)
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
        """
        try:
            log_dir = self.config.get("log_dir", "logs")
            if not os.path.exists(log_dir):
                return
            
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_dir, filename)
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        self.logger.info(f"删除旧日志文件: {filename}")
        
        except Exception as e:
            self.logger.error(f"清理旧日志文件失败: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            日志统计信息
        """
        try:
            log_dir = self.config.get("log_dir", "logs")
            if not os.path.exists(log_dir):
                return {"error": "日志目录不存在"}
            
            stats = {
                "日志目录": log_dir,
                "日志文件数": 0,
                "总大小": 0,
                "最新日志": None,
                "最旧日志": None
            }
            
            log_files = []
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_dir, filename)
                    file_size = os.path.getsize(filepath)
                    file_time = os.path.getmtime(filepath)
                    
                    stats["日志文件数"] += 1
                    stats["总大小"] += file_size
                    log_files.append((filename, file_time))
            
            if log_files:
                log_files.sort(key=lambda x: x[1])
                stats["最旧日志"] = log_files[0][0]
                stats["最新日志"] = log_files[-1][0]
            
            # 格式化文件大小
            size_mb = stats["总大小"] / (1024 * 1024)
            stats["总大小"] = f"{size_mb:.2f}MB"
            
            return stats
            
        except Exception as e:
            return {"error": f"获取日志统计失败: {e}"}


# 预定义的日志器
app_logger = None
api_logger = None
ui_logger = None
data_logger = None


def init_loggers(config: Dict[str, Any]) -> None:
    """
    初始化所有日志器
    
    Args:
        config: 日志配置
    """
    global app_logger, api_logger, ui_logger, data_logger
    
    app_logger = setup_logger("app", config.get("level", "INFO"), config)
    api_logger = setup_logger("api", config.get("level", "INFO"), config)
    ui_logger = setup_logger("ui", config.get("level", "INFO"), config)
    data_logger = setup_logger("data", config.get("level", "INFO"), config)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器对象
    """
    return logging.getLogger(name)