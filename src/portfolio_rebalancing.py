#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SeekingAlpha投资组合等权重再平衡器

专注于再平衡算法和交易指令生成，使用统一的portfolio_data模块进行数据解析。
遵循MECE和KISS原则的简化设计。

主要功能：
1. 等权重再平衡计算
2. 交易指令生成
3. 清仓功能支持
4. Excel报告导出
"""

import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

# 使用统一的数据解析模块
from portfolio_data import parse_portfolio_basic

logger = logging.getLogger(__name__)


@dataclass
class RebalanceConfig:
    """等权重再平衡配置"""
    min_trade_amount: float = 100.0        # 最小交易金额
    cash_adjustment: float = 0.0           # 现金调整: >0追加投入, <0保留现金, =0不调整
    liquidation_stocks: List[str] = None   # 需要清仓的股票代码列表
    
    def __post_init__(self):
        if self.liquidation_stocks is None:
            self.liquidation_stocks = []


@dataclass
class PortfolioSummary:
    """投资组合摘要"""
    total_value: float
    cash_value: float
    stock_value: float
    stock_count: int
    investment_amount: float
    liquidation_value: float = 0.0    # 清仓股票总价值
    liquidation_count: int = 0        # 清仓股票数量
    equal_weight_count: int = 0       # 等权重股票数量


@dataclass
class TradeInstruction:
    """交易指令"""
    symbol: str
    action: str  # 'BUY' or 'SELL'
    shares: int
    price: float
    amount: float
    current_shares: int
    target_shares: int
    current_value: float
    target_value: float
    reason: str


class EqualWeightCalculator:
    """等权重再平衡计算器"""
    
    def __init__(self, config: RebalanceConfig = None):
        self.config = config or RebalanceConfig()
    
    def calculate(self, portfolio_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        计算等权重再平衡指令
        
        Args:
            portfolio_df: 投资组合数据
            
        Returns:
            交易指令DataFrame
        """
        # 1. 数据验证
        if not self._validate_data(portfolio_df):
            return None
        
        # 2. 分析投资组合
        summary = self._analyze_portfolio(portfolio_df)
        self._log_portfolio_summary(summary)
        
        # 3. 计算目标配置
        target_amount_per_stock = self._calculate_target_amount(summary)
        
        # 4. 生成交易指令
        trades = self._generate_trades(portfolio_df, target_amount_per_stock)
        
        if not trades:
            logger.info("✅ 投资组合已接近等权重，无需再平衡")
            return None
            
        # 5. 输出摘要
        self._log_trade_summary(trades)
        
        return self._trades_to_dataframe(trades)
    
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
            
        return True
    
    def _analyze_portfolio(self, portfolio_df: pd.DataFrame) -> PortfolioSummary:
        """分析投资组合"""
        # 计算value列：price * shares
        portfolio_df = portfolio_df.copy()
        portfolio_df['value'] = portfolio_df['price'] * portfolio_df['shares']
        
        # 识别清仓股票（只处理投资组合中实际存在的）
        actual_liquidation_stocks = [s for s in self.config.liquidation_stocks 
                                   if s in portfolio_df['symbol'].values]
        
        # 分离清仓股票和等权重股票
        liquidation_df = portfolio_df[portfolio_df['symbol'].isin(actual_liquidation_stocks)]
        equal_weight_df = portfolio_df[~portfolio_df['symbol'].isin(actual_liquidation_stocks)]
        
        total_value = portfolio_df['value'].sum()
        cash_value = 0  # 不再有现金行
        stock_value = total_value
        stock_count = len(portfolio_df)
        
        # 清仓相关统计
        liquidation_value = liquidation_df['value'].sum()
        liquidation_count = len(liquidation_df)
        equal_weight_count = len(equal_weight_df)
        
        # 重新设计现金调整逻辑：清仓资金将加入等权重分配池
        if self.config.cash_adjustment > 0:
            # 追加投入：投资金额 = 当前总价值 + 追加金额
            investment_amount = total_value + self.config.cash_adjustment
        elif self.config.cash_adjustment < 0:
            # 保留现金：投资金额 = 当前总价值 - 保留金额(绝对值)
            investment_amount = total_value - abs(self.config.cash_adjustment)
        else:
            # 不调整：投资金额 = 当前总价值
            investment_amount = total_value
        
        return PortfolioSummary(
            total_value=total_value,
            cash_value=cash_value,
            stock_value=stock_value,
            stock_count=stock_count,
            investment_amount=investment_amount,
            liquidation_value=liquidation_value,
            liquidation_count=liquidation_count,
            equal_weight_count=equal_weight_count
        )
    
    def _calculate_target_amount(self, summary: PortfolioSummary) -> float:
        """计算等权重股票的目标金额（清仓股票不参与等权重分配）"""
        if summary.equal_weight_count == 0:
            logger.warning("没有等权重股票数据")
            return 0.0
            
        # 等权重资金 = 总投资金额（包括清仓释放的资金）
        target_amount = summary.investment_amount / summary.equal_weight_count
        logger.info(f"💰 等权重股票目标金额: ${target_amount:,.2f} (共{summary.equal_weight_count}只股票)")
        
        if summary.liquidation_count > 0:
            logger.info(f"🗑️ 清仓股票: {summary.liquidation_count}只，价值${summary.liquidation_value:,.2f}")
            
        return target_amount
    
    def _generate_trades(self, portfolio_df: pd.DataFrame, target_amount_per_stock: float) -> List[TradeInstruction]:
        """生成交易指令：先处理清仓，再处理等权重"""
        trades = []
        # 计算value列：price * shares
        stocks_df = portfolio_df.copy()
        stocks_df['value'] = stocks_df['price'] * stocks_df['shares']
        
        # 识别清仓股票（只处理投资组合中实际存在的）
        actual_liquidation_stocks = [s for s in self.config.liquidation_stocks 
                                   if s in stocks_df['symbol'].values]
        
        # 1. 先处理清仓股票（全部卖出）
        for _, stock in stocks_df.iterrows():
            if stock['symbol'] in actual_liquidation_stocks:
                trade = self._calculate_liquidation_trade(stock)
                if trade:
                    trades.append(trade)
        
        # 2. 再处理等权重股票
        for _, stock in stocks_df.iterrows():
            if stock['symbol'] not in actual_liquidation_stocks:
                trade = self._calculate_single_trade(stock, target_amount_per_stock)
                if trade:
                    trades.append(trade)
                
        return trades
    
    def _calculate_liquidation_trade(self, stock: pd.Series) -> Optional[TradeInstruction]:
        """计算清仓交易指令"""
        current_shares = int(stock['shares'])
        
        # 如果已经没有持股，跳过
        if current_shares <= 0:
            logger.debug(f"{stock['symbol']}: 已无持股，跳过清仓")
            return None
            
        # 全部卖出
        trade_amount = current_shares * stock['price']
        
        # 过滤小额交易
        if trade_amount < self.config.min_trade_amount:
            logger.debug(f"{stock['symbol']}: 清仓金额${trade_amount:.2f}小于最小阈值${self.config.min_trade_amount}，跳过")
            return None
            
        return TradeInstruction(
            symbol=stock['symbol'],
            action='SELL',
            shares=current_shares,
            price=stock['price'],
            amount=trade_amount,
            current_shares=current_shares,
            target_shares=0,
            current_value=stock['value'],
            target_value=0.0,
            reason='清仓卖出'
        )
    
    def _calculate_single_trade(self, stock: pd.Series, target_amount: float) -> Optional[TradeInstruction]:
        """计算单只股票的交易指令"""
        # 计算目标持股数（四舍五入）
        target_shares = int(np.round(target_amount / stock['price']))
        current_shares = int(stock['shares'])
        share_diff = target_shares - current_shares
        trade_amount = abs(share_diff) * stock['price']
        target_value = target_shares * stock['price']
        
        # 调试信息
        logger.debug(f"{stock['symbol']}: target=${target_amount:.2f}, target_shares={target_shares}, current_shares={current_shares}, diff={share_diff}, trade_amount=${trade_amount:.2f}, actual_target=${target_value:.2f}")
        
        # 过滤小额交易和零交易
        if share_diff == 0:
            logger.debug(f"{stock['symbol']}: 已达到目标持股数，无需调整")
            return None
            
        if trade_amount < self.config.min_trade_amount:
            logger.debug(f"{stock['symbol']}: 交易金额${trade_amount:.2f}小于最小阈值${self.config.min_trade_amount}，跳过")
            return None
            
        action = 'BUY' if share_diff > 0 else 'SELL'
        
        return TradeInstruction(
            symbol=stock['symbol'],
            action=action,
            shares=abs(share_diff),
            price=stock['price'],
            amount=trade_amount,
            current_shares=current_shares,
            target_shares=target_shares,
            current_value=stock['value'],
            target_value=target_value,
            reason=f'等权重调整 (${stock["value"]:.0f} → ${target_value:.0f})'
        )
    
    def _log_portfolio_summary(self, summary: PortfolioSummary):
        """记录投资组合摘要"""
        logger.info("开始计算简化等权重再平衡策略")
        
        # 根据现金调整类型显示不同信息
        if self.config.cash_adjustment > 0:
            adjustment_desc = f"追加投入${self.config.cash_adjustment:,.2f}"
        elif self.config.cash_adjustment < 0:
            adjustment_desc = f"保留现金${abs(self.config.cash_adjustment):,.2f}"
        else:
            adjustment_desc = "不调整现金"
        
        # 显示清仓股票配置
        liquidation_desc = f"清仓股票: {self.config.liquidation_stocks}" if self.config.liquidation_stocks else "无清仓股票"
            
        logger.info(f"配置参数: 最小交易金额=${self.config.min_trade_amount}, 现金调整({adjustment_desc}), {liquidation_desc}")
        logger.info(f"📊 投资组合总价值: ${summary.total_value:,.2f}")
        logger.info(f"💰 当前现金: ${summary.cash_value:,.2f}")
        logger.info(f"📈 当前股票价值: ${summary.stock_value:,.2f}")
        logger.info(f"🎯 总投资金额: ${summary.investment_amount:,.2f}")
        logger.info(f"📊 股票总数: {summary.stock_count} (等权重: {summary.equal_weight_count}, 清仓: {summary.liquidation_count})")
        
        if summary.liquidation_count > 0:
            logger.info(f"🗑️ 清仓股票价值: ${summary.liquidation_value:,.2f}")
    
    def _log_trade_summary(self, trades: List[TradeInstruction]):
        """记录交易摘要"""
        buy_trades = [t for t in trades if t.action == 'BUY']
        sell_trades = [t for t in trades if t.action == 'SELL']
        liquidation_trades = [t for t in sell_trades if t.reason == '清仓卖出']
        equal_weight_trades = [t for t in trades if t.reason != '清仓卖出']
        
        total_buy_amount = sum(t.amount for t in buy_trades)
        total_sell_amount = sum(t.amount for t in sell_trades)
        liquidation_amount = sum(t.amount for t in liquidation_trades)
        
        logger.info(f"\n💰 === 简化等权重再平衡摘要 ===")
        logger.info(f"买入交易: {len(buy_trades)} 笔，总计 ${total_buy_amount:,.2f}")
        logger.info(f"卖出交易: {len(sell_trades)} 笔，总计 ${total_sell_amount:,.2f}")
        
        if liquidation_trades:
            logger.info(f"  其中清仓: {len(liquidation_trades)} 笔，${liquidation_amount:,.2f}")
            
        logger.info(f"净资金需求: ${total_buy_amount - total_sell_amount:,.2f}")
        
        # 分类记录具体交易
        if liquidation_trades:
            logger.info("🗑️ 清仓交易:")
            for trade in liquidation_trades:
                logger.info(f"  {trade.symbol}: SELL {trade.shares} shares, ${trade.amount:,.2f}")
                
        if equal_weight_trades:
            logger.info("⚖️ 等权重交易:")
            for trade in equal_weight_trades:
                logger.info(f"  {trade.symbol}: {trade.action} {trade.shares} shares, ${trade.amount:,.2f}")
    
    def _trades_to_dataframe(self, trades: List[TradeInstruction]) -> pd.DataFrame:
        """将交易指令转换为DataFrame，按操作类型排序：清仓->卖出->买入"""
        # 将交易指令转换为DataFrame
        df = pd.DataFrame([{
            'symbol': t.symbol,
            'action': t.action,
            'shares': t.shares,
            'price': t.price,
            'amount': t.amount,
            'current_shares': t.current_shares,
            'target_shares': t.target_shares,
            'current_value': t.current_value,
            'target_value': t.target_value,
            'reason': t.reason
        } for t in trades])
        
        # 定义排序优先级：清仓操作 > 普通卖出 > 买入
        def get_sort_priority(row):
            if row['reason'] == '清仓卖出':
                return 1  # 清仓操作排在最前
            elif row['action'] == 'SELL':
                return 2  # 普通卖出操作
            else:  # BUY
                return 3  # 买入操作排在最后
        
        df['sort_priority'] = df.apply(get_sort_priority, axis=1)
        df = df.sort_values(['sort_priority', 'symbol']).drop('sort_priority', axis=1).reset_index(drop=True)
        
        return df
    
    def export_to_excel(self, trades_df: pd.DataFrame, portfolio_df: pd.DataFrame, 
                       output_dir: str = "../rebalance") -> str:
        """
        导出再平衡结果到Excel文件
        
        Args:
            trades_df: 交易指令DataFrame
            portfolio_df: 原始投资组合DataFrame
            output_dir: 输出目录
            
        Returns:
            生成的文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rebalance_plan_{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)
        
        # 创建Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 写入原始投资组合
            portfolio_df.to_excel(writer, sheet_name='原始投资组合', index=False)
            
            # 写入交易指令
            if trades_df is not None and not trades_df.empty:
                trades_df.to_excel(writer, sheet_name='交易指令', index=False)
            
            # 计算投资组合总价值（适配简化数据格式）
            if 'value' in portfolio_df.columns:
                total_value = portfolio_df['value'].sum()
            else:
                # 简化格式：计算 price * shares
                total_value = (portfolio_df['price'] * portfolio_df['shares']).sum()
            
            # 写入摘要信息
            summary_data = {
                '生成时间': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                '投资组合总价值': [f"${total_value:,.2f}"],
                '股票数量': [len(portfolio_df)],
                '交易数量': [len(trades_df) if trades_df is not None else 0],
                '最小交易金额': [f"${self.config.min_trade_amount:,.2f}"],
                '现金调整': [f"${self.config.cash_adjustment:,.2f}"]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='摘要信息', index=False)
        
        logger.info(f"📊 再平衡计划已导出到: {filepath}")
        return filepath





class PortfolioRebalancer:
    """完整的投资组合再平衡器 - 爬虫 + 算法集成"""
    
    def __init__(self, config: RebalanceConfig = None):
        self.config = config or RebalanceConfig()
        self.calculator = EqualWeightCalculator(self.config)
    
    def scrape_and_rebalance(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        一站式服务：本地文件解析 → 算法 → Excel导出
        
        Args:
            file_path: 本地MHTML/HTML文件路径
            
        Returns:
            (交易指令DataFrame, Excel文件路径) 或 (None, None)
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None, None
        
        try:
            logger.info(f"开始完整的再平衡流程 - 本地文件模式: {file_path}")
            
            # 1. 解析本地文件数据
            logger.info("正在解析本地文件数据...")
            portfolio_df = parse_portfolio_basic(file_path)
            
            if portfolio_df is None or portfolio_df.empty:
                logger.error("❌ 无法获取投资组合数据")
                return None, None
            
            # 显示爬取结果
            logger.info(f"✅ 成功爬取 {len(portfolio_df)} 只股票")
            logger.info("📊 投资组合预览:")
            for _, stock in portfolio_df.head().iterrows():
                logger.info(f"  {stock['symbol']}: ${stock['price']:.2f} × {stock['shares']:.0f}")
            
            # 2. 计算再平衡
            logger.info("⚖️ 正在计算等权重再平衡策略...")
            trades_df = self.calculator.calculate(portfolio_df)
            
            if trades_df is None:
                logger.info("投资组合已接近等权重，无需再平衡")
                # 仍然导出当前状态
                file_basename = os.path.splitext(os.path.basename(file_path))[0]
                output_name = f"rebalance_{file_basename}"
                excel_path = self.calculator.export_to_excel(None, portfolio_df, output_name)
                return None, excel_path
            
            # 3. 导出Excel报告
            logger.info("正在生成Excel报告...")
            # 生成输出文件名
            file_basename = os.path.splitext(os.path.basename(file_path))[0]
            output_name = f"rebalance_{file_basename}"
            
            excel_path = self.calculator.export_to_excel(trades_df, portfolio_df, output_name)
            
            logger.info(f"再平衡流程完成! Excel报告: {excel_path}")
            return trades_df, excel_path
            
        except Exception as e:
            logger.error(f"❌ 再平衡流程失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def analyze_portfolio_from_data(self, portfolio_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        从现有数据分析投资组合（不使用爬虫）
        
        Args:
            portfolio_df: 投资组合数据
            
        Returns:
            (交易指令DataFrame, Excel文件路径) 或 (None, None)
        """
        try:
            logger.info("⚖️ 正在分析投资组合数据...")
            
            # 计算再平衡
            trades_df = self.calculator.calculate(portfolio_df)
            
            # 导出Excel报告
            excel_path = self.calculator.export_to_excel(trades_df, portfolio_df)
            
            return trades_df, excel_path
            
        except Exception as e:
            logger.error(f"❌ 投资组合分析失败: {e}")
            return None, None


