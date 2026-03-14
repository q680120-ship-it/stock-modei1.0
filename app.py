import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股波段狙擊手 Pro", layout="wide", initial_sidebar_state="expanded")

# 自定義 CSS 優化介面
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4250; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄參數 ---
with st.sidebar:
    st.title("🎯 策略核心")
    ticker = st.text_input("股票代碼 (例: 2330.TW)", "2330.TW").upper()
    st.divider()
    vol_ratio = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    trailing_pct = st.slider("移動停利範圍 (%)", 5, 20, 10) / 100
    st.caption("💡 提示：若出現紅框報價錯誤，請嘗試在代碼後加上 .TW")

# --- 3. 核心數據函數 (含新版 yfinance 修正) ---
@st.cache_data(ttl=3600)
def get_pro_data(symbol, v_ratio, t_pct):
    try:
        # 下載資料
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=500)), progress=False)
        
        if df.empty or len(df) < 200:
            return None
            
        # 修正新版 yfinance 可能產生的多層索引 (MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns
            
