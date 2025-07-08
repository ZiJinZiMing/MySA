#!/usr/bin/env python3
"""
MSTR/BTC溢价监控 - 安装脚本
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    print(f"✓ Python版本检查通过: {sys.version}")
    return True


def install_requirements():
    """安装依赖包"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("错误: requirements.txt文件不存在")
        return False
    
    print("安装Python依赖包...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)
        print("✓ 依赖包安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: 依赖包安装失败: {e}")
        return False


def check_chrome():
    """检查Chrome浏览器"""
    chrome_commands = [
        "google-chrome --version",
        "chrome --version",
        "chromium --version",
        "chromium-browser --version"
    ]
    
    for cmd in chrome_commands:
        try:
            result = subprocess.run(
                cmd.split(), 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ 找到Chrome浏览器: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    print("警告: 未找到Chrome浏览器")
    print("请确保已安装Chrome浏览器并可从命令行访问")
    return False


def create_config():
    """创建配置文件"""
    config_dir = Path(__file__).parent / "configs"
    user_config = config_dir / "user_config.json"
    default_config = config_dir / "default_config.json"
    
    if user_config.exists():
        print("✓ 用户配置文件已存在")
        return True
    
    if default_config.exists():
        try:
            import shutil
            shutil.copy(default_config, user_config)
            print("✓ 创建用户配置文件")
            return True
        except Exception as e:
            print(f"警告: 创建配置文件失败: {e}")
            return False
    
    print("警告: 默认配置文件不存在")
    return False


def setup_desktop_shortcut():
    """设置桌面快捷方式 (仅Linux)"""
    if sys.platform != "linux":
        return True
    
    try:
        desktop_dir = Path.home() / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = Path.home() / "桌面"
        
        if desktop_dir.exists():
            shortcut_path = desktop_dir / "MSTR监控.desktop"
            script_path = Path(__file__).parent / "mstr_gui.py"
            
            shortcut_content = f"""[Desktop Entry]
Name=MSTR/BTC溢价监控
Comment=MSTR/BTC Premium Monitor
Exec=python3 {script_path}
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Office;Finance;
"""
            
            with open(shortcut_path, 'w', encoding='utf-8') as f:
                f.write(shortcut_content)
            
            os.chmod(shortcut_path, 0o755)
            print("✓ 创建桌面快捷方式")
            
    except Exception as e:
        print(f"警告: 创建桌面快捷方式失败: {e}")
    
    return True


def main():
    """主安装函数"""
    print("MSTR/BTC溢价监控 - 安装程序")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return 1
    
    # 安装依赖包
    if not install_requirements():
        return 1
    
    # 检查Chrome
    check_chrome()
    
    # 创建配置文件
    create_config()
    
    # 设置桌面快捷方式
    setup_desktop_shortcut()
    
    print("\n" + "=" * 50)
    print("安装完成!")
    print("\n使用说明:")
    print("1. 配置Finnhub API密钥:")
    print("   编辑 configs/user_config.json 文件")
    print("   在 'finnhub_api_key' 字段输入您的API密钥")
    print("\n2. 启动Chrome调试模式:")
    print("   google-chrome --remote-debugging-port=9222")
    print("\n3. 启动监控程序:")
    print("   python3 mstr_gui.py")
    print("\n4. 查看帮助:")
    print("   python3 mstr_gui.py --help")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n安装过程中发生错误: {e}")
        sys.exit(1)