#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合数据解析模块 (Portfolio Data Parser)

统一的SeekingAlpha投资组合HTML/MHTML文件解析器，提供标准化的股票数据提取功能。
支持从本地HTML文件中提取股票基础信息（symbol, price, shares）和扩展信息（beta, sector）。

主要组件：
1. StockData: 股票数据结构
2. PortfolioHTMLParser: HTML解析器
3. 数据提取和转换工具函数

支持的数据字段：
- symbol: 股票代码
- price: 当前价格  
- shares: 持股数量
- beta: Beta系数（可选）
- sector: GICS行业分类（可选）

作者: Claude
版本: 1.0
"""

import pandas as pd
import logging
import os
import re
import quopri
from typing import Dict, Optional, List
from dataclasses import dataclass

# HTML解析导入
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    """股票数据结构"""
    symbol: str
    price: float
    shares: float
    beta: Optional[float] = None
    sector: Optional[str] = None
    
    @property
    def value(self) -> float:
        """股票总价值"""
        return self.price * self.shares
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'shares': self.shares,
            'value': self.value,
            'beta': self.beta,
            'sector': self.sector
        }


class PortfolioHTMLParser:
    """统一的投资组合HTML解析器"""
    
    def __init__(self, extract_beta: bool = False, extract_sector: bool = False):
        """
        初始化解析器
        
        Args:
            extract_beta: 是否提取Beta值
            extract_sector: 是否提取行业信息
        """
        self.extract_beta = extract_beta
        self.extract_sector = extract_sector
        self.logger = logging.getLogger(__name__)
    
    def parse_file(self, file_path: str) -> List[StockData]:
        """
        从HTML/MHTML文件解析股票数据
        
        Args:
            file_path: 本地MHTML或HTML文件路径
            
        Returns:
            股票数据列表
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return []
        
        self.logger.info(f"开始解析投资组合文件: {file_path}")
        
        # 读取文件内容
        html_content = self._read_mhtml_file(file_path)
        if not html_content:
            self.logger.error("无法读取文件内容")
            return []
        
        # 解析HTML内容
        soup = BeautifulSoup(html_content, 'html.parser')
        stocks = self._parse_portfolio_data(soup)
        
        self.logger.info(f"成功解析 {len(stocks)} 只股票数据")
        return stocks
    
    def to_dataframe(self, stocks: List[StockData]) -> pd.DataFrame:
        """
        转换股票数据为DataFrame格式
        
        Args:
            stocks: 股票数据列表
            
        Returns:
            投资组合DataFrame
        """
        if not stocks:
            return pd.DataFrame()
        
        data = [stock.to_dict() for stock in stocks]
        return pd.DataFrame(data)
    
    def _read_mhtml_file(self, file_path: str) -> Optional[str]:
        """
        读取MHTML文件并提取HTML内容
        
        Args:
            file_path: MHTML文件路径
            
        Returns:
            HTML内容字符串或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 如果是普通HTML文件，直接返回
            if file_path.lower().endswith('.html'):
                return content
            
            # 如果是MHTML文件，需要提取HTML部分
            if file_path.lower().endswith('.mhtml'):
                return self._extract_html_from_mhtml(content)
            
            # 尝试直接解析
            return content
            
        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            return None
    
    def _extract_html_from_mhtml(self, mhtml_content: str) -> Optional[str]:
        """
        从MHTML内容中提取HTML部分
        
        Args:
            mhtml_content: MHTML文件完整内容
            
        Returns:
            HTML内容字符串或None
        """
        try:
            # MHTML文件格式：多个MIME部分，HTML通常在第一个或第二个部分
            # 寻找包含quoted-printable编码的HTML内容
            html_section_pattern = r'Content-Type: text/html.*?Content-Transfer-Encoding: quoted-printable.*?\n\n(.*?)(?=\n--.*?|\Z)'
            match = re.search(html_section_pattern, mhtml_content, re.DOTALL | re.IGNORECASE)
            
            if match:
                encoded_html = match.group(1)
                # 尝试多种解码方法
                try:
                    # 方法1: 使用latin1编码（通常适用于MHTML）
                    decoded_html = quopri.decodestring(encoded_html.encode()).decode('latin1')
                    if '<html' in decoded_html.lower():
                        self.logger.info("成功从MHTML中提取并解码HTML内容 (latin1)")
                        return decoded_html
                except Exception:
                    pass
                
                try:
                    # 方法2: 使用utf-8编码
                    decoded_html = quopri.decodestring(encoded_html.encode()).decode('utf-8')
                    if '<html' in decoded_html.lower():
                        self.logger.info("成功从MHTML中提取并解码HTML内容 (utf-8)")
                        return decoded_html
                except Exception:
                    pass
                
                try:
                    # 方法3: 直接使用原始内容
                    if '<html' in encoded_html.lower():
                        self.logger.info("成功从MHTML中提取HTML内容 (原始)")
                        return encoded_html
                except Exception:
                    pass
            
            # 备用方案：寻找直接的HTML内容
            patterns = [
                r'Content-Type: text/html.*?\n\n(.*?)(?=\n--.*?Content-Type|\nFrom:|\Z)',
                r'<html.*?</html>',
                r'<!DOCTYPE html.*?</html>',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, mhtml_content, re.DOTALL | re.IGNORECASE)
                if match:
                    html_content = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    if '<html' in html_content.lower():
                        self.logger.info("成功从MHTML中提取HTML内容")
                        return html_content
            
            self.logger.warning("无法从MHTML中提取HTML内容")
            return None
            
        except Exception as e:
            self.logger.error(f"从MHTML提取HTML失败: {e}")
            return None
    
    def _parse_portfolio_data(self, soup) -> List[StockData]:
        """
        解析投资组合数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            股票数据列表
        """
        try:
            # 直接查找所有股票名称元素
            ticker_elements = soup.find_all(attrs={'data-test-id': 'portfolio-ticker-name'})
            self.logger.info(f"找到 {len(ticker_elements)} 个股票ticker元素")
            
            stocks = []
            
            for ticker_elem in ticker_elements:
                symbol = ticker_elem.get_text(strip=True)
                
                # 清理股票名称
                symbol = symbol.replace(' ', '').strip()

                # 跳过现金项目
                if symbol.upper() in ['CASH', 'CURRENCY']:
                    self.logger.debug(f"跳过现金项目: {symbol}")
                    continue

                # 跳过空或无效的股票名称
                # 注意：美国股市存在合法的单字符股票代码（如 W, F, X, C, T, V 等）
                if not symbol or len(symbol.strip()) == 0:
                    self.logger.debug(f"跳过无效股票名称: '{symbol}'")
                    continue

                # 验证股票代码格式（允许字母、数字、点、连字符）
                if not re.match(r'^[A-Za-z0-9.\-]+$', symbol):
                    self.logger.debug(f"跳过格式无效的股票代码: '{symbol}'")
                    continue
                
                # 提取股票数据
                stock_data = self._extract_stock_data(soup, ticker_elem, symbol)
                if stock_data:
                    stocks.append(stock_data)
                    beta_info = f"Beta: {stock_data.beta}" if stock_data.beta is not None else "Beta: N/A"
                    sector_info = f"Sector: {stock_data.sector}" if stock_data.sector else "Sector: N/A"
                    self.logger.debug(f"提取: {symbol} - ${stock_data.price:.2f} × {stock_data.shares:.0f} ({beta_info}) ({sector_info})")
            
            # 移除重复项
            unique_stocks = []
            seen_symbols = set()
            
            for stock in stocks:
                if stock.symbol not in seen_symbols:
                    unique_stocks.append(stock)
                    seen_symbols.add(stock.symbol)
                else:
                    self.logger.debug(f"移除重复股票: {stock.symbol}")
            
            if len(stocks) != len(unique_stocks):
                self.logger.info(f"移除 {len(stocks) - len(unique_stocks)} 条重复记录")
            
            return unique_stocks
            
        except Exception as e:
            self.logger.error(f"数据解析失败: {e}")
            return []
    
    def _extract_stock_data(self, soup, ticker_elem, symbol) -> Optional[StockData]:
        """
        从HTML中提取单只股票的完整数据
        
        Args:
            soup: BeautifulSoup对象
            ticker_elem: 股票名称元素
            symbol: 股票代码
            
        Returns:
            StockData对象或None
        """
        try:
            # 找到股票所在的表格行
            row_elem = ticker_elem
            for _ in range(10):  # 向上找到tr元素
                row_elem = row_elem.parent
                if not row_elem:
                    break
                if row_elem.name == 'tr':
                    break
            
            if not row_elem or row_elem.name != 'tr':
                self.logger.debug(f"股票 {symbol} 未找到表格行元素")
                return None
            
            # 提取基础数据
            basic_data = self._extract_basic_data(row_elem, symbol)
            if not basic_data:
                return None
            
            # 提取扩展数据
            extended_data = {}
            if self.extract_beta:
                extended_data['beta'] = self._extract_beta(row_elem, symbol)
            
            if self.extract_sector:
                extended_data['sector'] = self._extract_sector(row_elem, symbol)
            
            # 创建StockData对象
            stock_data = StockData(
                symbol=basic_data['symbol'],
                price=basic_data['price'],
                shares=basic_data['shares'],
                beta=extended_data.get('beta'),
                sector=extended_data.get('sector')
            )
            
            return stock_data
            
        except Exception as e:
            self.logger.debug(f"提取股票 {symbol} 数据失败: {e}")
            return None
    
    def _extract_basic_data(self, row_elem, symbol) -> Optional[Dict]:
        """提取基础股票数据（价格、股数）"""
        try:
            data = {'symbol': symbol}
            
            # 在表格行的所有td元素中查找数据
            td_elements = row_elem.find_all(['td', 'th'])
            
            for td in td_elements:
                # 查找价格
                if 'price' not in data:
                    price_selectors = [
                        {'data-test-id': 'portfolio-ticker-price-price'},
                        {'data-test-id': 'portfolio-ticker-sub-price-price'},
                        {'data-test-id': 'price'},
                        {'data-test-id': 'portfolio-price'}
                    ]
                    for selector in price_selectors:
                        price_elem = td.find(attrs=selector)
                        if price_elem:
                            try:
                                price_text = price_elem.get_text(strip=True)
                                if price_text and price_text != '-':
                                    price_clean = re.sub(r'[^\d.-]', '', price_text)
                                    if price_clean:
                                        data['price'] = float(price_clean)
                                        self.logger.debug(f"股票 {symbol} 找到价格: {data['price']}")
                                        break
                            except Exception as ex:
                                self.logger.debug(f"解析价格失败 {symbol}: {ex}")
                
                # 查找持股数
                if 'shares' not in data:
                    shares_selectors = [
                        {'data-test-id': 'share-value'},
                        {'data-test-id': 'portfolio-ticker-shares'},
                        {'data-test-id': 'shares'},
                        {'data-test-id': 'portfolio-shares'}
                    ]
                    for selector in shares_selectors:
                        shares_elem = td.find(attrs=selector)
                        if shares_elem:
                            try:
                                shares_text = shares_elem.get_text(strip=True)
                                if shares_text and shares_text != '-':
                                    shares_clean = re.sub(r'[^\d.-]', '', shares_text)
                                    if shares_clean:
                                        data['shares'] = float(shares_clean)
                                        self.logger.debug(f"股票 {symbol} 找到股数: {data['shares']}")
                                        break
                            except Exception as ex:
                                self.logger.debug(f"解析股数失败 {symbol}: {ex}")
            
            # 如果在表格中找不到，尝试文本模式匹配
            if 'price' not in data or 'shares' not in data:
                self.logger.debug(f"股票 {symbol} 在表格中未找到所有数据，尝试文本解析")
                self._extract_by_text_pattern(row_elem, data, symbol)
            
            # 验证数据完整性
            if 'price' in data and 'shares' in data:
                return data
            else:
                missing = [field for field in ['price', 'shares'] if field not in data]
                self.logger.debug(f"股票 {symbol} 缺失字段: {missing}")
                return None
                
        except Exception as e:
            self.logger.debug(f"提取基础数据失败 {symbol}: {e}")
            return None
    
    def _extract_beta(self, row_elem, symbol) -> Optional[float]:
        """提取Beta值"""
        try:
            td_elements = row_elem.find_all(['td', 'th'])
            
            for td in td_elements:
                beta_selectors = [
                    {'data-test-id': 'portfolio-ticker-price-beta24m'},
                    {'data-test-id': 'beta24'},
                    {'data-test-id': 'portfolio-ticker-beta24m'},
                    {'data-test-id': 'beta'},
                    {'data-test-id': 'portfolio-beta'}
                ]
                for selector in beta_selectors:
                    beta_elem = td.find(attrs=selector)
                    if beta_elem:
                        try:
                            beta_text = beta_elem.get_text(strip=True)
                            if beta_text and beta_text != '-' and beta_text != 'N/A':
                                beta = float(beta_text.replace(',', ''))
                                self.logger.debug(f"股票 {symbol} 找到Beta: {beta}")
                                return beta
                        except Exception as ex:
                            self.logger.debug(f"解析Beta失败 {symbol}: {ex}")
                            continue
            
            self.logger.debug(f"股票 {symbol} 未找到Beta值")
            return None
            
        except Exception as e:
            self.logger.debug(f"提取Beta失败 {symbol}: {e}")
            return None
    
    def _extract_sector(self, row_elem, symbol) -> Optional[str]:
        """提取GICS行业分类"""
        try:
            valid_sectors = [
                'Information Technology', 'Financials', 'Industrials', 
                'Consumer Discretionary', 'Materials', 'Consumer Staples', 
                'Energy', 'Health Care', 'Utilities', 'Communication Services', 
                'Real Estate'
            ]
            
            # 方法1: 在所有span元素中查找
            all_spans = row_elem.find_all('span')
            for span in all_spans:
                span_text = span.get_text(strip=True)
                if span_text in valid_sectors:
                    self.logger.debug(f"股票 {symbol} 在span中找到Sector: {span_text}")
                    return span_text
            
            # 方法2: 搜索整个row的文本内容
            row_text = row_elem.get_text()
            for sector in valid_sectors:
                if sector in row_text:
                    self.logger.debug(f"股票 {symbol} 在row文本中找到Sector: {sector}")
                    return sector
            
            # 方法3: 查找所有文本节点
            all_text_elements = row_elem.find_all(text=True)
            for text in all_text_elements:
                text_stripped = text.strip()
                if text_stripped in valid_sectors:
                    self.logger.debug(f"股票 {symbol} 在文本节点中找到Sector: {text_stripped}")
                    return text_stripped
            
            self.logger.debug(f"股票 {symbol} 未找到sector信息")
            return None
            
        except Exception as e:
            self.logger.debug(f"提取sector失败 {symbol}: {e}")
            return None
    
    def _extract_by_text_pattern(self, row_elem, data, symbol):
        """通过文本模式匹配提取缺失的数据"""
        if not row_elem:
            return
            
        try:
            row_text = row_elem.get_text()
            
            # 价格模式 (通常在$符号后面)
            if 'price' not in data:
                price_patterns = [
                    r'\$\s*([0-9,]+\.?[0-9]*)',
                    r'([0-9,]+\.?[0-9]*)\s*\$',
                    r'([0-9]+\.[0-9]{2})'
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, row_text)
                    if matches:
                        try:
                            price = float(matches[0].replace(',', ''))
                            if 0.01 <= price <= 10000:  # 合理的价格范围
                                data['price'] = price
                                self.logger.debug(f"股票 {symbol} 通过模式匹配找到价格: {price}")
                                break
                        except:
                            continue
            
            # 股数模式 (通常是较大的整数)
            if 'shares' not in data:
                numbers = re.findall(r'\b([0-9,]+)\b', row_text)
                for num_str in numbers:
                    try:
                        num = int(num_str.replace(',', ''))
                        if 1 <= num <= 1000000:  # 合理的股数范围
                            data['shares'] = float(num)
                            self.logger.debug(f"股票 {symbol} 通过模式匹配找到股数: {num}")
                            break
                    except:
                        continue
                        
        except Exception as e:
            self.logger.debug(f"文本模式匹配失败 {symbol}: {e}")


# 便捷函数
def parse_portfolio_basic(file_path: str) -> pd.DataFrame:
    """
    解析基础投资组合数据（仅symbol, price, shares）
    
    Args:
        file_path: HTML/MHTML文件路径
        
    Returns:
        基础投资组合DataFrame
    """
    parser = PortfolioHTMLParser(extract_beta=False, extract_sector=False)
    stocks = parser.parse_file(file_path)
    return parser.to_dataframe(stocks)


def parse_portfolio_with_beta(file_path: str) -> pd.DataFrame:
    """
    解析包含Beta的投资组合数据
    
    Args:
        file_path: HTML/MHTML文件路径
        
    Returns:
        包含Beta的投资组合DataFrame
    """
    parser = PortfolioHTMLParser(extract_beta=True, extract_sector=True)
    stocks = parser.parse_file(file_path)
    return parser.to_dataframe(stocks)


def parse_portfolio_full(file_path: str) -> pd.DataFrame:
    """
    解析完整投资组合数据（包含所有可用字段）
    
    Args:
        file_path: HTML/MHTML文件路径
        
    Returns:
        完整投资组合DataFrame
    """
    parser = PortfolioHTMLParser(extract_beta=True, extract_sector=True)
    stocks = parser.parse_file(file_path)
    return parser.to_dataframe(stocks)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"测试解析文件: {file_path}")
        
        # 测试基础解析
        df_basic = parse_portfolio_basic(file_path)
        print(f"\n基础数据解析结果: {len(df_basic)} 只股票")
        print(df_basic.head())
        
        # 测试完整解析
        df_full = parse_portfolio_full(file_path)
        print(f"\n完整数据解析结果: {len(df_full)} 只股票")
        print(df_full.head())
        
    else:
        print("使用方法: python portfolio_data.py <HTML文件路径>")
        print("示例: python portfolio_data.py src/QuantPortfolios.html")