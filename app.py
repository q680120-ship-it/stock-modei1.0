import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面配置
st.set_page_config(page_title="台股 120 狙擊終端 Pro", layout="wide")

# 2. 完整 120 檔名單
ALL_SYMBOLS = [
    "2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW",
    "2303.TW","3711.TW","2379.TW","3034.TW","2408.TW","3661.TW","3443.TW","6415.TW","3035.TW","3583.TW",
    "3017.TW","3324.TW","3037.TW","8046.TW","2368.TW","2313.TW","2421.TW","3515.TW","2351.TW","6213.TW",
    "1513.TW","1519.TW","1503.TW","1504.TW","1514.TW","1605.TW","1608.TW","1609.TW","6806.TW","8996.TW",
    "1517.TW","1560.TW","3708.TW","6443.TWO","6477.TW","1506.TW","1522.TW","9958.TW","1516.TW","1589.TW",
    "2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2633.TW","2637.TW","2606.TW","2201.TW","2204.TW",
    "2002.TW","2014.TW","2006.TW","2031.TW","2027.TW","1101.TW","1102.TW","2105.TW","1301.TW","1303.TW",
    "2881.TW","2882.TW","2886.TW","2891.TW","2884.TW","2885.TW","2883.TW","2892.TW","2880.TW","2890.TW",
    "2801.TW","2834.TW","5880.TW","5871.TW","2812.TW","6005.TW","2855.TW","2887.TW","2888.TW","2889.TW",
    "1216.TW","1476.TW","1477.TW","1717.TW","1722.TW","1795.TW","2707.TW","2912.TW","8454.TW","9921.TW",
    "3131.TWO","3529.TWO","3680.TWO","6488.TWO","3105.TWO","6188.TWO","3376.TW","8069.TWO","3293.TWO","5483.TWO",
    "3008.TW","3406.TW","3481.TW","2409.TW","2344.TW","5347.TWO","5434.TW","6202.TW","6285.TW","8016.TW"
]

# 3. 繪圖核心函數
def draw_chart(df, sid):
    try:
        d = df.tail(100)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        # K線
        fig.add_trace(go.Candlestick(x=d.index, open=d['Open'], high=d['High'], low=d['Low'], close=d['Close'], name="K線"), row=1, col=1)
        # 停利線
        fig.add_trace(go.Scatter(x=d.index, y=d['TS'], name="停利價", line=dict(color='orange', width=2, dash='dash')), row=1, col=1)
        # 年線
        fig.add_trace(go.Scatter(x=d.index, y=d['MA200'], name="MA200", line=dict(color='rgba(255,255,255,0.4)', width=1)), row=1, col=1)
        # 成交量
        clrs = ['#EF5350' if c >= o else '#26A69A' for o, c in zip(d['Open'], d['Close'])]
        fig.add_trace(go.Bar(x=d.index, y=d['Volume'], marker_color=clrs, name="成交量"), row=2, col=1)
        
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=20, b=20, l=10, r=10))
        return fig
    except Exception as e:
        st.error(f"繪圖出錯: {e}")
        return None

# 4. 分析引擎
def analyze(sid, df, vr, tp, rsi_m):
    try:
        if df.empty or len(df) < 150: return None
        df = df.copy().astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['M20'] = df['Close'].shift(1).rolling(20).max()
        df['VMA'] = df['Volume'].rolling(5).mean()
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['TS'] = df['Close'].rolling(22).max() * (1 - tp)
        
        # 勝率回測
        trades = []
        in_pos, buy_p = False, 0
        c, ts, ma, hi, vol, vma, rsi = df['Close'].values, df['TS'].values, df['MA200'].values, df['M20'].values, df['Volume'].values, df['VMA'].values, df['RSI'].values
        
        for i in range(200, len(df)):
            if not in_pos:
                if c[i] > ma[i] and c[i] > hi[i] and vol[i] > vma[i-1] * vr and rsi[i] > rsi_m:
                    in_pos, buy_p = True, c[i]
            elif c[i] < ts[i]:
                trades.append((c[i] - buy_p) / buy_p)
                in_pos = False
        
        win = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0
        ret = sum(trades) * 100 if trades else 0
        last = df.iloc[-1]
        
        if last['Close'] < last['TS']: adv = "🔴 避險減碼"
        elif last['Close'] > last['MA200'] and last['Close'] > last['M20'] and last['RSI'] > rsi_m: adv = "🔥 強力噴發"
        elif last['Close'] > last['MA200']: adv = "🔵 偏多觀察"
        else: adv = "⚪ 觀望整理"
        
        return {"df": df, "sid": sid, "adv": adv, "win": win, "ret": ret, "price": last['Close'], "stop": last['TS']}
    except: return None

# 5. UI 介面
st.title("🏹 台股 120 狙擊終端 Pro")

with st.sidebar:
    st.header("⚙️ 狙擊濾網")
    rsi_val = st.slider("RSI 動能門檻", 40, 70, 55)
    v_m = st.slider("爆量倍數", 1.0, 3.0, 1.3)
    t_p = st.slider("停利 %", 5, 20, 10) / 100
    target = st.text_input("搜尋代碼", "2330.TW").upper()

# 單股搜尋區
if target:
    with st.spinner("抓取數據中..."):
        s_data = yf.download(target, period="2y", multi_level_index=False)
        res = analyze(target, s_data, v_m, t_p, rsi_val)
        if res:
            st.subheader(f"📊 {target} | 狀態: {res['adv']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("價格", f"{res['price']:.1f}")
            c2.metric("回測勝率", f"{res['win']:.1f}%")
            c3.metric("累計報酬", f"{res['ret']:.1f}%")
            fig = draw_chart(res['df'], target)
            if fig: st.plotly_chart(fig, use_container_width=True, key=f"main_{target}")

st.divider()

# 掃描區
if st.button("🚀 啟動 120 檔快速掃描"):
    with st.spinner("批量下載數據中..."):
        # 修正批量抓取逻辑，改用較穩定的下載方式
        raw = yf.download(ALL_SYMBOLS, period="2y", group_by='ticker')
    
    cats = {"🔥 強力噴發":[], "🔵 偏多觀察":[], "🔴 避險減碼":[], "⚪ 觀望整理":[]}
    pb = st.progress(0)
    
    for i, sid in enumerate(ALL_SYMBOLS):
        try:
            # 兼容單股與多股 DataFrame 結構
            temp_df = raw[sid] if len(ALL_SYMBOLS) > 1 else raw
            r = analyze(sid, temp_df, v_m, t_p, rsi_val)
            if r: cats[r['adv']].append(r)
        except: pass
        pb.progress((i+1)/len(ALL_SYMBOLS))
    
    for lv, items in cats.items():
        if items:
            with st.expander(f"{lv} ({len(items)} 檔)", expanded=(lv == "🔥 強力噴發")):
                for item in items:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"### {item['sid']}")
                        st.write(f"勝率: **{item['win']:.1f}%** | 報酬: **{item['ret']:.1f}%**")
                        st.metric("現價", f"{item['price']:.1f}", delta=f"停利 {item['stop']:.1f}")
                    with col2:
                        f = draw_chart(item['df'], item['sid'])
                        if f: st.plotly_chart(f, use_container_width=True, key=f"scan_{item['sid']}")
