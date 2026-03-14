import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股狙擊 Pro - 勝率強化版", layout="wide")

# 1. 精選 120 檔名單
ALL_SYMBOLS = [
    "2330.TW","2317.TW","2454.TW","2308.TW","2382.TW","3231.TW","2357.TW","4938.TW","2356.TW","2324.TW",
    "2303.TW","3711.TW","2379.TW","3034.TW","2408.TW","3661.TW","3443.TW","6415.TW","3035.TW","3583.TW",
    "3017.TW","3324.TW","3037.TW","8046.TW","2368.TW","2313.TW","2421.TW","3515.TW","2351.TW","6213.TW",
    "1513.TW","1519.TW","1503.TW","1504.TW","1514.TW","1605.TW","1608.TW","1609.TW","6806.TW","8996.TW",
    "2603.TW","2609.TW","2615.TW","2618.TW","2610.TW","2002.TW","2881.TW","2882.TW","2886.TW","2891.TW",
    "3131.TWO","3529.TWO","3680.TWO","6488.TWO","3105.TWO","8069.TWO","3293.TWO","5483.TWO","3008.TW","3406.TW"
] # 縮減示範名單以確保速度，你可以自行補齊至 120 檔

# 2. 核心分析引擎 (加入 RSI 與動能過濾)
def process_data_pro(sid, df_full, vr, tp, rsi_limit):
    try:
        df = df_full[sid].copy().dropna()
        if len(df) < 150: return None
        
        # 技術指標計算
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Donchian_High'] = df['Close'].shift(1).rolling(20).max()
        df['TS'] = df['Close'].rolling(22).max() * (1 - tp)
        
        # 回測邏輯
        trades = []
        in_pos, buy_p = False, 0
        c, ts, ma200, hi, vol, vma, rsi = df['Close'].values, df['TS'].values, df['MA200'].values, df['Donchian_High'].values, df['Volume'].values, df['VMA5'].values, df['RSI'].values
        
        for i in range(200, len(df)):
            if not in_pos:
                # 強化過濾條件：1.站上年線 2.破20日高 3.量增 4.RSI強勢
                if c[i] > ma200[i] and c[i] > hi[i] and vol[i] > vma[i-1] * vr and rsi[i] > rsi_limit:
                    in_pos, buy_p = True, c[i]
            elif c[i] < ts[i]:
                trades.append((c[i] - buy_p) / buy_p)
                in_pos = False
        
        last = df.iloc[-1]
        win_rate = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0
        total_ret = sum(trades) * 100 if trades else 0
        
        # 評等邏輯
        if last['Close'] < last['TS']: adv = "🔴 減碼避險"
        elif last['Close'] > last['MA200'] and last['Close'] > last['Donchian_High'] and last['RSI'] > rsi_limit: adv = "🔥 強力噴發"
        elif last['Close'] > last['MA200'] and last['Close'] > last['MA20']: adv = "🔵 趨勢偏多"
        else: adv = "⚪ 橫盤整理"

        return {"df": df, "adv": adv, "stop": last['TS'], "price": last['Close'], "sid": sid, "win": win_rate, "ret": total_ret}
    except: return None

# 3. UI
st.title("🏹 台股狙擊 Pro - 勝率強化版")
with st.sidebar:
    st.header("🛡️ 進階濾網")
    rsi_val = st.slider("RSI 動能門檻 (建議 > 55)", 40, 70, 55)
    v_m = st.slider("成交量爆發倍數", 1.0, 3.0, 1.3)
    t_p = st.slider("移動停利 %", 5, 20, 10) / 100
    target = st.text_input("搜尋代碼", "2330.TW").upper()

# 單股詳情
if target:
    df_single = yf.download(target, period="2y", multi_level_index=False)
    if not df_single.empty:
        d = process_data_pro(target, {target: df_single}, v_m, t_p, rsi_val)
        if d:
            st.subheader(f"📊 {target} | 狀態: {d['adv']} (勝率: {d['win']:.1f}%)")
            cols = st.columns(4)
            cols[0].metric("現價", f"{d['price']:.1f}")
            cols[1].metric("累積報酬", f"{d['ret']:.1f}%")
            cols[2].metric("建議停利", f"{d['stop']:.1f}")
            cols[3].metric("RSI", f"{d['df']['RSI'].iloc[-1]:.1f}")
            
            # 繪圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=d['df'].tail(100).index, open=d['df'].tail(100)['Open'], high=d['df'].tail(100)['High'], low=d['df'].tail(100)['Low'], close=d['df'].tail(100)['Close'], name="K線"), 1, 1)
            fig.add_trace(go.Scatter(x=d['df'].tail(100).index, y=d['df'].tail(100)['TS'], name="移動停利", line=dict(color='orange', dash='dash')), 1, 1)
            fig.add_trace(go.Scatter(x=d['df'].tail(100).index, y=d['df'].tail(100)['MA200'], name="年線", line=dict(color='white', width=1)), 1, 1)
            fig.add_trace(go.Bar(x=d['df'].tail(100).index, y=d['df'].tail(100)['Volume'], name="成交量"), 2, 1)
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# 掃描
if st.button(f"🚀 啟動 120 檔強化掃描"):
    with st.spinner('批量獲取數據中...'):
        raw = yf.download(ALL_SYMBOLS, period="2y", group_by='ticker', multi_level_index=True)
    
    cats = {"🔥 強力噴發":[], "🔵 趨勢偏多":[], "🔴 減碼避險":[], "⚪ 橫盤整理":[]}
    pb = st.progress(0)
    for i, sid in enumerate(ALL_SYMBOLS):
        res = process_data_pro(sid, raw, v_m, t_p, rsi_val)
        if res: cats[res['adv']].append(res)
        pb.progress((i+1)/len(ALL_SYMBOLS))
    
    for lv, items in cats.items():
        if items:
            with st.expander(f"{lv} ({len(items)} 檔)"):
                # 按報酬率排序顯示
                sorted_items = sorted(items, key=lambda x: x['ret'], reverse=True)
                for item in sorted_items:
                    st.write(f"**{item['sid']}** | 勝率: {item['win']:.1f}% | 總報酬: {item['ret']:.1f}% | 停利價: {item['stop']:.1f}")
