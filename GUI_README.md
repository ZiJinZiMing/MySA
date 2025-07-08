# MSTR/BTC溢价监控GUI应用

## 📋 概述

这是一个基于Python Tkinter的图形用户界面应用程序，用于实时监控MSTR/BTC溢价率并提供可视化分析。应用程序通过Chrome远程调试协议获取数据，提供实时图表显示和数据导出功能。

## 🚀 快速启动

### 前提条件
1. Python 3.7+
2. Chrome浏览器
3. 有效的Finnhub API密钥
4. 已安装的Python依赖包

### 启动Chrome调试模式
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### 启动应用
```bash
# 使用快速启动脚本
python mstr_gui.py

# 或使用主程序
python src/gui/main.py

# 查看帮助
python src/gui/main.py --help
```

## 📁 项目结构

```
src/gui/
├── core/                    # 核心功能模块
│   ├── api_client.py       # API客户端
│   ├── config_manager.py   # 配置管理器
│   └── data_manager.py     # 数据管理器
├── services/               # 服务层
│   ├── chart_service.py    # 图表服务
│   ├── monitor_service.py  # 监控服务
│   └── web_scraper.py      # 网页抓取
├── ui/                     # 用户界面
│   ├── components/         # UI组件
│   │   ├── data_cards.py   # 数据卡片
│   │   ├── control_panel.py # 控制面板
│   │   └── status_bar.py   # 状态栏
│   ├── dialogs/            # 对话框
│   │   ├── settings_dialog.py # 设置对话框
│   │   └── export_dialog.py   # 导出对话框
│   └── main_window.py      # 主窗口
├── utils/                  # 工具函数
│   ├── helpers.py          # 辅助函数
│   ├── logger.py           # 日志配置
│   └── validators.py       # 验证器
└── main.py                 # 主程序入口
```

## 🎯 主要功能

### 1. 实时数据监控
- **MSTR价格**: 实时显示MSTR股票价格
- **BTC价格**: 实时显示比特币价格
- **溢价率**: 自动计算并显示溢价率
- **变化指示**: 显示价格变化百分比和颜色指示

### 2. 可视化图表
- **实时图表**: 动态更新的溢价率走势图
- **时间范围**: 支持30分钟到1天的显示范围
- **图表样式**: 可自定义颜色、线宽、网格等
- **数据点**: 显示历史数据点和趋势

### 3. 数据管理
- **内存存储**: 高效的内存数据管理
- **数据限制**: 可配置的最大数据点数量
- **自动清理**: 定时清理过期数据
- **数据统计**: 实时统计信息显示

### 4. 导出功能
- **多种格式**: 支持CSV、JSON、Excel格式
- **时间过滤**: 按时间范围过滤导出数据
- **字段选择**: 自定义导出字段
- **预览功能**: 导出前预览数据

### 5. 配置系统
- **完整设置**: API、监控、UI、图表、告警设置
- **配置文件**: JSON格式的配置文件
- **导入导出**: 配置的导入和导出功能
- **实时应用**: 设置立即生效

## ⚙️ 配置选项

### API设置
```json
{
  "api": {
    "finnhub_api_key": "your_api_key",
    "request_timeout": 10,
    "retry_count": 3,
    "retry_delay": 1.0,
    "rate_limit_interval": 0.5
  }
}
```

### 监控设置
```json
{
  "monitor": {
    "default_interval": 10,
    "max_data_points": 1000,
    "btc_per_share": 0.00207973,
    "auto_start": false,
    "auto_cleanup_hours": 24
  }
}
```

### UI设置
```json
{
  "ui": {
    "window_width": 1000,
    "window_height": 700,
    "default_time_range": 3600,
    "theme": "default",
    "font_size": 10,
    "always_on_top": false,
    "minimize_to_tray": false
  }
}
```

### 图表设置
```json
{
  "chart": {
    "line_color": "#1f77b4",
    "line_width": 2,
    "grid_alpha": 0.3,
    "animation_interval": 1000,
    "background_color": "#f8f9fa",
    "show_grid": true,
    "show_legend": true
  }
}
```

## 🔧 命令行选项

```bash
# 基本用法
python src/gui/main.py [选项]

# 选项说明
--log-level {DEBUG,INFO,WARNING,ERROR}  # 设置日志级别
--config CONFIG_FILE                   # 指定配置文件
--check-deps                           # 检查依赖项
--chrome-help                          # 显示Chrome设置帮助
--no-chrome-check                      # 跳过Chrome连接检查
--version                              # 显示版本信息
```

## 📊 使用流程

### 1. 启动准备
1. 确保Chrome以调试模式运行
2. 在Chrome中登录SeekingAlpha
3. 配置Finnhub API密钥

