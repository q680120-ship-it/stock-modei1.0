import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股強勢狙擊手 Pro", layout="wide")

# 核心權值股清單 (可自行增加代碼)
TW_300_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "3231.TW", "2881.TW", "2882.TW", 
    "2303.TW", "3711.TW", "2603.TW", "2609.TW", "1513.TW", "1519.TW", "2357.TW", "3034.TW", 
    "2379.TW", "2408.TW", "4938.TW", "2347.TW", "1504.TW", "1514.TW", "2618.TW", "3017.TW"
]

# --- 2. 數據分析核心 ---
@st.cache_data(ttl=1800)
def fetch_and_analyze(symbol, vr, tp):
    try:
        t_obj = yf.Ticker(symbol)
        df = t_obj.history(period="2y")
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        name = t_obj.info.get('shortName', symbol)
        df = df.astype(float)
        
        # 指標：年線、5日量均、20日高點、移動停利線
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Trailing_Stop'] = df['Close'].rolling(window=22).max() * (1 - tp)
        
        last = df.iloc[-1]
        
        # 邏輯條件
        is_above_ma200 = last['Close'] > last['MA200']
        is_breakout = last['Close'] > last['Max20']
        is_vol_spike = last['Volume'] > last['VMA5'] * vr
        
        # 信心評等系統
        if is_above_ma200 and is_breakout and is_vol_spike:
            advice = "🔥 強力買進"
        elif is_above_ma200 and is_breakout:
            advice = "⚡ 建議買進"
        elif last['Close'] < last['Trailing_Stop']:
            advice = "🔴 避險賣出"
        elif is_above_ma200:
            advice = "🔵 持股觀察"
        else:
            advice = "⚪ 觀望等待"
            
        return {"df": df, "name": name, "advice": advice, "stop": last['Trailing_Stop']}
    except: return None

# --- 3. UI 介面 ---
st.title("🏹 台股強勢股狙擊系統")

with st.sidebar:
    st.header("⚙️ 策略參數")
    vol_mult = st.slider("成交量爆發倍數 (濾網)", 1.0, 3.0, 1.5, 0.1)
    exit_pct = st.slider("移動停利範圍 (%)", 5, 20, 10) / 100
    st.divider()
    target = st.text_input("輸入個股代碼分析", "2330.TW").upper()

# --- 4. 個股深度分析 ---
res = fetch_and_analyze(target, vol_mult, exit_pct)
if res:
    df, name, advice = res['df'], res['name'], res['advice']
    st.subheader(f"{name} ({target}) ｜ 當前狀態：{advice}")
    
    col1, col2, col3 = st.columns(3)
    curr_p = df['Close'].iloc[-1]
    col1.metric("目前股價", f"{curr_p:.2f}")
    col2.metric("防守停利價", f"{res['stop']:.2f}")
    col3.write(f"**操作策略：** {advice}")

    # 專業圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="年線", line=dict(color='white', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Trailing_Stop'], name="停利線", line=dict(color='orange', dash='dash')), row=1, col=1)
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 5. 全市場掃描 ---
st.divider()
st.header("🔍 自動掃描潛在買進機會")
if st.button("🚀 啟動全市場強勢股掃描", use_container_width=True):
    hits = []
    progress_bar = st.progress(0)
    for i, t in enumerate(TW_300_LIST):
        data = fetch_and_analyze(t, vol_mult, exit_pct)
        # 只捕捉「買進」訊號標的
        if data and ("買進" in data['advice']):
            hits.append({
                "公司名稱": data['name'],
                "股票代碼": t,
                "建議評等": data['advice'],
                "成交價": f"{data['df']['Close'].iloc[-1]:.2f}",
                "今日漲幅": f"{((data['df']['Close'].iloc[-1]/data['df']['Close'].iloc[-2])-1)*100:.2f}%"
            })
        progress_bar.progress((i+1)/len(TW_300_LIST))
    
    if hits:
        st.balloons()
        st.subheader("🎯 掃描成功！以下為建議進場標的")
        st.table(pd.DataFrame(hits))
    else:
        st.info("目前市場環境中，暫無符合「強力買進」或「建議買進」的標的。")
