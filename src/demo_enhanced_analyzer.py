#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强股票分析器演示脚本

演示如何从MyAlphaPicker获取股票筛选列表并分析详细量化评分信息
"""

import sys
sys.path.append('/home/zhangjinming/workspace/MySA/src')

from enhanced_stock_analyzer import EnhancedStockAnalyzer
import logging

# 配置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_enhanced_analyzer():
    """演示增强股票分析器"""
    
    print("🚀 增强股票分析器演示")
    print("=" * 50)
    
    print("\n📋 功能概述:")
    print("1. 从MyAlphaPicker获取股票筛选列表")
    print("2. 提取Symbol、Price、QuantRating、Sector&Industry等信息")
    print("3. 访问每只股票的量化评分页面获取交易所和评级历史")
    print("4. 测试模式：仅处理前5只股票")
    
    print("\n" + "=" * 50)
    
    # 创建分析器实例
    analyzer = EnhancedStockAnalyzer(test_mode=True, max_stocks=5)
    
    try:
        # 执行完整分析
        stocks_data = analyzer.analyze_stocks()
        
        if stocks_data:
            print(f"\n✅ 成功分析 {len(stocks_data)} 只股票")
            
            # 显示分析结果
            print("\n📊 分析结果摘要:")
            for i, stock in enumerate(stocks_data, 1):
                print(f"\n{i}. {stock['symbol']} ({stock.get('company_name', 'N/A')})")
                print(f"   价格: {stock.get('price', 'N/A')}")
                print(f"   量化评级: {stock.get('quant_rating', 'N/A')}")
                print(f"   行业: {stock.get('sector_industry', 'N/A')}")
                print(f"   交易所: {stock.get('exchange', 'N/A')}")
                
                rating_history = stock.get('rating_history', [])
                print(f"   评级历史: {len(rating_history)} 条记录")
                
                if rating_history:
                    latest = rating_history[-1]
                    print(f"   最新评级: {latest.get('date', 'N/A')} - {latest.get('rating', 'N/A')}")
            
            # 保存结果
            analyzer.save_results_to_csv(stocks_data, "demo_analysis_results.csv")
            print(f"\n💾 分析结果已保存到: demo_analysis_results.csv")
            
        else:
            print("❌ 未获取到任何数据")
    
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.close()
    
    print("\n" + "=" * 50)
    print("✨ 演示完成！")
    print("\n💡 新功能亮点:")
    print("- ✅ 鲁棒的数据提取 - 多种策略确保数据获取成功")
    print("- ✅ 完整信息获取 - 基础信息 + 详细量化评分")
    print("- ✅ 智能错误处理 - 优雅处理页面加载和数据提取异常")
    print("- ✅ Chrome远程调试 - 复用登录状态，避免重复认证")
    print("- ✅ 测试模式 - 支持限制股票数量进行快速测试")

if __name__ == "__main__":
    demo_enhanced_analyzer()