# 投资组合等权重再平衡系统 - 功能说明文档

## 📋 系统概述

投资组合等权重再平衡系统基于**分层处理策略**，专门为等权重再平衡、1-2周再平衡频率的投资策略设计。系统能够智能处理资金不足的情况，确保最重要的再平衡需求得到优先满足。

### 🎯 核心特性

- **分层处理策略**: 根据偏离程度和资金覆盖率智能分配资金
- **超配股票处理**: 自动卖出超配股票，增加再平衡资金
- **小头寸保护**: 优先处理价值极小的股票（如STX、LITE、WLDN）
- **配置驱动**: 所有参数可配置，适应不同投资策略
- **资金智能分配**: 根据资金覆盖率选择最优再平衡策略
- **动态股票数量**: 根据网页数据自动计算目标股票数量

## 📊 算法原理

### 分层处理策略

系统根据股票偏离程度将其分为三层处理：

```
第一层 (60%资金): 临界不足股票 (偏离 > 2%)
第二层 (30%资金): 严重不足股票 (偏离 1.5%-2%)
第三层 (10%资金): 中等不足股票 (偏离 0.5%-1.5%)
```

### 资金覆盖率策略

- **覆盖率 < 20%**: 集中火力解决最严重问题（前5只股票）
- **覆盖率 20%-60%**: 完整分层处理策略
- **覆盖率 > 60%**: 全面改善权重平衡

## 🔧 配置参数详解

### 基础配置

```python
'exclude_symbols': ['CASH'],               # 排除的股票代码
'liquidate_symbols': [],                   # 需要清仓的股票代码

# 注意：目标股票数量自动计算
# target_stock_count = 网页数据总数 - 清仓股票数 - 排除股票数
```

### 现金管理

```python
'target_cash_amount': None,                # 目标固定现金金额 (优先级高)
'target_cash_percentage': 0.02,            # 目标现金比例 (2%)
'min_cash_reserve': 1000,                  # 最小现金储备
```

### 偏离度阈值

```python
'deviation_thresholds': {
    'critical': 0.02,                      # 临界偏离 (2%)
    'severe': 0.015,                       # 严重偏离 (1.5%)
    'moderate': 0.01,                      # 中等偏离 (1%)
    'minor': 0.005,                        # 轻微偏离 (0.5%)
    'target_range': 0.003                  # 目标范围 (±0.3%)
}
```

### 分层处理配置

```python
'tier_allocation': {
    'tier1_budget_ratio': 0.6,             # 第一层预算比例 (60%)
    'tier2_budget_ratio': 0.3,             # 第二层预算比例 (30%)
    'tier3_budget_ratio': 0.1,             # 第三层预算比例 (10%)
    'max_single_stock_ratio': 0.15,        # 单只股票最大资金比例 (15%)
    'tier1_target_improvement': 0.7,       # 第一层目标改善比例 (70%)
    'tier2_target_improvement': 0.5,       # 第二层目标改善比例 (50%)
    'tier3_target_improvement': 0.3        # 第三层目标改善比例 (30%)
}
```

### 交易约束

```python
'trading_constraints': {
    'min_trade_amount': 100,               # 最小交易金额
    'min_shares_per_trade': 1,             # 最小交易股数
    'max_position_change': 0.5,            # 单次最大仓位变化 (50%)
    'overweight_sell_threshold': 0.015,    # 超配卖出阈值 (1.5%)
    'underweight_buy_threshold': -0.005    # 低配买入阈值 (-0.5%)
}
```

### 风险控制

```python
'risk_management': {
    'max_trades_per_session': 50,          # 单次最大交易数
    'emergency_cash_ratio': 0.05,          # 紧急现金比例 (5%)
    'concentration_limit': 0.1,            # 单只股票最大权重 (10%)
    'liquidity_buffer': 0.02               # 流动性缓冲 (2%)
}
```

## 🚀 使用方法

### 1. 基本使用

```python
from portfolio_rebalancing import FixedSeekingAlphaScraper

# 创建爬虫实例
scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=True)

# 获取投资组合数据
df = scraper.scrape_portfolio_by_id('64139349')

# 使用默认配置进行再平衡
rebalance_df = scraper.calculate_equal_weight_rebalance(df)

# 生成报告
report = scraper.generate_rebalance_report(df, rebalance_df)
```

### 2. 自定义配置