def test_calculator():
    """示例用法"""
    # 示例数据
    portfolio_data = [
        {'symbol': 'AAPL', 'price': 150.0, 'shares': 100},
        {'symbol': 'GOOGL', 'price': 250.0, 'shares': 200},
        {'symbol': 'MSFT', 'price': 300.0, 'shares': 50},
        {'symbol': 'NVDA', 'price': 120.0, 'shares': 25},  # 增加持股用于演示清仓
        {'symbol': 'TSLA', 'price': 180.0, 'shares': 30},  # 新增股票
    ]
    
    portfolio_df = pd.DataFrame(portfolio_data)
    # 计算value列用于显示
    portfolio_df['value'] = portfolio_df['price'] * portfolio_df['shares']
    
    print("=== 原始投资组合 ===")
    print(portfolio_df.to_string(index=False))
    print(f"\n投资组合总价值: ${portfolio_df['value'].sum():,.2f}")
    print(f"股票数量: {len(portfolio_df)}")

    # 使用重构后的计算器，演示清仓功能
    config = RebalanceConfig(
        min_trade_amount=100.0, 
        cash_adjustment=0.0,
        liquidation_stocks=['TSLA']  # 清仓NVDA和TSLA，剩余3只股票等权重
    )
    calculator = EqualWeightCalculator(config)

    # 传递原始数据（不包含value列）给计算器
    input_data = portfolio_df[['symbol', 'price', 'shares']].copy()
    result = calculator.calculate(input_data)
    if result is not None:
        print("\n=== 交易指令 ===")
        print(result.to_string(index=False))
        
        # 导出到Excel
        excel_path = calculator.export_to_excel(result, portfolio_df)
        print(f"\n[Excel] 交易指令已导出到: {excel_path}")
    else:
        print("\n=== 无需再平衡 ===")
        
        # 即使无需再平衡，也导出当前状态
        excel_path = calculator.export_to_excel(None, portfolio_df)
        print(f"\n[Excel] 投资组合状态已导出到: {excel_path}")


