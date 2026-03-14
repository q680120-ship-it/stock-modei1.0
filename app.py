import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股波段狙擊手 Pro", layout="wide")

# --- 2. 使用容器預留空間 (防止 Node 衝突關鍵) ---
header_container = st.container()
dashboard_container = st.container()
chart_container = st.container()
scanner_container = st.container()

with header_container:
    st.title("🚀 台股高勝率波段狙擊系統")

# --- 3. 側邊欄參數 ---
with st.sidebar:
    st.header("⚙️ 策略參數調整")
    ticker = st.text_input("輸入台股代碼", "2330.TW")
    vol_ratio = st.slider("成交量放大倍數", 1.0, 3.0, 1.5)
    rsi_range = st.slider("RSI 強勢區間", 40, 90, (50, 80))
    trailing_pct = st.slider("移動停利比例 (%)", 5, 20, 10) / 100

# --- 4. 數據運算 ---
@st.cache_data(ttl=3600)
def fetch_data(symbol):
    try:
        # progress=False 減少前端顯示衝突
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=730)), progress=False)
        if df.empty or len(df) < 200: return None
        
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & \
                      (df['Volume'] > df['VMA5'] * vol_ratio) & \
                      (df['RSI'] >= rsi_range[0]) & (df['RSI'] <= rsi_range[1])
        df['Exit'] = df['Close'].rolling(window=20).max() * (1 - trailing_pct)
        return df
    except: return None

# --- 5. 渲染與顯示 ---
df = fetch_data(ticker)

if df is not None:
    with dashboard_container:
        last_close = float(df['Close'].iloc[-1])
        last_exit = float(df['Exit'].iloc[-1])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"{last_close:.2f}")
        c2.metric("移動停利價", f"{last_exit:.2f}", delta=f"{last_close - last_exit:.2f}")
        c3.metric("進場狀態", "🔥 出現訊號" if df['Entry'].iloc[-1] else "監控中")

    with chart_container:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="收盤價"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="200MA (年線)", line=dict(dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Exit'], name="移動停利線", line=dict(color='orange')), row=1, col=1)
        
        entries = df[df['Entry']]
        fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', 
                                 marker=dict(symbol='star', size=10, color='gold'), name="進場點"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with scanner_container:
        st.markdown("### 🔍 市場強勢股雷達")
        if st.button("啟動全市場掃描"):
            watch_list = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2308.TW", "2603.TW"]
            matches = []
            with st.spinner("掃描中..."):
                for t in watch_list:
                    t_df = fetch_data(t)
                    if t_df is not None and t_df['Entry'].iloc[-1]:
                        matches.append(t)
            if matches:
                st.success(f"⚡ 符合條件：{', '.join(matches)}")
            else:
                st.info("暫無符合標的。")
else:
    st.error("代碼錯誤或資料不足")