```python
# 创建自定义配置
config = {
    'target_cash_amount': 5000,            # 保留5000美元现金
    'liquidate_symbols': ['AAPL', 'MSFT'], # 清仓AAPL和MSFT
    'deviation_thresholds': {
        'critical': 0.025,                 # 调整临界阈值为2.5%
        'severe': 0.02,
        'moderate': 0.015,
        'minor': 0.008,
        'target_range': 0.005
    },
    'tier_allocation': {
        'tier1_budget_ratio': 0.7,         # 第一层使用70%资金
        'tier2_budget_ratio': 0.25,        # 第二层使用25%资金
        'tier3_budget_ratio': 0.05,        # 第三层使用5%资金
        'tier1_target_improvement': 0.8,   # 第一层改善80%
        'tier2_target_improvement': 0.6,   # 第二层改善60%
        'tier3_target_improvement': 0.4    # 第三层改善40%
    }
}

# 使用自定义配置
rebalance_df = scraper.calculate_equal_weight_rebalance(df, config)
```

### 3. 快速分析函数

```python
from portfolio_rebalancing import quick_analyze_portfolio

# 快速分析（使用默认配置）
df, rebalance_df = quick_analyze_portfolio('64139349')

# 快速分析（自定义参数）
df, rebalance_df = quick_analyze_portfolio(
    portfolio_id='64139349',
    target_cash_amount=3000,
    liquidate_symbols=['OKTA', 'INTA'],
    exclude_symbols=['CASH']
)
# 注意：目标股票数量自动计算，无需手动指定
```

### 4. 命令行使用

```bash
# 使用默认配置
python src/portfolio_rebalancing.py 64139349

# 系统会自动：
# 1. 连接到Chrome浏览器（端口9222）
# 2. 爬取投资组合数据
# 3. 执行分层再平衡计算
# 4. 生成详细报告
# 5. 保存CSV和报告文件
```

## 📈 实际案例

### 案例1: 处理小头寸股票

**问题**: STX ($148)、LITE ($102)、WLDN ($79) 等小头寸股票在传统算法中被忽略

**解决方案**: 分层处理策略

```python
# 配置示例
config = {
    'deviation_thresholds': {
        'critical': 0.02,    # STX、LITE、WLDN偏离>2%，进入第一层
        'severe': 0.015,
        'moderate': 0.01,
        'minor': 0.005
    },
    'tier_allocation': {
        'tier1_budget_ratio': 0.6,          # 60%资金优先处理这些股票
        'tier1_target_improvement': 0.7     # 改善70%的偏离
    }
}
# 注意：目标股票数量自动计算，无需手动指定
```

**结果**: 
- STX: 从 $148 (0.1%) → $3,500 (1.3%)
- LITE: 从 $102 (0.0%) → $3,400 (1.3%)
- WLDN: 从 $79 (0.0%) → $3,350 (1.3%)

### 案例2: 资金不足情况

**场景**: 需要投资$50,000，但只有$15,000可用资金

**策略选择**: 资金覆盖率 30% → 分层处理策略

```
第一层处理：5只最严重股票，使用$9,000 (60%)
第二层处理：10只严重股票，使用$4,500 (30%)
第三层处理：其他股票，使用$1,500 (10%)
```

**结果**: 最严重的偏离问题得到解决，整体组合向等权重方向改善

### 案例3: 超配股票处理

**问题**: PSIX超配到3.7%，STRL超配到3.1%

**处理**: 自动卖出超配部分

```python
# 超配处理逻辑
if stock_deviation > 0.015:  # 超配1.5%
    excess_value = current_value - target_value
    shares_to_sell = int(excess_value / stock_price)
    # 卖出获得的资金用于补仓不足股票
```

**结果**: 
- PSIX: 卖出$3,353，获得再平衡资金
- STRL: 卖出$1,495，获得再平衡资金
- 总计获得$4,848用于补仓不足股票

## 📊 输出报告解读

### 交易指令格式

```
股票代码  操作      股数    金额        当前权重  目标权重  优先级
STX      BUY      23     $3,411     0.1%     1.3%     TIER1_CRITICAL
LITE     BUY      33     $3,357     0.0%     1.3%     TIER1_CRITICAL
WLDN     BUY      42     $3,338     0.0%     1.3%     TIER1_CRITICAL
PSIX     SELL     40     $3,353     3.7%     3.3%     OVERWEIGHT_REDUCTION
```

### 优先级说明

- **LIQUIDATION**: 清仓指令
- **OVERWEIGHT_REDUCTION**: 超配股票卖出
- **TIER1_CRITICAL**: 第一层临界不足股票
- **TIER2_SEVERE**: 第二层严重不足股票
- **TIER3_MODERATE**: 第三层中等不足股票
- **COMPREHENSIVE**: 全面改善模式

