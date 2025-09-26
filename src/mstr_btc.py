import yfinance as yf
import requests
import time
import random
import os
from datetime import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def get_btc_per_share():
    """
    从saylortracker.com网站获取MSTR的每股BTC数量
    
    返回:
    float: 每股MSTR对应的BTC数量
    """
    try:
        # 尝试连接到已运行的Chrome浏览器实例
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到Chrome浏览器...")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("成功连接到Chrome浏览器")
        except Exception as e:
            print(f"连接Chrome浏览器失败: {e}")
            print("尝试启动新的Chrome浏览器实例...")
            
            # 如果连接失败，启动新的浏览器实例
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式，不显示浏览器窗口
            driver = webdriver.Chrome(options=chrome_options)
            print("成功启动新的Chrome浏览器实例")
        
        # 访问网站
        url = "https://saylortracker.com/?tab=home"
        print(f"正在访问网站: {url}")
        driver.get(url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        print("页面加载完成")
        
        # 等待一段时间确保动态内容加载
        time.sleep(20)
        
        # 获取页面文本内容
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print("获取页面内容成功")
        except Exception as e:
            print(f"获取页面文本时出错: {e}")
            # 尝试获取页面源码并解析
            page_source = driver.page_source
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            page_text = soup.get_text()
            print("使用BeautifulSoup获取页面文本")
        
        # 查找Sats Per Basic Share信息（新的页面结构）
        sats_per_share = None
        match = re.search(r"Sats Per Basic Share\s*([0-9,]+)", page_text, re.DOTALL)
        if match:
            sats_str = match.group(1).replace(",", "")
            sats_per_share = int(sats_str)
            # 将sats转换为BTC (1 BTC = 100,000,000 sats)
            btc_per_share = sats_per_share / 100000000
            print(f"找到Sats Per Basic Share: {sats_per_share:,} sats")
            print(f"转换为BTC per Share: {btc_per_share:.8f} BTC")
            
            # 关闭新创建的浏览器（如果是新创建的）
            try:
                if driver.capabilities.get("chrome", {}).get("chromedriverArgs"):
                    if "--headless" in " ".join(driver.capabilities["chrome"]["chromedriverArgs"]):
                        driver.quit()
                        print("已关闭新创建的Chrome浏览器")
            except:
                pass
            
            return btc_per_share
        
        # 备用方法：查找BTC Holdings和Basic Shares来计算
        btc_holdings_match = re.search(r"₿([0-9,]+)", page_text)
        basic_shares_match = re.search(r"([0-9.]+)M\s*285", page_text)  # 查找类似"285.88M"的模式
        
        if btc_holdings_match and basic_shares_match:
            btc_holdings = float(btc_holdings_match.group(1).replace(",", ""))
            basic_shares_millions = float(basic_shares_match.group(1))
            basic_shares = basic_shares_millions * 1000000  # 转换为实际股数
            
            btc_per_share = btc_holdings / basic_shares
            print(f"备用方法 - BTC Holdings: ₿{btc_holdings:,.0f}")
            print(f"备用方法 - Basic Shares: {basic_shares:,.0f}")
            print(f"备用方法 - BTC per Share: {btc_per_share:.8f}")
            
            # 关闭新创建的浏览器（如果是新创建的）
            try:
                if driver.capabilities.get("chrome", {}).get("chromedriverArgs"):
                    if "--headless" in " ".join(driver.capabilities["chrome"]["chromedriverArgs"]):
                        driver.quit()
                        print("已关闭新创建的Chrome浏览器")
            except:
                pass
            
            return btc_per_share
        
        print("未能找到BTC per Share相关信息")
        print("页面内容预览（前1000字符）:")
        print(page_text[:1000])
        
        # 关闭新创建的浏览器（如果是新创建的）
        try:
            if driver.capabilities.get("chrome", {}).get("chromedriverArgs"):
                if "--headless" in " ".join(driver.capabilities["chrome"]["chromedriverArgs"]):
                    driver.quit()
                    print("已关闭新创建的Chrome浏览器")
        except:
            pass
        
        return None
    
    except Exception as e:
        print(f"获取BTC per Share时出错: {e}")
        return None

# 配置API密钥（可以通过环境变量设置，或直接在此处填写）
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "cn1l421r01qvjam26j60cn1l421r01qvjam26j6g")  # 替换为你的Finnhub API密钥


