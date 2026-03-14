import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股波段狙擊手 Pro", layout="wide", initial_sidebar_state="expanded")

# 自定義 CSS
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4250; }
    </style>
    """, unsafe_allow_html=True)

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
        # 下載數據
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=500)), progress=False)
        
        if df.empty or len(df) < 200:
            return None
            
        # 處理新版 yfinance 多層索引問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.astype(float)
        
        # 指標計算
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        
        # 邏輯判斷
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * v_ratio)
        df['Exit_Line'] = df['Close'].rolling(window=22).max() * (1 - t_pct)
        
        return df
    except Exception:
        return None

# --- 4. 畫面渲染 ---
df = get_pro_data(ticker, vol_ratio, trailing_pct)

if df is not None:
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    st.title(f"🚀 {ticker} 投資決策終端")
    
    # 指標卡
    m1, m2, m3, m4 = st.columns(4)
    price_diff = last_row['Close'] - prev_row['Close']
    m1.metric("當前股價", f"{last_row['Close']:.2f}", f"{price_diff:.
