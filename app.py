import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股波段狙擊手", layout="wide")
st.title("📈 台股高勝率投資決策模型")

# --- 側邊欄參數設定 ---
st.sidebar.header("⚙️ 策略參數")
ticker = st.sidebar.text_input("輸入台股代碼 (例如: 2330.TW)", "2330.TW")
vol_ratio = st.sidebar.slider("成交量放大倍數", 1.2, 3.0, 1.5)
rsi_limit = st.sidebar.slider("RSI 過熱警戒線", 70, 90, 80)
trailing_pct = st.sidebar.slider("移動停利比例 (%)", 5, 20, 10) / 100

# --- 資料處理核心 ---
@st.cache_data(ttl=3600)
def fetch_and_process(symbol):
    try:
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=730)), progress=False)
        if df.empty or len(df) < 200: return None
        
        # 指標計算
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        
        # 進場與移動停利邏輯
        df['Entry_Signal'] = (
            (df['Close'] > df['Max20']) & 
            (df['Close'] > df['MA200']) & 
            (df['Volume'] > df['VMA5'] * vol_ratio) &
            (df['RSI'] > 50) & (df['RSI'] < rsi_limit)
        )
        df['Exit_Price'] = df['Close'].rolling(window=20).max() * (1 - trailing_pct)
        return df
    except:
        return None

# --- 執行模型 ---
df = fetch_and_process(ticker)

if df is not None:
    curr_price = float(df['Close'].iloc[-1])
    exit_price = float(df['Exit_Price'].iloc[-1])
    
    # 1. 關鍵數據顯示 (改用 columns 穩定佈局)
    cols = st.columns(3)
    cols[0].metric("當前價格", f"{curr_price:.2f}")
    cols[1].metric("移動停損價", f"{exit_price:.2f}")
    cols[2].metric("訊號狀態", "🔥 進場" if df['Entry_Signal'].iloc[-1] else "等待")

    # 2. 警示區域
    if curr_price < exit_price:
        st.error(f"⚠️ 建議賣出：價格跌破移動停利點 ({exit_price:.2f})")

    # 3. 繪圖 (Plotly)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="收盤價"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Exit_Price'], name="停利線", line=dict(color='orange')))
    
    entries = df[df['Entry_Signal']]
    fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', 
                             marker=dict(symbol='triangle-up', size=12, color='red'), name="進場點"))
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4. 掃描功能 (優化穩定性)
    st.divider()
    if st.button("點擊掃描熱門股訊號"):
        watch_list = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2308.TW"]
        matches = []
        with st.spinner('掃描中...'):
            for t in watch_list:
                t_df = fetch_and_process(t)
                if t_df is not None and t_df['Entry_Signal'].iloc[-1]:
                    matches.append(t)
        
        if matches:
            st.success(f"今日訊號：{', '.join(matches)}")
        else:
            st.info("今日暫無符合條件標的。")
else:
    st.warning("查無資料，請確認代碼（例如: 2330.TW）")
