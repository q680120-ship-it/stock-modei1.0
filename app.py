import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 強制關閉所有可能導致衝突的自動更新
st.set_page_config(page_title="台股波段狙擊手", layout="wide")

# --- 核心數據函數 ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_data(symbol):
    try:
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=730)), progress=False)
        if df.empty or len(df) < 200: return None
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Exit'] = df['Close'].rolling(window=20).max() * 0.9 # 固定10%停利
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * 1.5)
        return df
    except: return None

# --- UI 渲染 ---
st.title("📈 投資決策系統")

ticker = st.sidebar.text_input("代碼", "2330.TW")

df = get_data(ticker)

if df is not None:
    # 使用簡單的 Markdown 代替 Metric 組件（減少 Node 衝突）
    last_p = df['Close'].iloc[-1]
    st.write(f"### 當前價格: {last_p:.2f} | 停利點: {df['Exit'].iloc[-1]:.2f}")
    
    if df['Entry'].iloc[-1]:
        st.success("🔥 今日符合進場訊號")

    # 單一圖表渲染
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="股價"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Exit'], name="停利線", line=dict(color='orange')))
    
    entries = df[df['Entry']]
    if not entries.empty:
        fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', 
                                 marker=dict(symbol='star', size=10, color='gold'), name="進場點"))
    
    fig.update_layout(height=500, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True, key="main_chart") # 加入唯一 key

else:
    st.error("請檢查代碼格式")
