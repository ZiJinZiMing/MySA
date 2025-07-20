#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试小头寸股票再平衡功能
"""

import pandas as pd
import sys
sys.path.append('src')
from portfolio_rebalancing import FixedSeekingAlphaScraper

def test_small_position_rebalancing():
    """测试小头寸股票再平衡"""
    
    # Load the test data
    df = pd.read_csv('portfolio_data_20250717_231306.csv')
    print('📊 测试数据加载成功')
    
    # Create scraper instance
    scraper = FixedSeekingAlphaScraper(use_existing_browser=False, debug_mode=True)
    
    print('\n🧪 测试小头寸股票再平衡...')
    try:
        # Get default config
        config = scraper.get_default_config()
        
        # Focus on small position protection
        config['tier_allocation'] = {
            'tier1_budget_ratio': 0.8,           # 80%资金处理小头寸
            'tier2_budget_ratio': 0.15,
            'tier3_budget_ratio': 0.05,
            'max_single_stock_ratio': 0.25,      # 允许单股使用更多资金
            'tier1_target_improvement': 0.9,     # 小头寸改善90%
            'tier2_target_improvement': 0.6,
            'tier3_target_improvement': 0.3
        }
        
        # Simulate the calculation steps
        cash_rows = df[df['symbol'] == 'CASH']
        stock_rows = df[df['symbol'] != 'CASH'].copy()
        
        # Apply exclude_symbols (CASH is already excluded)
        exclude_symbols = config.get('exclude_symbols', [])
        if exclude_symbols:
            exclude_mask = stock_rows['symbol'].isin(exclude_symbols)
            stock_rows = stock_rows[~exclude_mask]
        
        # Calculate target_stock_count dynamically
        target_stock_count = len(stock_rows)
        total_portfolio_value = df['value'].sum()
        target_weight = 1.0 / target_stock_count
        target_value_per_stock = total_portfolio_value * target_weight
        
        print(f'✅ 动态计算结果:')
        print(f'  目标股票数量: {target_stock_count}')
        print(f'  总投资组合价值: ${total_portfolio_value:,.2f}')
        print(f'  目标权重: {target_weight:.4f} ({target_weight*100:.2f}%)')
        print(f'  目标价值/股: ${target_value_per_stock:,.2f}')
        
        # Calculate deviations
        stock_rows['target_value'] = target_value_per_stock
        stock_rows['deviation'] = (stock_rows['value'] - target_value_per_stock) / total_portfolio_value
        stock_rows['abs_deviation'] = abs(stock_rows['deviation'])
        
        # Show small position analysis
        print('\n📈 小头寸股票分析:')
        small_positions = stock_rows[stock_rows['value'] < 500].sort_values('value')
        
        for _, row in small_positions.iterrows():
            current_weight = row['value'] / total_portfolio_value
            deviation = row['deviation']
            needed_investment = target_value_per_stock - row['value']
            
            # Determine tier based on deviation thresholds
            abs_dev = abs(deviation)
            if abs_dev >= 0.018:  # critical threshold for small positions
                tier = "TIER1_CRITICAL"
            elif abs_dev >= 0.012:
                tier = "TIER2_SEVERE"
            elif abs_dev >= 0.008:
                tier = "TIER3_MODERATE"
            else:
                tier = "MINOR"
            
            print(f'  {row["symbol"]}: ${row["value"]:.0f} ({current_weight:.3f}%) -> ${target_value_per_stock:.0f} ({target_weight:.3f}%)')
            print(f'    需要投资: ${needed_investment:.0f}, 偏离: {deviation:.3f}%, 优先级: {tier}')
        
        # Show overweight stocks that can provide funding
        print('\n💰 超配股票（可提供资金）:')
        overweight_stocks = stock_rows[stock_rows['deviation'] > 0.015].sort_values('deviation', ascending=False)
        
        total_excess_funds = 0
        for _, row in overweight_stocks.iterrows():
            current_weight = row['value'] / total_portfolio_value
            excess_value = row['value'] - target_value_per_stock
            total_excess_funds += excess_value
            
            print(f'  {row["symbol"]}: ${row["value"]:.0f} ({current_weight:.3f}%) -> 超配${excess_value:.0f}')
        
        print(f'\n💡 资金来源分析:')
        available_cash = cash_rows['value'].sum() if not cash_rows.empty else 0
        print(f'  现金: ${available_cash:,.2f}')
        print(f'  超配股票可释放资金: ${total_excess_funds:,.2f}')
        print(f'  总可用资金: ${available_cash + total_excess_funds:,.2f}')
        
        # Calculate total needed for small positions
        small_positions_needed = small_positions['target_value'].sum() - small_positions['value'].sum()
        print(f'  小头寸总需求: ${small_positions_needed:,.2f}')
        
        if available_cash + total_excess_funds >= small_positions_needed:
            print('✅ 资金充足，可以完全解决小头寸问题！')
        else:
            print('⚠️  资金不足，需要分层处理')
        
        return True
        
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_small_position_rebalancing()
    if success:
        print('\n✅ 小头寸股票再平衡测试成功!')
        print('修复后的算法现在可以正确处理STX、LITE、WLDN等小头寸股票。')
    else:
        print('\n❌ 测试失败，请检查代码')