import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股 120 狙擊終端 Pro", layout="wide")

# 2. 精選 120 檔名單 (分組編排防止截斷)
G1 = ["2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW"]
G2 = ["2303.TW","3711.TW","2379.TW","3034.TW","2408.TW","3661.TW","3443.TW","6415.TW","3035.TW","3583.TW"]
G3 = ["3017.TW","3324.TW","3037.TW","8046.TW","2368.TW","2313.TW","2421.TW","3515.TW","2351.TW","6213.TW"]
G4 = ["1513.TW","1519.TW","1503.TW","1504.TW","1514.TW","1605.TW","1608.TW","1609.TW","6806.TW","8996.TW"]
G5 = ["1517.TW","1560.TW","3708.TW","6443.TWO","6477.TW","1506.TW","1522.TW","9958.TW","1516.TW","1589.TW"]
G6 = ["2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2633.TW","2637.TW","2606.TW","2201.TW","2204.TW"]
G7 = ["2002.TW","2014.TW","2006.TW","2031.TW","2027.TW","1101.TW","1102.TW","2105.TW","1301.TW","1303.TW"]
G8 = ["2881.TW","2882.TW","2886.TW","2891.TW","2884.TW","2885.TW","2883.TW","2892.TW","2880.TW","2890.TW"]
G9 = ["2801.TW","2834.TW","5880.TW","5871.TW","2812.TW","6005.TW","2855.TW","2887.TW","2888.TW","2889.TW"]
G10 = ["1216.TW","1476.TW","1477.TW","1717.TW","1722.TW","1795.TW","2707.TW","2912.TW","8454.TW","9921.TW"]
G11 = ["3131.TWO","3529.TWO","3680.TWO","6488.TWO","3105.TWO","6188.TWO","3376.TW","8069.TWO","3293.TWO","5483.TWO"]
G12 = ["3008.TW","3406.TW","3481.TW","2409.TW","2344.TW","5347.TWO","5434.TW","6202.TW","6285.TW","8016.TW"]

TW_LIST = sorted(list(set(G1+G2+G3+G4+G5+G6+G7+G8+G9+G10+G11+G12)))

# 3. 分析與回測引擎
@st.cache_data(ttl=3600)
def analyze_data(sid, vr, tp):
    try:
        t = yf.Ticker(sid)
        df = t.history(period="2y")
        if df.empty or len(df) < 150: return None
        n = t.info.get('longName') or t.info.get('shortName') or sid
        n = n.split('Co')[0].split('Inc')[0].strip()
        
        df = df.astype(float)
        df['MA'] = ta.sma(df['Close'], length=200)
        df['VMA'] = df['Volume'].rolling(5).mean()
        df['M20'] = df['Close'].shift(1).rolling(20).max()
        df['TS'] = df['Close'].rolling(22).max() * (1 - tp)
        
        # 簡易回測
        trades = []
        in_pos, buy_p = False, 0
        for i in range(200, len(df)):
            r = df.iloc[i]
            if not in_pos:
                if r['Close'] > r['MA'] and r['Close'] > r['M20'] and r['Volume'] > df.iloc[i-1]['VMA'] * vr:
                    in_pos, buy_p = True, r['Close']
            else:
                if r['Close'] < r['TS']:
                    trades.append((r['Close'] - buy_p) / buy_p)
                    in_pos = False
        
        win_rate = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0
        total_ret = sum(trades) * 100 if trades else 0
        
        last = df.iloc[-1]
        c, s, ma, hi, v, vma = last['Close'], last['TS'], last['MA'], last['M20'], last['Volume'], last['VMA']
        
        if c < s: adv = "🔴 避險賣出"
        elif c > ma and c > hi and v > vma * vr: adv = "🔥 強力買進"
        elif c > ma and c > hi: adv = "⚡ 建議買進"
        elif c > ma: adv = "🔵 持股觀察"
        else: adv = "⚪ 觀望等待"
        
        return {"df": df, "name": n, "adv": adv, "stop": s, "price": c, "sid": sid, 
                "win": win_rate, "ret": total_ret, "cnt": len(trades)}
    except: return None

# 4. 繪圖
def draw_chart(df, sid, name):
    d = df.tail(80)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="K線"), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d['TS'], name="停利線", line=dict(color='orange', dash='dash')), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d['MA'], name="年線", line=dict(color='white', width=1, opacity=0.5)), 1, 1)
    clrs = ['red' if c >= o else 'green' for o, c in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(x=d.index, y=d['Volume'], marker_color=clrs, name="成交量"), 2, 1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, title=f"{name} ({sid})")
    return fig

# 5. UI
st.title("🏹 台股 120 狙擊終端 Pro")

with st.sidebar:
    st.header("⚙️ 參數設定")
    v_m = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    t_p = st.slider("移動停利 %", 5, 20, 10) / 100
    target = st.text_input("搜尋代碼", "2330.TW").upper()

d = analyze_data(target, v_m, t_p)
if d:
    st.subheader(f"📊 {d['name']} ({d['sid']}) | {d['adv']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("目前價格", f"{d['price']:.2f}")
    c2.metric("回測勝率", f"{d['win']:.1f}%")
    c3.metric("累積報酬", f"{d['ret']:.1f}%")
    c4.metric("交易次數", d['cnt'])
    st.plotly_chart(draw_chart(d['df'], d['sid'], d['name']), use_container_width=True)

st.divider()
if st.button(f"🚀 啟動 120 檔全量掃描"):
    cats = {"🔥 強力買進":[], "⚡ 建議買進":[], "🔴 避險賣出":[], "🔵 持股觀察":[], "⚪ 觀望等待":[]}
    pb = st.progress(0)
    for i, sid in enumerate(TW_LIST):
        res = analyze_data(sid, v_m, t_p)
        if res: cats[res['adv']].append(res)
        pb.progress((i+1)/len(TW_LIST))
    
    for lv in ["🔥 強力買進", "⚡ 建議買進", "🔴 避險賣出", "🔵 持股觀察", "⚪ 觀望等待"]:
        if cats[lv]:
            with st.expander(f"{lv} ({len(cats[lv])} 檔)", expanded=(lv in ["🔥 強力買進", "⚡ 建議買進"])):
                for item in cats[lv]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['name']} ({item['sid']})")
                        st.write(f"勝率: **{item['win']:.1f}%** | 報酬: **{item['ret']:.1f}%**")
                        st.metric("現價", f"{item['price']:.2f}", delta=f"停利:{item['stop']:.1f}")
                    with col2:
                        st.plotly_chart(draw_chart(item['df'], item['sid'], item['name']), use_container_width=True, key=f"s_{item['sid']}")
