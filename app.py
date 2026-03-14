import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股強勢狙擊手 Pro", layout="wide")

# --- 2. 核心名單 (200 檔標的節錄) ---
TW_200_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2303.TW", "3711.TW", "2308.TW", "2382.TW", "3231.TW", "2379.TW", "3034.TW",
    "2408.TW", "3661.TW", "3443.TW", "6415.TW", "2329.TW", "2449.TW", "6239.TW", "8046.TW", "3035.TW", "3583.TW",
    "6182.TWO", "3264.TWO", "6271.TW", "8150.TW", "2357.TW", "4938.TW", "2356.TW", "2324.TW", "2353.TW", "2376.TW",
    "1513.TW", "1519.TW", "1503.TW", "2603.TW", "2609.TW", "2881.TW", "2882.TW", "3017.TW", "3324.TW", "3037.TW"
] + [f"{i}.TW" for i in ["2618", "2610", "1605", "6806", "1216", "2886", "2891", "2105"]]

# --- 3. 繪圖功能：量價合一 + 排除假日 ---
def plot_advanced_chart(df, name, symbol):
    d = df.tail(60) # 取最近 60 根 K 線
    
    # 建立量價子圖 (行1: K線, 行2: 成交量)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # 1. K線圖
    fig.add_trace(go.Candlestick(
        x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'],
        name="K線"), row=1, col=1)
    
    # 2. 移動停利線 (橘色虛線)
    fig.add_trace(go.Scatter(
        x=d.index, y=d['Trailing_Stop'], name="停利價",
        line=dict(color='orange', width=2, dash='dash')), row=1, col=1)

    # 3. 年線 MA200 (白色實線)
    fig.add_trace(go.Scatter(
        x=d.index, y=d['MA200'], name="年線",
        line=dict(color='white', width=1)), row=1, col=1)

    # 4. 成交量柱狀圖 (根據漲跌變色)
    colors = ['red' if close >= open else 'green' for open, close in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(
        x=d.index, y=d['Volume'], name="成交量",
        marker_color=colors, opacity=0.7), row=2, col=1)

    # 設定佈局與排除假日
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) # 拿掉週六週日
    fig.update_layout(
        title=f"{name} ({symbol}) - 建議停利價：{d['Trailing_Stop'].iloc[-1]:.2f}",
        height=500, template="plotly_dark", xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- 4. 數據運算核心 ---
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
        c, s = last['Close'], last['Trailing_Stop']
        
        if c < s: advice = "🔴 避險賣出"
        elif c > last['MA200'] and c > last['Max20'] and last['Volume'] > last['VMA5'] * vr: advice = "🔥 強力買進"
        elif c > last['MA200'] and c > last['Max20']: advice = "⚡ 建議買進"
        elif c > last['MA200']: advice = "🔵 持股觀察"
        else: advice = "⚪ 觀望等待"
            
        return {"df": df, "name": name, "advice": advice, "stop": s}
    except: return None

# --- 5. UI 與掃描 ---
st.title("🏹 台股強勢狙擊終端 (量價 & 停利版)")

with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_mult = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, 0.1)
    exit_pct = st.slider("移動停利 (%)", 5, 20, 10, 1) / 100
    st.divider()
    target = st.text_input("分析代碼", "2330.TW").upper()

# 單股詳情
res = fetch_and_analyze(target, vol_mult, exit_pct)
if res:
    st.subheader(f"📊 {res['name']} ({target}) ｜ 狀態：{res['advice']}")
    st.write(f"📢 **今日建議停利/防守價：{res['stop']:.2f}** (跌破此價位即觸發賣出訊號)")
    st.plotly_chart(plot_advanced_chart(res['df'], res['name'], target), use_container_width=True)

# 掃描區
st.divider()
if st.button("🚀 執行 200 檔量價掃描", use_container_width=True):
    cats = {"🔥 強力買進": [], "⚡ 建議買進": [], "🔴 避險賣出": [], "🔵 持股觀察": [], "⚪ 觀望等待": []}
    pb = st.progress(0)
    for i, t in enumerate(TW_200_LIST):
        data = fetch_and_analyze(t, vol_mult, exit_pct)
        if data: cats[data['advice']].append(data)
        pb.progress((i+1)/len(TW_200_LIST))
    
    st.balloons()
    for level in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出", "🔵 持股觀察", "⚪ 觀望等待"]:
        if cats[level]:
            with st.expander(f"{level} ({len(cats[level])} 檔)", expanded=(level in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出"])):
                for s in cats[level]:
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.write(f"### {s['name']}")
                        st.metric("目前價格", f"{s['df']['Close'].iloc[-1]:.2f}")
                        st.error(f"停利價: {s['stop']:.2f}")
                    with c2:
                        st.plotly_chart(plot_advanced_chart(s['df'], "", ""), use_container_width=True)
