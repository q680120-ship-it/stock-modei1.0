import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. 頁面配置 ---
st.set_page_config(page_title="台股波段狙擊手 Pro", layout="wide", initial_sidebar_state="expanded")

# 自定義 CSS 讓介面更精緻
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4250; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄參數 ---
with st.sidebar:
    st.title("🎯 策略核心")
    ticker = st.text_input("股票代碼", "2330.TW").upper()
    st.divider()
    vol_ratio = st.slider("成交量爆發倍數", 1.0, 3.0, 1.5, help="當日量大於5日均量的幾倍")
    trailing_pct = st.slider("移動停利範圍 (%)", 5, 20, 10) / 100
    st.caption("建議：大盤多頭設 10-15%，震盪市設 5-8%")

# --- 3. 數據抓取與運算 ---
@st.cache_data(ttl=3600)
def get_pro_data(symbol):
    try:
        df = yf.download(symbol, start=(datetime.now() - timedelta(days=500)), progress=False)
        if df.empty or len(df) < 200: return None
        
        # 技術指標計算
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VMA5'] = df['Volume'].rolling(5).mean()
        df['Max20'] = df['Close'].shift(1).rolling(20).max()
        
        # 策略邏輯
        df['Entry'] = (df['Close'] > df['Max20']) & (df['Close'] > df['MA200']) & (df['Volume'] > df['VMA5'] * vol_ratio)
        df['Exit_Line'] = df['Close'].rolling(window=22).max() * (1 - trailing_pct)
        return df
    except: return None

# --- 4. 主畫面佈局 ---
df = get_pro_data(ticker)

if df is not None:
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 頂部狀態列
    st.title(f"🚀 {ticker} 投資決策終端")
    
    m1, m2, m3, m4 = st.columns(4)
    price_diff = last_row['Close'] - prev_row['Close']
    m1.metric("當前股價", f"{last_row['Close']:.2f}", f"{price_diff:.2f}")
    m2.metric("RSI (14)", f"{last_row['RSI']:.1f}", delta_color="off")
    m3.metric("防守停利價", f"{last_row['Exit_Line']:.2f}")
    
    status = "🔴 賣出避險" if last_row['Close'] < last_row['Exit_Line'] else ("🔥 強勢進場" if last_row['Entry'] else "🔵 觀望持股")
    m4.metric("策略建議", status)

    # 分頁系統
    tab1, tab2 = st.tabs(["📊 交互式 K 線圖表", "📋 策略詳細數據"])
    
    with tab1:
        # 建立專業 K 線圖
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # K 線圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="年線 (200MA)", line=dict(color='white', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Exit_Line'], name="移動停利線", line=dict(color='orange', dash='dash')), row=1, col=1)
        
        # 進場訊號標註
        entries = df[df['Entry']]
        fig.add_trace(go.Scatter(x=entries.index, y=entries['Close'], mode='markers', 
                                 marker=dict(symbol='triangle-up', size=12, color='lime'), name="進場訊號"), row=1, col=1)
        
        # 成交量
        colors = ['red' if df['Open'].iloc[i] > df['Close'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=colors, opacity=0.5), row=2, col=1)
        
        fig.update_layout(height=700, template="plotly_dark", showlegend=True, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.dataframe(df.tail(10).style.highlight_max(axis=0, color='#2e3344'), use_container_width=True)
        st.info(f"💡 策略提示：當股價收盤跌破橘色虛線 ({last_row['Exit_Line']:.2f})，應果斷執行賣出動作以保護利潤。")

    # 全市場掃描
    st.divider()
    if st.button("🔍 啟動全市場強勢股掃描"):
        with st.spinner("正在分析熱門股..."):
            watch = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2603.TW", "2609.TW", "1513.TW"]
            hits = []
            for t in watch:
                tdf = get_pro_data(t)
                if tdf is not None and tdf['Entry'].iloc[-1]:
                    hits.append(t)
            
            if hits:
                st.balloons()
                st.success(f"⚡ 今日出現進場訊號：{', '.join(hits)}")
            else:
                st.info("今日監控清單暫無強勢突破訊號。")
else:
    st.error("代碼錯誤或資料庫連線中，請檢查後重試。")
