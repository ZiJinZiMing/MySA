# -*- coding: utf-8 -*-
"""
MSTR/BTC 溢价监控脚本
从 strategy.com 获取 BTC per share 数据
使用 Finnhub API 获取实时价格数据
计算 MSTR 相对于 BTC 持有量的溢价率
"""

import sys
import io
import requests
import time
import re
import os
import threading
import sqlite3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# 设置标准输出编码为 UTF-8，避免 Windows 下的编码问题
# 同时禁用输出缓冲，确保实时显示
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except:
        pass

# 强制禁用输出缓冲
os.environ['PYTHONUNBUFFERED'] = '1'

# 配置参数
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g")
STRATEGY_URL = "https://www.strategy.com/"
CHROME_DEBUG_PORT = 9222
TICK_INTERVAL = 10  # 主循环更新间隔（秒）
BTC_PER_SHARE_UPDATE_INTERVAL = 30000  # BTC per share 更新间隔（秒，500分钟）
DB_FILE = "mstr_data.db"  # SQLite 数据库文件，用于可视化

# 全局变量
btc_per_share_global = None
ev_adjustment_global = None  # (Debt + Pref - Cash) / Shares，用于 Enterprise Value 计算
btc_per_share_lock = threading.Lock()


def get_btc_per_share_from_strategy():
    """
    使用 Selenium 从 strategy.com 首页获取 BTC per share 数据

    返回:
        tuple: (btc_per_share, ev_adjustment) 或 (None, None)
        - btc_per_share: 每股 MSTR 含有的 BTC 数量
        - ev_adjustment: (Debt + Pref - Cash) / Shares，用于计算 Enterprise Value
    """
    driver = None
    try:
        # 尝试连接到已运行的 Chrome 浏览器实例
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")
        print(f"正在连接到 Chrome 浏览器 (端口 {CHROME_DEBUG_PORT})...")

        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("成功连接到 Chrome 浏览器")
        except Exception as e:
            print(f"连接 Chrome 浏览器失败: {e}")
            print("尝试启动新的 Chrome 浏览器实例...")

            # 如果连接失败，启动新的无头浏览器实例
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=chrome_options)
            print("成功启动新的 Chrome 浏览器实例")

        # 访问 strategy.com 首页
        print(f"正在访问网站: {STRATEGY_URL}")
        driver.get(STRATEGY_URL)

        # 等待页面加载
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("页面加载完成，等待动态内容...")

        # 等待动态内容加载
        time.sleep(5)

        # 获取页面内容
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        page_text = soup.get_text()

        # 方法1: 查找 "BTC per share" 或类似的文本
        # 常见模式: "BTC per Share: 0.00123456" 或 "0.00123456 BTC/Share"
        patterns = [
            r"BTC\s*per\s*[Ss]hare[\s:]*([0-9.]+)",
            r"([0-9.]+)\s*BTC\s*/\s*[Ss]hare",
            r"BTC\s*/\s*[Ss]hare[\s:]*([0-9.]+)",
            r"Per\s*[Ss]hare[\s:]*([0-9.]+)\s*BTC",
            r"Bitcoin\s*per\s*[Ss]hare[\s:]*([0-9.]+)",
            r"([0-9.]+)\s*₿\s*/?\s*share",  # Bitcoin symbol
            r"₿\s*per\s*share[\s:]*([0-9.]+)",
            r"MSTR.*?([0-9.]{6,})\s*BTC",  # MSTR followed by BTC number
            r"([0-9.]{6,})\s*BTC.*?share",  # Long decimal followed by BTC
        ]

        btc_per_share = None
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                btc_per_share = float(match.group(1))
                print(f"找到 BTC per Share: {btc_per_share:.8f} BTC")
                break

        # 方法2: 如果没找到，尝试查找 sats per share 并转换
        if btc_per_share is None:
            sats_match = re.search(r"[Ss]ats\s*per\s*[Ss]hare[\s:]*([0-9,]+)", page_text)
            if sats_match:
                sats_str = sats_match.group(1).replace(",", "")
                sats_per_share = int(sats_str)
                btc_per_share = sats_per_share / 100000000  # 1 BTC = 100,000,000 sats
                print(f"找到 Sats per Share: {sats_per_share:,} sats")
                print(f"转换为 BTC per Share: {btc_per_share:.8f} BTC")

        # 方法3: 从 BTC Holdings 和 Enterprise Value 计算
        # 注意：正确的溢价计算应该使用 Enterprise Value，而不是 Market Cap
        # 因为 EV = Market Cap + Debt - Cash，更准确反映公司整体价值
        if btc_per_share is None:
            # 提取 BTC 持有量: "BTC₿650,000" 或类似格式
            btc_holdings_match = re.search(r"BTC₿([0-9,]+)", page_text)
            # 提取 Enterprise Value: "Enterprise Value ($M)$69,727" 或类似格式
            enterprise_value_match = re.search(r"Enterprise\s*Value\s*\(\$M\)\$([0-9,]+)", page_text, re.IGNORECASE)
            # 提取 MSTR Price: "MSTR Price$188.39" 或类似格式
            mstr_price_match = re.search(r"MSTR\s*Price\$([0-9,]+\.?[0-9]*)", page_text, re.IGNORECASE)

            if btc_holdings_match and enterprise_value_match and mstr_price_match:
                btc_holdings = float(btc_holdings_match.group(1).replace(",", ""))
                enterprise_value_m = float(enterprise_value_match.group(1).replace(",", ""))  # 单位：百万美元
                mstr_price = float(mstr_price_match.group(1).replace(",", ""))

                # 计算 Shares Outstanding (使用 Market Cap 推算)
                # 但注意：溢价计算将使用 Enterprise Value
                market_cap_match = re.search(r"Market\s*Cap\s*\(\$M\)\$([0-9,]+)", page_text, re.IGNORECASE)

                # 提取 Debt、Preferred Stock 和 USD Reserve (Cash) 用于 Enterprise Value 计算
                # EV = Market Cap + Debt + Preferred Stock - Cash
                debt_match = re.search(r"Debt\s*\(\$M\)\$([0-9,]+)", page_text, re.IGNORECASE)
                pref_match = re.search(r"Pref\s*\(\$M\)\$([0-9,]+)", page_text, re.IGNORECASE)
                usd_reserve_match = re.search(r"USD\s*Reserve\s*\(\$M\)\$([0-9,]+)", page_text, re.IGNORECASE)

                if market_cap_match:
                    market_cap_m = float(market_cap_match.group(1).replace(",", ""))
                    market_cap = market_cap_m * 1_000_000
                    shares_outstanding = market_cap / mstr_price
                    btc_per_share = btc_holdings / shares_outstanding

                    # 计算 debt_cash_pref_adjustment = (Debt + Pref - Cash) / Shares
                    # EV = Market Cap + Debt + Pref - Cash
                    debt_cash_pref_adjustment = 0  # 默认值
                    if debt_match and usd_reserve_match:
                        debt_m = float(debt_match.group(1).replace(",", ""))
                        usd_reserve_m = float(usd_reserve_match.group(1).replace(",", ""))
                        pref_m = 0
                        if pref_match:
                            pref_m = float(pref_match.group(1).replace(",", ""))

                        # EV 调整 = Debt + Pref - Cash
                        ev_adjustment_net = (debt_m + pref_m - usd_reserve_m) * 1_000_000  # 转换为美元
                        debt_cash_pref_adjustment = ev_adjustment_net / shares_outstanding

                        print(f"方法3: 通过计算获得 (使用 Enterprise Value)")
                        print(f"  BTC Holdings: {btc_holdings:,.0f} BTC")
                        print(f"  Enterprise Value: ${enterprise_value_m:,.0f}M")
                        print(f"  Market Cap: ${market_cap_m:,.0f}M")
                        print(f"  Debt: ${debt_m:,.0f}M")
                        if pref_m > 0:
                            print(f"  Preferred Stock: ${pref_m:,.0f}M")
                        print(f"  USD Reserve: ${usd_reserve_m:,.0f}M")
                        print(f"  MSTR Price: ${mstr_price:.2f}")
                        print(f"  Shares Outstanding: {shares_outstanding:,.0f}")
                        print(f"  BTC per Share: {btc_per_share:.8f} BTC")
                        print(f"  EV Adjustment per Share: ${debt_cash_pref_adjustment:.2f}")

                        return btc_per_share, debt_cash_pref_adjustment
                    else:
                        print(f"方法3: 通过计算获得 (未找到 Debt/Cash 数据)")
                        print(f"  BTC Holdings: {btc_holdings:,.0f} BTC")
                        print(f"  Enterprise Value: ${enterprise_value_m:,.0f}M")
                        print(f"  Market Cap: ${market_cap_m:,.0f}M")
                        print(f"  MSTR Price: ${mstr_price:.2f}")
                        print(f"  Shares Outstanding: {shares_outstanding:,.0f}")
                        print(f"  BTC per Share: {btc_per_share:.8f} BTC")
                        print("  警告: 将使用 Market Cap 方式计算溢价（不包含 Debt/Cash）")

                        return btc_per_share, debt_cash_adjustment

        # 如果仍未找到，保存页面内容到文件用于调试
        if btc_per_share is None:
            print("未能找到 BTC per Share 数据")

            # 保存页面内容到文件
            debug_file = "strategy_page_debug.html"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"已将页面内容保存到 {debug_file} 供调试")
            except Exception as e:
                print(f"保存页面内容时出错: {e}")

            print("页面文本预览（前500字符）:")
            try:
                # 处理 Windows GBK 编码问题
                preview = page_text[:500].replace('\n', ' ').replace('\r', '')
                print(preview.encode('utf-8', errors='replace').decode('utf-8'))
            except Exception as e:
                print(f"打印页面内容时出错: {e}")
            print("\n如果需要调试，请检查 strategy.com 的页面结构或查看 strategy_page_debug.html 文件")

        return btc_per_share, 0  # 返回 tuple，debt_cash_adjustment 默认为 0

    except Exception as e:
        print(f"获取 BTC per Share 时出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None

    finally:
        # 如果是新启动的无头浏览器，关闭它
        if driver:
            try:
                if "--headless" in driver.capabilities.get("goog:chromeOptions", {}).get("args", []):
                    driver.quit()
                    print("已关闭新创建的 Chrome 浏览器")
            except:
                pass


def get_price_from_api(symbol):
    """
    使用 Finnhub API 获取价格

    参数:
        symbol: 股票/加密货币代码，如 "MSTR" 或 "BINANCE:BTCUSDT"

    返回:
        float: 价格，失败返回 None
    """
    if not FINNHUB_API_KEY:
        print("警告: 未设置 Finnhub API 密钥")
        return None

    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "error" in data:
            print(f"Finnhub API 错误 ({symbol}): {data['error']}")
            return None

        price = data.get("c")  # 当前价格
        if price is None or price == 0:
            print(f"警告: {symbol} 返回了无效的价格: {price}")
            return None

        return price

    except Exception as e:
        print(f"获取 {symbol} 价格时出错: {e}")
        return None


def calculate_premium(mstr_price, btc_price, btc_per_share, ev_adjustment=0):
    """
    计算 MSTR 相对于其 BTC 持有量的溢价 (同时返回市值溢价和 Enterprise Value 溢价)

    参数:
        mstr_price: MSTR 股票价格
        btc_price: BTC 价格
        btc_per_share: 每股 MSTR 对应的 BTC 数量
        ev_adjustment: (Debt + Pref - Cash) / Shares，用于计算 Enterprise Value

    返回:
        tuple: (market_cap_premium, ev_premium)
            - market_cap_premium: 基于市值的溢价百分比
            - ev_premium: 基于 Enterprise Value 的溢价百分比
    """
    if not all([mstr_price, btc_price, btc_per_share]):
        return None, None

    # 计算每股 MSTR 对应的 BTC 价值
    btc_value_per_share = btc_per_share * btc_price

    # 计算市值溢价 (Market Cap Premium)
    # 市值溢价 = (股价 / BTC价值 per share - 1) × 100%
    market_cap_premium = (mstr_price / btc_value_per_share - 1) * 100

    # 计算 Enterprise Value per share
    # EV_per_share = Stock Price + (Debt + Pref - Cash) / Shares
    ev_per_share = mstr_price + ev_adjustment

    # 计算 EV 溢价 (mNAV): (Enterprise Value per share / BTC价值 per share - 1) × 100%
    ev_premium = (ev_per_share / btc_value_per_share - 1) * 100

    return market_cap_premium, ev_premium


def init_database():
    """
    初始化 SQLite 数据库，创建数据表
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 创建数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mstr_premium (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                mstr_price REAL NOT NULL,
                btc_price REAL NOT NULL,
                btc_per_share REAL NOT NULL,
                market_cap_premium REAL NOT NULL,
                ev_premium REAL NOT NULL,
                ev_adjustment REAL DEFAULT 0
            )
        ''')

        # 创建索引加速查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON mstr_premium(timestamp DESC)
        ''')

        conn.commit()
        conn.close()
        print(f"数据库初始化成功: {DB_FILE}", flush=True)

    except Exception as e:
        print(f"数据库初始化失败: {e}", flush=True)


def save_to_database(timestamp, mstr_price, btc_price, btc_per_share,
                     market_cap_premium, ev_premium, ev_adjustment):
    """
    保存溢价数据到 SQLite 数据库

    参数:
        timestamp: 时间戳
        mstr_price: MSTR 价格
        btc_price: BTC 价格
        btc_per_share: 每股 BTC 数量
        market_cap_premium: 市值溢价百分比
        ev_premium: EV 溢价百分比
        ev_adjustment: EV 调整值
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO mstr_premium
            (timestamp, mstr_price, btc_price, btc_per_share,
             market_cap_premium, ev_premium, ev_adjustment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, mstr_price, btc_price, btc_per_share,
              market_cap_premium, ev_premium, ev_adjustment))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"保存数据到数据库失败: {e}", flush=True)