### 2. 启动应用
1. 运行启动脚本
2. 检查连接状态
3. 配置监控参数

### 3. 开始监控
1. 点击"开始监控"按钮
2. 观察实时数据更新
3. 查看图表走势

### 4. 数据导出
1. 点击"导出CSV"按钮
2. 选择导出选项
3. 预览并确认导出

## 🎨 界面说明

### 主窗口布局
```
┌─────────────────────────────────────────────────────────────┐
│                    MSTR/BTC 溢价监控                         │
├─────────────────────────────────────────────────────────────┤
│  [MSTR价格卡片]  [BTC价格卡片]  [溢价率卡片]                  │
├─────────────────────────────────────────────────────────────┤
│                    溢价走势图表                              │
│                    (实时更新)                                │
├─────────────────────────────────────────────────────────────┤
│ [开始监控] [停止监控] [清除数据] [设置] [导出CSV] [帮助]       │
│ 更新间隔: [10秒] 显示时间: [1小时] □自动滚动 □声音提醒        │
├─────────────────────────────────────────────────────────────┤
│ ●连接状态: 监控中 | 最后更新: 14:30:25 | 数据点: 156        │
│ 错误: 0 | API: 正常(98.5%) | 内存: 45.2MB | 运行时间: 00:15:30 │
└─────────────────────────────────────────────────────────────┘
```

### 数据卡片
- **实时更新**: 显示当前价格和变化
- **颜色指示**: 根据变化幅度显示不同颜色
- **状态指示**: 显示数据获取状态
- **更新时间**: 显示最后更新时间

### 图表区域
- **实时动画**: 平滑的数据更新动画
- **缩放功能**: 支持时间轴缩放
- **工具提示**: 鼠标悬停显示详细信息
- **图例显示**: 可选的图例显示

### 控制面板
- **监控控制**: 开始/停止监控按钮
- **数据管理**: 清除数据功能
- **设置访问**: 打开设置对话框
- **导出功能**: 数据导出功能
- **参数调整**: 实时调整监控参数

### 状态栏
- **连接状态**: 显示API连接状态
- **数据统计**: 显示数据点数量
- **错误监控**: 显示错误计数
- **性能监控**: 显示内存使用情况
- **运行时间**: 显示程序运行时间

## 🛠️ 故障排除

### 常见问题

1. **Chrome连接失败**
   - 确保Chrome以调试模式运行
   - 检查端口9222是否被占用
   - 重启Chrome并重新启动调试模式

2. **API连接失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 检查API配额使用情况

3. **数据获取失败**
   - 确认已在Chrome中登录SeekingAlpha
   - 检查网页结构是否发生变化
   - 查看日志文件获取详细错误信息

4. **图表显示异常**
   - 检查matplotlib是否正确安装
   - 确认图表配置参数正确
   - 尝试重置图表设置

### 日志文件位置
- **Windows**: `%APPDATA%\MSTRMonitor\logs\mstr_gui.log`
- **Linux**: `~/.local/share/MSTRMonitor/logs/mstr_gui.log`
- **macOS**: `~/Library/Application Support/MSTRMonitor/logs/mstr_gui.log`

### 性能优化
- 适当调整数据更新间隔
- 限制最大数据点数量
- 定期清理历史数据
- 监控内存使用情况

## 📦 依赖项

### 必需依赖
```
tkinter (Python标准库)
requests
selenium
beautifulsoup4
matplotlib
```

### 可选依赖
```
pandas (Excel导出功能)
psutil (系统监控功能)
```

## 🔐 安全注意事项

1. **API密钥安全**
   - 不要在代码中硬编码API密钥
   - 使用配置文件管理敏感信息
   - 定期更换API密钥

2. **Chrome调试模式**
   - 调试模式会绕过某些安全限制
   - 仅在监控时使用调试模式
   - 监控完成后正常启动Chrome

3. **数据隐私**
   - 数据仅存储在本地内存中
   - 不会向第三方发送数据
   - 导出数据时注意文件安全

## 🚀 未来计划

- [ ] 支持更多交易对监控
- [ ] 添加预警和通知系统
- [ ] 提供历史数据回放功能
- [ ] 支持多账户管理
- [ ] 添加技术指标分析
- [ ] 支持插件系统

## 💡 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证，详情请参阅LICENSE文件。

## 📞 支持

如需技术支持或报告问题，请通过以下方式联系：
- 创建GitHub Issue
- 发送邮件至项目维护者
- 加入讨论群组

---

**注意**: 本工具仅用于教育和研究目的，请遵守相关法律法规和网站使用条款。