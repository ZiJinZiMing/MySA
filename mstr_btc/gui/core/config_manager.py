"""
配置管理模块 - 管理应用配置的加载、保存和验证
"""

import json
import os
import shutil
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config/user_config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 用户配置文件路径
        """
        self.config_file = config_file
        self.default_config_file = "config/default_config.json"
        self.backup_dir = "config/backups"
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 加载配置
        self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            # 首先尝试加载用户配置
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    
                # 合并默认配置和用户配置
                default_config = self.get_default_config()
                self.config = self._merge_configs(default_config, user_config)
                
                self.logger.info(f"成功加载用户配置: {self.config_file}")
                
            else:
                # 如果用户配置不存在，使用默认配置
                self.config = self.get_default_config()
                self.save_config()  # 创建用户配置文件
                
                self.logger.info("使用默认配置并创建用户配置文件")
                
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            self.config = self.get_default_config()
            
        return self.config
    
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            # 创建配置备份
            self._create_backup()
            
            # 保存配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"配置保存成功: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            "api": {
                "finnhub_api_key": "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g",
                "request_timeout": 10,
                "retry_count": 3,
                "retry_delay": 1.0,
                "rate_limit_interval": 0.5
            },
            "monitor": {
                "default_interval": 10,
                "max_data_points": 1000,
                "btc_per_share": 0.00207973,
                "auto_start": False,
                "auto_cleanup_hours": 24
            },
            "ui": {
                "window_width": 1000,
                "window_height": 700,
                "window_x": 100,
                "window_y": 100,
                "default_time_range": 3600,
                "theme": "default",
                "font_size": 10,
                "always_on_top": False,
                "minimize_to_tray": False
            },
            "chart": {
                "line_color": "#1f77b4",
                "line_width": 2,
                "grid_alpha": 0.3,
                "animation_interval": 1000,
                "background_color": "#f8f9fa",
                "show_grid": True,
                "show_legend": True
            },
            "alerts": {
                "enabled": False,
                "high_premium_threshold": 50.0,
                "low_premium_threshold": -10.0,
                "price_change_threshold": 5.0,
                "sound_enabled": True,
                "sound_volume": 0.5
            },
            "logging": {
                "level": "INFO",
                "file_handler": True,
                "console_handler": True,
                "max_file_size": 10485760,  # 10MB
                "backup_count": 5,
                "log_dir": "logs"
            },
            "export": {
                "default_format": "csv",
                "include_headers": True,
                "date_format": "%Y-%m-%d %H:%M:%S",
                "default_export_dir": "exports"
            }
        }
    
    def get(self, key: str, default=None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到目标位置
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        
        self.logger.debug(f"设置配置: {key} = {value}")
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        验证配置有效性
        
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        
        try:
            # 验证API配置
            api_key = self.get("api.finnhub_api_key")
            if not api_key or len(api_key) < 10:
                errors.append("API密钥无效")
            
            timeout = self.get("api.request_timeout")
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("请求超时时间必须为正数")
            
            # 验证监控配置
            interval = self.get("monitor.default_interval")
            if not isinstance(interval, (int, float)) or interval < 1:
                errors.append("更新间隔必须至少为1秒")
            
            max_points = self.get("monitor.max_data_points")
            if not isinstance(max_points, int) or max_points < 100:
                errors.append("最大数据点数必须至少为100")
            
            btc_per_share = self.get("monitor.btc_per_share")
            if not isinstance(btc_per_share, (int, float)) or btc_per_share <= 0:
                errors.append("BTC per share必须为正数")
            
            # 验证UI配置
            width = self.get("ui.window_width")
            height = self.get("ui.window_height")
            if not isinstance(width, int) or width < 600:
                errors.append("窗口宽度必须至少为600")
            if not isinstance(height, int) or height < 400:
                errors.append("窗口高度必须至少为400")
            
            # 验证图表配置
            line_width = self.get("chart.line_width")
            if not isinstance(line_width, (int, float)) or line_width <= 0:
                errors.append("线条宽度必须为正数")
            
            grid_alpha = self.get("chart.grid_alpha")
            if not isinstance(grid_alpha, (int, float)) or not (0 <= grid_alpha <= 1):
                errors.append("网格透明度必须在0-1之间")
            
        except Exception as e:
            errors.append(f"配置验证异常: {e}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = self.get_default_config()
        self.save_config()
        self.logger.info("配置已重置为默认值")
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            new_config: 新配置字典
        """
        self.config = self._merge_configs(self.config, new_config)
        self.save_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            配置摘要字典
        """
        return {
            "api_key_configured": bool(self.get("api.finnhub_api_key")),
            "update_interval": self.get("monitor.default_interval"),
            "max_data_points": self.get("monitor.max_data_points"),
            "window_size": f"{self.get('ui.window_width')}x{self.get('ui.window_height')}",
            "alerts_enabled": self.get("alerts.enabled"),
            "logging_level": self.get("logging.level"),
            "last_modified": datetime.fromtimestamp(
                os.path.getmtime(self.config_file)
            ).strftime("%Y-%m-%d %H:%M:%S") if os.path.exists(self.config_file) else "未知"
        }
    
    def export_config(self, filename: str) -> bool:
        """
        导出配置到文件
        
        Args:
            filename: 导出文件名
            
        Returns:
            是否成功导出
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置导出成功: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            return False
    
    def import_config(self, filename: str) -> bool:
        """
        从文件导入配置
        
        Args:
            filename: 导入文件名
            
        Returns:
            是否成功导入
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证导入的配置
            temp_config = self.config.copy()
            self.config = self._merge_configs(self.get_default_config(), imported_config)
            
            is_valid, errors = self.validate_config()
            if not is_valid:
                self.config = temp_config
                self.logger.error(f"导入的配置无效: {errors}")
                return False
            
            self.save_config()
            self.logger.info(f"配置导入成功: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            return False
    
    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并配置字典
        
        Args:
            base: 基础配置
            update: 更新配置
            
        Returns:
            合并后的配置
        """
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_backup(self) -> None:
        """创建配置备份"""
        if os.path.exists(self.config_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"config_backup_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            try:
                shutil.copy2(self.config_file, backup_path)
                self.logger.debug(f"创建配置备份: {backup_path}")
                
                # 清理旧备份文件（保留最近10个）
                self._cleanup_backups()
                
            except Exception as e:
                self.logger.warning(f"创建配置备份失败: {e}")
    
    def _cleanup_backups(self) -> None:
        """清理旧的备份文件"""
        try:
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("config_backup_") and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除超过10个的旧备份
            for filepath, _ in backup_files[10:]:
                os.remove(filepath)
                self.logger.debug(f"删除旧备份: {filepath}")
                
        except Exception as e:
            self.logger.warning(f"清理备份文件失败: {e}")
    
    def get_available_backups(self) -> list[tuple[str, str]]:
        """
        获取可用的备份文件
        
        Returns:
            备份文件列表，每个元素为(文件路径, 创建时间)
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("config_backup_") and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    create_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    backups.append((filepath, create_time))
            
            # 按时间排序
            backups.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            self.logger.error(f"获取备份文件列表失败: {e}")
        
        return backups
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        从备份恢复配置
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否成功恢复
        """
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 先备份当前配置
            self._create_backup()
            
            # 恢复配置
            shutil.copy2(backup_path, self.config_file)
            self.load_config()
            
            self.logger.info(f"从备份恢复配置成功: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"从备份恢复配置失败: {e}")
            return False