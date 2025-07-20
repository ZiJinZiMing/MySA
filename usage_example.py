#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合再平衡使用示例
演示如何使用分层处理策略进行等权重再平衡
"""

from src.portfolio_rebalancing import FixedSeekingAlphaScraper, quick_analyze_portfolio
from config_examples import get_config, customize_config

def example_1_basic_usage():
    """
    示例1：基本使用方法
    """
    print("=" * 60)
    print("示例1：基本使用方法")
    print("=" * 60)
    
    # 创建爬虫实例
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=False)
    
    try:
        # 获取投资组合数据（需要Chrome浏览器运行在9222端口）
        portfolio_id = '64139349'
        print(f"获取投资组合数据: {portfolio_id}")
        
        # 注意：这里需要实际的Chrome浏览器连接，示例中跳过
        # df = scraper.scrape_portfolio_by_id(portfolio_id)
        
        # 使用默认配置
        # rebalance_df = scraper.calculate_equal_weight_rebalance(df)
        
        print("✅ 基本使用方法演示完成")
        print("实际使用时需要：")
        print("1. 启动Chrome: google-chrome --remote-debugging-port=9222")
        print("2. 在浏览器中登录SeekingAlpha")
        print("3. 运行上述代码")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        scraper.close()

def example_2_custom_config():
    """
    示例2：自定义配置
    """
    print("\n" + "=" * 60)
    print("示例2：自定义配置")
    print("=" * 60)
    
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
    
    print("自定义配置:")
    print(f"  保留现金: ${config['target_cash_amount']:,}")
    print(f"  清仓股票: {config['liquidate_symbols']}")
    print(f"  临界偏离阈值: {config['deviation_thresholds']['critical']:.1%}")
    print(f"  第一层资金比例: {config['tier_allocation']['tier1_budget_ratio']:.1%}")
    print("  目标股票数量: 自动计算（网页数据 - 清仓股票 - 排除股票）")
    
    # 使用自定义配置
    scraper = FixedSeekingAlphaScraper(use_existing_browser=True, debug_mode=False)
    
    try:
        # rebalance_df = scraper.calculate_equal_weight_rebalance(df, config)
        print("✅ 自定义配置演示完成")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        scraper.close()

def example_3_preset_configs():
    """
    示例3：使用预设配置
    """
    print("\n" + "=" * 60)
    print("示例3：使用预设配置")
    print("=" * 60)
    
    # 小头寸保护配置
    small_pos_config = get_config('small_position_protection')
    print("小头寸保护配置:")
    print(f"  第一层资金比例: {small_pos_config['tier_allocation']['tier1_budget_ratio']:.1%}")
    print(f"  第一层改善比例: {small_pos_config['tier_allocation']['tier1_target_improvement']:.1%}")
    print(f"  单股最大资金比例: {small_pos_config['tier_allocation']['max_single_stock_ratio']:.1%}")
    
    # 保守型配置
    conservative_config = get_config('conservative')
    print("\n保守型配置:")
    print(f"  临界偏离阈值: {conservative_config['deviation_thresholds']['critical']:.1%}")
    print(f"  最小交易金额: ${conservative_config['trading_constraints']['min_trade_amount']}")
    print(f"  最大交易数量: {conservative_config['risk_management']['max_trades_per_session']}")
    
    # 积极型配置
    aggressive_config = get_config('aggressive')
    print("\n积极型配置:")
    print(f"  临界偏离阈值: {aggressive_config['deviation_thresholds']['critical']:.1%}")
    print(f"  最小交易金额: ${aggressive_config['trading_constraints']['min_trade_amount']}")
    print(f"  最大交易数量: {aggressive_config['risk_management']['max_trades_per_session']}")
    
    print("✅ 预设配置演示完成")

def example_4_quick_analysis():
    """
    示例4：快速分析函数
    """
    print("\n" + "=" * 60)
    print("示例4：快速分析函数")
    print("=" * 60)
    
    # 使用快速分析函数
    portfolio_id = '64139349'
    
    print("快速分析参数:")
    print(f"  投资组合ID: {portfolio_id}")
    print(f"  保留现金: $3,000")
    print(f"  清仓股票: ['OKTA', 'INTA']")
    print("  目标股票数量: 自动计算（网页数据 - 清仓股票 - 排除股票）")
    
    try:
        # df, rebalance_df = quick_analyze_portfolio(
        #     portfolio_id=portfolio_id,
        #     target_stock_count=30,
        #     target_cash_amount=3000,
        #     liquidate_symbols=['OKTA', 'INTA'],
        #     exclude_symbols=['CASH']
        # )
        print("✅ 快速分析函数演示完成")
        print("实际使用时会自动生成详细的再平衡报告")
    except Exception as e:
        print(f"❌ 错误: {e}")

def example_5_addressing_small_positions():
    """
    示例5：专门解决小头寸问题（STX、LITE、WLDN）
    """
    print("\n" + "=" * 60)
    print("示例5：专门解决小头寸问题")
    print("=" * 60)
    
    # 创建专门解决小头寸的配置
    config = customize_config(
        'small_position_protection',
        deviation_thresholds={
            'critical': 0.018,    # 降低临界阈值，让小头寸更容易进入第一层
            'severe': 0.012,
            'moderate': 0.008,
            'minor': 0.004
        },
        tier_allocation={
            'tier1_budget_ratio': 0.8,         # 80%资金优先处理小头寸
            'tier1_target_improvement': 0.9,   # 小头寸改善90%
            'max_single_stock_ratio': 0.25     # 允许单股使用更多资金
        },
        trading_constraints={
            'min_trade_amount': 50,             # 降低最小交易金额
            'underweight_buy_threshold': -0.001 # 对小头寸更敏感
        }
    )
    
    print("小头寸保护配置特点:")
    print(f"  临界偏离阈值: {config['deviation_thresholds']['critical']:.1%} (更低)")
    print(f"  第一层资金比例: {config['tier_allocation']['tier1_budget_ratio']:.1%} (更高)")
    print(f"  第一层改善比例: {config['tier_allocation']['tier1_target_improvement']:.1%} (更高)")
    print(f"  最小交易金额: ${config['trading_constraints']['min_trade_amount']} (更低)")
    
    print("\n预期效果:")
    print("  STX: 从 $148 (0.1%) → $3,500+ (1.3%+)")
    print("  LITE: 从 $102 (0.0%) → $3,400+ (1.3%+)")
    print("  WLDN: 从 $79 (0.0%) → $3,350+ (1.3%+)")
    
    print("✅ 小头寸保护方案演示完成")

def example_6_different_scenarios():
    """
    示例6：不同资金情况的处理
    """
    print("\n" + "=" * 60)
    print("示例6：不同资金情况的处理")
    print("=" * 60)
    
    # 资金充足情况
    large_funds_config = get_config('large_funds')
    print("资金充足情况:")
    print(f"  策略: 全面改善权重平衡")
    print(f"  资金分配: 第一层{large_funds_config['tier_allocation']['tier1_budget_ratio']:.0%}, " +
          f"第二层{large_funds_config['tier_allocation']['tier2_budget_ratio']:.0%}, " +
          f"第三层{large_funds_config['tier_allocation']['tier3_budget_ratio']:.0%}")
    print(f"  改善比例: {large_funds_config['tier_allocation']['tier1_target_improvement']:.0%}/" +
          f"{large_funds_config['tier_allocation']['tier2_target_improvement']:.0%}/" +
          f"{large_funds_config['tier_allocation']['tier3_target_improvement']:.0%}")
    
    # 资金不足情况
    limited_funds_config = get_config('limited_funds')
    print("\n资金不足情况:")
    print(f"  策略: 集中火力解决最严重问题")
    print(f"  资金分配: 第一层{limited_funds_config['tier_allocation']['tier1_budget_ratio']:.0%}, " +
          f"第二层{limited_funds_config['tier_allocation']['tier2_budget_ratio']:.0%}, " +
          f"第三层{limited_funds_config['tier_allocation']['tier3_budget_ratio']:.0%}")
    print(f"  单股最大资金比例: {limited_funds_config['tier_allocation']['max_single_stock_ratio']:.0%}")
    
    print("\n系统会根据资金覆盖率自动选择策略:")
    print("  覆盖率 < 20%: 集中火力（前5只股票）")
    print("  覆盖率 20%-60%: 分层处理")
    print("  覆盖率 > 60%: 全面改善")
    
    print("✅ 不同资金情况处理演示完成")

if __name__ == "__main__":
    print("🚀 投资组合等权重再平衡系统 - 使用示例")
    print("=" * 60)
    
    # 运行所有示例
    example_1_basic_usage()
    example_2_custom_config()
    example_3_preset_configs()
    example_4_quick_analysis()
    example_5_addressing_small_positions()
    example_6_different_scenarios()
    
    print("\n" + "=" * 60)
    print("📚 更多信息:")
    print("  - 完整文档: PORTFOLIO_REBALANCING_GUIDE.md")
    print("  - 配置示例: config_examples.py")
    print("  - 实际运行: python src/portfolio_rebalancing.py 64139349")
    print("=" * 60)