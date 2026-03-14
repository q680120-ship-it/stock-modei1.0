import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股波段狙擊手 Pro", layout="wide", initial_sidebar_state="expanded")

# --- 2. 側邊欄 ---
with st.sidebar:
    st.title("🎯 策略核心")
    ticker = st.text_input("股票代碼 (例: 2330.TW)", "2330.TW").upper()
    st.divider()
    vol_ratio = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    trailing_pct = st.slider("移動停利範圍 (%)", 5, 20, 10) / 100

# --- 3. 數據運算函數 ---
@st.cache_data(ttl=3600)
def get_pro_data(symbol, v_ratio, t_pct):
    try:
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=500)), progress=False)
        if df.empty or len(df) < 200:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * v_ratio)
        df['Exit_Line'] = df['Close'].rolling(window=22).max() * (1 - t_pct)
        return df
    except:
        return None

# --- 4. 畫面渲染 ---
df = get_pro_data(ticker, vol_ratio, trailing_pct)

if df is not None:
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    st.title(f"🚀 {ticker} 投資決策終端")
    
    # --- 指標卡 (修復這部分) ---
    m1, m2, m3, m4 = st.columns(4)
    price_diff = float(last_row['Close'] - prev_row['Close'])
    
    m1.metric("當前股價", f"{last_row['Close']:.2f}", f"{price_diff:.2f}")
    m2.metric("RSI (14)", f"{last_row['RSI']:.1f}")
    m3.metric("防守停利價", f"{last_row['Exit_Line']:.2f}")
    
    if last_row['Close'] < last_row['Exit_Line']:
        m4.error("🔴 建議：賣出避險")
    elif last_row['Entry']:
        m4.success("🔥 建議：強勢進場")
    else:
        m4.info("🔵 建議：觀望持股")

    # --- 圖表 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="年線", line=dict(color='white', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Exit_Line'], name="停利線", line=dict(color='orange', dash='dash')), row=1, col=1)
    
    entries = df[df['Entry']]
    fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name="進場訊號"), row=1, col=1)
    
    bar_colors = ['red' if df['Open'].iloc[i] > df['Close'].iloc[i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交
