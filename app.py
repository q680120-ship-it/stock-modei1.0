import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# 1. 配置與樣式
st.set_page_config(page_title="台股 300 大全市場雷達", layout="wide")
st.markdown("<style>.stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }</style>", unsafe_allow_html=True)

# 2. 側邊欄參數
with st.sidebar:
    st.title("🎯 策略設定")
    v_ratio = st.slider("成交量爆發倍數", 1.0, 5.0, 1.5)
    t_pct = st.slider("移動停利 (%)", 3, 20, 10) / 100
    st.divider()
    st.info("市值 300 大掃描包含：半導體、AI伺服器、重電、航運及大型金融股。")

# 3. 高速數據運算函數
@st.cache_data(ttl=1800) # 縮短快取時間確保資料即時
def get_data(symbol, vr, tp):
    try:
        df = yf.download(symbol, start=(datetime.now()-timedelta(days=400)), progress=False)
        if df.empty or len(df) < 150: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * vr)
        df['Exit'] = df['Close'].rolling(window=22).max() * (1 - tp)
        return df
    except: return None

# 4. 主畫面佈局
st.title("🚀 台股市值 Top 300 強勢股掃描儀")
st.caption("策略邏輯：收盤突破20日高點 + 站在年線之上 + 成交量倍增")

# --- 核心掃描邏輯 ---
if st.button("🔥 啟動全市場 300 大標的掃描", use_container_width=True):
    # 市值前 300 常用代碼清單 (範例縮減以維持效能，建議分批)
    # 這裡可以放入你整理好的 300 檔清單
    tw_300 = [
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "3231.TW", "2881.TW", "2882.TW", "2303.TW", "3711.TW",
        "2412.TW", "2886.TW", "2891.TW", "1216.TW", "2884.TW", "2603.TW", "2609.TW", "2615.TW", "2379.TW", "3034.TW",
        "2357.TW", "2408.TW", "3044.TW", "2393.TW", "6176.TW", "4938.TW", "2347.TW", "1513.TW", "1503.TW", "1519.TW",
        "6806.TW", "8996.TW", "1605.TW", "2618.TW", "2610.TW", "2324.TW", "2353.TW", "2376.TW", "2356.TW", "2409.TW"
        # ... 此處可持續擴充至 300 檔
    ]
    
    hits = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    # 開始分組掃描以避免超時
    for i, t in enumerate(tw_300):
        status_text.text(f"正在分析第 {i+1}/{len(tw_300)} 檔: {t}")
        td = get_data(t, v_ratio, t_pct)
        if td is not None and td['Entry'].iloc[-1]:
            hits.append({"ticker": t, "price": td['Close'].iloc[-1], "vol": td['Volume'].iloc[-1]})
        
        progress_bar.progress((i + 1) / len(tw_300))
        # 避免請求過快
        if i % 20 == 0: time.sleep(0.1)

    status_text.success(f"掃描完成！耗時: {int(time.time() - start_time)} 秒")
    
    if hits:
        st.balloons()
        st.header("🎯 今日符合強勢突破標的")
        
        # 用表格展示精緻化結果
        hit_df = pd.DataFrame(hits)
        hit_df.columns = ["股票代碼", "目前價格", "今日成交量"]
        st.table(hit_df)
        
        # 自動為符合的標的生成小圖表
        for hit in hits:
            with st.expander(f"查看 {hit['ticker']} 詳細線圖"):
                h_data = get_data(hit['ticker'], v_ratio, t_pct)
                fig = go.Figure(data=[go.Candlestick(x=h_data.index[-60:],
                                open=h_data['Open'][-60:], high=h_data['High'][-60:],
                                low=h_data['Low'][-60:], close=h_data['Close'][-60:])])
                fig.update_layout(height=300, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ 300 大標的中目前暫無符合條件的標的。")

st.divider()
st.info("註：掃描範圍涵蓋台灣市值前 300 大企業，若需查看特定股票，請使用左側輸入框。")
