#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试扩展评级历史功能
- 单只股票测试滚动加载180+交易日
- 验证连续评级天数计算
- 测试详细CSV输出
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_stock_analyzer import EnhancedStockAnalyzer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_stock_extended_history():
    """测试单只股票的扩展评级历史"""
    logger.info("🧪 开始测试扩展评级历史功能...")
    
    # 创建分析器 - 测试模式，只处理1只股票
    analyzer = EnhancedStockAnalyzer(test_mode=True, max_stocks=1)
    
    try:
        if not analyzer.setup_driver():
            logger.error("浏览器连接失败")
            return
        
        # 测试单只股票：AEVA（因为截图显示了AEVA的详细信息）
        test_symbol = "AEVA"
        logger.info(f"🔍 测试股票: {test_symbol}")
        
        # 直接获取详细信息
        detailed_info = analyzer.extract_stock_detailed_info(test_symbol)
        
        if detailed_info:
            logger.info(f"✅ 获取到 {test_symbol} 的详细信息:")
            logger.info(f"   - 交易所: {detailed_info.get('exchange', 'N/A')}")
            
            rating_history = detailed_info.get('rating_history', [])
            logger.info(f"   - 评级历史记录数: {len(rating_history)}")
            
            if rating_history:
                logger.info(f"   - 最新评级: {rating_history[0].get('rating', 'N/A')}")
                logger.info(f"   - 最新评级连续天数: {rating_history[0].get('consecutive_days', 'N/A')}")
                
                # 显示前10条记录
                logger.info("   - 前10条评级记录:")
                for i, record in enumerate(rating_history[:10]):
                    logger.info(f"     {i+1}. {record.get('date', 'N/A')} | "
                              f"{record.get('rating', 'N/A')} | "
                              f"连续{record.get('consecutive_days', 'N/A')}天")
            
            # 分析结果
            rating_analysis = detailed_info.get('rating_analysis', {})
            if rating_analysis:
                logger.info(f"   - 总交易日数: {rating_analysis.get('total_days', 'N/A')}")
                logger.info(f"   - 最长连续评级: {rating_analysis.get('max_consecutive_days', 'N/A')} 天")
                logger.info(f"   - 最常见评级: {rating_analysis.get('most_common_rating', 'N/A')}")
                logger.info(f"   - 当前评级连续: {rating_analysis.get('current_rating_streak', 'N/A')} 天")
            
            # 保存测试结果
            test_data = [{
                'symbol': test_symbol,
                'price': 'N/A',  # 测试时不需要价格
                'quant_rating': 'N/A',
                'sector_industry': 'N/A',
                'market_cap': 'N/A',
                **detailed_info
            }]
            
            analyzer.save_results_to_csv(test_data, f"test_extended_{test_symbol.lower()}_rating_history.csv")
            
        else:
            logger.error(f"❌ 无法获取 {test_symbol} 的详细信息")
    
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.close()

if __name__ == "__main__":
    test_single_stock_extended_history()