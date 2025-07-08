# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL ARCHITECTURE REQUIREMENT

**ALL project functionality is 100% dependent on Chrome Remote Debugging (port 9222)**

🔴 **For Claude Code**: When developing ANY new features for this project, you MUST:
1. Use Chrome remote debugging connection on port 9222
2. Connect to existing Chrome instance with `debuggerAddress: "127.0.0.1:9222"`
3. Leverage the browser's logged-in session state
4. Access SeekingAlpha through real browser environment for anti-detection

**Never suggest**: Direct HTTP requests, headless browsers, or API calls - ALL data must be retrieved through the Chrome debugging connection.

## 项目概述

这是一个基于Python和Chrome远程调试架构的SeekingAlpha数据爬取和分析工具包，用于提取股票投资组合数据、评级信息并进行投资分析。

### 🔧 核心架构依赖
**所有项目功能都依赖Chrome远程调试连接**：
- **端口9222**: 硬编码使用此端口连接Chrome实例
- **实时数据**: 通过真实浏览器环境访问SeekingAlpha
- **会话保持**: 利用浏览器已登录状态，无需重复认证
- **统一访问**: 所有脚本共享同一个Chrome进程和网络会话

## 运行应用程序

### 前提条件
- Chrome浏览器必须以远程调试模式运行在9222端口
- 启动Chrome命令：`google-chrome --remote-debugging-port=9222`
- 必须在浏览器中登录SeekingAlpha账户

### 主要脚本
```bash

# 监控MSTR/BTC溢价率
python src/mstr_btc.py

# 投资组合等权重再平衡分析 (NEW!)
python src/PortfolioRebalancingCalculator.py 64139349
```

### 依赖项
安装所需包：
```bash
pip install pandas numpy beautifulsoup4 selenium requests yfinance matplotlib seaborn
```

## 架构概述

### 核心数据流水线
1. **浏览器连接** - 所有脚本通过debuggerAddress连接到现有Chrome实例 (127.0.0.1:9222)
2. **页面导航和滚动** - 自动滚动加载动态内容
3. **数据提取** - 使用BeautifulSoup和Selenium选择器解析HTML
4. **数据处理** - 清理和验证提取的数据
5. **输出生成** - 将结果保存为CSV文件并生成统计信息

### 关键模块

#### `common_func.py` - 核心功能
- `get_ticker_rating_info()` - 从SeekingAlpha获取股票评级历史
- `connect_parse_screener_picker_list()` - 从筛选器页面提取股票列表
- `connect_parse_portfolio_picker_list()` - 提取投资组合持仓数据
- `parse_ticker_rating_days()` - 分析连续评级天数

#### `PortfolioRebalancingCalculator.py` - 高级投资组合爬虫
- `FixedSeekingAlphaScraper` 类，具有智能表格结构检测
- `clean_symbol_from_element()` - 鲁棒的股票代码提取
- `extract_numeric_value()` - 处理各种数值格式（价格、百分比）
- `analyze_table_structure()` - 自动检测表格列映射

### 数据流架构
```
Chrome浏览器(9222) → Selenium WebDriver → 页面源码 → BeautifulSoup解析器 → 
数据提取函数 → 验证和清理 → CSV输出 + 统计信息
```

### 关键实现细节

#### 浏览器连接模式
所有脚本使用此连接模式：
```python
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)
```

#### 动态内容加载
脚本实现智能滚动来加载无限滚动页面：
- 监控页面高度变化
- 计算已加载元素数量
- 达到目标数量或无新内容时停止滚动

#### 错误处理策略
- 数据字段缺失时优雅降级
- 支持键盘中断(Ctrl+C)并保存进度
- 缓存机制避免重复处理股票
- 全面记录提取失败情况

#### 数据输出格式
所有脚本生成的CSV文件包含：
- 股票代码和基本信息（价格、市值、行业）
- 评级信息（量化、作者、卖方评级及分数）
- 分析结果（连续评级天数、投资组合权重）
- 控制台输出统计摘要

### 投资组合数据结构
每个股票记录包含：
- `ticker` - 股票代码
- `price`, `shares`, `weight`, `value` - 投资组合持仓数据
- `quant_rating`, `author_rating`, `sell_side_rating` - 三种评级类型
- `quant_score`, `author_score`, `sell_side_score` - 数值分数
- `exchange` - 交易所信息

### URL配置
- MyAlphaPicker: `https://seekingalpha.com/screeners/967f241ea593-MyAlphaPicker`
- TopQuant: `https://seekingalpha.com/screeners/967141c6704b-TopQuant`
- 投资组合URL格式: `https://seekingalpha.com/account/portfolio/total_view?portfolioId=XXXXX`

### 速率限制和反检测
- 请求间随机延迟（1-3秒，每10-40只股票后增加更长延迟）
- 通过现有浏览器实例进行用户代理和会话管理
- 渐进式数据保存避免中断时丢失工作进度

## 投资组合再平衡分析 (PortfolioRebalancingCalculator.py)

### 核心功能
- **数据获取**: 从SeekingAlpha自动获取投资组合持仓数据
- **等权重分析**: 计算等权重再平衡策略和交易指令
- **可视化报告**: 生成详细的分析报告和图表
- **离线支持**: 支持本地HTML文件解析，避免重复网络请求

### 🆕 增强功能特性

#### 1. 固定现金金额保留
- **功能**: 保留指定固定金额的现金，而非百分比
- **优先级**: `target_cash_amount` 参数优先于 `target_cash_percentage`
- **用途**: 确保投资组合中始终保持具体的现金储备

#### 2. 指定股票清仓功能
- **功能**: 配置特定股票完全清仓
- **资金流**: 清仓获得的资金自动用于再平衡计算
- **灵活性**: 可同时清仓多只股票

#### 3. 组合功能使用
- **功能**: 可同时使用固定现金和清仓功能
- **智能计算**: 自动处理清仓资金与现金保留的逻辑关系

### 基础使用方式
```bash
# 使用默认投资组合ID (64139349)
python src/PortfolioRebalancingCalculator.py

# 使用指定投资组合ID
python src/PortfolioRebalancingCalculator.py YOUR_PORTFOLIO_ID

# 分析本地HTML文件
python src/PortfolioRebalancingCalculator.py portfolio_data.html
```

### 增强功能API使用
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

### 增强功能参数说明
- **`target_cash_amount`**: 保留的固定现金金额（美元）
- **`liquidate_symbols`**: 需要清仓的股票代码列表
- **`target_cash_percentage`**: 现金保留百分比（当未指定固定金额时使用）
- **`exclude_symbols`**: 从再平衡中排除的股票代码列表

### 输出文件
- **HTML备份**: `portfolio_data_{portfolio_id}.html` - 原始网页数据
- **分析报告**: `portfolio_rebalance_report_{timestamp}.txt` - 详细再平衡报告
- **可视化图表**: 
  - `portfolio_weights_pie_{timestamp}.png` - 权重分布饼图
  - `rebalance_comparison_{timestamp}.png` - 再平衡对比图
  - `trade_distribution_{timestamp}.png` - 交易分布图
  - `portfolio_dashboard_{timestamp}.png` - 综合仪表板

## 详细技术文档

📋 **完整项目架构和设计文档**: [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md)

该文档包含：
- 系统架构图和类设计图
- 核心算法流程图  
- 功能模块组织图
- 技术栈和依赖关系图
- 详细的实现说明和扩展指南

建议开发者和维护者阅读该文档以深入理解项目设计思路。