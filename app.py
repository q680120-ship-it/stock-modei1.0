import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股強勢狙擊手 Pro", layout="wide")

# --- 2. 核心名單 ---
TW_200_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "3231.TW", "2303.TW", "3711.TW",
    "1513.TW", "1519.TW", "1503.TW", "2603.TW", "2609.TW", "2881.TW", "2882.TW", "3017.TW"
] # 可自行補齊

# --- 3. 繪圖功能：恢復 X 軸日期與量價顯示 ---
def plot_advanced_chart(df, name, symbol):
    d = df.tail(60)
    
    # 建立量價子圖
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, row_heights=[0.7, 0.3])

    # 1. K線圖
    fig.add_trace(go.Candlestick(
        x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'],
        name="K線"), row=1, col=1)
    
    # 2. 移動停利線
    fig.add_trace(go.Scatter(
        x=d.index, y=d['Trailing_Stop'], name="停利價",
        line=dict(color='orange', width=2, dash='dash')), row=1, col=1)

    # 3. 成交量 (依漲跌變色)
    colors = ['#EF5350' if close >= open else '#26A69A' for open, close in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(
        x=d.index, y=d['Volume'], name="成交量",
        marker_color=colors), row=2, col=1)

    # 設定佈局與排除假日
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    # 強制顯示底部的 X 軸標籤
    fig.update_xaxes(showticklabels=True, row=2, col=1)
    
    fig.update_layout(
        height=600, template="plotly_dark", xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=20, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# --- 4. 分析核心 ---
@st.cache_data(ttl=3600)
def fetch_and_analyze(symbol, vr, tp):
    try:
        t_obj = yf.Ticker(symbol)
        df = t_obj.history(period="2y")
        if df.empty or len(df) < 150: return None
        
        info = t_obj.info
        name = info.get('longName', symbol).split('Co')[0].split('Inc')[0].strip()
        
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Trailing_Stop'] = df['Close'].rolling(window=22).max() * (1 - tp)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        change = ((last['Close'] - prev['Close']) / prev['Close']) * 100
        
        if last['Close'] < last['Trailing_Stop']: advice = "🔴 避險賣出"
        elif last['Close'] > last['MA200'] and last['Close'] > last['Max20'] and last['Volume'] > last['VMA5'] * vr: advice = "🔥 強力買進"
        elif last['Close'] > last['MA200'] and last['Close'] > last['Max20']: advice = "⚡ 建議買進"
        elif last['Close'] > last['MA200']: advice = "🔵 持股觀察"
        else: advice = "⚪ 觀望等待"
            
        return {"df": df, "name": name, "advice": advice, "stop": last['Trailing_Stop'], "change": change}
    except: return None

# --- 5. UI 介面 ---
st.title("🏹 台股強勢狙擊終端")

with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_mult = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, 0.1)
    exit_pct = st.slider("移動停利 (%)", 5, 20, 10, 1) / 100
    target = st.text_input("分析代碼", "2330.TW").upper()

res = fetch_and_analyze(target, vol_mult, exit_pct)
if res:
    # 這裡就是你要的「每日價格」面板
    st.subheader(f"📊 {res['name']} ({target})")
    
    m1, m2, m3, m4 = st.columns(4)
    curr_price = res['df']['Close'].iloc[-
