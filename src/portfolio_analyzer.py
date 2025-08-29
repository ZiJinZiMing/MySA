#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合综合分析器 (Portfolio Analyzer)

专注于投资组合Beta风险分析和GICS行业分布分析，使用统一的portfolio_data模块进行数据解析。

主要功能：
1. Beta分析：计算投资组合加权平均Beta和风险等级评估
2. 行业分析：GICS行业分布统计和可视化饼状图
3. 风险评估：识别高风险和低风险股票
4. 报告生成：创建详细的Excel分析报告
5. 可视化：生成行业分布饼状图
"""

import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

# 使用统一的数据解析模块
from portfolio_data import parse_portfolio_full

# 绘图导入
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

logger = logging.getLogger(__name__)


@dataclass
class BetaAnalysis:
    """Beta分析结果"""
    portfolio_beta: float
    total_value: float
    stock_count: int
    weighted_avg_beta: float
    beta_contributions: Dict[str, float]
    risk_level: str
    high_beta_stocks: List[str]
    low_beta_stocks: List[str]
    missing_beta_stocks: List[str]
    sector_distribution: Dict[str, int]
    sector_value_distribution: Dict[str, float]
    sector_weight_distribution: Dict[str, float]




class PortfolioBetaCalculator:
    """投资组合Beta计算器"""
    
    def __init__(self):
        self.risk_levels = {
            'low': (0, 0.8),
            'moderate': (0.8, 1.2),
            'high': (1.2, float('inf'))
        }
    
    def calculate_portfolio_beta(self, portfolio_df: pd.DataFrame) -> Optional[BetaAnalysis]:
        """
        计算投资组合Beta和GICS统计
        
        Args:
            portfolio_df: 包含symbol, price, shares, beta, sector的DataFrame
            
        Returns:
            BetaAnalysis对象
        """
        if not self._validate_data(portfolio_df):
            return None
        
        try:
            # 计算每只股票的价值
            portfolio_df = portfolio_df.copy()
            portfolio_df['value'] = portfolio_df['price'] * portfolio_df['shares']
            total_value = portfolio_df['value'].sum()
            
            # 计算权重
            portfolio_df['weight'] = portfolio_df['value'] / total_value
            
            # 分离有Beta值和无Beta值的股票
            valid_beta_df = portfolio_df.dropna(subset=['beta'])
            missing_beta_df = portfolio_df[portfolio_df['beta'].isna()]
            
            # 计算GICS行业统计
            sector_stats = self._calculate_sector_statistics(portfolio_df, total_value)
            
            # 计算加权平均Beta
            if len(valid_beta_df) == 0:
                logger.warning("没有有效的Beta数据")
                portfolio_beta = None
                weighted_avg_beta = None
            else:
                # 基于有Beta值股票的权重重新归一化
                valid_total_value = valid_beta_df['value'].sum()
                valid_beta_df = valid_beta_df.copy()
                valid_beta_df['normalized_weight'] = valid_beta_df['value'] / valid_total_value
                
                # 计算加权平均Beta
                portfolio_beta = (valid_beta_df['normalized_weight'] * valid_beta_df['beta']).sum()
                weighted_avg_beta = portfolio_beta
                
                # 计算每只股票的Beta贡献
                valid_beta_df['beta_contribution'] = valid_beta_df['normalized_weight'] * valid_beta_df['beta']
            
            # Beta贡献字典
            beta_contributions = {}
            if len(valid_beta_df) > 0:
                for _, row in valid_beta_df.iterrows():
                    beta_contributions[row['symbol']] = row['beta_contribution']
            
            # 风险等级评估
            risk_level = self._assess_risk_level(portfolio_beta) if portfolio_beta is not None else "Unknown"
            
            # 分类股票
            high_beta_stocks = []
            low_beta_stocks = []
            missing_beta_stocks = missing_beta_df['symbol'].tolist()
            
            for _, row in valid_beta_df.iterrows():
                if row['beta'] > 1.2:
                    high_beta_stocks.append(row['symbol'])
                elif row['beta'] < 0.8:
                    low_beta_stocks.append(row['symbol'])
            
            # 创建分析结果
            analysis = BetaAnalysis(
                portfolio_beta=portfolio_beta,
                total_value=total_value,
                stock_count=len(portfolio_df),
                weighted_avg_beta=weighted_avg_beta,
                beta_contributions=beta_contributions,
                risk_level=risk_level,
                high_beta_stocks=high_beta_stocks,
                low_beta_stocks=low_beta_stocks,
                missing_beta_stocks=missing_beta_stocks,
                sector_distribution=sector_stats['sector_distribution'],
                sector_value_distribution=sector_stats['sector_value_distribution'],
                sector_weight_distribution=sector_stats['sector_weight_distribution']
            )
            
            self._log_beta_analysis(analysis, portfolio_df)
            return analysis
            
        except Exception as e:
            logger.error(f"Beta计算失败: {e}")
            return None
    
    def _validate_data(self, portfolio_df: pd.DataFrame) -> bool:
        """验证输入数据"""
        if portfolio_df is None or portfolio_df.empty:
            logger.error("投资组合数据为空")
            return False
            
        required_columns = ['symbol', 'price', 'shares']
        missing_columns = [col for col in required_columns if col not in portfolio_df.columns]
        if missing_columns:
            logger.error(f"缺少必要列: {missing_columns}")
            return False
        
        # Beta列是可选的，但如果不存在需要添加
        if 'beta' not in portfolio_df.columns:
            logger.warning("未找到Beta列，将添加空的Beta列")
            portfolio_df['beta'] = None
            
        return True
    
    def _calculate_sector_statistics(self, portfolio_df: pd.DataFrame, total_value: float) -> Dict:
        """计算行业统计数据"""
        # 确保有sector列
        if 'sector' not in portfolio_df.columns:
            portfolio_df['sector'] = 'Unknown'
        
        # 统计行业数量分布
        sector_distribution = portfolio_df['sector'].value_counts().to_dict()
        
        # 统计行业价值分布
        sector_value_distribution = portfolio_df.groupby('sector')['value'].sum().to_dict()
        
        # 统计行业权重分布
        sector_weight_distribution = {}
        for sector, value in sector_value_distribution.items():
            sector_weight_distribution[sector] = value / total_value
        
        return {
            'sector_distribution': sector_distribution,
            'sector_value_distribution': sector_value_distribution,
            'sector_weight_distribution': sector_weight_distribution
        }
    
    def _assess_risk_level(self, portfolio_beta: float) -> str:
        """评估风险等级"""
        if portfolio_beta is None:
            return "Unknown"
        
        for level, (min_beta, max_beta) in self.risk_levels.items():
            if min_beta <= portfolio_beta < max_beta:
                return level.title()
        return "Unknown"
    
    def _log_beta_analysis(self, analysis: BetaAnalysis, portfolio_df: pd.DataFrame):
        """记录Beta分析结果"""
        logger.info("开始投资组合Beta风险分析")
        logger.info(f"📊 投资组合总价值: ${analysis.total_value:,.2f}")
        logger.info(f"📈 投资组合Beta: {analysis.portfolio_beta:.3f}" if analysis.portfolio_beta is not None else "📈 投资组合Beta: 无法计算（缺少Beta数据）")
        logger.info(f"🎯 风险等级: {analysis.risk_level}")
        logger.info(f"📋 股票总数: {analysis.stock_count}")
        
        if analysis.high_beta_stocks:
            logger.info(f"⚠️ 高风险股票 (Beta > 1.2): {', '.join(analysis.high_beta_stocks)}")
        
        if analysis.low_beta_stocks:
            logger.info(f"🛡️ 低风险股票 (Beta < 0.8): {', '.join(analysis.low_beta_stocks)}")
        
        if analysis.missing_beta_stocks:
            logger.info(f"❓ 缺少Beta数据的股票: {', '.join(analysis.missing_beta_stocks)}")
        
        # 显示前5大Beta贡献
        if analysis.beta_contributions:
            sorted_contributions = sorted(analysis.beta_contributions.items(), key=lambda x: abs(x[1]), reverse=True)
            logger.info("🔝 Beta贡献度排序 (前5位):")
            for i, (symbol, contribution) in enumerate(sorted_contributions[:5]):
                logger.info(f"  {i+1}. {symbol}: {contribution:.4f}")
        
        # 显示行业分布
        logger.info("📊 行业分布:")
        for sector, count in analysis.sector_distribution.items():
            weight_pct = analysis.sector_weight_distribution.get(sector, 0) * 100
            logger.info(f"  {sector}: {count}只股票 ({weight_pct:.1f}%)")
        
        # 添加详细的股票sector调试信息
        logger.debug("=== 详细股票Sector信息 ===")
        for _, row in portfolio_df.iterrows():
            logger.debug(f"  {row['symbol']}: Sector='{row['sector']}'")
        logger.debug("===========================")
    
    def export_beta_analysis_to_excel(self, analysis: BetaAnalysis, portfolio_df: pd.DataFrame, 
                                    output_dir: str = "../beta_analysis") -> str:
        """
        导出Beta分析结果到Excel文件
        
        Args:
            analysis: Beta分析结果
            portfolio_df: 原始投资组合数据
            output_dir: 输出目录
            
        Returns:
            生成的文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_beta_analysis_{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # 创建Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 1. 原始数据
                portfolio_df.to_excel(writer, sheet_name='投资组合数据', index=False)
                
                # 2. Beta分析详情
                if analysis.portfolio_beta is not None:
                    # 计算详细数据
                    detailed_df = portfolio_df.copy()
                    detailed_df['value'] = detailed_df['price'] * detailed_df['shares']
                    detailed_df['weight'] = detailed_df['value'] / analysis.total_value
                    
                    # 添加Beta贡献
                    detailed_df['beta_contribution'] = detailed_df['symbol'].map(
                        analysis.beta_contributions
                    ).fillna(0)
                    
                    # 风险分级
                    def categorize_risk(beta):
                        if pd.isna(beta):
                            return "Unknown"
                        elif beta < 0.8:
                            return "Low"
                        elif beta <= 1.2:
                            return "Moderate"
                        else:
                            return "High"
                    
                    detailed_df['risk_category'] = detailed_df['beta'].apply(categorize_risk)
                    
                    # 按Beta贡献度排序
                    detailed_df = detailed_df.sort_values('beta_contribution', ascending=False, na_position='last')
                    
                    detailed_df.to_excel(writer, sheet_name='Beta详细分析', index=False)
                
                # 3. 汇总信息
                summary_data = {
                    '指标': ['投资组合总价值', '投资组合Beta', '风险等级', '股票总数', 
                            '有Beta数据股票数', '缺少Beta数据股票数', 
                            '高风险股票数 (Beta > 1.2)', '低风险股票数 (Beta < 0.8)'],
                    '数值': [
                        f"${analysis.total_value:,.2f}",
                        f"{analysis.portfolio_beta:.4f}" if analysis.portfolio_beta is not None else "N/A",
                        analysis.risk_level,
                        analysis.stock_count,
                        len(analysis.beta_contributions),
                        len(analysis.missing_beta_stocks),
                        len(analysis.high_beta_stocks),
                        len(analysis.low_beta_stocks)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Beta汇总', index=False)
                
                # 4. 风险分类明细
                if analysis.beta_contributions:
                    risk_categories = []
                    
                    # 高风险股票
                    for symbol in analysis.high_beta_stocks:
                        risk_categories.append({
                            '股票代码': symbol,
                            '风险类别': 'High',
                            'Beta值': next((row['beta'] for _, row in portfolio_df.iterrows() if row['symbol'] == symbol), None),
                            'Beta贡献': analysis.beta_contributions.get(symbol, 0)
                        })
                    
                    # 中等风险股票
                    moderate_stocks = [s for s in analysis.beta_contributions.keys() 
                                     if s not in analysis.high_beta_stocks and s not in analysis.low_beta_stocks]
                    for symbol in moderate_stocks:
                        risk_categories.append({
                            '股票代码': symbol,
                            '风险类别': 'Moderate',
                            'Beta值': next((row['beta'] for _, row in portfolio_df.iterrows() if row['symbol'] == symbol), None),
                            'Beta贡献': analysis.beta_contributions.get(symbol, 0)
                        })
                    
                    # 低风险股票
                    for symbol in analysis.low_beta_stocks:
                        risk_categories.append({
                            '股票代码': symbol,
                            '风险类别': 'Low',
                            'Beta值': next((row['beta'] for _, row in portfolio_df.iterrows() if row['symbol'] == symbol), None),
                            'Beta贡献': analysis.beta_contributions.get(symbol, 0)
                        })
                    
                    # 缺少Beta数据的股票
                    for symbol in analysis.missing_beta_stocks:
                        risk_categories.append({
                            '股票代码': symbol,
                            '风险类别': 'Unknown',
                            'Beta值': None,
                            'Beta贡献': 0
                        })
                    
                    risk_df = pd.DataFrame(risk_categories)
                    risk_df = risk_df.sort_values(['风险类别', 'Beta贡献'], ascending=[True, False])
                    risk_df.to_excel(writer, sheet_name='风险分类明细', index=False)
                
                # 5. 生成信息
                generation_data = {
                    '生成时间': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    '分析版本': ['Portfolio Beta Calculator v1.0'],
                    '数据来源': ['SeekingAlpha Portfolio Data']
                }
                generation_df = pd.DataFrame(generation_data)
                generation_df.to_excel(writer, sheet_name='生成信息', index=False)
        
            logger.info(f"📊 Beta分析报告已导出到: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"导出Excel文件失败: {e}")
            return None
    
    def create_sector_pie_chart(self, analysis: BetaAnalysis, output_dir: str = "../beta_analysis") -> str:
        """
        创建GICS行业分布饼状图
        
        Args:
            analysis: Beta分析结果
            output_dir: 输出目录
            
        Returns:
            生成的图片文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_filename = f"sector_distribution_{timestamp}.png"
            chart_filepath = os.path.join(output_dir, chart_filename)
            
            # 准备数据
            sectors = list(analysis.sector_weight_distribution.keys())
            weights = [w * 100 for w in analysis.sector_weight_distribution.values()]  # 转换为百分比
            counts = [analysis.sector_distribution.get(sector, 0) for sector in sectors]
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 支持中文显示
            plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
            
            # 创建图形
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            
            # 定义颜色方案
            colors = plt.cm.Set3(np.linspace(0, 1, len(sectors)))
            
            # 左侧：按权重的饼状图
            wedges1, texts1, autotexts1 = ax1.pie(
                weights, 
                labels=sectors, 
                colors=colors,
                autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
                startangle=90,
                pctdistance=0.85
            )
            
            # 设置字体大小
            for autotext in autotexts1:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')
            
            for text in texts1:
                text.set_fontsize(9)
            
            ax1.set_title('投资组合GICS行业分布 (按价值权重)', fontsize=14, fontweight='bold', pad=20)
            
            # 右侧：按数量的饼状图
            wedges2, texts2, autotexts2 = ax2.pie(
                counts,
                labels=[f"{sector}\n({count}只)" for sector, count in zip(sectors, counts)],
                colors=colors,
                autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
                startangle=90,
                pctdistance=0.85
            )
            
            # 设置字体大小
            for autotext in autotexts2:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')
            
            for text in texts2:
                text.set_fontsize(9)
            
            ax2.set_title('投资组合GICS行业分布 (按股票数量)', fontsize=14, fontweight='bold', pad=20)
            
            # 添加总体标题
            fig.suptitle('投资组合GICS行业分析', fontsize=16, fontweight='bold', y=0.95)
            
            # 添加统计信息
            total_stocks = sum(counts)
            total_value = sum(w * analysis.total_value / 100 for w in weights)
            stats_text = f'总股票数: {total_stocks}只 | 总价值: ${total_value:,.0f}'
            fig.text(0.5, 0.02, stats_text, ha='center', fontsize=12, style='italic')
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.90, bottom=0.10)
            
            # 保存图片
            plt.savefig(chart_filepath, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"📊 GICS行业分布饼状图已保存到: {chart_filepath}")
            return chart_filepath
            
        except Exception as e:
            logger.error(f"创建饼状图失败: {e}")
            return None


class PortfolioBetaAnalyzer:
    """完整的投资组合Beta分析器"""
    
    def __init__(self):
        self.calculator = PortfolioBetaCalculator()
    
    def analyze_portfolio_beta(self, file_path: str) -> Tuple[Optional[BetaAnalysis], Optional[str]]:
        """
        一站式Beta分析服务：文件解析 → Beta计算 → Excel导出
        
        Args:
            file_path: 本地MHTML/HTML文件路径
            
        Returns:
            (Beta分析结果, Excel文件路径) 或 (None, None)
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None, None
        
        try:
            logger.info(f"开始完整的Beta分析流程 - 本地文件模式: {file_path}")
            
            # 1. 解析本地文件数据（含Beta）
            logger.info("正在解析本地文件数据（含Beta）...")
            portfolio_df = parse_portfolio_full(file_path)
            
            if portfolio_df is None or portfolio_df.empty:
                logger.error("❌ 无法获取投资组合数据")
                return None, None
            
            # 显示爬取结果
            logger.info(f"✅ 成功爬取 {len(portfolio_df)} 只股票")
            logger.info("📊 投资组合预览（含Beta）:")
            for _, stock in portfolio_df.head().iterrows():
                beta_str = f"Beta: {stock['beta']:.3f}" if pd.notna(stock['beta']) else "Beta: N/A"
                logger.info(f"  {stock['symbol']}: ${stock['price']:.2f} × {stock['shares']:.0f} ({beta_str})")
            
            # 2. 计算Beta分析
            logger.info("📈 正在计算投资组合Beta分析...")
            analysis = self.calculator.calculate_portfolio_beta(portfolio_df)
            
            if analysis is None:
                logger.error("❌ Beta分析失败")
                return None, None
            
            # 3. 生成GICS行业分布饼状图
            logger.info("正在生成GICS行业分布饼状图...")
            file_basename = os.path.splitext(os.path.basename(file_path))[0]
            output_name = f"beta_analysis_{file_basename}"
            chart_path = self.calculator.create_sector_pie_chart(analysis, output_name)
            
            # 4. 导出Excel报告
            logger.info("正在生成Beta分析Excel报告...")
            excel_path = self.calculator.export_beta_analysis_to_excel(analysis, portfolio_df, output_name)
            
            logger.info(f"Beta分析流程完成!")
            logger.info(f"Excel报告: {excel_path}")
            logger.info(f"饼状图: {chart_path}")
            return analysis, excel_path
            
        except Exception as e:
            logger.error(f"❌ Beta分析流程失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None


def test_beta_calculator():
    """测试Beta计算器功能"""
    # 示例数据（包含Beta）
    portfolio_data = [
        {'symbol': 'AAPL', 'price': 150.0, 'shares': 100, 'beta': 1.25},
        {'symbol': 'GOOGL', 'price': 250.0, 'shares': 200, 'beta': 1.05},
        {'symbol': 'MSFT', 'price': 300.0, 'shares': 50, 'beta': 0.95},
        {'symbol': 'NVDA', 'price': 120.0, 'shares': 25, 'beta': 1.75},  # 高Beta
        {'symbol': 'TSLA', 'price': 180.0, 'shares': 30, 'beta': 2.10},  # 高Beta
        {'symbol': 'KO', 'price': 60.0, 'shares': 80, 'beta': 0.65},    # 低Beta
        {'symbol': 'STRL', 'price': 45.0, 'shares': 40, 'beta': None},  # 缺少Beta
    ]
    
    portfolio_df = pd.DataFrame(portfolio_data)
    # 计算value列用于显示
    portfolio_df['value'] = portfolio_df['price'] * portfolio_df['shares']
    
    print("=== 原始投资组合（含Beta） ===")
    print(portfolio_df.to_string(index=False))
    print(f"\n投资组合总价值: ${portfolio_df['value'].sum():,.2f}")
    print(f"股票数量: {len(portfolio_df)}")

    # 使用Beta计算器
    calculator = PortfolioBetaCalculator()
    analysis = calculator.calculate_portfolio_beta(portfolio_df)
    
    if analysis:
        print(f"\n=== Beta分析结果 ===")
        print(f"投资组合Beta: {analysis.portfolio_beta:.4f}")
        print(f"风险等级: {analysis.risk_level}")
        print(f"高风险股票: {analysis.high_beta_stocks}")
        print(f"低风险股票: {analysis.low_beta_stocks}")
        print(f"缺少Beta数据: {analysis.missing_beta_stocks}")
        
        # 导出到Excel
        excel_path = calculator.export_beta_analysis_to_excel(analysis, portfolio_df)
        print(f"\n[Excel] Beta分析报告已导出到: {excel_path}")
    else:
        print("\n=== Beta分析失败 ===")


def main():
    """主函数"""
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('portfolio_beta_analysis.log', encoding='utf-8')
        ]
    )
    
    # 检查命令行参数，默认使用 src/QuantPortfolios.html
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "src/QuantPortfolios.html"
        print(f"\n使用默认文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        if len(sys.argv) <= 1:
            print("请确保 src/QuantPortfolios.html 文件存在，或使用命令行参数指定文件路径")
        else:
            print("请确保提供有效的MHTML或HTML文件路径")
        return
        
    print(f"\n本地文件Beta分析模式 - 文件: {file_path}")
    print("=" * 60)
    
    # 执行Beta分析
    analyzer = PortfolioBetaAnalyzer()
    analysis, excel_path = analyzer.analyze_portfolio_beta(file_path)
    
    if analysis:
        print("\nBeta分析预览:")
        print(f"投资组合Beta: {analysis.portfolio_beta:.4f}" if analysis.portfolio_beta else "投资组合Beta: 无法计算")
        print(f"风险等级: {analysis.risk_level}")
        print(f"Excel报告已保存: {excel_path}")
    else:
        print("\nBeta分析失败")
    
    print("\n使用说明:")
    print("- 默认模式: python src/portfolio_analyzer.py")
    print("- 指定文件: python src/portfolio_analyzer.py <MHTML文件路径>")
    print("- 支持格式: .mhtml, .html 文件")
    print("- 输出报告: 详细的Excel投资组合分析报告 + GICS行业分布饼状图")


def quick_beta_analysis(file_path: str) -> Tuple[Optional[BetaAnalysis], Optional[str]]:
    """
    快速Beta分析的便捷函数
    
    Args:
        file_path: 本地MHTML/HTML文件路径
        
    Returns:
        (Beta分析结果, Excel文件路径)
    """
    analyzer = PortfolioBetaAnalyzer()
    analysis, excel_path = analyzer.analyze_portfolio_beta(file_path)
    
    if analysis and excel_path:
        print(f"\n✅ Beta分析完成!")
        print(f"投资组合Beta: {analysis.portfolio_beta:.4f}" if analysis.portfolio_beta else "投资组合Beta: 无法计算")
        print(f"风险等级: {analysis.risk_level}")
        print(f"Excel报告: {excel_path}")
    
    return analysis, excel_path


if __name__ == "__main__":
    main()