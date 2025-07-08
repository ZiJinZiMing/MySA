# MySA - SeekingAlpha数据分析工具套件

这是一个基于Python的SeekingAlpha数据爬取和投资分析工具包，专注于股票投资组合数据提取、评级分析和投资决策支持。

## 🚀 主要功能

### 📊 投资组合再平衡分析 (NEW!)
- **自动数据获取**: 从SeekingAlpha投资组合页面获取实时持仓数据
- **等权重策略**: 计算等权重再平衡的详细交易指令
- **可视化报告**: 生成权重分布图、对比分析图和综合仪表板
- **离线分析**: 支持本地HTML文件解析，提高分析效率

#### 🆕 增强功能特性
- **固定现金金额保留**: 支持保留指定固定金额现金（如$12,000），优先级高于百分比设置
- **指定股票清仓功能**: 可配置特定股票完全清仓，清仓资金自动用于再平衡
- **组合功能使用**: 可同时使用固定现金和清仓功能，智能处理资金流

### 📈 股票评级分析
- **投资组合持仓信息**: 提取投资组合中所有股票的详细信息
- **顶级量化评级**: 分析量化评级最高的股票
- **评级天数统计**: 计算投资组合中股票的评级持续天数
- **MSTR/BTC溢价监控**: 实时监控MicroStrategy相对比特币的溢价率

## 🛠️ 快速开始

### ⚠️ 核心架构说明
**本项目的所有功能都基于Chrome远程调试架构**：
- 🌐 **统一网络访问**: 所有数据获取都通过Chrome浏览器进行
- 🔐 **会话保持**: 利用浏览器已登录状态，无需重复认证
- 🚀 **实时数据**: 直接从SeekingAlpha网站获取最新数据
- 🛡️ **反检测**: 使用真实浏览器环境，避免爬虫识别

### 环境准备
1. **安装依赖包**:
```bash
pip install pandas numpy beautifulsoup4 selenium requests yfinance matplotlib seaborn
```

2. **启动Chrome远程调试** (必须步骤):
```bash
# 方法1: 使用项目提供的启动脚本 (推荐)
./start_chrome.sh

# 方法2: 手动启动命令
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/software/chrome_userdata"
```

3. **登录SeekingAlpha**: 在打开的Chrome浏览器中登录您的SeekingAlpha账户

### 🔧 Chrome远程调试配置详解
- **端口9222**: 项目硬编码使用此端口连接Chrome
- **用户数据目录**: 保持登录状态和浏览器设置
- **必须保持运行**: Chrome进程必须在脚本运行期间保持活跃
- **网络要求**: 需要稳定的网络连接访问SeekingAlpha

### 使用示例

#### 投资组合再平衡分析

##### 基础用法
```bash
# 使用默认投资组合ID
python src/PortfolioRebalancingCalculator.py

# 使用指定投资组合ID  
python src/PortfolioRebalancingCalculator.py 64139349

# 分析本地HTML文件
python src/PortfolioRebalancingCalculator.py portfolio_data.html
```

##### 🆕 增强功能Python API
```python
from PortfolioRebalancingCalculator import quick_analyze_portfolio

# 基础等权重再平衡
df, rebalance_df = quick_analyze_portfolio('64139349')

# 保留固定现金金额 $12,000
df, rebalance_df = quick_analyze_portfolio(
    portfolio_id='64139349',
    target_cash_amount=12000,
    exclude_symbols=['CASH']
)

# 清仓特定股票 
df, rebalance_df = quick_analyze_portfolio(
    portfolio_id='64139349',
    target_cash_percentage=0.05,
    liquidate_symbols=['AEVA', 'EXE'],
    exclude_symbols=['CASH']
)

# 组合使用：固定现金 + 清仓
df, rebalance_df = quick_analyze_portfolio(
    portfolio_id='64139349',
    target_cash_amount=15000,  # 固定现金优先
    liquidate_symbols=['APP'],
    exclude_symbols=['CASH']
)
```

#### 其他分析功能
```bash

# 监控MSTR/BTC溢价率
python src/mstr_btc.py
```

## 📋 输出文件

### 投资组合再平衡分析输出
- `portfolio_data_{portfolio_id}.html` - 原始网页数据备份
- `portfolio_rebalance_report_{timestamp}.txt` - 详细再平衡分析报告
- `portfolio_weights_pie_{timestamp}.png` - 投资组合权重分布饼图
- `rebalance_comparison_{timestamp}.png` - 再平衡前后权重对比图
- `trade_distribution_{timestamp}.png` - 交易金额分布图
- `portfolio_dashboard_{timestamp}.png` - 综合分析仪表板

### 其他分析输出
- 各种CSV格式的数据文件
- 股票评级和统计信息

## 🏗️ 项目架构

项目采用模块化设计，主要包含：

- **数据获取层**: Chrome远程调试连接、页面爬取、HTML解析
- **数据处理层**: 数据清理、验证、转换和分析
- **分析引擎**: 等权重计算、评级分析、溢价监控
- **输出层**: 报告生成、图表可视化、文件管理

详细的技术架构请参考: [📋 PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md)

## 🔧 技术栈

- **Python 3.7+**: 主要开发语言
- **Selenium WebDriver**: 浏览器自动化
- **BeautifulSoup**: HTML解析
- **Pandas**: 数据处理和分析
- **Matplotlib/Seaborn**: 数据可视化
- **NumPy**: 数值计算

## 📚 详细文档

- [CLAUDE.md](./CLAUDE.md) - 项目使用指南和配置说明
- [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) - 完整技术架构文档

## ⚠️ 重要说明

### 🔴 Chrome远程调试依赖 (核心要求)
1. **必须启动**: Chrome必须运行在远程调试模式（端口9222）
2. **登录状态**: 必须在Chrome浏览器中保持SeekingAlpha登录状态
3. **进程保持**: Chrome进程在脚本运行期间不能关闭
4. **端口独占**: 端口9222不能被其他应用占用

### 📋 技术架构核心
- **所有功能**: 100%依赖Chrome远程调试连接
- **数据来源**: 全部通过实时网络请求获取
- **会话管理**: 利用浏览器cookie和登录状态
- **反爬策略**: 使用真实浏览器环境规避检测

### 🛡️ 使用规范
1. **数据使用**: 请遵守SeekingAlpha的使用条款，仅用于个人投资分析
2. **风险提示**: 本工具仅供分析参考，投资决策请谨慎
3. **网络稳定**: 确保网络连接稳定，避免数据获取中断

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目功能。

---

*最后更新: 2025-07-06*