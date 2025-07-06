#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式数据导出器
支持CSV、JSON、数据库(SQLite)、Protocol Buffers等多种格式
"""

import json
import sqlite3
import pickle
import pandas as pd
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MultiFormatExporter:
    """多格式数据导出器"""
    
    def __init__(self, base_filename: str = None):
        """
        初始化导出器
        
        Args:
            base_filename: 基础文件名，不包含扩展名
        """
        if base_filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_filename = f"stock_analysis_{timestamp}"
        
        self.base_filename = base_filename
        self.timestamp = datetime.now().isoformat()
    
    def export_all_formats(self, stocks_data: List[Dict], export_formats: List[str] = None):
        """
        导出到所有支持的格式
        
        Args:
            stocks_data: 股票数据列表
            export_formats: 要导出的格式列表，None表示导出所有格式
        """
        if export_formats is None:
            export_formats = ['csv', 'json', 'sqlite', 'pickle', 'excel']
        
        results = {}
        
        for format_name in export_formats:
            try:
                if format_name == 'csv':
                    results['csv'] = self.export_to_csv(stocks_data)
                elif format_name == 'json':
                    results['json'] = self.export_to_json(stocks_data)
                elif format_name == 'sqlite':
                    results['sqlite'] = self.export_to_sqlite(stocks_data)
                elif format_name == 'pickle':
                    results['pickle'] = self.export_to_pickle(stocks_data)
                elif format_name == 'excel':
                    results['excel'] = self.export_to_excel(stocks_data)
                else:
                    logger.warning(f"不支持的导出格式: {format_name}")
            
            except Exception as e:
                logger.error(f"导出{format_name}格式失败: {e}")
                results[format_name] = None
        
        return results
    
    def export_to_csv(self, stocks_data: List[Dict]) -> Dict[str, str]:
        """导出到CSV格式"""
        try:
            csv_files = {}
            
            # 1. 主要汇总数据
            summary_data = []
            for stock in stocks_data:
                rating_history = stock.get('rating_history', [])
                rating_analysis = stock.get('rating_analysis', {})
                
                row = {
                    'Symbol': stock.get('symbol', 'N/A'),
                    'Price': stock.get('price', 'N/A'),
                    'QuantRating': stock.get('quant_rating', 'N/A'),
                    'SectorIndustry': stock.get('sector_industry', 'N/A'),
                    'MarketCap': stock.get('market_cap', 'N/A'),
                    'Exchange': stock.get('exchange', 'N/A'),
                    'TotalRatingDays': rating_analysis.get('total_days', 'N/A'),
                    'CurrentRating': rating_history[0].get('rating', 'N/A') if rating_history else 'N/A',
                    'CurrentConsecutiveDays': rating_history[0].get('consecutive_days', 'N/A') if rating_history else 'N/A',
                    'MaxConsecutiveDays': rating_analysis.get('max_consecutive_days', 'N/A'),
                    'MostCommonRating': rating_analysis.get('most_common_rating', 'N/A')
                }
                summary_data.append(row)
            
            summary_filename = f"{self.base_filename}_summary.csv"
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_csv(summary_filename, index=False, encoding='utf-8-sig')
            csv_files['summary'] = summary_filename
            
            # 2. 详细评级历史
            detailed_data = []
            for stock in stocks_data:
                symbol = stock.get('symbol', 'Unknown')
                for record in stock.get('rating_history', []):
                    detailed_data.append({
                        'Symbol': symbol,
                        'Date': record.get('date', 'N/A'),
                        'Price': record.get('price', 'N/A'),
                        'Rating': record.get('rating', 'N/A'),
                        'Score': record.get('score', 'N/A'),
                        'ConsecutiveDays': record.get('consecutive_days', 'N/A'),
                        'PositionFromLatest': record.get('position_from_latest', 'N/A')
                    })
            
            if detailed_data:
                detailed_filename = f"{self.base_filename}_detailed_history.csv"
                df_detailed = pd.DataFrame(detailed_data)
                df_detailed.to_csv(detailed_filename, index=False, encoding='utf-8-sig')
                csv_files['detailed_history'] = detailed_filename
            
            logger.info(f"✅ CSV导出完成: {csv_files}")
            return csv_files
            
        except Exception as e:
            logger.error(f"❌ CSV导出失败: {e}")
            return {}
    
    def export_to_json(self, stocks_data: List[Dict]) -> str:
        """导出到JSON格式"""
        try:
            # 准备JSON数据结构
            json_data = {
                'export_info': {
                    'timestamp': self.timestamp,
                    'total_stocks': len(stocks_data),
                    'format_version': '2.0'
                },
                'stocks': []
            }
            
            for stock in stocks_data:
                stock_data = {
                    'basic_info': {
                        'symbol': stock.get('symbol', 'N/A'),
                        'price': stock.get('price', 'N/A'),
                        'quant_rating': stock.get('quant_rating', 'N/A'),
                        'sector_industry': stock.get('sector_industry', 'N/A'),
                        'market_cap': stock.get('market_cap', 'N/A'),
                        'exchange': stock.get('exchange', 'N/A')
                    },
                    'rating_analysis': stock.get('rating_analysis', {}),
                    'rating_history': stock.get('rating_history', [])
                }
                json_data['stocks'].append(stock_data)
            
            # 保存JSON文件
            json_filename = f"{self.base_filename}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ JSON导出完成: {json_filename}")
            return json_filename
            
        except Exception as e:
            logger.error(f"❌ JSON导出失败: {e}")
            return ""
    
    def export_to_sqlite(self, stocks_data: List[Dict]) -> str:
        """导出到SQLite数据库"""
        try:
            db_filename = f"{self.base_filename}.db"
            conn = sqlite3.connect(db_filename)
            cursor = conn.cursor()
            
            # 创建股票基础信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price TEXT,
                    quant_rating TEXT,
                    sector_industry TEXT,
                    market_cap TEXT,
                    exchange TEXT,
                    total_rating_days INTEGER,
                    max_consecutive_days INTEGER,
                    most_common_rating TEXT,
                    created_at TEXT
                )
            ''')
            
            # 创建评级历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rating_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_id INTEGER,
                    symbol TEXT NOT NULL,
                    date TEXT,
                    price TEXT,
                    rating TEXT,
                    score TEXT,
                    consecutive_days INTEGER,
                    position_from_latest INTEGER,
                    FOREIGN KEY (stock_id) REFERENCES stocks (id)
                )
            ''')
            
            # 创建分析结果表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rating_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_id INTEGER,
                    symbol TEXT NOT NULL,
                    total_days INTEGER,
                    max_consecutive_days INTEGER,
                    current_rating TEXT,
                    current_rating_streak INTEGER,
                    most_common_rating TEXT,
                    rating_distribution TEXT,
                    FOREIGN KEY (stock_id) REFERENCES stocks (id)
                )
            ''')
            
            # 插入数据
            for stock in stocks_data:
                # 插入股票基础信息
                rating_analysis = stock.get('rating_analysis', {})
                cursor.execute('''
                    INSERT INTO stocks (
                        symbol, price, quant_rating, sector_industry, market_cap, exchange,
                        total_rating_days, max_consecutive_days, most_common_rating, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock.get('symbol', 'N/A'),
                    stock.get('price', 'N/A'),
                    stock.get('quant_rating', 'N/A'),
                    stock.get('sector_industry', 'N/A'),
                    stock.get('market_cap', 'N/A'),
                    stock.get('exchange', 'N/A'),
                    rating_analysis.get('total_days', 0),
                    rating_analysis.get('max_consecutive_days', 0),
                    rating_analysis.get('most_common_rating', 'N/A'),
                    self.timestamp
                ))
                
                stock_id = cursor.lastrowid
                symbol = stock.get('symbol', 'Unknown')
                
                # 插入评级历史
                for record in stock.get('rating_history', []):
                    cursor.execute('''
                        INSERT INTO rating_history (
                            stock_id, symbol, date, price, rating, score,
                            consecutive_days, position_from_latest
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_id,
                        symbol,
                        record.get('date', 'N/A'),
                        record.get('price', 'N/A'),
                        record.get('rating', 'N/A'),
                        record.get('score', 'N/A'),
                        record.get('consecutive_days', 0),
                        record.get('position_from_latest', 0)
                    ))
                
                # 插入分析结果
                if rating_analysis:
                    cursor.execute('''
                        INSERT INTO rating_analysis (
                            stock_id, symbol, total_days, max_consecutive_days,
                            current_rating, current_rating_streak, most_common_rating,
                            rating_distribution
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_id,
                        symbol,
                        rating_analysis.get('total_days', 0),
                        rating_analysis.get('max_consecutive_days', 0),
                        rating_analysis.get('current_rating', 'N/A'),
                        rating_analysis.get('current_rating_streak', 0),
                        rating_analysis.get('most_common_rating', 'N/A'),
                        json.dumps(rating_analysis.get('rating_distribution', {}))
                    ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ SQLite数据库导出完成: {db_filename}")
            return db_filename
            
        except Exception as e:
            logger.error(f"❌ SQLite导出失败: {e}")
            return ""
    
    def export_to_pickle(self, stocks_data: List[Dict]) -> str:
        """导出到Pickle格式（Python原生序列化）"""
        try:
            pickle_data = {
                'export_info': {
                    'timestamp': self.timestamp,
                    'total_stocks': len(stocks_data),
                    'format_version': '2.0'
                },
                'stocks_data': stocks_data
            }
            
            pickle_filename = f"{self.base_filename}.pkl"
            with open(pickle_filename, 'wb') as f:
                pickle.dump(pickle_data, f)
            
            logger.info(f"✅ Pickle导出完成: {pickle_filename}")
            return pickle_filename
            
        except Exception as e:
            logger.error(f"❌ Pickle导出失败: {e}")
            return ""
    
    def export_to_excel(self, stocks_data: List[Dict]) -> str:
        """导出到Excel格式（多工作表）"""
        try:
            excel_filename = f"{self.base_filename}.xlsx"
            
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                # 工作表1: 股票汇总
                summary_data = []
                for stock in stocks_data:
                    rating_history = stock.get('rating_history', [])
                    rating_analysis = stock.get('rating_analysis', {})
                    
                    row = {
                        'Symbol': stock.get('symbol', 'N/A'),
                        'Price': stock.get('price', 'N/A'),
                        'QuantRating': stock.get('quant_rating', 'N/A'),
                        'SectorIndustry': stock.get('sector_industry', 'N/A'),
                        'MarketCap': stock.get('market_cap', 'N/A'),
                        'Exchange': stock.get('exchange', 'N/A'),
                        'TotalRatingDays': rating_analysis.get('total_days', 'N/A'),
                        'CurrentRating': rating_history[0].get('rating', 'N/A') if rating_history else 'N/A',
                        'CurrentConsecutiveDays': rating_history[0].get('consecutive_days', 'N/A') if rating_history else 'N/A',
                        'MaxConsecutiveDays': rating_analysis.get('max_consecutive_days', 'N/A'),
                        'MostCommonRating': rating_analysis.get('most_common_rating', 'N/A')
                    }
                    summary_data.append(row)
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Stock_Summary', index=False)
                
                # 工作表2: 详细评级历史
                detailed_data = []
                for stock in stocks_data:
                    symbol = stock.get('symbol', 'Unknown')
                    for record in stock.get('rating_history', []):
                        detailed_data.append({
                            'Symbol': symbol,
                            'Date': record.get('date', 'N/A'),
                            'Price': record.get('price', 'N/A'),
                            'Rating': record.get('rating', 'N/A'),
                            'Score': record.get('score', 'N/A'),
                            'ConsecutiveDays': record.get('consecutive_days', 'N/A'),
                            'PositionFromLatest': record.get('position_from_latest', 'N/A')
                        })
                
                if detailed_data:
                    df_detailed = pd.DataFrame(detailed_data)
                    df_detailed.to_excel(writer, sheet_name='Rating_History', index=False)
                
                # 工作表3: 评级分析统计
                analysis_data = []
                for stock in stocks_data:
                    rating_analysis = stock.get('rating_analysis', {})
                    if rating_analysis:
                        analysis_data.append({
                            'Symbol': stock.get('symbol', 'N/A'),
                            'TotalDays': rating_analysis.get('total_days', 'N/A'),
                            'MaxConsecutiveDays': rating_analysis.get('max_consecutive_days', 'N/A'),
                            'CurrentRating': rating_analysis.get('current_rating', 'N/A'),
                            'CurrentRatingStreak': rating_analysis.get('current_rating_streak', 'N/A'),
                            'MostCommonRating': rating_analysis.get('most_common_rating', 'N/A'),
                            'RatingDistribution': str(rating_analysis.get('rating_distribution', {}))
                        })
                
                if analysis_data:
                    df_analysis = pd.DataFrame(analysis_data)
                    df_analysis.to_excel(writer, sheet_name='Rating_Analysis', index=False)
            
            logger.info(f"✅ Excel导出完成: {excel_filename}")
            return excel_filename
            
        except Exception as e:
            logger.error(f"❌ Excel导出失败: {e}")
            return ""
    
    @staticmethod
    def load_from_json(json_filename: str) -> Optional[List[Dict]]:
        """从JSON文件加载数据"""
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('stocks', [])
        except Exception as e:
            logger.error(f"从JSON加载失败: {e}")
            return None
    
    @staticmethod
    def load_from_pickle(pickle_filename: str) -> Optional[List[Dict]]:
        """从Pickle文件加载数据"""
        try:
            with open(pickle_filename, 'rb') as f:
                data = pickle.load(f)
            return data.get('stocks_data', [])
        except Exception as e:
            logger.error(f"从Pickle加载失败: {e}")
            return None


def demo_multi_format_export():
    """演示多格式导出功能"""
    # 模拟股票数据
    sample_data = [
        {
            'symbol': 'AEVA',
            'price': '32.89',
            'quant_rating': '4.99',
            'sector_industry': 'Electronic Equipment',
            'market_cap': '1.81B',
            'exchange': 'NASDAQ',
            'rating_history': [
                {
                    'date': '07/03/2025',
                    'price': '32.73',
                    'rating': 'Strong Buy',
                    'score': '4.99',
                    'consecutive_days': 38,
                    'position_from_latest': 1
                },
                {
                    'date': '07/02/2025',
                    'price': '30.88',
                    'rating': 'Strong Buy',
                    'score': '4.99',
                    'consecutive_days': 37,
                    'position_from_latest': 2
                }
            ],
            'rating_analysis': {
                'total_days': 207,
                'max_consecutive_days': 124,
                'current_rating': 'Strong Buy',
                'current_rating_streak': 38,
                'most_common_rating': 'Hold',
                'rating_distribution': {'Strong Buy': 45, 'Hold': 162}
            }
        }
    ]
    
    # 导出到所有格式
    exporter = MultiFormatExporter("demo_multi_format")
    results = exporter.export_all_formats(sample_data)
    
    print("📁 多格式导出结果:")
    for format_name, filename in results.items():
        if filename:
            print(f"  ✅ {format_name.upper()}: {filename}")
        else:
            print(f"  ❌ {format_name.upper()}: 导出失败")


if __name__ == "__main__":
    demo_multi_format_export()