def get_ticker_price_finnhub(ticker="MSTR"):
    """
    使用Finnhub API获取MSTR价格（首选方法）
    """
    if not FINNHUB_API_KEY:
        print("警告: 未设置Finnhub API密钥")
        return None

    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "error" in data:
            print(f"Finnhub API错误: {data['error']}")
            return None

        price = data["c"]  # 当前价格
        return price
    except Exception as e:
        print(f"Finnhub获取MSTR价格时出错: {e}")
        return None


def get_mstr_price_finnhub():
    """
    使用Finnhub API获取MSTR价格（首选方法）
    """
    if not FINNHUB_API_KEY:
        print("警告: 未设置Finnhub API密钥")
        return None
        
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol=MSTR&token={FINNHUB_API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "error" in data:
            print(f"Finnhub API错误: {data['error']}")
            return None
            
        price = data["c"]  # 当前价格
        return price
    except Exception as e:
        print(f"Finnhub获取MSTR价格时出错: {e}")
        return None




def get_btc_price_coingecko():
    """
    使用CoinGecko API获取比特币(BTC)的价格
    """
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd'
        response = requests.get(url)
        price = response.json()['bitcoin']['usd']
        return price
    except Exception as e:
        print(f"CoinGecko获取BTC价格时出错: {e}")
        return None

def get_btc_price_coinapi():
    """
    使用CoinAPI获取BTC价格
    """
    try:
        # 这里需要替换为你的CoinAPI密钥
        api_key = ""  # 需要替换为你的API密钥
        if not api_key:
            return None
            
        url = 'https://rest.coinapi.io/v1/exchangerate/BTC/USD'
        headers = {'X-CoinAPI-Key': api_key}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if "error" in data:
            print(f"CoinAPI错误: {data['error']}")
            return None
            
        price = data["rate"]
        return price
    except Exception as e:
        print(f"CoinAPI获取BTC价格时出错: {e}")
        return None

def calculate_premium(mstr_price, btc_price, btc_per_share):
    """
    计算MSTR相对于其BTC持有量的溢价
    
    参数:
    mstr_price: MSTR股票价格
    btc_price: BTC价格
    btc_per_share: 每股MSTR对应的BTC数量
    
    返回:
    premium: 溢价百分比
    """
    # 计算每股MSTR对应的BTC价值
    btc_value_per_share = btc_per_share * btc_price
    
    # 计算溢价
    premium = (mstr_price / btc_value_per_share - 1) * 100
    
    return premium

def main():
    """
    主函数：获取并显示MSTR和BTC的价格，计算溢价
    """
    # 尝试获取最新的BTC_PER_SHARE值
    BTC_PER_SHARE = get_btc_per_share()
    # BTC_PER_SHARE = 0.00207973

    # 查询间隔时间（秒）
    TICK_INTERVAL = 10  # 10秒

    # 显示配置信息
    print("=== MSTR/BTC溢价率监控 ===")
    print(f"参数: 每股MSTR对应BTC数量 = {BTC_PER_SHARE}")
    print(f"数据更新间隔: {TICK_INTERVAL}秒")

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # print(f"\n===== {current_time} =====")
        
        # 获取MSTR价格
        mstr_price = get_ticker_price_finnhub("MSTR")
        # 获取BTC价格
        btc_price = get_ticker_price_finnhub("BINANCE:BTCUSDT")

        # 如果两者都有价格，计算MSTR持有BTC的溢价
        if mstr_price and btc_price:
            premium = calculate_premium(mstr_price, btc_price, BTC_PER_SHARE)
            print(f"{current_time}:: [MSTR: ${mstr_price}]||[BTC: ${btc_price}]||[溢价: {premium:.2f}%]")
        else:
            print("无法计算溢价率，缺少必要数据")
        
        # 随机等待时间，避免被API封锁
        # print(f"{TICK_INTERVAL}秒后更新...")
        time.sleep(TICK_INTERVAL)

if __name__ == "__main__":
    main()



