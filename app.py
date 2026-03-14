import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 基礎設定
st.set_page_config(page_title="台股狙擊 Pro", layout="wide")

# 2. 核心名單
TW_LIST = ["2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2881.TW","2882.TW",
           "2303.TW","3711.TW","2603.TW","2609.TW","1513.TW","1519.TW","1503.TW","3017.TW"]

# 3. 繪圖函數 (量價合一 + 排除假日)
def draw_chart(df, name):
    d = df.tail(60)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    # K線
    fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="K線"), row=1, col=1)
    # 停利線
    fig.add_trace(go.Scatter(x=d.index, y=d['Trailing_Stop'], name="停利價", line=dict(color='orange', dash='dash')), row=1, col=1)
    # 成交量
    colors = ['red' if c >= o else 'green' for o, c in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(x=d.index, y=d['Volume'], name="成交量", marker_color=colors), row=2, col=1)
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) # 排除假日
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, title=name, margin=dict(t=30, b=10))
    return fig

# 4. 分析邏輯 (五大評等)
@st.cache_data(ttl=3600)
def analyze(sid, vr, tp):
    try:
        t = yf.Ticker(sid)
        df = t.history(period="2y")
        if df.empty or len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 中文名稱清理
        n = t.info.get('longName', sid).split('Co')[0].split('Inc')[0].strip()
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Trailing_Stop'] = df['Close'].rolling(22).max() * (1 - tp)
        
        last = df.iloc[-1]
        c, s, v, ma, hi = last['Close'], last['Trailing_Stop'], last['Volume'], last['MA200'], last['Max20']
        vma = last['VMA5']
        
        # 評等邏輯
        if c < s: adv = "🔴 避險賣出"
        elif c > ma and c > hi and v > vma * vr: adv = "🔥 強力買進"
        elif c > ma and c > hi: adv = "⚡ 建議買進"
        elif c > ma: adv = "🔵 持股觀察"
        else: adv = "⚪ 觀望等待"
        return {"df": df, "name": n, "adv": adv, "stop": s, "price": c}
    except: return None

# 5. UI 介面
st.title("🏹 台股強勢狙擊系統 Pro")
with st.sidebar:
    v_m = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    e_p = st.slider("移動停利 %", 5, 20, 10) / 100
    target = st.text_input("輸入代碼", "2330.TW").upper()

res = analyze(target, v_m, e_p)
if res:
    st.subheader(f"{res['name']} ({target}) | {res['adv']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("目前股價", f"{res['price']:.2f}")
    c2.metric("建議停利價", f"{res['stop']:.2f}")
    c3.info(f"建議策略：{res['adv']}")
    st.plotly_chart(draw_chart(res['df'], ""), use_container_width=True)

st.divider()
if st.button("🚀 啟動 200 檔全自動掃描"):
    cats = {"🔥 強力買進":[], "⚡ 建議買進":[], "🔴 避險賣出":[], "🔵 持股觀察":[], "⚪ 觀望等待":[]}
    pb = st.progress(0)
    for i, sid in enumerate(TW_LIST):
        d = analyze(sid, v_m, e_p)
        if d: cats[d['adv']].append(d)
        pb.progress((i+1)/len(TW_LIST))
    
    for lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出", "🔵 持股觀察", "⚪ 觀望等待"]:
        if cats[lv]:
            with st.expander(f"{level} ({len(cats[lv])} 檔)", expanded=(lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出"])):
                for item in cats[lv]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['name']}")
                        st.metric("現價", f"{item['price']:.2f}")
                        st.error(f"停利價: {item['stop']:.2f}")
                    with col2:
                        st.plotly_chart(draw_chart(item['df'], ""), use_container_width=True)
