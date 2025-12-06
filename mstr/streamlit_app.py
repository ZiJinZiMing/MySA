# -*- coding: utf-8 -*-
"""
MSTR/BTC 溢价可视化监控
使用 Streamlit 实时展示溢价趋势
"""

import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 配置参数
DB_FILE = "mstr_data.db"
REFRESH_INTERVAL = 2  # 页面刷新间隔（秒）

# 配置页面
st.set_page_config(
    page_title="MSTR/BTC 溢价监控",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def get_data_from_db(hours=24):
    """
    从 SQLite 数据库读取指定时间范围内的数据

    参数:
        hours: 读取最近多少小时的数据，默认24小时

    返回:
        DataFrame: 包含溢价数据的 DataFrame
    """
    try:
        conn = sqlite3.connect(DB_FILE)

        # 计算时间范围
        time_threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        # 查询数据
        query = f"""
            SELECT
                timestamp,
                mstr_price,
                btc_price,
                btc_per_share,
                market_cap_premium,
                ev_premium,
                ev_adjustment
            FROM mstr_premium
            WHERE timestamp >= '{time_threshold}'
            ORDER BY timestamp ASC
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        # 转换时间戳为 datetime 类型
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df

    except Exception as e:
        st.error(f"读取数据库失败: {e}")
        return pd.DataFrame()


def get_latest_data():
    """
    获取最新的一条数据

    返回:
        dict: 最新数据的字典，如果没有数据返回 None
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                timestamp,
                mstr_price,
                btc_price,
                btc_per_share,
                market_cap_premium,
                ev_premium,
                ev_adjustment
            FROM mstr_premium
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'timestamp': row[0],
                'mstr_price': row[1],
                'btc_price': row[2],
                'btc_per_share': row[3],
                'market_cap_premium': row[4],
                'ev_premium': row[5],
                'ev_adjustment': row[6]
            }
        return None

    except Exception as e:
        st.error(f"读取最新数据失败: {e}")
        return None


# 主界面
st.title("📈 MSTR/BTC 溢价实时监控")
st.markdown("---")

# 侧边栏：时间范围选择
with st.sidebar:
    st.header("设置")
    time_range = st.selectbox(
        "时间范围",
        options=[1, 3, 6, 12, 24, 48, 72],
        index=4,  # 默认 24 小时
        format_func=lambda x: f"最近 {x} 小时"
    )

    st.markdown("---")
    st.markdown("### 关于")
    st.markdown("""
    实时监控 MSTR 股票相对于其持有的 BTC 价值的溢价率。

    **两种溢价指标：**
    - **市值溢价**：直接用股价除以每股BTC价值
    - **EV溢价**：考虑债务和现金的企业价值溢价

    数据每10秒更新一次。
    """)

# 创建占位符
metrics_placeholder = st.empty()
chart_placeholder = st.empty()
stats_placeholder = st.empty()

# 主循环：实时刷新
while True:
    # 获取最新数据
    latest = get_latest_data()

    if latest:
        # 显示当前指标
        with metrics_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="MSTR 价格",
                    value=f"${latest['mstr_price']:.2f}"
                )

            with col2:
                st.metric(
                    label="BTC 价格",
                    value=f"${latest['btc_price']:,.2f}"
                )

            with col3:
                # 市值溢价，显示正负颜色
                premium_delta = latest['market_cap_premium']
                st.metric(
                    label="市值溢价",
                    value=f"{premium_delta:.2f}%",
                    delta=f"{premium_delta:.2f}%"
                )

            with col4:
                # EV 溢价
                ev_premium_delta = latest['ev_premium']
                st.metric(
                    label="EV 溢价",
                    value=f"{ev_premium_delta:.2f}%",
                    delta=f"{ev_premium_delta:.2f}%"
                )

        # 获取历史数据
        df = get_data_from_db(hours=time_range)

        if not df.empty:
            # 创建两个独立的折线图
            with chart_placeholder:
                # 计算市值溢价的 Y 轴范围
                market_cap_min = df['market_cap_premium'].min()
                market_cap_max = df['market_cap_premium'].max()
                market_cap_range = market_cap_max - market_cap_min
                market_cap_padding = market_cap_range * 0.1 if market_cap_range > 0 else 1

                # 计算 EV 溢价的 Y 轴范围
                ev_min = df['ev_premium'].min()
                ev_max = df['ev_premium'].max()
                ev_range = ev_max - ev_min
                ev_padding = ev_range * 0.1 if ev_range > 0 else 1

                # 创建子图：两个溢价图表
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=('市值溢价趋势', 'EV溢价趋势'),
                    row_heights=[0.5, 0.5]
                )

                # 第一个子图：市值溢价
                fig.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['market_cap_premium'],
                        name='市值溢价',
                        line=dict(color='#1f77b4', width=3),
                        mode='lines',
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.1)'
                    ),
                    row=1, col=1
                )

                # 添加零线到市值溢价图
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)

                # 第二个子图：EV溢价
                fig.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['ev_premium'],
                        name='EV溢价',
                        line=dict(color='#ff7f0e', width=3),
                        mode='lines',
                        fill='tozeroy',
                        fillcolor='rgba(255, 127, 14, 0.1)'
                    ),
                    row=2, col=1
                )

                # 添加零线到 EV 溢价图
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

                # 更新布局
                fig.update_layout(
                    height=700,
                    showlegend=True,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )

                # 设置 Y 轴标签和范围
                fig.update_yaxes(
                    title_text="溢价率 (%)",
                    range=[market_cap_min - market_cap_padding, market_cap_max + market_cap_padding],
                    row=1, col=1
                )

                fig.update_yaxes(
                    title_text="溢价率 (%)",
                    range=[ev_min - ev_padding, ev_max + ev_padding],
                    row=2, col=1
                )

                # 设置 X 轴标签
                fig.update_xaxes(title_text="时间", row=2, col=1)

                st.plotly_chart(fig)

            # 显示统计信息
            with stats_placeholder:
                st.markdown("### 📊 统计信息")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**市值溢价**")
                    st.write(f"当前: {df['market_cap_premium'].iloc[-1]:.2f}%")
                    st.write(f"平均: {df['market_cap_premium'].mean():.2f}%")
                    st.write(f"最高: {df['market_cap_premium'].max():.2f}%")
                    st.write(f"最低: {df['market_cap_premium'].min():.2f}%")

                with col2:
                    st.markdown("**EV溢价**")
                    st.write(f"当前: {df['ev_premium'].iloc[-1]:.2f}%")
                    st.write(f"平均: {df['ev_premium'].mean():.2f}%")
                    st.write(f"最高: {df['ev_premium'].max():.2f}%")
                    st.write(f"最低: {df['ev_premium'].min():.2f}%")

                with col3:
                    st.markdown("**数据信息**")
                    st.write(f"数据点: {len(df)} 个")
                    st.write(f"最新更新: {latest['timestamp']}")
                    st.write(f"BTC/股: {latest['btc_per_share']:.8f}")
                    if latest['ev_adjustment'] != 0:
                        st.write(f"EV调整: ${latest['ev_adjustment']:.2f}/股")

        else:
            st.info("暂无数据，请等待数据采集...")

    else:
        st.warning("⚠️ 数据库中没有数据，请先运行 mstr_btc.py 开始数据采集")

    # 等待后刷新页面
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
