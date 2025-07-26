# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
本文件为 Claude Code (claude.ai/code) 在此代码库中工作提供指导。

## Project Overview | 项目概述

MySA is a Python-based financial analysis toolkit focused on stock portfolio analysis and monitoring. It combines web scraping capabilities with data analysis for SeekingAlpha portfolios and specific stock tracking (particularly MSTR/BTC relationships).

MySA 是一个基于 Python 的金融分析工具包，专注于股票投资组合分析和监控。它结合了网页爬虫功能和数据分析，用于 SeekingAlpha 投资组合和特定股票追踪（特别是 MSTR/BTC 关系）。

## Architecture | 架构

The project has two main components:
项目包含两个主要组件：

1. **Standalone Scripts | 独立脚本** (in `src/`):
   - `mstr_btc.py`: Monitors MSTR (MicroStrategy) stock and its Bitcoin holdings relationship
     监控 MSTR (MicroStrategy) 股票及其比特币持仓关系
   - `portfolio_rebalancing.py`: SeekingAlpha portfolio scraper and rebalancing analyzer
     SeekingAlpha 投资组合爬虫和再平衡分析器
   - `quant_rating_tracker.py`: Tracks quantitative ratings for stocks from SeekingAlpha
     追踪 SeekingAlpha 股票的量化评级
   - `portfolio_rating_days_tracker.py`: Analyzes consecutive rating days for portfolio stocks
     分析投资组合股票的连续评级天数
## Key Dependencies | 关键依赖

- **Web Scraping | 网页爬虫**: selenium, beautifulsoup4
- **Data Analysis | 数据分析**: pandas, numpy, yfinance
- **Browser Automation | 浏览器自动化**: Chrome with remote debugging (port 9222)
  Chrome远程调试模式（端口9222）

## Development Commands | 开发命令

### Running the Applications | 运行应用程序

```bash

# Run standalone scripts | 运行独立脚本
python src/mstr_btc.py
python src/portfolio_rebalancing.py
python src/quant_rating_tracker.py
python src/portfolio_rating_days_tracker.py
```

### Chrome Remote Debugging Setup | Chrome远程调试设置

Most scripts require Chrome to be running in remote debugging mode:
大多数脚本需要Chrome在远程调试模式下运行：

```bash
# Linux/Mac
google-chrome --remote-debugging-port=9222

# Windows
chrome.exe --remote-debugging-port=9222
```

## Important Notes | 重要说明

- All web scrapers connect to an existing Chrome browser instance on port 9222 to reuse login sessions
  所有网页爬虫连接到端口9222上的现有Chrome浏览器实例以重用登录会话
- The project primarily scrapes SeekingAlpha and strategytracker.com
  项目主要爬取 SeekingAlpha 和 strategytracker.com
- Data analysis focuses on stock ratings, portfolio rebalancing, and MSTR/BTC premium calculations
  数据分析聚焦于股票评级、投资组合再平衡和 MSTR/BTC 溢价计算
- The GUI application provides a monitoring interface for MSTR/BTC data with real-time updates
  GUI应用提供MSTR/BTC数据的监控界面，支持实时更新

## Code Conventions | 代码规范

- Use UTF-8 encoding with BOM for Chinese character support where needed
  在需要中文字符支持的地方使用带BOM的UTF-8编码
- Follow PEP 8 style guidelines | 遵循 PEP 8 风格指南
- Use type hints for function parameters and return values
  为函数参数和返回值使用类型提示
- Implement error handling with try-except blocks for web scraping operations
  为网页爬虫操作实现try-except错误处理
- Log important operations using the logging module
  使用logging模块记录重要操作