def main():
    """主函数 - 纯本地MHTML文件模式"""
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('portfolio_rebalancing.log', encoding='utf-8')
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
        
    print(f"\n本地文件模式 - 文件: {file_path}")
    print("=" * 50)
    
    # 创建配置（支持清仓功能演示）
    config = RebalanceConfig(
        min_trade_amount=200.0,
        cash_adjustment=-20000,
        liquidation_stocks=[]  # 可以在这里添加要清仓的股票
    )
    
    # 执行数据处理+再平衡
    rebalancer = PortfolioRebalancer(config)
    trades_df, excel_path = rebalancer.scrape_and_rebalance(file_path)
    
    if trades_df is not None and not trades_df.empty:
        print("\n交易指令预览:")
        print(trades_df.to_string(index=False))
        print(f"\nExcel报告已保存: {excel_path}")
    else:
        print("\n无需再平衡或数据处理失败")
    
    print("\n使用说明:")
    print("- 默认模式: python src/portfolio_rebalancing.py")
    print("- 指定文件: python src/portfolio_rebalancing.py <MHTML文件路径>")
    print("- 清仓功能: 修改代码中的 liquidation_stocks 参数")
    print("- 支持格式: .mhtml, .html 文件")


def quick_scrape_and_rebalance(file_path: str, liquidation_stocks: List[str] = None) -> None:
    """
    快速本地文件解析和再平衡的便捷函数
    
    Args:
        file_path: 本地MHTML/HTML文件路径
        liquidation_stocks: 要清仓的股票代码列表
    """
    config = RebalanceConfig(
        min_trade_amount=100.0,
        cash_adjustment=0.0,
        liquidation_stocks=liquidation_stocks or []
    )
    
    rebalancer = PortfolioRebalancer(config)
    trades_df, excel_path = rebalancer.scrape_and_rebalance(file_path)
    
    print(f"\n完成! Excel报告: {excel_path}")
    return trades_df, excel_path


if __name__ == "__main__":
    main()