### 资金流分析

```
💰 === 分层再平衡摘要 ===
总可用资金: $22,275.33
买入交易: 15 笔，总计 $22,262.33
卖出交易: 8 笔，总计 $11,841.89
清仓交易: 2 笔，总计 $10,609.44
剩余现金: $13.00
资金利用率: 99.94%
```

## 🎛️ 高级配置

### 等权重策略优化

```python
# 针对等权重策略的优化配置
config_equal_weight = {
    'deviation_thresholds': {
        'critical': 0.02,     # 目标权重 ± 2%
        'severe': 0.015,      # 目标权重 ± 1.5%
        'moderate': 0.01,     # 目标权重 ± 1%
        'minor': 0.005,       # 目标权重 ± 0.5%
        'target_range': 0.003 # 目标权重 ± 0.3%
    },
    'tier_allocation': {
        'tier1_budget_ratio': 0.6,           # 重点解决严重问题
        'tier2_budget_ratio': 0.3,           # 适度改善
        'tier3_budget_ratio': 0.1,           # 微调
        'max_single_stock_ratio': 0.15,      # 单股最多15%资金
        'tier1_target_improvement': 0.7,     # 第一层改善70%
        'tier2_target_improvement': 0.5,     # 第二层改善50%
        'tier3_target_improvement': 0.3      # 第三层改善30%
    }
}
# 注意：目标股票数量自动计算，目标权重 = 1/目标股票数量
```

### 1-2周再平衡频率配置

```python
# 针对短期再平衡的配置
config_short_term = {
    'deviation_thresholds': {
        'critical': 0.025,    # 稍微放宽阈值，避免过度交易
        'severe': 0.02,
        'moderate': 0.015,
        'minor': 0.01,
        'target_range': 0.005
    },
    'trading_constraints': {
        'min_trade_amount': 200,        # 提高最小交易金额
        'min_shares_per_trade': 5,      # 提高最小交易股数
        'max_position_change': 0.3      # 限制单次仓位变化
    },
    'risk_management': {
        'liquidity_buffer': 0.03        # 增加流动性缓冲
    }
}
```

## 🔍 故障排除

### 常见问题

1. **STX、LITE、WLDN等小头寸股票仍未被处理**
   - 检查`deviation_thresholds.critical`是否设置过高
   - 确认`tier1_budget_ratio`是否足够
   - 验证资金覆盖率是否过低

2. **资金利用率过低**
   - 调整`tier_allocation`中的预算比例
   - 检查`max_single_stock_ratio`限制
   - 确认`min_trade_amount`是否设置过高

3. **交易数量过多**
   - 提高`deviation_thresholds`中的阈值
   - 增加`trading_constraints.min_trade_amount`
   - 调整`risk_management.max_trades_per_session`

### 调试模式

```python
# 启用调试模式
scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=True)

# 查看详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 API参考

### 主要类和方法

#### FixedSeekingAlphaScraper

```python
class FixedSeekingAlphaScraper:
    def __init__(self, use_existing_browser=True, debug_mode=False)
    def scrape_portfolio_by_id(self, portfolio_id, save_html=True)
    def calculate_equal_weight_rebalance(self, portfolio_df, config=None)
    def generate_rebalance_report(self, portfolio_df, rebalance_df, save_to_file=True)
    def get_default_config(self)
```

#### 便捷函数

```python
def quick_analyze_portfolio(portfolio_id, target_cash_amount=None, 
                           target_cash_percentage=0.02,
                           liquidate_symbols=None, exclude_symbols=None)
# 注意：目标股票数量自动计算，无需手动指定
```

### 返回数据格式

#### 投资组合数据 (DataFrame)

```python
columns = ['symbol', 'price', 'shares', 'weight', 'value', 'calculated_value', 'calculated_weight']
```

#### 再平衡指令 (DataFrame)

```python
columns = ['symbol', 'action', 'shares', 'price', 'amount', 'current_value', 
           'target_value', 'difference', 'current_weight', 'target_weight', 
           'priority', 'reason']
```

## 🔗 系统要求

### 环境要求

- Python 3.7+
- Chrome浏览器 (必须以`--remote-debugging-port=9222`启动)
- 依赖包：pandas, numpy, beautifulsoup4, selenium

### 启动Chrome

```bash
# Linux/Mac
google-chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### 安装依赖

```bash
pip install pandas numpy beautifulsoup4 selenium requests yfinance matplotlib seaborn
```

## 📄 许可证

MIT License

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📞 支持

如有问题或建议，请提交Issue或联系维护者。

---

*最后更新: 2025年1月17日*