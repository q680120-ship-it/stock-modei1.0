import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股 200 狙擊 Pro", layout="wide")

# 2. 核心名單 (分更短的組，防止截斷)
L1 = ["2330.TW","2303.TW","2454.TW","3711.TW","2379.TW","3034.TW","2408.TW"]
L2 = ["3661.TW","3443.TW","6415.TW","2329.TW","2449.TW","6239.TW","3035.TW"]
L3 = ["3583.TW","6271.TW","8150.TW","3264.TWO","6182.TWO","6223.TWO","3587.TWO"]
L4 = ["2317.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW"]
L5 = ["2353.TW","2376.TW","6669.TW","2395.TW","3013.TW","3515.TW","2417.TW"]
L6 = ["3017.TW","3324.TW","3037.TW","8046.TW","2368.TW","2313.TW","2421.TW"]
L7 = ["2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2633.TW","2637.TW"]
L8 = ["2002.TW","2014.TW","2006.TW","2031.TW","2027.TW","1101.TW","1102.TW"]
L9 = ["2881.TW","2882.TW","2886.TW","2891.TW","2884.TW","2885.TW","2883.TW"]
L10 = ["2892.TW","2880.TW","2890.TW","2801.TW","2834.TW","5880.TW","5871.TW"]
L11 = ["1216.TW","1476.TW","1477.TW","1717.TW","1722.TW","1795.TW","2105.TW"]
L12 = ["2201.TW","2204.TW","2354.TW","2451.TW","3044.TW","8069.TWO","9921.TW"]

TW_LIST = sorted(list(set(L1+L2+L3+L4+L5+L6+L7+L8+L9+L10+L11+L12)))

# 3. 繪圖函數
def draw_chart(df, name):
    d = df.tail(60)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.1, row_heights=[0.7, 0.3])
    # K線
    fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], 
                                low=d['Low'], close=d['Close'], name="K線"), row=1, col=1)
    # 停利線
    fig.add_trace(go.Scatter(x=d.index, y=d['TS'], name="停利價", 
                             line=dict(color='orange', width=2, dash='dash')), row=1, col=1)
    # 成交量 (紅漲綠跌)
    clrs = ['#EF5350' if c >= o else '#26A69A' for o, c in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(x=d.index, y=d['Volume'], name="成交量", marker_color=clrs), row=2, col=1)
    
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=30, b=20))
    return fig

# 4. 分析核心
@st.cache_data(ttl=3600)
def analyze(sid, vr, tp):
    try:
        t = yf.Ticker(sid)
        df = t.history(period="2y")
        if df.empty or len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        n = t.info.get('longName', sid).split('Co')[0].split('Inc')[0].strip()
        df = df.astype(float)
        df['MA'] = ta.sma(df['Close'], length=200)
        df['VMA'] = df['Volume'].rolling(5).mean()
        df['M20'] = df['Close'].shift(1).rolling(20).max()
        df['TS'] = df['Close'].rolling(22).max() * (1 - tp)
        
        l = df.iloc[-1]
        c, s, v, ma, hi, vma = l['Close'], l['TS'], l['Volume'], l['MA'], l['M20'], l['VMA']
        
        if c < s: adv = "🔴 避險賣出"
        elif c > ma and c > hi and v > vma * vr: adv = "🔥 強力買進"
        elif c > ma and c > hi: adv = "⚡ 建議買進"
        elif c > ma: adv = "🔵 持股觀察"
        else: adv = "⚪ 觀望等待"
        return {"df": df, "name": n, "adv": adv, "stop": s, "price": c, "sid": sid}
    except: return None

# 5. UI
st.title("🏹 台股強勢狙擊終端 Pro")
with st.sidebar:
    st.header("⚙️ 狙擊參數")
    v_m = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, 0.1)
    e_p = st.slider("移動停利 %", 5, 20, 10, 1) / 100
    target = st.text_input("輸入分析代碼", "2330.TW").upper()

res = analyze(target, v_m, e_p)
if res:
    st.subheader(f"{res['name']} ({target}) | {res['adv']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("目前報價", f"{res['price']:.2f}")
    c2.metric("建議停利價", f"{res['stop']:.2f}")
    c3.info(f"評等：{res['adv']}")
    st.plotly_chart(draw_chart(res['df'], ""), use_container_width=True, key=f"m_{target}")

st.divider()
if st.button(f"🚀 啟動掃描 ({len(TW_LIST)} 檔)"):
    cats = {"🔥 強力買進":[], "⚡ 建議買進":[], "🔴 避險賣出":[], "🔵 持股觀察":[], "⚪ 觀望等待":[]}
    pb = st.progress(0)
    for i, sid in enumerate(TW_LIST):
        d = analyze(sid, v_m, e_p)
        if d: cats[d['adv']].append(d)
        pb.progress((i+1)/len(TW_LIST))
    
    st.balloons()
    for lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出", "🔵 持股觀察", "⚪ 觀望等待"]:
        if cats[lv]:
            with st.expander(f"{lv} ({len(cats[lv])} 檔)", expanded=(lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出"])):
                for item in cats[lv]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['name']}")
                        st.metric("現價", f"{item['price']:.2f}")
                        st.error(f"停利價: {item['stop']:.2f}")
                    with col2:
                        st.plotly_chart(draw_chart(item['df'], ""), use_container_width=True, key=f"s_{item['sid']}")
