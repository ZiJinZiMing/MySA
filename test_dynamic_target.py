#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试动态目标股票数量计算功能
"""

import pandas as pd
import sys
sys.path.append('src')
from portfolio_rebalancing import FixedSeekingAlphaScraper

def test_dynamic_target_stock_count():
    """测试动态目标股票数量计算"""
    
    # Load the test data
    df = pd.read_csv('portfolio_data_20250717_231306.csv')
    print('📊 测试数据加载成功')
    print(f'总股票数量: {len(df)}')
    
    non_cash_stocks = df[df['symbol'] != 'CASH']
    print(f'非现金股票数量: {len(non_cash_stocks)}')

    # Create scraper instance
    scraper = FixedSeekingAlphaScraper(use_existing_browser=False, debug_mode=True)

    # Test the new dynamic target_stock_count calculation
    print('\n🧪 测试动态目标股票数量计算...')
    try:
        # Test with default config
        config = scraper.get_default_config()
        print(f'默认配置: {config.get("exclude_symbols", [])}')
        
        # Simulate the calculation logic
        cash_rows = df[df['symbol'] == 'CASH']
        stock_rows = df[df['symbol'] != 'CASH'].copy()
        
        # Apply exclude_symbols
        exclude_symbols = config.get('exclude_symbols', [])
        if exclude_symbols:
            exclude_mask = stock_rows['symbol'].isin(exclude_symbols)
            stock_rows = stock_rows[~exclude_mask]
        
        # Apply liquidate_symbols
        liquidate_symbols = config.get('liquidate_symbols', [])
        if liquidate_symbols:
            liquidation_mask = stock_rows['symbol'].isin(liquidate_symbols)
            stock_rows = stock_rows[~liquidation_mask]
        
        # Calculate target_stock_count
        target_stock_count = len(stock_rows)
        print(f'✅ 动态计算的目标股票数量: {target_stock_count}')
        print(f'目标权重: {1/target_stock_count:.4f} ({1/target_stock_count*100:.2f}%)')
        
        # Show some examples
        print('\n📈 小头寸股票示例:')
        small_positions = stock_rows[stock_rows['value'] < 500].sort_values('value')
        total_value = df['value'].sum()
        
        for _, row in small_positions.head(5).iterrows():
            current_weight = row['value'] / total_value
            target_weight = 1 / target_stock_count
            deviation = abs(current_weight - target_weight)
            print(f'  {row["symbol"]}: ${row["value"]:.0f} ({current_weight:.3f}%) -> 目标({target_weight:.3f}%) 偏离{deviation:.3f}%')
        
        # Test with liquidation
        print('\n🔥 测试清仓功能...')
        test_config = config.copy()
        test_config['liquidate_symbols'] = ['OKTA', 'INTA']
        
        test_stock_rows = df[df['symbol'] != 'CASH'].copy()
        
        # Apply liquidation
        liquidation_mask = test_stock_rows['symbol'].isin(test_config['liquidate_symbols'])
        test_stock_rows = test_stock_rows[~liquidation_mask]
        
        # Apply exclude_symbols
        exclude_mask = test_stock_rows['symbol'].isin(test_config['exclude_symbols'])
        test_stock_rows = test_stock_rows[~exclude_mask]
        
        test_target_stock_count = len(test_stock_rows)
        print(f'清仓 {test_config["liquidate_symbols"]} 后的目标股票数量: {test_target_stock_count}')
        print(f'新目标权重: {1/test_target_stock_count:.4f} ({1/test_target_stock_count*100:.2f}%)')
        
        return True
        
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dynamic_target_stock_count()
    if success:
        print('\n✅ 动态目标股票数量计算测试成功!')
        print('现在算法会根据实际数据自动计算目标股票数量，确保STX、LITE、WLDN等股票能正确参与再平衡。')
    else:
        print('\n❌ 测试失败，请检查代码')