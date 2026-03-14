import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 1. 基礎配置
st.set_page_config(page_title="台股狙擊 Pro", layout="wide")

# 2. 核心 200 檔名單 (節錄範例)
TW_LIST = [
    "2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2881.TW","2882.TW",
    "2303.TW","3711.TW","2603.TW","2609.TW","1513.TW","1519.TW","2357.TW","3034.TW",
    "2379.TW","2408.TW","4938.TW","2347.TW","1504.TW","1514.TW","2618.TW","3017.TW"
]

# 3. 繪圖函數
def draw_chart(df, name):
    d = df.tail(60)
    f = go.Figure(data=[go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="K線")])
    f.add_trace(go.Scatter(x=d.index, y=d['MA200'], name="年線", line=dict(color='white', width=1)))
    f.update_layout(height=300, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=30,b=10), title=name)
    return f

# 4. 分析邏輯
@st.cache_data(ttl=3600)
def analyze(sid, vr, tp):
    try:
        t = yf.Ticker(sid)
        df = t.history(period="2y")
        if df.empty or len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 中文名稱清理
        raw_name = t.info.get('longName', sid)
        name = raw_name.split('Co')[0].split('Inc')[0].strip()
        
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Stop'] = df['Close'].rolling(22).max() * (1 - tp)
        
        last = df.iloc[-1]
        c, m, v, x, s = last['Close'], last['MA200'], last['Volume'], last['VMA5'], last['Stop']
        hi20 = last['Max20']
        
        # 五大評等
        if c < s: adv = "🔴 避險賣出"
        elif c > m and c > hi20 and v > x * vr: adv = "🔥 強力買進"
        elif c > m and c > hi20: adv = "⚡ 建議買進"
        elif c > m: adv = "🔵 持股觀察"
        else: adv = "⚪ 觀望等待"
        
        return {"df": df, "name": name, "adv": adv, "stop": s}
    except: return None

# 5. UI 介面
with st.sidebar:
    st.header("⚙️ 設定")
    v_m = st.slider("量爆發倍數", 1.0, 3.0, 1.5)
    e_p = st.slider("停利 %", 5, 20, 10) / 100
    target = st.text_input("查代碼", "2330.TW").upper()

st.title("🏹 台股強勢狙擊系統")

# 個股分析
res = analyze(target, v_m, e_p)
if res:
    st.subheader(f"{res['name']} ({target}) ｜ {res['adv']}")
    st.plotly_chart(draw_chart(res['df'], "個股分析"), use_container_width=True)

# 掃描按鈕
st.divider()
if st.button("🚀 執行全市場 200 檔掃描"):
    cats = {"🔥 強力買進":[], "⚡ 建議買進":[], "🔴 避險賣出":[], "🔵 持股觀察":[], "⚪ 觀望等待":[]}
    pb = st.progress(0)
    for i, sid in enumerate(TW_LIST):
        d = analyze(sid, v_m, e_p)
        if d: cats[d['adv']].append(d)
        pb.progress((i+1)/len(TW_LIST))
    
    st.balloons()
    for lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出", "🔵 持股觀察", "⚪ 觀望等待"]:
        if cats[lv]:
            with st.expander(f"{lv} ({len(cats[lv])} 檔)", expanded=(lv in ["🔥 強力買進", "⚡ 建議買進"])):
                for item in cats[lv]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['name']}")
                        st.write(f"代碼: {item['df'].index[-1].strftime('%m-%d')}")
                        st.write(f"現價: {item['df']['Close'].iloc[-1]:.1f}")
                    with col2:
                        st.plotly_chart(draw_chart(item['df'], ""), use_container_width=True)
