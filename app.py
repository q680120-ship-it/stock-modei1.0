import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股波段狙擊手", layout="wide")
st.title("📈 台股高勝率投資決策模型")
st.markdown("本模型採用 **[強勢突破 + 籌碼過濾 + 移動停利]** 策略，目標為 60% 以上勝率。")

# --- 側邊欄參數設定 ---
st.sidebar.header("⚙️ 策略參數")
ticker = st.sidebar.text_input("輸入台股代碼 (例如: 2330.TW)", "2330.TW")
vol_ratio = st.sidebar.slider("成交量放大倍數", 1.2, 3.0, 1.5)
rsi_limit = st.sidebar.slider("RSI 過熱警戒線", 70, 90, 80)
trailing_pct = st.sidebar.slider("移動停利比例 (%)", 5, 20, 10) / 100

# --- 資料處理核心 ---
@st.cache_data(ttl=3600)
def fetch_and_process(symbol):
    # 抓取過去兩年的數據
    df = yf.download(symbol, start=(datetime.now() - timedelta(days=730)))
    if df.empty: return None
    
    # 計算技術指標
    df['MA20'] = ta.sma(df['Close'], length=20)
    df['MA200'] = ta.sma(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['VMA5'] = df['Volume'].rolling(5).mean()
    df['Max20'] = df['Close'].shift(1).rolling(20).max()
    
    # 【進場邏輯】
    df['Entry_Signal'] = (
        (df['Close'] > df['Max20']) & 
        (df['Close'] > df['MA200']) & 
        (df['Volume'] > df['VMA5'] * vol_ratio) &
        (df['RSI'] > 50) & (df['RSI'] < rsi_limit)
    )
    
    # 【移動停利邏輯】(高點回落)
    df['Exit_Price'] = df['Close'].rolling(window=20).max() * (1 - trailing_pct)
    return df

# --- 執行模型與繪圖 ---
df = fetch_and_process(ticker)

if df is not None:
    curr_price = float(df['Close'].iloc[-1])
    curr_rsi = float(df['RSI'].iloc[-1])
    exit_price = float(df['Exit_Price'].iloc[-1])
    
    # 1. 數據摘要指標
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("當前價格", f"{curr_price:.2f}")
    c2.metric("RSI 指標", f"{curr_rsi:.1f}")
    c3.metric("移動停損價", f"{exit_price:.2f}")
    c4.metric("進場訊號", "🔥 符合" if df['Entry_Signal'].iloc[-1] else "等待")

    # 2. 警示通知
    if df['Entry_Signal'].iloc[-1]:
        st.success(f"🔥 **進場訊號觸發**：{ticker} 今日量價齊揚，符合突破條件！")
    if curr_price < exit_price:
        st.error(f"⚠️ **獲利了結警示**：價格低於移動停利點 ({exit_price:.2f})，建議賣出。")

    # 3. 互動式 Plotly 圖表
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="收盤價"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="200MA (年線)", line=dict(dash='dot', color='gray')))
    fig.add_trace(go.Scatter(x=df.index, y=df['Exit_Price'], name="移動停利線", line=dict(color='orange')))
    
    # 標註歷史進場點
    entries = df[df['Entry_Signal']]
    fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', 
                             marker=dict(symbol='triangle-up', size=12, color='red'), name="進場訊號"))
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. 自動選股雷達按鈕
    if st.button("掃描今日熱門股訊號"):
        watch_list = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2308.TW"]
        matches = []
        for t in watch_list:
            temp_df = fetch_and_process(t)
            if temp_df is not None and temp_df['Entry_Signal'].iloc[-1]:
                matches.append(t)
        if matches:
            st.success(f"今日符合強勢突破標的：{', '.join(matches)}")
        else:
            st.info("熱門股中今日暫無符合條件的標的。")

else:
    st.warning("請輸入正確的台股代碼（需含 .TW 或 .TWO，如 2330.TW）")
