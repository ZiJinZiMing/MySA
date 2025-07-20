#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合再平衡配置示例
提供各种投资策略的配置模板
"""

# 默认配置 - 1-2周再平衡
DEFAULT_CONFIG = {
    # 基础配置
    'exclude_symbols': ['CASH'],
    'liquidate_symbols': [],
    
    # 现金管理
    'target_cash_amount': None,
    'target_cash_percentage': 0.02,
    'min_cash_reserve': 1000,
    
    # 偏离度阈值
    'deviation_thresholds': {
        'critical': 0.02,
        'severe': 0.015,
        'moderate': 0.01,
        'minor': 0.005,
        'target_range': 0.003
    },
    
    # 分层处理配置
    'tier_allocation': {
        'tier1_budget_ratio': 0.6,
        'tier2_budget_ratio': 0.3,
        'tier3_budget_ratio': 0.1,
        'max_single_stock_ratio': 0.15,
        'tier1_target_improvement': 0.7,
        'tier2_target_improvement': 0.5,
        'tier3_target_improvement': 0.3
    },
    
    # 交易约束
    'trading_constraints': {
        'min_trade_amount': 100,
        'min_shares_per_trade': 1,
        'max_position_change': 0.5,
        'overweight_sell_threshold': 0.015,
        'underweight_buy_threshold': -0.005
    },
    
    # 风险控制
    'risk_management': {
        'max_trades_per_session': 50,
        'emergency_cash_ratio': 0.05,
        'concentration_limit': 0.1,
        'liquidity_buffer': 0.02
    }
}

# 保守型配置 - 更高的阈值，更少的交易
CONSERVATIVE_CONFIG = {
    'target_cash_percentage': 0.05,  # 保留5%现金
    'min_cash_reserve': 2000,
    
    'deviation_thresholds': {
        'critical': 0.03,     # 3%才算临界
        'severe': 0.025,      # 2.5%才算严重
        'moderate': 0.02,     # 2%才算中等
        'minor': 0.015,       # 1.5%才算轻微
        'target_range': 0.01  # ±1%为目标范围
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.7,           # 更多资金处理严重问题
        'tier2_budget_ratio': 0.25,
        'tier3_budget_ratio': 0.05,
        'max_single_stock_ratio': 0.1,       # 单股最多10%资金
        'tier1_target_improvement': 0.5,     # 更保守的改善比例
        'tier2_target_improvement': 0.3,
        'tier3_target_improvement': 0.2
    },
    
    'trading_constraints': {
        'min_trade_amount': 500,              # 更高的最小交易金额
        'min_shares_per_trade': 5,
        'max_position_change': 0.3,           # 限制单次仓位变化
        'overweight_sell_threshold': 0.02,    # 更高的卖出阈值
        'underweight_buy_threshold': -0.015
    },
    
    'risk_management': {
        'max_trades_per_session': 30,         # 限制交易数量
        'emergency_cash_ratio': 0.08,         # 更高的紧急现金比例
        'concentration_limit': 0.08,          # 更严格的集中度限制
        'liquidity_buffer': 0.03
    }
}

# 积极型配置 - 更低的阈值，更多的交易
AGGRESSIVE_CONFIG = {
    'target_cash_percentage': 0.01,  # 只保留1%现金
    'min_cash_reserve': 500,
    
    'deviation_thresholds': {
        'critical': 0.015,    # 1.5%就算临界
        'severe': 0.01,       # 1%就算严重
        'moderate': 0.008,    # 0.8%就算中等
        'minor': 0.003,       # 0.3%就算轻微
        'target_range': 0.002 # ±0.2%为目标范围
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.5,           # 更平均的资金分配
        'tier2_budget_ratio': 0.3,
        'tier3_budget_ratio': 0.2,
        'max_single_stock_ratio': 0.2,       # 单股最多20%资金
        'tier1_target_improvement': 0.8,     # 更积极的改善比例
        'tier2_target_improvement': 0.6,
        'tier3_target_improvement': 0.4
    },
    
    'trading_constraints': {
        'min_trade_amount': 50,               # 更低的最小交易金额
        'min_shares_per_trade': 1,
        'max_position_change': 0.8,           # 允许更大的仓位变化
        'overweight_sell_threshold': 0.01,    # 更低的卖出阈值
        'underweight_buy_threshold': -0.003
    },
    
    'risk_management': {
        'max_trades_per_session': 80,         # 允许更多交易
        'emergency_cash_ratio': 0.02,         # 更低的紧急现金比例
        'concentration_limit': 0.12,          # 更宽松的集中度限制
        'liquidity_buffer': 0.01
    }
}

# 小头寸保护配置 - 专门解决STX、LITE、WLDN等问题
SMALL_POSITION_PROTECTION_CONFIG = {
    'target_cash_percentage': 0.02,
    
    'deviation_thresholds': {
        'critical': 0.018,    # 稍微降低临界阈值
        'severe': 0.012,      # 稍微降低严重阈值
        'moderate': 0.008,
        'minor': 0.004,
        'target_range': 0.002
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.8,           # 80%资金处理小头寸
        'tier2_budget_ratio': 0.15,
        'tier3_budget_ratio': 0.05,
        'max_single_stock_ratio': 0.25,      # 允许单股使用更多资金
        'tier1_target_improvement': 0.9,     # 小头寸改善90%
        'tier2_target_improvement': 0.6,
        'tier3_target_improvement': 0.3
    },
    
    'trading_constraints': {
        'min_trade_amount': 50,               # 降低最小交易金额
        'min_shares_per_trade': 1,
        'max_position_change': 0.8,
        'overweight_sell_threshold': 0.02,    # 优先处理超配
        'underweight_buy_threshold': -0.001   # 对小头寸更敏感
    }
}

# 高频交易配置 - 每周再平衡
HIGH_FREQUENCY_CONFIG = {
    'target_cash_percentage': 0.03,  # 稍多现金应对频繁交易
    
    'deviation_thresholds': {
        'critical': 0.025,    # 稍高阈值避免过度交易
        'severe': 0.02,
        'moderate': 0.015,
        'minor': 0.01,
        'target_range': 0.005
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.6,
        'tier2_budget_ratio': 0.3,
        'tier3_budget_ratio': 0.1,
        'max_single_stock_ratio': 0.1,       # 限制单股资金使用
        'tier1_target_improvement': 0.6,     # 更温和的改善
        'tier2_target_improvement': 0.4,
        'tier3_target_improvement': 0.2
    },
    
    'trading_constraints': {
        'min_trade_amount': 200,              # 更高最小交易金额
        'min_shares_per_trade': 2,
        'max_position_change': 0.4,           # 限制单次变化
        'overweight_sell_threshold': 0.02,
        'underweight_buy_threshold': -0.01
    },
    
    'risk_management': {
        'max_trades_per_session': 40,         # 限制交易数量
        'emergency_cash_ratio': 0.06,
        'concentration_limit': 0.08,
        'liquidity_buffer': 0.025
    }
}

# 资金有限配置 - 专门处理资金不足的情况
LIMITED_FUNDS_CONFIG = {
    'target_cash_percentage': 0.01,  # 减少现金保留
    'min_cash_reserve': 500,
    
    'deviation_thresholds': {
        'critical': 0.015,    # 降低阈值，更早介入
        'severe': 0.01,
        'moderate': 0.008,
        'minor': 0.005,
        'target_range': 0.003
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.8,           # 集中资金解决关键问题
        'tier2_budget_ratio': 0.15,
        'tier3_budget_ratio': 0.05,
        'max_single_stock_ratio': 0.3,       # 允许更大的单股投资
        'tier1_target_improvement': 0.8,     # 尽可能改善
        'tier2_target_improvement': 0.5,
        'tier3_target_improvement': 0.2
    },
    
    'trading_constraints': {
        'min_trade_amount': 30,               # 很低的最小交易金额
        'min_shares_per_trade': 1,
        'max_position_change': 0.9,           # 允许大幅变化
        'overweight_sell_threshold': 0.012,   # 更积极地卖出超配
        'underweight_buy_threshold': -0.003
    },
    
    'risk_management': {
        'max_trades_per_session': 60,
        'emergency_cash_ratio': 0.02,         # 降低紧急现金
        'concentration_limit': 0.15,          # 放宽集中度限制
        'liquidity_buffer': 0.01
    }
}

# 大资金配置 - 资金充足的情况
LARGE_FUNDS_CONFIG = {
    'target_cash_percentage': 0.03,  # 稍多现金
    'min_cash_reserve': 5000,
    
    'deviation_thresholds': {
        'critical': 0.02,
        'severe': 0.015,
        'moderate': 0.01,
        'minor': 0.005,
        'target_range': 0.002   # 更严格的目标范围
    },
    
    'tier_allocation': {
        'tier1_budget_ratio': 0.4,           # 更均衡的资金分配
        'tier2_budget_ratio': 0.35,
        'tier3_budget_ratio': 0.25,
        'max_single_stock_ratio': 0.08,      # 限制单股资金
        'tier1_target_improvement': 0.95,    # 几乎完全改善
        'tier2_target_improvement': 0.8,
        'tier3_target_improvement': 0.6
    },
    
    'trading_constraints': {
        'min_trade_amount': 500,              # 更高的最小交易
        'min_shares_per_trade': 5,
        'max_position_change': 0.6,
        'overweight_sell_threshold': 0.01,    # 更敏感的卖出
        'underweight_buy_threshold': -0.003
    },
    
    'risk_management': {
        'max_trades_per_session': 100,        # 允许更多交易
        'emergency_cash_ratio': 0.04,
        'concentration_limit': 0.06,          # 更严格的集中度限制
        'liquidity_buffer': 0.02
    }
}

# 配置字典 - 方便选择
CONFIGS = {
    'default': DEFAULT_CONFIG,
    'conservative': CONSERVATIVE_CONFIG,
    'aggressive': AGGRESSIVE_CONFIG,
    'small_position_protection': SMALL_POSITION_PROTECTION_CONFIG,
    'high_frequency': HIGH_FREQUENCY_CONFIG,
    'limited_funds': LIMITED_FUNDS_CONFIG,
    'large_funds': LARGE_FUNDS_CONFIG
}

def get_config(config_name='default'):
    """
    获取指定配置
    
    Args:
        config_name: 配置名称
        
    Returns:
        配置字典
    """
    if config_name not in CONFIGS:
        print(f"配置 '{config_name}' 不存在，使用默认配置")
        return DEFAULT_CONFIG
    
    return CONFIGS[config_name].copy()

def customize_config(base_config_name='default', **kwargs):
    """
    基于基础配置创建自定义配置
    
    Args:
        base_config_name: 基础配置名称
        **kwargs: 要修改的配置参数
        
    Returns:
        自定义配置字典
    """
    config = get_config(base_config_name)
    
    # 深度更新配置
    for key, value in kwargs.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    return config

# 使用示例
if __name__ == "__main__":
    # 获取默认配置
    default_config = get_config('default')
    print("默认配置:")
    print("目标股票数量: 自动计算（网页数据 - 清仓股票 - 排除股票）")
    print(f"临界偏离阈值: {default_config['deviation_thresholds']['critical']:.1%}")
    
    # 获取小头寸保护配置
    small_pos_config = get_config('small_position_protection')
    print(f"\n小头寸保护配置:")
    print(f"第一层资金比例: {small_pos_config['tier_allocation']['tier1_budget_ratio']:.1%}")
    
    # 创建自定义配置
    custom_config = customize_config(
        'default',
        deviation_thresholds={'critical': 0.025, 'severe': 0.02},
        tier_allocation={'tier1_budget_ratio': 0.7}
    )
    print(f"\n自定义配置:")
    print("目标股票数量: 自动计算（网页数据 - 清仓股票 - 排除股票）")
    print(f"临界偏离阈值: {custom_config['deviation_thresholds']['critical']:.1%}")
    print(f"第一层资金比例: {custom_config['tier_allocation']['tier1_budget_ratio']:.1%}")