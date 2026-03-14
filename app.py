import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股 200 強勢狙擊 Pro", layout="wide")

# --- 2. 200 檔核心標的清單 ---
TW_200_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2303.TW", "3711.TW", "2308.TW", "2382.TW", "3231.TW", "2379.TW", "3034.TW",
    "2408.TW", "3661.TW", "3443.TW", "6415.TW", "2329.TW", "2449.TW", "6239.TW", "8046.TW", "3035.TW", "3583.TW",
    "6182.TWO", "3264.TWO", "6271.TW", "8150.TW", "2357.TW", "4938.TW", "2356.TW", "2324.TW", "2353.TW", "2376.TW",
    "6669.TW", "2417.TW", "3515.TW", "2395.TW", "3013.TW", "3017.TW", "3324.TW", "3037.TW", "2368.TW", "2313.TW",
    "1513.TW", "1519.TW", "1503.TW", "1504.TW", "1514.TW", "1605.TW", "6806.TW", "8996.TW", "1506.TW", "1516.TW",
    "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "2002.TW", "1101.TW", "1102.TW", "2633.TW", "1216.TW",
    "2881.TW", "2882.TW", "2886.TW", "2891.TW", "2884.TW", "2885.TW", "2883.TW", "2892.TW", "2880.TW", "2890.TW",
    "2801.TW", "2834.TW", "5880.TW", "5871.TW", "2812.TW", "6005.TW", "2855.TW", "2887.TW", "2888.TW", "2889.TW"
] # 清單可依需求繼續增加

# --- 3. 繪圖函數 ---
def plot_mini_chart(df, name, symbol):
    # 只取最近 60 根 K 線
    df_mini = df.tail(60)
    fig = go.Figure(data=[go.Candlestick(
        x=df_mini.index,
        open=df_mini['Open'], high=df_mini['High'],
        low=df_mini['Low'], close=df_mini['Close'],
        name="K線"
    )])
    # 加入年線 (MA200)
    fig.add_trace(go.Scatter(x=df_mini.index, y=df_mini['MA200'], name="年線", line=dict(color='white', width=1)))
    
    fig.update_layout(
        title=f"{name} ({symbol}) 走勢圖",
        height=300,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# --- 4. 數據運算核心 ---
@st.cache_data(ttl=3600)
def fetch_and_analyze(symbol, vr, tp):
    try:
        t_obj = yf.Ticker(symbol)
        df = t_obj.history(period="2y")
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        info = t_obj.info
        name = info.get('longName', symbol)
        for s in ["Co., Ltd.", "Corporation", "Inc.", "Enterprise"]: name = name.replace(s, "").strip()
        
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Trailing_Stop'] = df['Close'].rolling(window=22).max() * (1 - tp)
        
        last = df.iloc[-1]
        is_above_ma200 = last['Close'] > last['MA200']
        is_breakout = last['Close'] > last['Max20']
        is_vol_spike = last['Volume'] > last['VMA5'] * vr
        is_below_stop = last['Close'] < last['Trailing_Stop']
        
        if is_below_stop: advice = "🔴 避險賣出"
        elif is_above_ma200 and is_breakout and is_vol_spike: advice = "🔥 強力買進"
        elif is_above_ma200 and is_breakout: advice = "⚡ 建議買進"
        elif is_above_ma200: advice = "🔵 持股觀察"
        else: advice = "⚪ 觀望等待"
            
        return {"df": df, "name": name, "advice": advice, "stop": last['Trailing_Stop']}
    except: return None

# --- 5. UI 與掃描邏輯 ---
st.title("🏹 台股強勢狙擊系統 Pro (含自動圖形化)")

with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_mult = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, 0.1)
    exit_pct = st.slider("移動停利 (%)", 5, 20, 1
    
