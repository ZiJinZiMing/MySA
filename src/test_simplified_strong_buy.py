#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简化的连续Strong Buy天数功能
- 只记录从最近交易日开始连续Strong Buy的天数
- 直接输出CSV格式
- 性能优化，减少不必要的数据加载
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_stock_analyzer import EnhancedStockAnalyzer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simplified_strong_buy():
    """测试简化的连续Strong Buy天数功能"""
    logger.info("🧪 开始测试简化的连续Strong Buy功能...")
    
    # 创建分析器 - 测试模式，只处理1只股票
    analyzer = EnhancedStockAnalyzer(test_mode=True, max_stocks=1)
    
    try:
        if not analyzer.setup_driver():
            logger.error("浏览器连接失败")
            return
        
        # 测试单只股票：AEVA
        test_symbol = "AEVA"
        logger.info(f"🔍 测试股票: {test_symbol}")
        
        # 直接获取连续Strong Buy天数
        detailed_info = analyzer.extract_stock_detailed_info(test_symbol)
        
        if detailed_info:
            logger.info(f"✅ 获取到 {test_symbol} 的信息:")
            logger.info(f"   - 交易所: {detailed_info.get('exchange', 'N/A')}")
            logger.info(f"   - 连续Strong Buy天数: {detailed_info.get('consecutive_strong_buy_days', 0)}")
            
            # 构造完整测试数据
            test_data = [{
                'symbol': test_symbol,
                'price': '32.89',  # 从截图获取的实际价格
                'quant_rating': '4.99',
                'sector_industry': 'Electronic Equipment and Instruments',
                'market_cap': '1.81B',
                **detailed_info
            }]
            
            # 保存简化的CSV结果
            analyzer.save_results_to_csv(test_data, f"simplified_{test_symbol.lower()}_strong_buy_test.csv")
            
        else:
            logger.error(f"❌ 无法获取 {test_symbol} 的详细信息")
    
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.close()

if __name__ == "__main__":
    test_simplified_strong_buy()