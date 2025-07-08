"""
数据验证工具模块 - 数据验证和类型检查
"""

import re
import logging
from typing import Any, Dict, List, Tuple, Optional, Union
from datetime import datetime


def validate_price(price: Any) -> bool:
    """
    验证价格数据
    
    Args:
        price: 价格数据
        
    Returns:
        是否有效
    """
    try:
        if price is None:
            return False
        
        # 转换为浮点数
        price_float = float(price)
        
        # 检查是否为有效数字
        if price_float != price_float:  # 检查NaN
            return False
        
        if price_float == float('inf') or price_float == float('-inf'):
            return False
        
        # 检查价格范围（价格应该为正数且在合理范围内）
        if price_float <= 0 or price_float > 1000000:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_premium(premium: Any) -> bool:
    """
    验证溢价率数据
    
    Args:
        premium: 溢价率数据
        
    Returns:
        是否有效
    """
    try:
        if premium is None:
            return False
        
        # 转换为浮点数
        premium_float = float(premium)
        
        # 检查是否为有效数字
        if premium_float != premium_float:  # 检查NaN
            return False
        
        if premium_float == float('inf') or premium_float == float('-inf'):
            return False
        
        # 检查溢价率范围（通常在-100%到500%之间）
        if premium_float < -100 or premium_float > 500:
            return False
        
        return True
        
    except (ValueError, TypeError):
        return False


def validate_api_key(api_key: str) -> bool:
    """
    验证API密钥
    
    Args:
        api_key: API密钥
        
    Returns:
        是否有效
    """
    try:
        if not isinstance(api_key, str):
            return False
        
        # 检查长度（Finnhub API密钥通常是32个字符）
        if len(api_key) < 10 or len(api_key) > 64:
            return False
        
        # 检查字符（只包含字母、数字和特定符号）
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            return False
        
        return True
        
    except Exception:
        return False


def validate_symbol(symbol: str) -> bool:
    """
    验证股票代码
    
    Args:
        symbol: 股票代码
        
    Returns:
        是否有效
    """
    try:
        if not isinstance(symbol, str):
            return False
        
        # 去除空格
        symbol = symbol.strip().upper()
        
        # 检查长度
        if len(symbol) < 1 or len(symbol) > 20:
            return False
        
        # 检查格式（基本的股票代码格式）
        if not re.match(r'^[A-Z][A-Z0-9.:_-]*$', symbol):
            return False
        
        return True
        
    except Exception:
        return False


