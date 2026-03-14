import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 1. 配置
st.set_page_config(page_title="台股波段 Pro", layout="wide")

# 2. 側邊欄
with st.sidebar:
    st.title("🎯 策略參數")
    ticker = st.text_input("代碼", "2330.TW").upper()
    v_ratio = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5)
    t_pct = st.slider("移動停利 (%)", 5, 20, 10) / 100

# 3. 數據運算
@st.cache_data(ttl=3600)
def get_data(symbol, vr, tp):
    try:
        df = yf.download(symbol, start=(datetime.now()-timedelta(days=500)), progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * vr)
        df['Exit'] = df['Close'].rolling(window=22).max() * (1 - tp)
        return df
    except: return None

# 4. 主畫面
df = get_data(ticker, v_ratio, t_pct)

if df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    st.title(f"🚀 {ticker} 決策終端")
    
    # 指標卡
    c1, c2, c3, c4 = st.columns(4)
    diff = float(last['Close'] - prev['Close'])
    c1.metric("價格", f"{last['Close']:.2f}", f"{diff:.2f}")
    c2.metric("RSI", f"{last['RSI']:.1f}")
    c3.metric("停利價", f"{last['Exit']:.2f}")
    
    if last['Close'] < last['Exit']: c4.error("🔴 建議賣出")
    elif last['Entry']: c4.success("🔥 強勢進場")
    else: c4.info("🔵 觀望持股")

    # 圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="年線", line=dict(color='white')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Exit'], name="停利線", line=dict(color='orange', dash='dash')), row=1, col=1)
    
    ent = df[df['Entry']]
    fig.add_trace(go.Scatter(x=ent.index, y=ent['Close'], mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name="進場"), row=1, col=1)
    
    colors = ['red' if df['Open'].iloc[i] > df['Close'].iloc[i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="量", marker_color=colors), row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 掃描
    st.divider()
    if st.button("🔍 掃描強勢股"):
        watch = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2603.TW", "2609.TW", "1513.TW"]
        hits = [t for t in watch if (td := get_data(t, v_ratio, t_pct)) is not None and td['Entry'].iloc[-1]]
        if hits:
            st.balloons()
            st.success(f"⚡ 訊號現蹤: {', '.join(hits)}")
        else: st.info("目前無訊號")
else:
    st.error("❌ 無法獲取資料，請檢查代碼。")
