# MSTR/BTC 溢价监控系统使用文档

## 📋 目录

- [功能介绍](#功能介绍)
- [快速开始](#快速开始)
- [详细使用说明](#详细使用说明)
- [界面功能说明](#界面功能说明)
- [两种溢价指标详解](#两种溢价指标详解)
- [常见问题](#常见问题)
- [高级功能](#高级功能)

---

## 功能介绍

本系统提供 MSTR 股票溢价的实时监控和可视化分析，帮助你追踪 MSTR 相对于其持有的 BTC 价值的溢价变化。

### 核心功能

✅ **实时数据采集** - 每 10 秒自动获取 MSTR 和 BTC 价格
✅ **双溢价计算** - 同时计算市值溢价和企业价值(EV)溢价
✅ **可视化展示** - 交互式折线图展示历史趋势
✅ **统计分析** - 自动计算平均值、最高值、最低值
✅ **数据持久化** - SQLite 数据库存储，支持历史回溯

### 系统组成

1. **mstr_btc.py** - 数据采集程序
   - 从 strategy.com 获取 BTC per share 数据
   - 从 Finnhub API 获取实时价格
   - 计算溢价并保存到数据库

2. **streamlit_app.py** - 可视化界面
   - 实时折线图展示溢价趋势
   - 价格走势双 Y 轴对比
   - 统计信息和实时指标

---

## 快速开始

### 第一步：安装依赖

```bash
pip install streamlit pandas plotly selenium beautifulsoup4 requests
```

### 第二步：启动 Chrome 远程调试（如果需要）

```bash
# Windows
chrome.exe --remote-debugging-port=9222

# Linux/Mac
google-chrome --remote-debugging-port=9222
```

> 💡 **提示**：如果你的 Chrome 已经在端口 9222 运行远程调试模式，可以跳过此步骤。

### 第三步：启动数据采集程序

**打开第一个终端窗口：**

```bash
cd C:\Users\Administrator\Desktop\SeekingAlpha\SeekingAlpha\mstr
python mstr_btc.py
```

你会看到类似的输出：

```
============================================================
MSTR/BTC 溢价监控系统 (Enterprise Value 方法)
============================================================
数据来源: https://www.strategy.com/
更新间隔: 10 秒
BTC per Share 更新间隔: 30000 秒
============================================================

初始化数据库...
数据库初始化成功: mstr_data.db
初始化：获取 BTC per Share 数据...
方法3: 通过计算获得 (使用 Enterprise Value)
  BTC Holdings: 447,470 BTC
  ...
初始化完成! BTC per Share = 0.00123456 BTC

2025-12-06 09:30:00:: [MSTR: $350.25]||[BTC: $98,234.50]||[市值溢价: 12.45%]||[EV溢价: 8.32%]
```

> ⚠️ **重要**：让这个程序持续运行，不要关闭！

### 第四步：启动可视化界面

**打开第二个终端窗口：**

```bash
cd C:\Users\Administrator\Desktop\SeekingAlpha\SeekingAlpha\mstr
streamlit run streamlit_app.py
```

> ⚠️ **注意**：必须使用 `streamlit run` 命令，不是 `python`！

浏览器会自动打开 `http://localhost:8501`，你就能看到实时监控界面了！

---

## 详细使用说明

### 数据采集程序 (mstr_btc.py)

#### 工作流程

1. **初始化阶段**
   - 创建 SQLite 数据库 `mstr_data.db`
   - 连接到 Chrome 浏览器获取 BTC per share 数据
   - 从 strategy.com 抓取债务、现金等财务数据

2. **主循环（每 10 秒）**
   - 调用 Finnhub API 获取 MSTR 实时价格
   - 调用 Finnhub API 获取 BTC 实时价格
   - 计算市值溢价和 EV 溢价
   - 保存数据到数据库
   - 在终端打印实时数据

3. **后台线程（每 500 分钟）**
   - 更新 BTC per share 数据
   - 更新 EV 调整参数

#### 配置参数

可以在 `mstr_btc.py` 开头修改这些参数：

```python
TICK_INTERVAL = 10  # 主循环更新间隔（秒）
BTC_PER_SHARE_UPDATE_INTERVAL = 30000  # BTC per share 更新间隔（秒）
CHROME_DEBUG_PORT = 9222  # Chrome 远程调试端口
DB_FILE = "mstr_data.db"  # 数据库文件名
```

#### 输出说明

```
2025-12-06 09:30:00:: [MSTR: $350.25]||[BTC: $98,234.50]||[市值溢价: 12.45%]||[EV溢价: 8.32%]
│                      │              │                   │                    │
│                      │              │                   │                    └─ EV溢价百分比
│                      │              │                   └────────────────────── 市值溢价百分比
│                      │              └────────────────────────────────────────── BTC价格
│                      └───────────────────────────────────────────────────────── MSTR股价
└──────────────────────────────────────────────────────────────────────────────── 时间戳
```

### 可视化界面 (streamlit_app.py)

#### 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  📈 MSTR/BTC 溢价实时监控                                │
├─────────────────────────────────────────────────────────┤
│  [MSTR价格]  [BTC价格]  [市值溢价]  [EV溢价]             │
│   $350.25    $98,234    +12.45%    +8.32%              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│          溢价率趋势图 (可交互)                           │
│          ▲                                              │
│       15%│         ╭──╮                                 │
│          │      ╭──╯  ╰─╮                               │
│       10%│  ╭───╯       ╰──╮                            │
│          │──╯              ╰───                         │
│          └────────────────────────▶                     │
│                                                         │
│          MSTR & BTC 价格走势 (双Y轴)                    │
│          ▲                          ▲                   │
│     $400 │    ╭─╮              100k│                    │
│          │ ╭──╯ ╰─╮                │                    │
│     $350 │─╯      ╰──╮          98k│                    │
│          └────────────────────▶    │                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  📊 统计信息                                             │
│  [市值溢价统计] [EV溢价统计] [数据信息]                  │
└─────────────────────────────────────────────────────────┘
```

#### 功能特性

1. **实时指标卡片**（顶部）
   - MSTR 当前价格
   - BTC 当前价格
   - 市值溢价百分比（带颜色指示）
   - EV 溢价百分比（带颜色指示）

2. **溢价率趋势图**（中上）
   - 蓝色线：市值溢价
   - 橙色线：EV 溢价
   - 灰色虚线：零线参考
   - 可缩放、拖动、悬停查看详情

3. **价格走势图**（中下）
   - 绿色线：MSTR 价格（左 Y 轴）
   - 红色线：BTC 价格（右 Y 轴）
   - 双 Y 轴对比价格变化

4. **统计信息面板**（底部）
   - 当前值、平均值、最高值、最低值
   - 数据点数量
   - 最新更新时间
   - BTC per share 和 EV 调整值

5. **侧边栏设置**（左侧）
   - 时间范围选择：1/3/6/12/24/48/72 小时
   - 默认显示最近 24 小时

#### 交互功能

- **缩放**：鼠标滚轮或拖动选择区域
- **平移**：点击拖动图表
- **悬停**：显示具体数值
- **重置**：双击图表恢复原始视图
- **下载**：点击图表右上角相机图标保存为 PNG

---

## 界面功能说明

### 实时指标卡片

每个指标卡片显示：
- **标签**：指标名称
- **数值**：当前值
- **Delta**：变化量（绿色上涨，红色下跌）

### 折线图详解

#### 溢价率趋势图
- **X 轴**：时间（自动格式化）
- **Y 轴**：溢价百分比
- **蓝色线**：市值溢价 - 直接反映股价相对 BTC 的溢价
- **橙色线**：EV 溢价 - 考虑债务后的溢价
- **零线**：溢价为 0% 的参考线

#### 价格走势图
- **X 轴**：时间
- **左 Y 轴**：MSTR 股价（美元）
- **右 Y 轴**：BTC 价格（美元）
- **绿色线**：MSTR 价格变化
- **红色线**：BTC 价格变化

### 统计信息

#### 市值溢价统计
- **当前**：最新的市值溢价值
- **平均**：所选时间范围内的平均溢价
- **最高**：历史最高溢价
- **最低**：历史最低溢价

#### EV 溢价统计
- 同上，但针对 EV 溢价

#### 数据信息
- **数据点**：共有多少条记录
- **最新更新**：最后一次数据更新时间
- **BTC/股**：每股 MSTR 含有多少 BTC
- **EV 调整**：每股的企业价值调整额

---

## 两种溢价指标详解

### 市值溢价 (Market Cap Premium)

**公式：**
```
市值溢价 = (MSTR股价 / 每股BTC价值 - 1) × 100%

其中：
每股BTC价值 = BTC per share × BTC价格
```

**例子：**
```
MSTR 股价 = $350
BTC 价格 = $100,000
BTC per share = 0.003

每股BTC价值 = 0.003 × $100,000 = $300
市值溢价 = ($350 / $300 - 1) × 100% = 16.67%
```

**意义：**
- 最直观的溢价指标
- 大多数投资者关注的指标
- 反映市场对 MSTR 的估值相对于其 BTC 持有量
- 正值表示溢价，负值表示折价

### EV 溢价 (Enterprise Value Premium)

**公式：**
```
EV溢价 = ((MSTR股价 + EV调整) / 每股BTC价值 - 1) × 100%

其中：
EV调整 = (债务 + 优先股 - 现金) / 总股数
```

**例子：**
```
MSTR 股价 = $350
债务 = $40亿
优先股 = $5亿
现金 = $10亿
总股数 = 2亿股

EV调整 = ($40亿 + $5亿 - $10亿) / 2亿股 = $17.5/股
EV per share = $350 + $17.5 = $367.5

每股BTC价值 = $300（同上）
EV溢价 = ($367.5 / $300 - 1) × 100% = 22.5%
```

**意义：**
- 更准确的财务指标
- 考虑了公司的债务结构
- 反映企业整体价值相对 BTC 的溢价
- 对于负债较高的公司，EV 溢价会高于市值溢价

### 两种溢价的对比

| 特性 | 市值溢价 | EV 溢价 |
|------|---------|---------|
| **计算基础** | 股价 | 股价 + 债务调整 |
| **直观性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **准确性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **常用程度** | 高 | 中等 |
| **适用场景** | 快速判断溢价 | 深度财务分析 |

### 如何解读溢价

- **正溢价（> 0%）**：市场给予 MSTR 高于其 BTC 持有量的估值
  - 可能原因：看好未来 BTC 增持、看好业务前景、流动性溢价

- **零溢价（≈ 0%）**：股价几乎等于 BTC 价值
  - 市场认为公司价值主要来自 BTC 持有量

- **负溢价（< 0%）**：股价低于 BTC 持有量价值（折价）
  - 可能原因：担心债务风险、流动性问题、市场恐慌

---

## 常见问题

### Q1: 可视化界面显示"暂无数据"怎么办？

**A:** 这是因为数据库还没有数据。请确保：

1. ✅ `mstr_btc.py` 正在运行
2. ✅ 等待至少 10-20 秒让程序采集几条数据
3. ✅ 检查是否生成了 `mstr_data.db` 文件
4. ✅ 在可视化界面点击刷新或等待自动刷新

### Q2: 数据采集程序无法获取 BTC per share 怎么办？

**A:** 可能的原因和解决方法：

1. **Chrome 远程调试未启动**
   ```bash
   chrome.exe --remote-debugging-port=9222
   ```

2. **网络问题**
   - 检查能否访问 strategy.com
   - 检查防火墙设置

3. **网页结构变化**
   - 查看终端错误信息
   - 查看生成的 `strategy_page_debug.html` 文件

### Q3: 运行 streamlit_app.py 报错 "missing ScriptRunContext"

**A:** 你使用了错误的命令！

❌ **错误**：`python streamlit_app.py`
✅ **正确**：`streamlit run streamlit_app.py`

### Q4: 如何查看历史数据？

**A:** 两种方法：

1. **在界面上**：使用侧边栏的时间范围选择器
2. **导出数据**：
   ```bash
   sqlite3 mstr_data.db
   .mode csv
   .output export.csv
   SELECT * FROM mstr_premium;
   .quit
   ```

### Q5: 数据库文件在哪里？

**A:** 在运行 `mstr_btc.py` 的目录下，文件名是 `mstr_data.db`

### Q6: 可以同时多个人访问可视化界面吗？

**A:** 可以！Streamlit 支持多用户访问：

```bash
# 允许远程访问
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

然后其他设备访问：`http://你的IP地址:8501`

### Q7: 溢价数据多久更新一次？

**A:**
- 数据采集：每 10 秒
- 界面刷新：每 2 秒
- BTC per share：每 500 分钟（约 8.3 小时）

### Q8: 如何停止程序？

**A:** 在终端按 `Ctrl + C`

---

## 高级功能

### 后台运行数据采集

#### Windows (PowerShell)

```powershell
# 启动后台进程
Start-Process python -ArgumentList "mstr_btc.py" -WindowStyle Hidden

# 查看进程
Get-Process | Where-Object {$_.Name -eq "python"}

# 停止进程
Stop-Process -Name python
```

#### Linux/Mac

```bash
# 后台运行
nohup python mstr_btc.py > mstr_btc.log 2>&1 &

# 查看日志
tail -f mstr_btc.log

# 停止程序
ps aux | grep mstr_btc.py
kill <PID>
```

### 自定义配置

#### 修改数据采集间隔

编辑 `mstr_btc.py`：

```python
TICK_INTERVAL = 5  # 改为 5 秒更新一次（更频繁）
```

#### 修改界面刷新间隔

编辑 `streamlit_app.py`：

```python
REFRESH_INTERVAL = 1  # 改为 1 秒刷新一次
```

#### 修改默认时间范围

编辑 `streamlit_app.py`：

```python
time_range = st.selectbox(
    "时间范围",
    options=[1, 3, 6, 12, 24, 48, 72],
    index=2,  # 改为索引 2，即默认显示 6 小时
    format_func=lambda x: f"最近 {x} 小时"
)
```

### 数据库管理

#### 查询数据

```bash
sqlite3 mstr_data.db

# 查看表结构
.schema mstr_premium

# 查询最近 10 条记录
SELECT * FROM mstr_premium ORDER BY id DESC LIMIT 10;

# 查询溢价超过 10% 的记录
SELECT * FROM mstr_premium WHERE market_cap_premium > 10;

# 统计数据
SELECT
    COUNT(*) as 总记录数,
    AVG(market_cap_premium) as 平均市值溢价,
    MAX(market_cap_premium) as 最高市值溢价,
    MIN(market_cap_premium) as 最低市值溢价
FROM mstr_premium;
```

#### 清理旧数据

```bash
sqlite3 mstr_data.db

# 删除 7 天前的数据
DELETE FROM mstr_premium
WHERE timestamp < datetime('now', '-7 days');

# 压缩数据库
VACUUM;
```

#### 备份数据库

```bash
# 复制文件备份
cp mstr_data.db mstr_data_backup_20251206.db

# 或导出为 SQL
sqlite3 mstr_data.db .dump > mstr_backup.sql
```

### 系统监控

#### 监控程序运行状态

创建一个简单的监控脚本 `check_status.py`：

```python
import sqlite3
from datetime import datetime, timedelta

# 检查最后更新时间
conn = sqlite3.connect('mstr_data.db')
cursor = conn.cursor()
cursor.execute("SELECT timestamp FROM mstr_premium ORDER BY id DESC LIMIT 1")
result = cursor.fetchone()

if result:
    last_update = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    time_diff = datetime.now() - last_update

    if time_diff < timedelta(minutes=1):
        print("✅ 系统运行正常")
    else:
        print(f"⚠️ 警告：最后更新于 {time_diff.seconds} 秒前")
else:
    print("❌ 错误：没有数据")

conn.close()
```

### 性能优化

#### 优化数据库查询

编辑 `streamlit_app.py`，添加索引：

```python
def optimize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建复合索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp_premium
        ON mstr_premium(timestamp DESC, market_cap_premium, ev_premium)
    ''')

    conn.commit()
    conn.close()
```

#### 限制数据库大小

编辑 `mstr_btc.py`，添加自动清理：

```python
def cleanup_old_data(days=7):
    """删除指定天数之前的数据"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM mstr_premium WHERE timestamp < ?", (cutoff_date,))

        deleted_rows = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_rows > 0:
            print(f"清理了 {deleted_rows} 条旧数据")
    except Exception as e:
        print(f"清理数据失败: {e}")

# 在主函数中定期调用（例如每天一次）
```

---

## 技术支持

### 数据来源

- **BTC per share**：strategy.com
- **价格数据**：Finnhub API
- **财务数据**：strategy.com（债务、优先股、现金）

### 系统要求

- Python 3.7+
- Chrome 浏览器（用于抓取数据）
- 稳定的网络连接
- 最低 2GB RAM

### 依赖库版本

推荐版本：
```
streamlit >= 1.28.0
pandas >= 2.0.0
plotly >= 5.17.0
selenium >= 4.0.0
beautifulsoup4 >= 4.11.0
requests >= 2.28.0
```

---

## 更新日志

### v1.0 (2025-12-06)
- ✅ 实现基础数据采集功能
- ✅ 实现双溢价计算（市值溢价 + EV 溢价）
- ✅ 实现 SQLite 数据持久化
- ✅ 实现 Streamlit 可视化界面
- ✅ 添加实时折线图
- ✅ 添加统计分析功能
- ✅ 添加时间范围选择

---

## 致谢

感谢以下开源项目：
- Streamlit
- Plotly
- Pandas
- Selenium

---

**祝你监控愉快！📈**

如有问题，请查看上方的常见问题部分，或检查终端的错误信息。
