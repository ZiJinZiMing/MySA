#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('portfolio_data_20250717_224704.csv')
stock_rows = df[df['symbol'] != 'CASH']
print(f'总股票数: {len(stock_rows)}')
print(f'投资组合总价值: {df["value"].sum():.2f}')
print(f'股票总价值: {stock_rows["value"].sum():.2f}')
print(f'等权重目标价值: {stock_rows["value"].sum() / len(stock_rows):.2f}')
print()
print('STX, LITE, WLDN 的详细信息:')
for symbol in ['STX', 'LITE', 'WLDN']:
    stock = stock_rows[stock_rows['symbol'] == symbol]
    if not stock.empty:
        current_value = stock['value'].iloc[0]
        target_value = stock_rows['value'].sum() / len(stock_rows)
        difference = target_value - current_value
        price = stock['price'].iloc[0]
        shares_to_buy = difference / price
        shares = int(shares_to_buy)
        print(f'{symbol}: 当前价值={current_value:.2f}, 目标价值={target_value:.2f}, 差额={difference:.2f}, 价格={price:.2f}, 需买入={shares_to_buy:.2f}股, 整数股={shares}')