def validate_timestamp(timestamp: Any) -> bool:
    """
    验证时间戳
    
    Args:
        timestamp: 时间戳
        
    Returns:
        是否有效
    """
    try:
        if timestamp is None:
            return False
        
        # 如果是datetime对象
        if isinstance(timestamp, datetime):
            # 检查是否在合理范围内（2000年到2050年）
            if timestamp.year < 2000 or timestamp.year > 2050:
                return False
            return True
        
        # 如果是字符串，尝试解析
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return validate_timestamp(dt)
            except ValueError:
                return False
        
        # 如果是数字，假设是Unix时间戳
        if isinstance(timestamp, (int, float)):
            try:
                dt = datetime.fromtimestamp(timestamp)
                return validate_timestamp(dt)
            except (ValueError, OSError):
                return False
        
        return False
        
    except Exception:
        return False


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证配置文件
    
    Args:
        config: 配置字典
        
    Returns:
        (是否有效, 错误消息列表)
    """
    errors = []
    
    try:
        # 验证API配置
        if 'api' in config:
            api_config = config['api']
            
            # 验证API密钥
            if 'finnhub_api_key' in api_config:
                if not validate_api_key(api_config['finnhub_api_key']):
                    errors.append("API密钥格式无效")
            
            # 验证超时时间
            if 'request_timeout' in api_config:
                timeout = api_config['request_timeout']
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    errors.append("请求超时时间必须为正数")
            
            # 验证重试次数
            if 'retry_count' in api_config:
                retry_count = api_config['retry_count']
                if not isinstance(retry_count, int) or retry_count < 0:
                    errors.append("重试次数必须为非负整数")
        
        # 验证监控配置
        if 'monitor' in config:
            monitor_config = config['monitor']
            
            # 验证更新间隔
            if 'default_interval' in monitor_config:
                interval = monitor_config['default_interval']
                if not isinstance(interval, (int, float)) or interval < 1:
                    errors.append("更新间隔必须至少为1秒")
            
            # 验证最大数据点
            if 'max_data_points' in monitor_config:
                max_points = monitor_config['max_data_points']
                if not isinstance(max_points, int) or max_points < 100:
                    errors.append("最大数据点数必须至少为100")
            
            # 验证BTC per share
            if 'btc_per_share' in monitor_config:
                btc_per_share = monitor_config['btc_per_share']
                if not isinstance(btc_per_share, (int, float)) or btc_per_share <= 0:
                    errors.append("BTC per share必须为正数")
        
        # 验证UI配置
        if 'ui' in config:
            ui_config = config['ui']
            
            # 验证窗口大小
            if 'window_width' in ui_config:
                width = ui_config['window_width']
                if not isinstance(width, int) or width < 600:
                    errors.append("窗口宽度必须至少为600像素")
            
            if 'window_height' in ui_config:
                height = ui_config['window_height']
                if not isinstance(height, int) or height < 400:
                    errors.append("窗口高度必须至少为400像素")
            
            # 验证字体大小
            if 'font_size' in ui_config:
                font_size = ui_config['font_size']
                if not isinstance(font_size, int) or font_size < 8 or font_size > 24:
                    errors.append("字体大小必须在8-24之间")
        
        # 验证图表配置
        if 'chart' in config:
            chart_config = config['chart']
            
            # 验证线条宽度
            if 'line_width' in chart_config:
                line_width = chart_config['line_width']
                if not isinstance(line_width, (int, float)) or line_width <= 0:
                    errors.append("线条宽度必须为正数")
            
            # 验证网格透明度
            if 'grid_alpha' in chart_config:
                grid_alpha = chart_config['grid_alpha']
                if not isinstance(grid_alpha, (int, float)) or not (0 <= grid_alpha <= 1):
                    errors.append("网格透明度必须在0-1之间")
            
            # 验证颜色格式
            if 'line_color' in chart_config:
                color = chart_config['line_color']
                if not validate_color(color):
                    errors.append("线条颜色格式无效")
        
        # 验证告警配置
        if 'alerts' in config:
            alerts_config = config['alerts']
            
            # 验证阈值
            if 'high_premium_threshold' in alerts_config:
                threshold = alerts_config['high_premium_threshold']
                if not isinstance(threshold, (int, float)):
                    errors.append("高溢价阈值必须为数字")
            
            if 'low_premium_threshold' in alerts_config:
                threshold = alerts_config['low_premium_threshold']
                if not isinstance(threshold, (int, float)):
                    errors.append("低溢价阈值必须为数字")
            
            # 验证音量
            if 'sound_volume' in alerts_config:
                volume = alerts_config['sound_volume']
                if not isinstance(volume, (int, float)) or not (0 <= volume <= 1):
                    errors.append("音量必须在0-1之间")
        
        is_valid = len(errors) == 0
        return is_valid, errors
        
    except Exception as e:
        errors.append(f"配置验证异常: {str(e)}")
        return False, errors


def validate_color(color: str) -> bool:
    """
    验证颜色格式
    
    Args:
        color: 颜色字符串
        
    Returns:
        是否有效
    """
    try:
        if not isinstance(color, str):
            return False
        
        # 检查十六进制颜色格式
        if re.match(r'^#[0-9a-fA-F]{6}$', color):
            return True
        
        # 检查RGB格式
        if re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', color):
            return True
        
        # 检查颜色名称
        color_names = [
            'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink',
            'brown', 'gray', 'black', 'white', 'cyan', 'magenta'
        ]
        
        if color.lower() in color_names:
            return True
        
        return False
        
    except Exception:
        return False


class DataValidator:
    """数据验证器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def is_valid_numeric(value: Any, min_val: Optional[float] = None, 
                        max_val: Optional[float] = None) -> bool:
        """
        验证数值范围
        
        Args:
            value: 待验证的值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            是否有效
        """
        try:
            if value is None:
                return False
            
            # 转换为浮点数
            num_value = float(value)
            
            # 检查是否为有效数字
            if num_value != num_value:  # 检查NaN
                return False
            
            if num_value == float('inf') or num_value == float('-inf'):
                return False
            
            # 检查范围
            if min_val is not None and num_value < min_val:
                return False
            
            if max_val is not None and num_value > max_val:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_string(value: Any, min_length: int = 0, 
                       max_length: Optional[int] = None, 
                       pattern: Optional[str] = None) -> bool:
        """
        验证字符串
        
        Args:
            value: 待验证的值
            min_length: 最小长度
            max_length: 最大长度
            pattern: 正则表达式模式
            
        Returns:
            是否有效
        """
        try:
            if not isinstance(value, str):
                return False
            
            # 检查长度
            if len(value) < min_length:
                return False
            
            if max_length is not None and len(value) > max_length:
                return False
            
            # 检查模式
            if pattern is not None:
                if not re.match(pattern, value):
                    return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        try:
            if not isinstance(email, str):
                return False
            
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, email) is not None
            
        except Exception:
            return False
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: URL地址
            
        Returns:
            是否有效
        """
        try:
            if not isinstance(url, str):
                return False
            
            pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            return re.match(pattern, url) is not None
            
        except Exception:
            return False
    
    def validate_data_point(self, timestamp: Any, mstr_price: Any, 
                          btc_price: Any, premium: Any) -> Tuple[bool, str]:
        """
        验证数据点
        
        Args:
            timestamp: 时间戳
            mstr_price: MSTR价格
            btc_price: BTC价格
            premium: 溢价率
            
        Returns:
            (是否有效, 错误消息)
        """
        try:
            # 验证时间戳
            if not validate_timestamp(timestamp):
                return False, "时间戳无效"
            
            # 验证MSTR价格
            if not validate_price(mstr_price):
                return False, "MSTR价格无效"
            
            # 验证BTC价格
            if not validate_price(btc_price):
                return False, "BTC价格无效"
            
            # 验证溢价率
            if not validate_premium(premium):
                return False, "溢价率无效"
            
            return True, ""
            
        except Exception as e:
            return False, f"验证数据点时发生错误: {str(e)}"
    
    def validate_batch_data(self, data_list: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        批量验证数据
        
        Args:
            data_list: 数据列表
            
        Returns:
            (是否全部有效, 错误消息列表)
        """
        errors = []
        
        try:
            for i, data in enumerate(data_list):
                # 检查必需字段
                required_fields = ['timestamp', 'mstr_price', 'btc_price', 'premium']
                for field in required_fields:
                    if field not in data:
                        errors.append(f"数据项 {i}: 缺少字段 {field}")
                        continue
                
                # 验证数据点
                is_valid, error_msg = self.validate_data_point(
                    data['timestamp'],
                    data['mstr_price'],
                    data['btc_price'],
                    data['premium']
                )
                
                if not is_valid:
                    errors.append(f"数据项 {i}: {error_msg}")
            
            is_all_valid = len(errors) == 0
            return is_all_valid, errors
            
        except Exception as e:
            errors.append(f"批量验证时发生错误: {str(e)}")
            return False, errors
    
    def sanitize_input(self, value: Any, data_type: str) -> Any:
        """
        清理输入数据
        
        Args:
            value: 输入值
            data_type: 数据类型
            
        Returns:
            清理后的值
        """
        try:
            if value is None:
                return None
            
            if data_type == 'string':
                return str(value).strip()
            
            elif data_type == 'int':
                return int(float(value))
            
            elif data_type == 'float':
                return float(value)
            
            elif data_type == 'bool':
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                else:
                    return bool(value)
            
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"清理输入数据时发生错误: {e}")
            return None


# 便捷验证函数
def quick_validate(value: Any, validator_type: str, **kwargs) -> bool:
    """
    快速验证函数
    
    Args:
        value: 待验证的值
        validator_type: 验证器类型
        **kwargs: 额外参数
        
    Returns:
        是否有效
    """
    validators = {
        'price': validate_price,
        'premium': validate_premium,
        'api_key': validate_api_key,
        'symbol': validate_symbol,
        'timestamp': validate_timestamp,
        'color': validate_color
    }
    
    validator = validators.get(validator_type)
    if validator is None:
        return False
    
    try:
        return validator(value, **kwargs)
    except Exception:
        return False