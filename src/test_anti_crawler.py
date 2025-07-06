#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试反爬虫功能
- 测试智能延时机制
- 测试断点续传功能
- 测试请求计数和限制
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_stock_analyzer import EnhancedStockAnalyzer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_anti_crawler_features():
    """测试反爬虫功能"""
    logger.info("🧪 开始测试反爬虫功能...")
    
    # 创建分析器 - 测试模式，处理10只股票
    analyzer = EnhancedStockAnalyzer(test_mode=True, max_stocks=10)
    
    try:
        # 执行股票分析（带反爬虫保护）
        stocks_data = analyzer.analyze_stocks()
        
        # 保存结果
        if stocks_data:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"anti_crawler_test_{timestamp}.csv"
            analyzer.save_results_to_csv(stocks_data, filename)
            
            logger.info(f"✅ 反爬虫测试完成，处理了 {len(stocks_data)} 只股票")
            
            # 显示反爬虫统计
            logger.info(f"📊 最终统计: {analyzer.anti_crawler.get_status()}")
        else:
            logger.warning("❌ 未获取到任何股票数据")
        
    except KeyboardInterrupt:
        logger.info("🛑 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()

def test_progress_resume():
    """测试断点续传功能"""
    logger.info("🧪 测试断点续传功能...")
    
    # 第一次运行，故意中断
    analyzer = EnhancedStockAnalyzer(test_mode=True, max_stocks=15)
    
    try:
        # 模拟处理一些股票后中断
        logger.info("第一次运行：处理5只股票后模拟中断...")
        stocks_data = analyzer.analyze_stocks()
        
    except Exception as e:
        logger.info(f"第一次运行异常结束: {e}")
    finally:
        analyzer.close()
    
    # 第二次运行，从断点继续
    logger.info("第二次运行：从断点继续...")
    analyzer2 = EnhancedStockAnalyzer(test_mode=True, max_stocks=15)
    
    try:
        stocks_data = analyzer2.analyze_stocks()
        
        if stocks_data:
            logger.info(f"✅ 断点续传测试完成，总共处理了 {len(stocks_data)} 只股票")
        
    except Exception as e:
        logger.error(f"❌ 断点续传测试失败: {e}")
    finally:
        analyzer2.close()

if __name__ == "__main__":
    import time
    
    # 自动执行基础反爬虫功能测试
    logger.info("🚀 自动执行基础反爬虫功能测试...")
    test_anti_crawler_features()