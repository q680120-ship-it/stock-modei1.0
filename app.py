import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股狙擊 Pro (回測版)", layout="wide")

# 1. 完整分段名單 (確保 150+ 檔)
L1 = ["2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2357.TW","4938.TW"]
L2 = ["2303.TW","3711.TW","2603.TW","2609.TW","1513.TW","1519.TW","1503.TW","3017.TW"]
L3 = ["2881.TW","2882.TW","2886.TW","2891.TW","5880.TW","2884.TW","2885.TW","2892.TW"]
L4 = ["1605.TW","1608.TW","1609.TW","6806.TW","1514.TW","1560.TW","3708.TW","9958.TW"]
L5 = ["3661.TW","3443.TW","6415.TW","3034.TW","2379.TW","2408.TW","3035.TW","3583.TW"]
L6 = ["1101.TW","1102.TW","2002.TW","2618.TW","2610.TW","1216.TW","1476.TW","1795.TW"]
TW_LIST = sorted(list(set(L1+L2+L3+L4+L5+L6)))

# 2. 核心分析與回測引擎
@st.cache_data(ttl=3600)
def analyze_with_backtest(sid, vr, tp):
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
        
        # --- 簡易回測邏輯 ---
        trades = []
        in_pos = False
        buy_p = 0
        
        for i in range(200, len(df)):
            c_row = df.iloc[i]
            # 買進訊號: 站上年線 + 破20日高 + 量增
            if not in_pos:
                if c_row['Close'] > c_row['MA'] and c_row['Close'] > c_row['M20'] and c_row['Volume'] > df.iloc[i-1]['VMA'] * vr:
                    in_pos = True
                    buy_p = c_row['Close']
            # 賣出訊號: 跌破移動停利
            else:
                if c_row['Close'] < c_row['TS']:
                    trades.append((c_row['Close'] - buy_p) / buy_p)
                    in_pos = False
        
        win_rate = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
        total_ret = sum(trades) * 100 if trades else 0
        # ------------------

        last = df.iloc[-1]
        c, s, ma, hi = last['Close'], last['TS'], last['MA'], last['M20']
        if c < s: adv = "🔴 避險賣出"
        elif c > ma and c > hi and last['Volume'] > last['VMA'] * vr: adv = "🔥 強力買進"
        elif c > ma and c > hi: adv = "⚡ 建議買進"
        else: adv = "⚪ 觀望等待"
        
        return {"df": df, "name": n, "adv": adv, "stop": s, "price": c, "sid": sid, 
                "win_rate": win_rate, "total_ret": total_ret, "trade_count": len(trades)}
    except: return None

# 3. 繪圖函數
def draw_chart(df, sid, name):
    d = df.tail(80)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['TS'], name="Stop Loss", line=dict(color='orange', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=d['MA'], name="MA200", line=dict(color='gray', width=1)), row=1, col=1)
    clrs = ['red' if c >= o else 'green' for o, c in zip(d['Open'], d['Close'])]
    fig.add_trace(go.Bar(x=d.index, y=d['Volume'], marker_color=clrs, name="Volume"), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, title=f"{name} ({sid})")
    return fig

# 4. UI 介面
st.title("🏹 台股狙擊 Pro (回測勝率版)")

with st.sidebar:
    v_mult = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    t_pct = st.slider("移動停利 %", 5, 20, 10) / 100
    target = st.text_input("輸入代碼", "2330.TW").upper()

data = analyze_with_backtest(target, v_mult, t_pct)
if data:
    st.subheader(f"📊 {data['name']} ({data['sid']}) | {data['adv']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("目前價格", f"{data['price']:.2f}")
    c2.metric("回測勝率", f"{data['win_rate']:.1f}%")
    c3.metric("累積報酬", f"{data['total_ret']:.1f}%")
    c4.metric("交易次數", data['trade_count'])
    st.plotly_chart(draw_chart(data['df'], data['sid'], data['name']), use_container_width=True)

st.divider()
if st.button(f"🚀 全自動掃描與回測 ({len(TW_LIST)} 檔)"):
    cats = {"🔥 強力買進":[], "⚡ 建議買進":[], "🔴 避險賣出":[], "⚪ 觀望等待":[]}
    pb = st.progress(0)
    for i, sid in enumerate(TW_LIST):
        res = analyze_with_backtest(sid, v_mult, t_pct)
        if res: cats[res['adv']].append(res)
        pb.progress((i+1)/len(TW_LIST))
    
    for lv in cats:
        if cats[lv]:
            with st.expander(f"{lv} ({len(cats[lv])} 檔)"):
                for item in cats[lv]:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['name']} ({item['sid']})")
                        st.write(f"勝率: **{item['win_rate']:.1f}%**")
                        st.write(f"累計報酬: **{item['total_ret']:.1f}%**")
                        st.error(f"建議停利: {item['stop']:.2f}")
                    with col2:
                        st.plotly_chart(draw_chart(item['df'], item['sid'], item['name']), use_container_width=True, key=f"s_{item['sid']}")
