#!/usr/bin/env python3
"""
MSTR/BTC溢价监控GUI - 主程序入口
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入GUI模块
from src.gui.ui.main_window import MSTRMonitorGUI
from src.gui.utils.logger import setup_logger
from src.gui.utils.helpers import get_app_data_dir, check_dependencies
from src.gui.core.config_manager import ConfigManager


def setup_logging(log_level: str = "INFO") -> None:
    """
    设置日志系统
    
    Args:
        log_level: 日志级别
    """
    try:
        # 创建日志目录
        log_dir = os.path.join(get_app_data_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件路径
        log_file = os.path.join(log_dir, "mstr_gui.log")
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"日志系统已启动，日志文件: {log_file}")
        
    except Exception as e:
        print(f"设置日志系统时发生错误: {e}")
        sys.exit(1)


def check_chrome_debug_port() -> bool:
    """
    检查Chrome远程调试端口是否可用
    
    Returns:
        是否可用
    """
    try:
        import requests
        response = requests.get('http://127.0.0.1:9222/json/version', timeout=5)
        return response.status_code == 200
    except:
        return False


def show_chrome_setup_help() -> None:
    """显示Chrome设置帮助"""
    help_text = """
Chrome远程调试设置帮助
======================

此应用程序需要Chrome浏览器以远程调试模式运行。

Windows系统:
1. 关闭所有Chrome窗口
2. 打开命令提示符
3. 运行: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
4. 在Chrome中登录SeekingAlpha

Linux系统:
1. 关闭所有Chrome窗口
2. 打开终端
3. 运行: google-chrome --remote-debugging-port=9222
4. 在Chrome中登录SeekingAlpha

macOS系统:
1. 关闭所有Chrome窗口
2. 打开终端
3. 运行: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
4. 在Chrome中登录SeekingAlpha

注意事项:
• 请确保Chrome浏览器已安装并可在命令行中使用
• 必须先关闭所有Chrome窗口再启动调试模式
• 启动后请访问SeekingAlpha并完成登录
• 保持Chrome窗口打开直到程序结束
"""
    
    print(help_text)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="MSTR/BTC溢价监控GUI应用程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 使用默认配置启动
  %(prog)s --log-level DEBUG  # 启用调试日志
  %(prog)s --config myconfig.json  # 使用自定义配置文件
  %(prog)s --check-deps       # 检查依赖项
  %(prog)s --chrome-help      # 显示Chrome设置帮助
        """
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='设置日志级别 (默认: INFO)'
    )
    
    parser.add_argument(
        '--config',
        help='指定配置文件路径'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='检查依赖项并退出'
    )
    
    parser.add_argument(
        '--chrome-help',
        action='store_true',
        help='显示Chrome设置帮助并退出'
    )
    
    parser.add_argument(
        '--no-chrome-check',
        action='store_true',
        help='跳过Chrome连接检查'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='MSTR GUI v1.0.0'
    )
    
    return parser


def main():
    """主函数"""
    try:
        # 解析命令行参数
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # 显示Chrome设置帮助
        if args.chrome_help:
            show_chrome_setup_help()
            return 0
        
        # 检查依赖项
        if args.check_deps:
            print("检查依赖项...")
            missing_deps = check_dependencies()
            if missing_deps:
                print(f"缺少依赖项: {', '.join(missing_deps)}")
                print("请运行: pip install " + " ".join(missing_deps))
                return 1
            else:
                print("所有依赖项都已安装")
                return 0
        
        # 设置日志
        setup_logging(args.log_level)
        logger = logging.getLogger(__name__)
        
        logger.info("MSTR/BTC溢价监控GUI启动")
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"工作目录: {os.getcwd()}")
        
        # 检查依赖项
        missing_deps = check_dependencies()
        if missing_deps:
            logger.error(f"缺少依赖项: {', '.join(missing_deps)}")
            print(f"错误: 缺少依赖项 {', '.join(missing_deps)}")
            print("请运行: pip install " + " ".join(missing_deps))
            return 1
        
        # 检查Chrome远程调试连接
        if not args.no_chrome_check:
            logger.info("检查Chrome远程调试连接...")
            if not check_chrome_debug_port():
                logger.warning("Chrome远程调试端口(9222)不可用")
                print("警告: Chrome远程调试端口(9222)不可用")
                print("请确保Chrome浏览器以远程调试模式运行")
                print("使用 --chrome-help 查看设置帮助")
                print("使用 --no-chrome-check 跳过此检查")
                
                response = input("继续启动吗? (y/N): ")
                if response.lower() != 'y':
                    return 1
            else:
                logger.info("Chrome远程调试连接正常")
        
        # 初始化配置管理器
        config_manager = ConfigManager()
        if args.config:
            logger.info(f"使用配置文件: {args.config}")
            if not config_manager.load_config(args.config):
                logger.error("加载配置文件失败")
                return 1
        
        # 创建GUI应用
        logger.info("创建GUI应用...")
        app = MSTRMonitorGUI()
        
        # 启动应用
        logger.info("启动GUI应用...")
        app.run()
        
        logger.info("应用正常退出")
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"程序运行时发生错误: {e}", exc_info=True)
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())