def update_btc_per_share_periodically():
    """
    后台线程函数，定期更新 BTC per share 数据
    """
    global btc_per_share_global, ev_adjustment_global

    while True:
        try:
            print(f"\n{'='*60}", flush=True)
            print("正在更新 BTC per Share 数据...", flush=True)
            btc_per_share, ev_adjustment = get_btc_per_share_from_strategy()

            if btc_per_share:
                with btc_per_share_lock:
                    btc_per_share_global = btc_per_share
                    ev_adjustment_global = ev_adjustment
                print(f"BTC per Share 更新成功: {btc_per_share:.8f} BTC", flush=True)
                if ev_adjustment != 0:
                    print(f"EV Adjustment: ${ev_adjustment:.2f} per share", flush=True)
            else:
                print("BTC per Share 更新失败，将在下个周期重试", flush=True)

            print(f"{'='*60}\n", flush=True)

        except Exception as e:
            print(f"更新 BTC per Share 时出错: {e}", flush=True)

        # 等待下一个更新周期
        time.sleep(BTC_PER_SHARE_UPDATE_INTERVAL)


def main():
    """
    主函数：协调所有功能，监控 MSTR/BTC 溢价
    """
    global btc_per_share_global, ev_adjustment_global

    print("="*60, flush=True)
    print("MSTR/BTC 溢价监控系统 (Enterprise Value 方法)", flush=True)
    print("="*60, flush=True)
    print(f"数据来源: {STRATEGY_URL}", flush=True)
    print(f"更新间隔: {TICK_INTERVAL} 秒", flush=True)
    print(f"BTC per Share 更新间隔: {BTC_PER_SHARE_UPDATE_INTERVAL} 秒", flush=True)
    print("="*60, flush=True)

    # 初始化数据库
    print("\n初始化数据库...", flush=True)
    init_database()

    # 初始化: 首次获取 BTC per share
    print("初始化：获取 BTC per Share 数据...", flush=True)
    btc_per_share_global, ev_adjustment_global = get_btc_per_share_from_strategy()

    if not btc_per_share_global:
        print("错误: 无法获取 BTC per Share 数据，无法继续", flush=True)
        print("请检查:", flush=True)
        print(f"1. Chrome 浏览器是否在端口 {CHROME_DEBUG_PORT} 运行", flush=True)
        print("2. 网站 strategy.com 是否可访问", flush=True)
        print("3. 网页结构是否发生变化", flush=True)
        return

    print(f"初始化完成! BTC per Share = {btc_per_share_global:.8f} BTC", flush=True)
    if ev_adjustment_global != 0:
        print(f"EV Adjustment = ${ev_adjustment_global:.2f} per share", flush=True)
    print("", flush=True)

    # 启动后台线程定期更新 BTC per share
    update_thread = threading.Thread(target=update_btc_per_share_periodically, daemon=True)
    update_thread.start()
    print("已启动后台更新线程\n", flush=True)

    # 主循环：定期获取价格并计算溢价
    print("开始监控 MSTR/BTC 溢价率...\n", flush=True)

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 获取当前的 BTC per share 和 ev_adjustment（使用锁确保线程安全）
            with btc_per_share_lock:
                current_btc_per_share = btc_per_share_global
                current_ev_adjustment = ev_adjustment_global

            if not current_btc_per_share:
                print(f"{current_time}:: 等待 BTC per Share 数据...", flush=True)
                time.sleep(TICK_INTERVAL)
                continue

            # 使用 API 获取实时价格
            mstr_price = get_price_from_api("MSTR")
            btc_price = get_price_from_api("BINANCE:BTCUSDT")

            # 计算并输出溢价 (同时计算市值溢价和 EV 溢价)
            if mstr_price and btc_price:
                market_cap_premium, ev_premium = calculate_premium(mstr_price, btc_price, current_btc_per_share, current_ev_adjustment)

                if market_cap_premium is not None and ev_premium is not None:
                    # 格式化输出，flush=True 确保立即显示
                    # 显示两种溢价：市值溢价（更直观）和 EV 溢价（考虑债务）
                    print(f"{current_time}:: [MSTR: ${mstr_price:.2f}]||[BTC: ${btc_price:,.2f}]||[市值溢价: {market_cap_premium:.2f}%]||[EV溢价: {ev_premium:.2f}%]", flush=True)

                    # 保存数据到数据库
                    save_to_database(
                        timestamp=current_time,
                        mstr_price=mstr_price,
                        btc_price=btc_price,
                        btc_per_share=current_btc_per_share,
                        market_cap_premium=market_cap_premium,
                        ev_premium=ev_premium,
                        ev_adjustment=current_ev_adjustment
                    )
                else:
                    print(f"{current_time}:: 计算溢价失败", flush=True)
            else:
                # 输出哪些数据获取失败
                missing = []
                if not mstr_price:
                    missing.append("MSTR价格")
                if not btc_price:
                    missing.append("BTC价格")
                print(f"{current_time}:: 无法获取数据: {', '.join(missing)}", flush=True)

        except KeyboardInterrupt:
            print("\n\n收到中断信号，正在退出...", flush=True)
            break

        except Exception as e:
            print(f"主循环出错: {e}", flush=True)
            import traceback
            traceback.print_exc()

        # 等待下一个周期
        time.sleep(TICK_INTERVAL)

    print("\n监控已停止", flush=True)


if __name__ == "__main__":
    main()
