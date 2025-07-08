# MSTR/BTC溢价监控 - 安装指南

## 📋 系统要求

### 必需软件
- **Python 3.7+**: 推荐使用Python 3.8或更高版本
- **Chrome浏览器**: 支持远程调试功能
- **网络连接**: 用于API请求和数据获取

### 硬件要求
- **内存**: 最少2GB RAM，推荐4GB以上
- **存储**: 至少100MB可用空间
- **显示器**: 最小分辨率1024x768

## 🚀 快速安装

### 1. 自动安装 (推荐)
```bash
# 进入项目目录
cd mstr_btc

# 运行安装脚本
python3 install.py
```

### 2. 手动安装

#### 步骤1: 检查Python版本
```bash
python3 --version
# 应该显示Python 3.7或更高版本
```

#### 步骤2: 安装依赖包
```bash
pip3 install -r requirements.txt
```

#### 步骤3: 验证安装
```bash
python3 -c "import tkinter, requests, selenium, matplotlib; print('所有依赖包安装成功')"
```

## ⚙️ 配置设置

### 1. API密钥配置
1. 访问 [Finnhub.io](https://finnhub.io) 注册免费账户
2. 获取API密钥
3. 编辑配置文件:
```bash
cp configs/default_config.json configs/user_config.json
# 编辑 configs/user_config.json 文件
# 在 "finnhub_api_key" 字段输入您的API密钥
```

### 2. Chrome浏览器设置
启动Chrome调试模式:

**Windows:**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222
```

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### 3. SeekingAlpha登录
1. 在Chrome中访问 [SeekingAlpha](https://seekingalpha.com)
2. 完成登录
3. 保持浏览器会话活跃

## 🏃‍♂️ 运行应用

### 启动GUI应用
```bash
# 基本启动
python3 mstr_gui.py

# 查看所有选项
python3 mstr_gui.py --help

# 使用调试模式
python3 mstr_gui.py --log-level DEBUG
```

### 命令行参数
```bash
--log-level {DEBUG,INFO,WARNING,ERROR}  # 设置日志级别
--config CONFIG_FILE                   # 指定配置文件
--check-deps                           # 检查依赖项
--chrome-help                          # 显示Chrome设置帮助
--no-chrome-check                      # 跳过Chrome连接检查
--version                              # 显示版本信息
```

## 🔧 故障排除

### 常见问题

#### 1. Python版本过低
```bash
# 错误信息: 需要Python 3.7或更高版本
# 解决方案: 升级Python
sudo apt update && sudo apt install python3.8
```

#### 2. 依赖包安装失败
```bash
# 错误信息: pip install失败
# 解决方案: 使用虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

#### 3. Chrome连接失败
```bash
# 错误信息: Chrome远程调试端口不可用
# 解决方案:
# 1. 确保Chrome完全关闭
# 2. 重新启动Chrome调试模式
# 3. 检查端口9222是否被占用
netstat -an | grep 9222
```

#### 4. API连接失败
```bash
# 错误信息: API连接测试失败
# 解决方案:
# 1. 检查API密钥是否正确
# 2. 确认网络连接正常
# 3. 检查API配额使用情况
```

#### 5. GUI启动失败
```bash
# 错误信息: tkinter相关错误
# 解决方案: 安装tkinter
sudo apt install python3-tk  # Ubuntu/Debian
```

### 日志文件位置
- **Linux**: `~/.local/share/MSTRMonitor/logs/mstr_gui.log`
- **Windows**: `%APPDATA%\MSTRMonitor\logs\mstr_gui.log`
- **macOS**: `~/Library/Application Support/MSTRMonitor/logs/mstr_gui.log`

### 性能优化
1. **内存使用**: 限制最大数据点数量 (默认1000)
2. **更新频率**: 根据需要调整更新间隔 (默认10秒)
3. **图表渲染**: 降低动画刷新率以减少CPU使用

## 🎯 验证安装

### 运行测试
```bash
# 检查所有依赖
python3 mstr_gui.py --check-deps

# 运行基本示例
python3 examples/basic_usage.py

# 测试API连接
python3 -c "
from gui.core.api_client import APIClient
client = APIClient('your_api_key')
print('API连接:', '成功' if client.test_connection() else '失败')
"
```

### 功能验证清单
- [ ] Python版本符合要求
- [ ] 所有依赖包已安装
- [ ] Chrome调试模式正常运行
- [ ] API密钥配置正确
- [ ] GUI应用可以启动
- [ ] 数据可以正常获取
- [ ] 图表可以正常显示

## 📚 下一步

安装完成后，请参阅:
- [README.md](../README.md) - 主要使用文档
- [docs/gui/](./gui/) - 详细的GUI设计文档
- [examples/](../examples/) - 使用示例代码

## 💡 获取帮助

如果遇到问题:
1. 查看日志文件获取详细错误信息
2. 运行 `python3 mstr_gui.py --chrome-help` 获取Chrome设置帮助
3. 检查 [故障排除](#故障排除) 部分
4. 提交Issue到项目仓库