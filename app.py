import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股 200 強勢狙擊手 Pro", layout="wide")

# --- 2. 200 檔核心標的清單 (維持不變) ---
TW_200_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "3231.TW", "2881.TW", "2882.TW", "2303.TW", "3711.TW",
    "2412.TW", "2886.TW", "2891.TW", "1216.TW", "2884.TW", "2603.TW", "2609.TW", "1513.TW", "1519.TW", "2618.TW",
    "2357.TW", "3034.TW", "2379.TW", "2408.TW", "4938.TW", "2356.TW", "2324.TW", "2353.TW", "2376.TW", "6669.TW",
    "3017.TW", "3324.TW", "3037.TW", "2368.TW", "2313.TW", "2354.TW", "2451.TW", "2351.TW", "3044.TW", "2421.TW",
    "1503.TW", "1504.TW", "1514.TW", "1605.TW", "6806.TW", "8996.TW", "2615.TW", "2610.TW", "2002.TW", "1101.TW"
    # ... (此處省略部分清單以保持長度，你可以續接上一個版本的清單)
]

# --- 3. 數據運算核心 (含五大評等邏輯) ---
@st.cache_data(ttl=1800)
def fetch_and_analyze(symbol, vr, tp):
    try:
        t_obj = yf.Ticker(symbol)
        df = t_obj.history(period="2y")
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        name = t_obj.info.get('shortName', symbol)
        df = df.astype(float)
        
        # 指標計算
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Trailing_Stop'] = df['Close'].rolling(window=22).max() * (1 - tp)
        
        last = df.iloc[-1]
        
        # 條件變數
        is_above_ma200 = last['Close'] > last['MA200']
        is_breakout = last['Close'] > last['Max20']
        is_vol_spike = last['Volume'] > last['VMA5'] * vr
        is_below_stop = last['Close'] < last['Trailing_Stop']
        
        # --- 五大評等邏輯 ---
        if is_below_stop:
            advice = "🔴 避險賣出"
        elif is_above_ma200 and is_breakout and is_vol_spike:
            advice = "🔥 強力買進"
        elif is_above_ma200 and is_breakout:
            advice = "⚡ 建議買進"
        elif is_above_ma200:
            advice = "🔵 持股觀察"
        else:
            advice = "⚪ 觀望等待"
            
        return {"df": df, "name": name, "advice": advice, "stop": last['Trailing_Stop']}
    except: return None

# --- 4. UI 介面 ---
st.title("🏹 台股強勢狙擊系統 Pro (五大信心評等版)")

with st.sidebar:
    st.header("⚙️ 參數設定")
    vol_mult = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, 0.1)
    exit_pct = st.slider("移動停利 (%)", 5, 20, 10) / 100
    st.divider()
    target = st.text_input("個股代碼分析", "2330.TW").upper()

# 單股詳情
res = fetch_and_analyze(target, vol_mult, exit_pct)
if res:
    st.subheader(f"📊 {res['name']} ({target}) ｜ 當前建議：{res['advice']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("目前價格", f"{res['df']['Close'].iloc[-1]:.2f}")
    c2.metric("防守位", f"{res['stop']:.2f}")
    c3.info(f"評等說明：{res['advice']}")

# --- 5. 市場掃描區 (分類展示) ---
st.divider()
st.header("🔍 全市場掃描 (市值 Top 200)")

if st.button("🚀 執行五大評等全自動掃描", use_container_width=True):
    # 用來分類存儲結果
    categories = {"🔥 強力買進": [], "⚡ 建議買進": [], "🔴 避險賣出": [], "🔵 持股觀察": [], "⚪ 觀望等待": []}
    
    pb = st.progress(0)
    for i, t in enumerate(TW_200_LIST):
        data = fetch_and_analyze(t, vol_mult, exit_pct)
        if data:
            categories[data['advice']].append({
                "公司名稱": data['name'],
                "代碼": t,
                "價格": f"{data['df']['Close'].iloc[-1]:.2f}",
                "漲幅": f"{((data['df']['Close'].iloc[-1]/data['df']['Close'].iloc[-2])-1)*100:.2f}%"
            })
        pb.progress((i+1)/len(TW_200_LIST))
    
    # 分類顯示表格
    for level, stocks in categories.items():
        if stocks:
            st.subheader(f"{level} ({len(stocks)} 檔)")
            st.table(pd.DataFrame(stocks))

    st.balloons()
